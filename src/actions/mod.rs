//  © 2024 Intel Corporation
//  SPDX-License-Identifier: Apache-2.0 and MIT
//! Actions that the DLS can perform: responding to requests, watching files,
//! etc.

use log::{debug, trace, error, warn};
use thiserror::Error;
use crossbeam::channel;
use serde::Deserialize;
use serde_json::json;

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::fs;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use crate::actions::analysis_storage::AnalysisStorage;
use crate::actions::analysis_queue::AnalysisQueue;
use crate::actions::progress::{AnalysisProgressNotifier, ProgressNotifier};
use crate::analysis::structure::expressions::Expression;
use crate::concurrency::{Jobs, ConcurrentJob};
use crate::config::Config;
use crate::file_management::{PathResolver, CanonPath};
use crate::lint::{LintCfg, maybe_parse_lint_cfg};
use crate::lsp_data;
use crate::lsp_data::*;
use crate::server::{Output, ServerToHandle, error_message};
use crate::Span;
use crate::span;
use crate::span::{ZeroIndexed, FilePosition};
use crate::vfs::Vfs;

// Define macros before submodules
macro_rules! parse_file_path {
    ($uri: expr, $log_name: expr) => {
        ignore_non_file_uri!(parse_file_path($uri), $uri, $log_name)
    };
}

// TODO: Support non-`file` URI schemes in VFS. We're currently ignoring them because
// we don't want to crash the DLS in case a client opens a file under different URI scheme
// like with git:/ or perforce:/ (Probably even http:/? We currently don't support remote schemes).
macro_rules! ignore_non_file_uri {
    ($expr: expr, $uri: expr, $log_name: expr) => {
        $expr.map_err(|_| {
            trace!("{}: Non-`file` URI scheme, ignoring: {:?}", $log_name, $uri);
        })
    };
}

pub mod analysis_storage;
pub mod analysis_queue;
pub mod hover;
pub mod notifications;
pub mod requests;
pub mod progress;
pub mod work_pool;

/// Persistent context shared across all requests and notifications.
pub enum ActionContext {
    /// Context after server initialization.
    Init(InitActionContext),
    /// Context before initialization.
    Uninit(UninitActionContext),
}

#[derive(Error, Debug)]
#[error("Initialization error")]
pub struct InitError;

impl From<()> for InitError {
    fn from(_: ()) -> InitError {
        InitError {}
    }
}

impl ActionContext {
    /// Construct a new, uninitialized context.
    pub fn new(
        vfs: Arc<Vfs>,
        config: Arc<Mutex<Config>>,
        notify: channel::Sender<ServerToHandle>,
    ) -> ActionContext {
        ActionContext::Uninit(UninitActionContext::new(
            Arc::new(Mutex::new(AnalysisStorage::init(notify))),
            vfs, config))
    }

    /// Initialize this context, returns `Err(())` if it has already been initialized.
    pub fn init<O: Output>(
        &mut self,
        init_options: InitializationOptions,
        client_capabilities: lsp_data::ClientCapabilities,
        out: O,
    ) -> Result<(), InitError> {
        let ctx = match *self {
            ActionContext::Uninit(ref uninit) => {
                // This means other references to the config will mismatch if
                // we update it, but I am fairly sure they do not exist
                let new_config = init_options.settings.as_ref()
                    .map(|settings|Arc::new(Mutex::new(settings.dml.clone())))
                    .unwrap_or(Arc::clone(&uninit.config));

                let mut ctx = InitActionContext::new(
                    Arc::clone(&uninit.analysis),
                    Arc::clone(&uninit.vfs),
                    new_config,
                    client_capabilities,
                    uninit.pid,
                    init_options.cmd_run,
                );
                ctx.init(init_options, out);
                ctx
            }
            ActionContext::Init(_) => return Err(().into()),
        };
        trace!("Inited context has {:?} as config",
               ctx.config.lock().unwrap());
        *self = ActionContext::Init(ctx);

        Ok(())
    }

    /// Returns an initialiased wrapped context,
    /// or `Err(())` if not initialised.
    pub fn inited(&self) -> Result<InitActionContext, InitError> {
        match *self {
            ActionContext::Uninit(_) => Err(().into()),
            ActionContext::Init(ref ctx) => Ok(ctx.clone()),
        }
    }

