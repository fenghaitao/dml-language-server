# File Management and Virtual File System Integration

<cite>
**Referenced Files in This Document**
- [file_management.rs](file://src/file_management.rs)
- [vfs/mod.rs](file://src/vfs/mod.rs)
- [vfs/test.rs](file://src/vfs/test.rs)
- [lsp_data.rs](file://src/lsp_data.rs)
- [actions/notifications.rs](file://src/actions/notifications.rs)
- [config.rs](file://src/config.rs)
- [main.rs](file://src/main.rs)
- [file_management.py](file://python-port/dml_language_server/file_management.py)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py)
- [config.py](file://python-port/dml_language_server/config.py)
- [main.py](file://python-port/dml_language_server/main.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the file management and Virtual File System (VFS) integration within the Language Server Protocol (LSP) implementation. It covers the virtual file system architecture, file caching strategies, and change tracking mechanisms. It also documents file open/close operations, content synchronization, incremental updates, and workspace file management. The integration between LSP file operations and the underlying VFS layer is explained, including file resolution, path handling, and cross-referencing. Practical examples, performance optimization techniques, and troubleshooting guidance for distributed development environments are included.

## Project Structure
The project implements both a Rust-based server and a Python-based server. The Rust server focuses on the VFS and LSP integration, while the Python server provides a complementary VFS implementation and file watcher.

```mermaid
graph TB
subgraph "Rust Server"
RS_Main["src/main.rs"]
RS_VFS["src/vfs/mod.rs"]
RS_FileMgr["src/file_management.rs"]
RS_LSPData["src/lsp_data.rs"]
RS_Notify["src/actions/notifications.rs"]
RS_Config["src/config.rs"]
end
subgraph "Python Server"
PY_Main["python-port/dml_language_server/main.py"]
PY_VFS["python-port/dml_language_server/vfs/__init__.py"]
PY_FileMgr["python-port/dml_language_server/file_management.py"]
PY_Config["python-port/dml_language_server/config.py"]
end
RS_Main --> RS_VFS
RS_Main --> RS_Notify
RS_Notify --> RS_VFS
RS_Notify --> RS_LSPData
RS_FileMgr --> RS_Config
PY_Main --> PY_VFS
PY_VFS --> PY_Config
PY_FileMgr --> PY_Config
```

**Diagram sources**
- [main.rs](file://src/main.rs#L56-L58)
- [vfs/mod.rs](file://src/vfs/mod.rs#L180-L288)
- [actions/notifications.rs](file://src/actions/notifications.rs#L75-L106)
- [lsp_data.rs](file://src/lsp_data.rs#L47-L107)
- [file_management.rs](file://src/file_management.rs#L30-L64)
- [main.py](file://python-port/dml_language_server/main.py#L82-L83)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L123-L133)
- [file_management.py](file://python-port/dml_language_server/file_management.py#L33-L41)
- [config.py](file://python-port/dml_language_server/config.py#L89-L129)

**Section sources**
- [main.rs](file://src/main.rs#L56-L58)
- [main.py](file://python-port/dml_language_server/main.py#L82-L83)

## Core Components
- Rust VFS: A thread-safe in-memory file cache with change tracking, line indexing, and user data storage. It supports incremental edits, file snapshots, and persistence to disk.
- Rust PathResolver: Canonicalizes and resolves file paths against include directories and workspace roots.
- Rust LSP integration: Handlers for DidOpenTextDocument, DidCloseTextDocument, and DidChangeTextDocument that synchronize editor content with the VFS.
- Python VFS: Async file loader with caching, dirty tracking, and file system change monitoring via watchdog.
- Python file manager: Discovers DML files, categorizes them, extracts imports, and resolves include paths.
- Configuration: Centralized configuration for include paths, linting, and analysis behavior.

**Section sources**
- [vfs/mod.rs](file://src/vfs/mod.rs#L180-L288)
- [file_management.rs](file://src/file_management.rs#L55-L64)
- [actions/notifications.rs](file://src/actions/notifications.rs#L75-L106)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L123-L133)
- [file_management.py](file://python-port/dml_language_server/file_management.py#L33-L41)
- [config.py](file://python-port/dml_language_server/config.py#L89-L129)

## Architecture Overview
The LSP server integrates VFS operations with editor notifications. Rust-side handlers convert LSP ranges to internal spans, apply incremental changes to the VFS, and trigger analysis. The Python-side VFS provides asynchronous file loading and change monitoring.

```mermaid
sequenceDiagram
participant Client as "Editor"
participant LSP as "LSP Server"
participant VFS as "VFS"
participant FS as "File System"
Client->>LSP : "DidOpenTextDocument"
LSP->>VFS : "set_file(path, text)"
VFS->>VFS : "cache text, mark changed=false"
LSP-->>Client : "acknowledge"
Client->>LSP : "DidChangeTextDocument"
LSP->>LSP : "convert LSP range to span"
LSP->>VFS : "on_changes([ReplaceText/AddFile])"
VFS->>VFS : "apply incremental edits"
VFS->>FS : "write_file(path) when saved"
LSP-->>Client : "analysis results"
Client->>LSP : "DidCloseTextDocument"
LSP->>LSP : "remove direct open tracking"
LSP-->>Client : "acknowledge"
```

**Diagram sources**
- [actions/notifications.rs](file://src/actions/notifications.rs#L75-L106)
- [actions/notifications.rs](file://src/actions/notifications.rs#L108-L163)
- [vfs/mod.rs](file://src/vfs/mod.rs#L221-L231)
- [vfs/mod.rs](file://src/vfs/mod.rs#L202-L205)
- [vfs/mod.rs](file://src/vfs/mod.rs#L514-L530)

## Detailed Component Analysis

### Rust VFS: Architecture and Operations
The VFS maintains an in-memory cache of files, tracks changes, and supports efficient line-based access. It distinguishes between text and binary files, supports user data per file, and coordinates concurrent access with pending file locks.

Key capabilities:
- Incremental edits: AddFile and ReplaceText changes applied to cached text.
- Line indexing: Precomputed indices for fast line and range access.
- Change tracking: Per-file “changed” flag and “has_changes” aggregation.
- Persistence: write_file writes cached content to disk via a file loader.
- Concurrency: Pending file queues coordinate readers/writers to avoid race conditions.

```mermaid
classDiagram
class Vfs {
+new() Vfs
+set_file(path, text) void
+on_changes(changes) Result
+load_file(path) Result
+snapshot_file(path) Result
+load_line(path, line) Result
+load_lines(path, start, end) Result
+load_span(span) Result
+write_file(path) Result
+file_saved(path) Result
+flush_file(path) Result
+file_is_synced(path) Result
+has_changes() bool
+get_cached_files() Map
+get_changes() Map
+set_user_data(path, data) Result
+with_user_data(path, f) Result
+ensure_user_data(path, f) Result
+clear() void
}
class VfsInternal {
-files : Mutex<Map<PathBuf, File>>
-pending_files : Mutex<Map<PathBuf, Vec<Thread>>>
+new() VfsInternal
+set_file(path, text) void
+on_changes(changes) Result
+ensure_file(path, f) Result
+write_file(path) Result
+file_saved(path) Result
+flush_file(path) Result
+file_is_synced(path) Result
+has_changes() bool
+get_cached_files() Map
+get_changes() Map
+set_user_data(path, data) Result
+with_user_data(path, f) Result
+ensure_user_data(path, f) Result
+clear() void
}
class TextFile {
+text : String
+line_indices : Vec<u32>
+changed : bool
+make_change(changes) Result
+load_line(line) Result
+load_lines(start, end) Result
+load_range(range) Result
+for_each_line(f) Result
}
class File {
-kind : FileKind
-user_data : Option<U>
+contents() FileContents
+make_change(changes) Result
+load_line(line) Result
+load_lines(start, end) Result
+load_range(range) Result
+for_each_line(f) Result
+changed() bool
}
class FileKind {
<<enumeration>>
Text(TextFile)
Binary(Vec<u8>)
}
class FileLoader {
<<trait>>
+read(file_name) Result
+write(file_name, file) Result
}
class RealFileLoader {
+read(file_name) Result
+write(file_name, file) Result
}
Vfs --> VfsInternal : "wraps"
VfsInternal --> File : "stores"
File --> FileKind : "contains"
FileKind --> TextFile : "Text variant"
FileLoader <|.. RealFileLoader : "implements"
```

**Diagram sources**
- [vfs/mod.rs](file://src/vfs/mod.rs#L180-L288)
- [vfs/mod.rs](file://src/vfs/mod.rs#L293-L602)
- [vfs/mod.rs](file://src/vfs/mod.rs#L625-L729)
- [vfs/mod.rs](file://src/vfs/mod.rs#L847-L845)
- [vfs/mod.rs](file://src/vfs/mod.rs#L895-L952)

**Section sources**
- [vfs/mod.rs](file://src/vfs/mod.rs#L180-L288)
- [vfs/mod.rs](file://src/vfs/mod.rs#L293-L602)
- [vfs/mod.rs](file://src/vfs/mod.rs#L625-L729)
- [vfs/mod.rs](file://src/vfs/mod.rs#L847-L845)
- [vfs/mod.rs](file://src/vfs/mod.rs#L895-L952)

### Rust Path Resolution and Include Paths
The PathResolver resolves relative paths to absolute paths using include directories and workspace roots. It caches resolution results and supports context-aware resolution.

Key features:
- Roots: Workspace roots and include directories.
- Caching: Memoized resolution results keyed by path and optional context.
- Priority: include_paths -> workspace_folders -> root -> extra_path.

```mermaid
flowchart TD
Start(["Resolve Path"]) --> CheckCache["Check cache for (path, context)"]
CheckCache --> Cached{"Cached?"}
Cached --> |Yes| ReturnCache["Return cached CanonPath"]
Cached --> |No| IsRelative{"Is relative path?"}
IsRelative --> |Yes| ResolveRel["Resolve from relative to source context"]
IsRelative --> |No| ResolveWithContext["Resolve with context and include paths"]
ResolveRel --> TryPath["Try path existence"]
ResolveWithContext --> TryPath
TryPath --> Exists{"Exists and is file?"}
Exists --> |Yes| Canonicalize["Canonicalize to CanonPath"]
Exists --> |No| NextRoot["Try next root/include path"]
NextRoot --> Exists
Canonicalize --> StoreCache["Store in cache"]
StoreCache --> ReturnResult["Return CanonPath"]
ReturnCache --> End(["Done"])
ReturnResult --> End
```

**Diagram sources**
- [file_management.rs](file://src/file_management.rs#L104-L148)
- [file_management.rs](file://src/file_management.rs#L150-L206)

**Section sources**
- [file_management.rs](file://src/file_management.rs#L55-L64)
- [file_management.rs](file://src/file_management.rs#L104-L148)
- [file_management.rs](file://src/file_management.rs#L150-L206)

### LSP File Operations and VFS Integration
The server handles DidOpenTextDocument, DidCloseTextDocument, and DidChangeTextDocument. It converts LSP ranges to internal spans, applies incremental edits, and triggers analysis.

- DidOpenTextDocument: Sets initial file content in VFS and marks as directly opened.
- DidCloseTextDocument: Removes direct open tracking.
- DidChangeTextDocument: Validates version ordering, converts LSP ranges to spans, applies ReplaceText/AddFile changes, and marks file dirty.

```mermaid
sequenceDiagram
participant Editor as "Editor"
participant Handler as "DidOpenTextDocument"
participant VFS as "VFS"
participant Analysis as "Analysis"
Editor->>Handler : "DidOpenTextDocument"
Handler->>VFS : "set_file(path, text)"
Handler->>Handler : "add_direct_open(path)"
Handler->>Analysis : "isolated_analyze(path)"
Handler-->>Editor : "acknowledge"
```

**Diagram sources**
- [actions/notifications.rs](file://src/actions/notifications.rs#L75-L91)

```mermaid
sequenceDiagram
participant Editor as "Editor"
participant Handler as "DidChangeTextDocument"
participant VFS as "VFS"
participant Analysis as "Analysis"
Editor->>Handler : "DidChangeTextDocument"
Handler->>Handler : "check_change_version()"
Handler->>Handler : "convert LSP range to span"
Handler->>VFS : "on_changes([ReplaceText/AddFile])"
Handler->>Analysis : "mark_file_dirty(path)"
Handler-->>Editor : "acknowledge"
```

**Diagram sources**
- [actions/notifications.rs](file://src/actions/notifications.rs#L108-L163)

**Section sources**
- [actions/notifications.rs](file://src/actions/notifications.rs#L75-L106)
- [actions/notifications.rs](file://src/actions/notifications.rs#L108-L163)
- [lsp_data.rs](file://src/lsp_data.rs#L134-L186)

### Python VFS: Async File Loader and Watcher
The Python VFS provides asynchronous file loading, caching, and change monitoring. It supports two loaders: RealFileLoader (disk) and MemoryFileLoader (in-memory). It uses watchdog to monitor file system changes and invalidates cache entries accordingly.

Key features:
- read_file: Returns cached content if available and not dirty; otherwise loads from disk.
- write_file: Stores content in memory cache and marks as dirty.
- save_file: Writes cached content to disk.
- watch_directory: Starts monitoring a directory for DML file changes.
- process_changes: Processes file change events asynchronously.

```mermaid
flowchart TD
Start(["Read File"]) --> CheckCache["Check cache and dirty set"]
CheckCache --> Cached{"Cached and not dirty?"}
Cached --> |Yes| ReturnCache["Return cached content"]
Cached --> |No| LoadDisk["Load from file system"]
LoadDisk --> UpdateCache["Update cache, remove dirty"]
UpdateCache --> ReturnContent["Return content"]
ReturnCache --> End(["Done"])
ReturnContent --> End
```

**Diagram sources**
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L135-L163)

**Section sources**
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L123-L133)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L135-L163)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L178-L197)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L240-L269)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L280-L304)

### Python File Manager: Discovery, Categorization, and Dependencies
The Python file manager discovers DML files, extracts metadata (device/library classification, imports), and resolves include paths. It maintains dependency graphs and supports invalidation.

Key operations:
- discover_dml_files: Recursively finds DML files.
- get_file_info: Analyzes file content to extract metadata and imports.
- _resolve_import_path: Resolves import names to absolute paths using include paths.
- get_dependencies/get_dependents: Retrieves direct and transitive dependencies.
- invalidate_file: Clears caches and returns affected files.

```mermaid
flowchart TD
Start(["Analyze File"]) --> ReadContent["Read file content"]
ReadContent --> ExtractMeta["Extract DML version, device/library flags"]
ExtractMeta --> ExtractImports["Extract import statements"]
ExtractImports --> ResolvePaths["Resolve import paths using include paths"]
ResolvePaths --> UpdateGraphs["Update dependency and reverse dependency graphs"]
UpdateGraphs --> CacheInfo["Cache FileInfo"]
CacheInfo --> End(["Done"])
```

**Diagram sources**
- [file_management.py](file://python-port/dml_language_server/file_management.py#L100-L137)
- [file_management.py](file://python-port/dml_language_server/file_management.py#L163-L188)

**Section sources**
- [file_management.py](file://python-port/dml_language_server/file_management.py#L42-L74)
- [file_management.py](file://python-port/dml_language_server/file_management.py#L100-L137)
- [file_management.py](file://python-port/dml_language_server/file_management.py#L163-L188)
- [file_management.py](file://python-port/dml_language_server/file_management.py#L216-L241)
- [file_management.py](file://python-port/dml_language_server/file_management.py#L305-L334)

### Configuration and Include Paths
Configuration controls include paths, linting, and analysis behavior. The Python Config class loads compile commands and lint configurations, and exposes helper methods to resolve include paths and flags for a given file.

Key responsibilities:
- load_compile_commands: Loads device-specific include paths and flags.
- get_include_paths_for_file: Returns include paths for a file, considering device context.
- get_dmlc_flags_for_file: Returns compiler flags for a file.
- Initialization options: Log level, linting enablement, and diagnostic limits.

**Section sources**
- [config.py](file://python-port/dml_language_server/config.py#L131-L201)
- [config.py](file://python-port/dml_language_server/config.py#L202-L224)
- [config.py](file://python-port/dml_language_server/config.py#L116-L129)

## Dependency Analysis
The Rust VFS depends on internal file loaders and maintains thread-safe access to cached files. The Python VFS depends on async file operations and watchdog for change detection. Both integrate with LSP handlers to synchronize editor content.

```mermaid
graph TB
subgraph "Rust"
RS_VFS["VFS"]
RS_Internal["VfsInternal"]
RS_File["File"]
RS_Text["TextFile"]
RS_Loader["RealFileLoader"]
RS_Path["PathResolver"]
end
subgraph "Python"
PY_VFS["VFS"]
PY_Watcher["FileSystemWatcher"]
PY_RFL["RealFileLoader"]
PY_MFL["MemoryFileLoader"]
end
RS_VFS --> RS_Internal
RS_Internal --> RS_File
RS_File --> RS_Text
RS_Internal --> RS_Loader
RS_Path --> RS_Internal
PY_VFS --> PY_RFL
PY_VFS --> PY_MFL
PY_VFS --> PY_Watcher
```

**Diagram sources**
- [vfs/mod.rs](file://src/vfs/mod.rs#L180-L288)
- [vfs/mod.rs](file://src/vfs/mod.rs#L293-L602)
- [vfs/mod.rs](file://src/vfs/mod.rs#L625-L729)
- [vfs/mod.rs](file://src/vfs/mod.rs#L900-L952)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L123-L133)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L92-L121)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L50-L90)

**Section sources**
- [vfs/mod.rs](file://src/vfs/mod.rs#L180-L288)
- [vfs/mod.rs](file://src/vfs/mod.rs#L293-L602)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L123-L133)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L92-L121)

## Performance Considerations
- Incremental edits: Prefer ReplaceText over full reloads to minimize overhead.
- Line indexing: Precomputed line indices enable O(1) line access and efficient range operations.
- Concurrency: Pending file queues prevent race conditions and reduce contention.
- Caching: Use VFS get_cached_files and get_changes to batch operations and avoid repeated disk I/O.
- Async I/O: Python VFS uses async file operations and watchdog to avoid blocking the event loop.
- Include path resolution: Cache resolution results to avoid repeated filesystem checks.
- Dirty tracking: Separate dirty sets allow targeted saves and reduce unnecessary writes.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Out-of-sync files: Use file_is_synced to detect unsaved changes; call write_file to persist.
- Bad locations: Verify LSP range conversion and UTF-16 vs UTF-8 offsets; use VfsSpan helpers.
- Circular dependencies: Detect and handle cycles when computing transitive dependencies.
- File not cached: Ensure ensure_file is called before accessing cached content.
- Change ordering: Validate version ordering to avoid applying edits out of order.
- Watcher errors: Restart watchers if file system events fail; ensure DML file filtering.

**Section sources**
- [vfs/mod.rs](file://src/vfs/mod.rs#L110-L128)
- [vfs/mod.rs](file://src/vfs/mod.rs#L346-L352)
- [vfs/mod.rs](file://src/vfs/mod.rs#L468-L512)
- [actions/notifications.rs](file://src/actions/notifications.rs#L125-L135)
- [vfs/__init__.py](file://python-port/dml_language_server/vfs/__init__.py#L280-L304)

## Conclusion
The LSP implementation integrates a robust VFS with incremental file operations, change tracking, and path resolution. The Rust server emphasizes thread safety and efficient text editing, while the Python server complements with async file loading and change monitoring. Together, they provide a scalable foundation for file management in distributed development environments.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Example Workflows

- Open a file:
  - Editor sends DidOpenTextDocument.
  - Server calls VFS.set_file and marks as directly opened.
  - Analysis is triggered if configured.

- Edit a file incrementally:
  - Editor sends DidChangeTextDocument with content changes.
  - Server validates version ordering, converts ranges, and applies ReplaceText/AddFile.
  - VFS updates cached content and marks file as changed.

- Close a file:
  - Editor sends DidCloseTextDocument.
  - Server removes direct open tracking.

- Save a file:
  - Server calls write_file to persist cached content to disk.

**Section sources**
- [actions/notifications.rs](file://src/actions/notifications.rs#L75-L106)
- [actions/notifications.rs](file://src/actions/notifications.rs#L108-L163)
- [vfs/mod.rs](file://src/vfs/mod.rs#L221-L231)
- [vfs/mod.rs](file://src/vfs/mod.rs#L514-L530)