    pub fn pid(&self) -> u32 {
        match self {
            ActionContext::Uninit(ctx) => ctx.pid,
            ActionContext::Init(ctx) => ctx.pid,
        }
    }
}

#[derive(Clone, Debug)]
pub struct CompilationDefine {
    pub name: String,
    pub expression: Expression,
}


#[derive(Clone, Debug, Default)]
pub struct CompilationInfo {
    pub extra_defines: Vec<CompilationDefine>,
    pub include_paths: HashSet<PathBuf>,
}

pub type CompilationInfoStorage = HashMap<CanonPath, CompilationInfo>;

/// Persistent context shared across all requests and actions after the DLS has
/// been initialized.
// NOTE: This is sometimes cloned before being passed to a handler
// (not concurrent), so make sure shared info is behind Arcs, and that no overly
// large data structures are stored.
#[derive(Clone)]
pub struct InitActionContext {
    pub analysis: Arc<Mutex<AnalysisStorage>>,
    vfs: Arc<Vfs>,
    // Queues analysis jobs so that we don't over-use the CPU.
    analysis_queue: Arc<AnalysisQueue>,
    current_notifier: Arc<Mutex<Option<String>>>,

    // Set to true when a potentially mutating request is received. Set to false
    // if a change arrives. We can thus tell if the DLS has been quiescent while
    // waiting to mutate the client state.
    pub quiescent: Arc<AtomicBool>,

    // the root workspaces
    pub workspace_roots: Arc<Mutex<Vec<Workspace>>>,

    // directly opened files
    pub direct_opens: Arc<Mutex<HashSet<CanonPath>>>,
    pub pending_direct_results: Arc<AtomicBool>,
    pub compilation_info: Arc<Mutex<CompilationInfoStorage>>,

    prev_changes: Arc<Mutex<HashMap<PathBuf, i32>>>,

    pub config: Arc<Mutex<Config>>,
    pub lint_config: Arc<Mutex<LintCfg>>,
    jobs: Arc<Mutex<Jobs>>,
    pub client_capabilities: Arc<lsp_data::ClientCapabilities>,
    pub has_notified_missing_builtins: bool,
    /// Whether the server is performing cleanup (after having received
    /// 'shutdown' request), just before final 'exit' request.
    pub shut_down: Arc<AtomicBool>,
    pub pid: u32,
}

/// Persistent context shared across all requests and actions before the DLS has
/// been initialized.
pub struct UninitActionContext {
    analysis: Arc<Mutex<AnalysisStorage>>,
    vfs: Arc<Vfs>,
    config: Arc<Mutex<Config>>,
    pid: u32,
}

impl UninitActionContext {
    fn new(
        analysis: Arc<Mutex<AnalysisStorage>>,
        vfs: Arc<Vfs>,
        config: Arc<Mutex<Config>>,
    ) -> UninitActionContext {
        UninitActionContext { analysis, vfs, config, pid: ::std::process::id() }
    }
}

impl InitActionContext {
    fn new(
        analysis: Arc<Mutex<AnalysisStorage>>,
        vfs: Arc<Vfs>,
        config: Arc<Mutex<Config>>,
        client_capabilities: lsp_data::ClientCapabilities,
        pid: u32,
        _client_supports_cmd_run: bool,
    ) -> InitActionContext {
        let lint_config = Arc::new(Mutex::new(
            config.lock().unwrap().lint_cfg_path.clone()
                .and_then(maybe_parse_lint_cfg)
                .unwrap_or_default()));
        InitActionContext {
            vfs,
            analysis,
            analysis_queue: Arc::new(AnalysisQueue::init()),
            current_notifier: Arc::default(),
            config,
            lint_config,
            jobs: Arc::default(),
            direct_opens: Arc::default(),
            pending_direct_results: Arc::new(AtomicBool::new(false)),
            quiescent: Arc::new(AtomicBool::new(false)),
            prev_changes: Arc::default(),
            client_capabilities: Arc::new(client_capabilities),
            has_notified_missing_builtins: false,
            //client_supports_cmd_run,
            shut_down: Arc::new(AtomicBool::new(false)),
            pid,
            workspace_roots: Arc::default(),
            compilation_info: Arc::default(),
        }
    }

    fn add_direct_open(&mut self, path: PathBuf) {
        let canon_path: CanonPath = path.into();
        self.direct_opens.lock().unwrap().insert(canon_path);
    }

    fn remove_direct_open(&mut self, path: PathBuf) {
        let canon_path: CanonPath = path.into();
        if !self.direct_opens.lock().unwrap().remove(&canon_path) {
            debug!("Tried to remove a directly opened file ({:?}) \
                    that wasnt tracked", canon_path);
        }
    }

    fn init<O: Output>(&mut self,
                       _init_options: InitializationOptions,
                       out: O) {
        self.update_compilation_info(&out)
    }

    pub fn update_workspaces(&mut self,
                             mut add: Vec<Workspace>,
                             remove: Vec<Workspace>) {
        if let Ok(mut workspaces) = self.workspace_roots.lock() {
            workspaces.retain(|workspace|
                              remove.iter().all(|rem|rem != workspace));
            workspaces.append(&mut add);
        }
    }

    fn update_linter_config<O: Output>(&mut self, _out: &O) {
        trace!("Updating linter config");
        if let Ok(config) = self.config.lock() {
            *self.lint_config.lock().unwrap() =
                config.lint_cfg_path.clone()
                .and_then(maybe_parse_lint_cfg)
                .unwrap_or_default();
        }
    }

    pub fn update_compilation_info<O: Output>(&mut self, out: &O) {
        trace!("Updating compile info");
        if let Ok(config) = self.config.lock() {
            if let Some(compile_info) = &config.compile_info_path {
                if let Some(canon_path) = CanonPath::from_path_buf(
                    compile_info.clone()) {
                    let workspaces = self.workspace_roots.lock().unwrap();
                    if !workspaces.is_empty() &&
                        workspaces.iter().any(
                            |root|parse_file_path!(&root.uri, "workspace")
                                .map_or(false, |p|canon_path.as_path()
                                        .starts_with(p))) {
                            crate::server::warning_message(
                                out,
                                "Compilation info file is not under \
                                 any workspace root, might be configured \
                                 for a different workspace.".to_string());
                        }
                }
                match self.compilation_info_from_file(compile_info) {
                    Ok(compilation_info) => {
                        trace!("Updated to {:?}", compilation_info);
                        {
                            let mut ci = self.compilation_info.lock().unwrap();
                            *ci = compilation_info;
                        }
                        self.analysis.lock().unwrap()
                            .update_all_context_dependencies(
                                self.construct_resolver());
                    },
                    Err(e) => {
                        error!("Failed to update compilation info: {}", e);
                        error_message(
                            out,
                            format!("Could not update compilation info: {}",
                                    e));
                    }
                }
            } else {
                trace!("No compile info path");
            }
        } else {
            trace!("Failed to lock config");
        }
    }

    pub fn compilation_info_from_file(&self, path: &PathBuf) ->
        Result<CompilationInfoStorage, String> {
            debug!("Reading compilation info from {:?}",
                   path);
            let file_content = fs::read_to_string(path).map_err(
                |e|e.to_string())?;
            trace!("Content is {:?}", file_content);
            #[allow(dead_code)]
            #[derive(Deserialize)]
            struct FileInfo {
                dmlc_flags: Vec<String>,
                includes: Vec<PathBuf>,
            }
            type CompileCommands = HashMap<PathBuf, FileInfo>;
            let json_structure: CompileCommands =
                serde_json::from_str(&file_content).map_err(|e|e.to_string())?;
            let mut new_compinfo = CompilationInfoStorage::default();
            for (file, file_info) in json_structure {
                // This is sanity, by design all files in this file should be
                // .dml
                if let Some(extension) = file.extension() {
                    if extension == "dml" {
                        let FileInfo {
                            includes, ..
                        } = file_info;
                        if let Some(canon_path) = CanonPath::from_path_buf(file)
                        {
                            let compentry = new_compinfo.entry(
                                canon_path).or_insert(CompilationInfo {
                                    extra_defines: vec![],
                                    include_paths : HashSet::default(),
                                });
                            // TODO: For now, ignore flags since we have no
                            // means to pass them to device analysis anyway
                            compentry.include_paths
                                .extend(includes.into_iter());
                        }
                    } else {
                        warn!(
                            "File in compile information file is not .dml; \
                             {:?}",
                            file
                        );
                    }
                }
            }
            Ok(new_compinfo)
        }

    pub fn update_analysis(&mut self) {
        self.analysis.lock().unwrap()
            .update_analysis(&self.construct_resolver());
    }

    pub fn trigger_device_analysis<O: Output>(&mut self,
                                              file: &Path,
                                              out: &O) {
        let canon_path: CanonPath = file.to_path_buf().into();
        debug!("triggering devices dependant on {}", canon_path.as_str());
        self.update_analysis();
        let maybe_triggers = self.analysis.lock().unwrap().device_triggers
            .get(&canon_path).cloned();
        trace!("should trigger: {:?}", maybe_triggers);
        if let Some(triggers) = maybe_triggers {
            for trigger in triggers {
                debug!("Wants to trigger {}", trigger.as_str());
                let ready = {
                    let mut analysis = self.analysis.lock().unwrap();
                    let has_dependencies = analysis.has_dependencies(&trigger)
                        && analysis.get_isolated_analysis(&trigger).unwrap()
                        .is_device_file();
                    // Skip triggering if the device cannot be outdated,
                    // i.e. it's newer than all it's dependencies
                    let not_outdated = analysis.device_newer_than_dependencies(
                        &trigger);
                    has_dependencies && !not_outdated
                };
                if ready {
                    debug!("Triggered device analysis {}", trigger.as_str());
                    self.device_analyze(&trigger, out);
                }
            }
        }
    }

    // Called when config might have changed, re-update include paths
    // and similar
    pub fn maybe_changed_config<O: Output>(&mut self, out: &O) {
        trace!("Compilation info might have changed");
        self.update_compilation_info(out);
        self.update_linter_config(out);
    }

    // Call before adding new analysis
    pub fn maybe_start_progress<O: Output>(&mut self, out: &O) {

        let mut notifier = self.current_notifier.lock().unwrap();

        if notifier.is_none() {
            debug!("started progress status");
            let new_notifier = AnalysisProgressNotifier::new(
                "Analysing".to_string(), out.clone());
            *notifier = Some(new_notifier.id());
            new_notifier.notify_begin_progress();
            self.pending_direct_results.store(true, Ordering::SeqCst);
        }
    }
    pub fn maybe_end_progress<O: Output>(&mut self, out: &O) {
        if !self.analysis_queue.has_work()
            && self.has_no_pending_direct_diagnostics() {
            // Need the scope here to succesfully drop the guard lock before
            // going into maybe_warn_missing_builtins below
            let lock_id = { self.current_notifier.lock().unwrap().clone() };
            if let Some(id) = lock_id {
                debug!("ended progress status");
                let notifier = AnalysisProgressNotifier::new_with_id(
                    id,
                    "Analysing".to_string(),
                    out.clone());
                notifier.notify_end_progress();
                self.maybe_warn_missing_builtins(out);
            }
        }
    }

    fn maybe_warn_missing_builtins<O: Output>(&mut self, out: &O) {
        if !self.has_notified_missing_builtins &&
            !self.analysis.lock().unwrap().has_client_file(
                &PathBuf::from("dml-builtins.dml")) {
                self.has_notified_missing_builtins = true;
                crate::server::warning_message(
                    out,
                    "Unable to find dml-builtins, various essential \
                     built-in templates, methods, and paramters will \
                     be unavailable and semantic analysis is likely \
                     to produce errors as a result".to_string());
            }
    }

    pub fn construct_resolver(&self) -> PathResolver {
        trace!("About to construct resolver");
        let mut toret: PathResolver =
               self.client_capabilities.root.clone().into();
        toret.add_paths(self.workspace_roots.lock().unwrap()
                        .iter().map(|w|parse_file_path!(&w.uri, "workspace")
                                    .unwrap()));
        toret.set_include_paths(&self.compilation_info.lock().unwrap().iter()
                                .map(|(r, info)|(r.clone(),
                                                 info.include_paths.clone()
                                                 .into_iter().collect()))
                                .collect());
        trace!("Constructed resolver: {:?}", toret);
        toret
    }

    pub fn isolated_analyze<O: Output>(&mut self,
                                       client_path: &Path,
                                       context: Option<CanonPath>,
                                       out: &O) {
        debug!("Wants isolated analysis of {:?}{}",
               client_path,
               context.as_ref().map(|s|format!(" under context {}", s.as_str()))
               .unwrap_or_default());
        let path = if let Some(p) =
            self.construct_resolver()
            .resolve_with_maybe_context(client_path, context.as_ref()) {
                p
            } else {
                debug!("Could not canonicalize client path {:?}", client_path);
                return;
            };
        if self.analysis.lock().unwrap().has_isolated_analysis(&path) {
            debug!("Was already analyzed");
            return;
        }
        self.maybe_start_progress(out);
        let (job, token) = ConcurrentJob::new();
        self.add_job(job);

        self.analysis_queue.enqueue_isolated_job(
            &mut self.analysis.lock().unwrap(),
            &self.vfs, context, path, client_path.to_path_buf(), token);
    }

    fn device_analyze<O: Output>(&mut self, device: &CanonPath, out: &O) {
        debug!("Wants device analysis of {:?}", device);
        self.maybe_start_progress(out);
        let (job, token) = ConcurrentJob::new();
        self.add_job(job);
        let locked_analysis = &mut self.analysis.lock().unwrap();
        let dependencies = locked_analysis.all_dependencies(device,
                                                            Some(device));
        self.analysis_queue.enqueue_device_job(
            locked_analysis,
            device,
            dependencies,
            token);
    }

    pub fn maybe_trigger_lint_analysis<O: Output>(&mut self,
                                                  file: &Path,
                                                  out: &O) {
        if !self.config.lock().unwrap().linting_enabled {
            self.pending_direct_results.store(true, Ordering::SeqCst);
            return;
        }
        let lint_config = self.lint_config.lock().unwrap().to_owned();
        if lint_config.cli_mode {
            let canon_path: CanonPath = file.to_path_buf().into();
            if !self.direct_opens.lock().unwrap().contains(&canon_path) {
                return;
            }
        }
        debug!("Triggering linting analysis of {:?}", file);
        self.lint_analyze(file,
                          None,
                          lint_config,
                          out);
    }

    fn has_no_pending_direct_diagnostics(&self) -> bool {
        if self.lint_config.lock().unwrap().direct_only {
            return !self.pending_direct_results.load(Ordering::SeqCst)
        }
        true
    }

    fn lint_analyze<O: Output>(&mut self,
                                   file: &Path,
                                   context: Option<CanonPath>,
                                   cfg: LintCfg,
                                   out: &O) {
        debug!("Wants to lint {:?}", file);
        self.maybe_start_progress(out);
        let path = if let Some(p) =
        self.construct_resolver()
        .resolve_with_maybe_context(file, context.as_ref()) {
            p
        } else {
            debug!("Could not canonicalize client path {:?}", file);
            return;
        };
        let (job, token) = ConcurrentJob::new();
        self.add_job(job);

        self.analysis_queue.enqueue_linter_job(
            &mut self.analysis.lock().unwrap(),
            cfg,
            &self.vfs, path, token);
    }

    pub fn add_job(&self, job: ConcurrentJob) {
        self.jobs.lock().unwrap().add(job);
    }

    pub fn wait_for_concurrent_jobs(&self) {
        self.jobs.lock().unwrap().wait_for_all();
    }

    /// See docs on VersionOrdering
    fn check_change_version(&self, file_path: &Path,
                            version_num: i32) -> VersionOrdering {
        let file_path = file_path.to_owned();
        let mut prev_changes = self.prev_changes.lock().unwrap();

        if prev_changes.contains_key(&file_path) {
            let prev_version = prev_changes[&file_path];
            if version_num <= prev_version {
                debug!(
                    "Out of order or duplicate change {:?}, prev: {}, current: {}",
                    file_path, prev_version, version_num,
                );

                if version_num == prev_version {
                    return VersionOrdering::Duplicate;
                } else {
                    return VersionOrdering::OutOfOrder;
                }
            }
        }

        prev_changes.insert(file_path, version_num);
        VersionOrdering::Ok
    }

    fn reset_change_version(&self, file_path: &Path) {
        let file_path = file_path.to_owned();
        let mut prev_changes = self.prev_changes.lock().unwrap();
        prev_changes.remove(&file_path);
    }

    fn text_doc_pos_to_pos(&self,
                           params: &TextDocumentPositionParams,
                           context: &str)
                           -> Option<FilePosition<ZeroIndexed>> {
        let file_path = parse_file_path!(
            &params.text_document.uri, context)
            .ok()?;
        // run this through pos_to_span once to get the word range, then return
        // the front of it
        Some(self.convert_pos_to_span(file_path, params.position)
             .start_position())
    }

    fn convert_pos_to_span(&self, file_path: PathBuf, pos: Position) -> Span {
        trace!("convert_pos_to_span: {:?} {:?}", file_path, pos);

        let pos = ls_util::position_to_dls(pos);
        let line = self.vfs.load_line(&file_path, pos.row).unwrap();
        trace!("line: `{}`", line);

        let (start, end) = find_word_at_pos(&line, pos.col);
        trace!("start: {}, end: {}", start.0, end.0);

        Span::from_positions(
            span::Position::new(pos.row, start),
            span::Position::new(pos.row, end),
            file_path,
        )
    }
}

/// Some notifications come with sequence numbers, we check that these are in
/// order. However, clients might be buggy about sequence numbers so we do cope
/// with them being wrong.
///
/// This enum defines the state of sequence numbers.
#[derive(Eq, PartialEq, Debug, Clone, Copy)]
pub enum VersionOrdering {
    /// Sequence number is in order (note that we don't currently check that
    /// sequence numbers are sequential, but we probably should).
    Ok,
    /// This indicates the client sent us multiple copies of the same notification
    /// and some should be ignored.
    Duplicate,
    /// Just plain wrong sequence number. No obvious way for us to recover.
    OutOfOrder,
}

/// Represents a text cursor between characters, pointing at the next character
/// in the buffer.
type Column = span::Column<span::ZeroIndexed>;

/// Returns a text cursor range for a found word inside `line` at which `pos`
/// text cursor points to. Resulting type represents a (`start`, `end`) range
/// between `start` and `end` cursors.
/// For example (4, 4) means an empty selection starting after first 4 characters.
fn find_word_at_pos(line: &str, pos: Column) -> (Column, Column) {
    let col = pos.0 as usize;
    let is_ident_char = |c: char| c.is_alphanumeric() || c == '_';

    let start = line
        .chars()
        .enumerate()
        .take(col)
        .filter(|&(_, c)| !is_ident_char(c))
        .last()
        .map(|(i, _)| i + 1)
        .unwrap_or(0) as u32;

    #[allow(clippy::filter_next)]
    let end = line
        .chars()
        .enumerate()
        .skip(col)
        .filter(|&(_, c)| !is_ident_char(c))
        .next()
        .map(|(i, _)| i)
        .unwrap_or(col) as u32;

    (span::Column::new_zero_indexed(start), span::Column::new_zero_indexed(end))
}

// /// Client file-watching request / filtering logic
pub struct FileWatch {
    file_path: PathBuf,
}

impl FileWatch {
    /// Construct a new `FileWatch`.
    pub fn new(ctx: &InitActionContext) -> Option<Self> {
        match ctx.config.lock() {
            Ok(config) => {
                config.compile_info_path.as_ref().map(
                    |c| FileWatch {
                        file_path: c.clone()
                    })
            },
            Err(e) => {
                error!("Unable to access configuration: {:?}", e);
                None
            }
        }
    }

    /// Returns if a file change is relevant to the files we
    /// actually wanted to watch
    /// Implementation note: This is expected to be called a
    /// large number of times in a loop so should be fast / avoid allocation.
    #[inline]
    fn relevant_change_kind(&self, change_uri: &Uri,
                            _kind: FileChangeType) -> bool {
        let path = change_uri.as_str();
        self.file_path.to_str().map_or(false, |fp|fp == path)
    }

    #[inline]
    pub fn is_relevant(&self, change: &FileEvent) -> bool {
        self.relevant_change_kind(&change.uri, change.typ)
    }

    #[inline]
    pub fn is_relevant_save_doc(&self, did_save: &DidSaveTextDocumentParams)
                                -> bool {
        self.relevant_change_kind(&did_save.text_document.uri,
                                  FileChangeType::CHANGED)
    }

    /// Returns json config for desired file watches
    pub fn watchers_config(&self) -> serde_json::Value {
        fn watcher(pat: String) -> FileSystemWatcher {
            FileSystemWatcher { glob_pattern: GlobPattern::String(pat),
                                kind: None }
        }
        fn _watcher_with_kind(pat: String, kind: WatchKind)
                             -> FileSystemWatcher {
            FileSystemWatcher { glob_pattern: GlobPattern::String(pat),
                                kind: Some(kind) }
        }

        let watchers = vec![watcher(
            self.file_path.to_string_lossy().to_string())];

        json!({ "watchers": watchers })
    }
}
