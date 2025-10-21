"""
LSP server implementation for the DML Language Server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from pygls.server import LanguageServer
from lsprotocol.types import (
    InitializeParams,
    InitializeResult,
    ServerCapabilities,
    TextDocumentSyncKind,
    CompletionOptions,
    DidOpenTextDocumentParams,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidSaveTextDocumentParams,
    CompletionParams,
    HoverParams,
    DefinitionParams,
    ReferenceParams,
    DocumentSymbolParams,
    WorkspaceSymbolParams,
    Position as LspPosition,
    PublishDiagnosticsParams,
)

from ..vfs import VFS
from ..config import Config
from ..file_management import FileManager
from ..analysis import DeviceAnalysis
from ..lint import LintEngine
from ..lsp_data import (
    LSPInitializationOptions,
    uri_to_path,
    path_to_uri,
    lsp_position_to_zero_indexed,
)

logger = logging.getLogger(__name__)


class DMLLanguageServer(LanguageServer):
    """DML Language Server implementation."""
    
    def __init__(self, vfs: VFS):
        super().__init__("dml-language-server", "0.9.14")
        
        self.vfs = vfs
        self.config = Config()
        self.file_manager = FileManager(self.config)
        self.analysis_engine = DeviceAnalysis(self.config, self.file_manager)
        self.lint_engine: Optional[LintEngine] = None
        
        # Track open documents
        self.open_documents: Dict[str, str] = {}
        
        # Set up VFS change callback
        self.vfs.add_change_callback(self._on_file_change)
        
        # Register LSP handlers
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register LSP message handlers."""
        
        @self.feature("initialize")
        async def initialize(params: InitializeParams) -> InitializeResult:
            """Handle initialize request."""
            logger.info("Initializing DML Language Server")
            
            # Set workspace root
            if params.root_uri:
                workspace_root = uri_to_path(params.root_uri)
                self.config.workspace_root = workspace_root
                logger.info(f"Workspace root: {workspace_root}")
                
                # Start watching workspace
                self.vfs.watch_directory(workspace_root)
            
            # Process initialization options
            if params.initialization_options:
                init_options = LSPInitializationOptions.from_dict(params.initialization_options)
                self.config.set_initialization_options(init_options.__dict__)
                
                # Load compile commands if specified
                if init_options.compile_commands_file:
                    compile_commands_path = Path(init_options.compile_commands_file)
                    if compile_commands_path.exists():
                        self.config.load_compile_commands(compile_commands_path)
                
                # Set up linting
                if init_options.linting_enabled:
                    self.lint_engine = LintEngine(self.config)
                    if init_options.lint_config_file:
                        lint_config_path = Path(init_options.lint_config_file)
                        if lint_config_path.exists():
                            self.config.load_lint_config(lint_config_path)
            
            # Return server capabilities
            return InitializeResult(
                capabilities=ServerCapabilities(
                    text_document_sync=TextDocumentSyncKind.Full,
                    completion_provider=CompletionOptions(
                        trigger_characters=["."],
                        resolve_provider=False
                    ),
                    hover_provider=True,
                    definition_provider=True,
                    references_provider=True,
                    document_symbol_provider=True,
                    workspace_symbol_provider=True,
                )
            )
        
        @self.feature("textDocument/didOpen")
        async def did_open(params: DidOpenTextDocumentParams) -> None:
            """Handle document open."""
            uri = params.text_document.uri
            content = params.text_document.text
            
            # Store document content
            self.open_documents[uri] = content
            
            # Cache in VFS
            file_path = uri_to_path(uri)
            self.vfs.write_file(file_path, content)
            
            # Analyze document
            await self._analyze_document(uri, content)
        
        @self.feature("textDocument/didChange")
        async def did_change(params: DidChangeTextDocumentParams) -> None:
            """Handle document change."""
            uri = params.text_document.uri
            
            # Update content (assuming full sync for simplicity)
            if params.content_changes:
                content = params.content_changes[0].text
                self.open_documents[uri] = content
                
                # Update VFS
                file_path = uri_to_path(uri)
                self.vfs.write_file(file_path, content)
                
                # Re-analyze document
                await self._analyze_document(uri, content)
        
        @self.feature("textDocument/didClose")
        async def did_close(params: DidCloseTextDocumentParams) -> None:
            """Handle document close."""
            uri = params.text_document.uri
            self.open_documents.pop(uri, None)
            
            # Remove from VFS cache
            file_path = uri_to_path(uri)
            self.vfs.remove_file(file_path)
        
        @self.feature("textDocument/didSave")
        async def did_save(params: DidSaveTextDocumentParams) -> None:
            """Handle document save."""
            uri = params.text_document.uri
            file_path = uri_to_path(uri)
            
            # Save to disk if we have cached content
            if self.vfs.is_dirty(file_path):
                await self.vfs.save_file(file_path)
        
        @self.feature("textDocument/completion")
        async def completion(params: CompletionParams) -> List[Any]:
            """Handle completion request."""
            try:
                uri = params.text_document.uri
                file_path = uri_to_path(uri)
                position = lsp_position_to_zero_indexed(params.position)
                
                # Get symbols for completion
                symbols = self.analysis_engine.get_all_symbols_in_file(file_path)
                
                # Convert to completion items
                completion_items = []
                for symbol in symbols:
                    completion_item = symbol.to_lsp_document_symbol()
                    # This would need proper conversion to CompletionItem
                    completion_items.append({
                        "label": symbol.name,
                        "kind": 1,  # Text
                        "detail": symbol.detail
                    })
                
                return completion_items
                
            except Exception as e:
                logger.error(f"Error in completion: {e}")
                return []
        
        @self.feature("textDocument/hover")
        async def hover(params: HoverParams) -> Optional[Any]:
            """Handle hover request."""
            try:
                uri = params.text_document.uri
                file_path = uri_to_path(uri)
                position = lsp_position_to_zero_indexed(params.position)
                
                # Find symbol at position
                symbol = self.analysis_engine.get_symbol_at_position(file_path, position)
                
                if symbol:
                    hover_content = f"**{symbol.name}** ({symbol.kind.value})"
                    if symbol.detail:
                        hover_content += f"\n\n{symbol.detail}"
                    if symbol.documentation:
                        hover_content += f"\n\n{symbol.documentation}"
                    
                    return {
                        "contents": {
                            "kind": "markdown",
                            "value": hover_content
                        }
                    }
                
                return None
                
            except Exception as e:
                logger.error(f"Error in hover: {e}")
                return None
        
        @self.feature("textDocument/definition")
        async def definition(params: DefinitionParams) -> Optional[List[Any]]:
            """Handle go-to-definition request."""
            try:
                uri = params.text_document.uri
                file_path = uri_to_path(uri)
                position = lsp_position_to_zero_indexed(params.position)
                
                # Find symbol at position
                symbol = self.analysis_engine.get_symbol_at_position(file_path, position)
                
                if symbol:
                    # Return the symbol's location
                    location = symbol.location.to_lsp_location()
                    return [location]
                
                return None
                
            except Exception as e:
                logger.error(f"Error in definition: {e}")
                return None
        
        @self.feature("textDocument/references")
        async def references(params: ReferenceParams) -> Optional[List[Any]]:
            """Handle find references request."""
            try:
                uri = params.text_document.uri
                file_path = uri_to_path(uri)
                position = lsp_position_to_zero_indexed(params.position)
                
                # Find symbol at position
                symbol = self.analysis_engine.get_symbol_at_position(file_path, position)
                
                if symbol:
                    # Find all references to this symbol
                    definitions = self.analysis_engine.find_symbol_definitions(symbol.name)
                    locations = []
                    
                    for definition in definitions:
                        location = definition.symbol.location.to_lsp_location()
                        locations.append(location)
                        
                        # Add reference locations
                        for ref in definition.references:
                            ref_location = ref.location.to_lsp_location()
                            locations.append(ref_location)
                    
                    return locations
                
                return None
                
            except Exception as e:
                logger.error(f"Error in references: {e}")
                return None
        
        @self.feature("textDocument/documentSymbol")
        async def document_symbol(params: DocumentSymbolParams) -> Optional[List[Any]]:
            """Handle document symbol request."""
            try:
                uri = params.text_document.uri
                file_path = uri_to_path(uri)
                
                # Get all symbols in the file
                symbols = self.analysis_engine.get_all_symbols_in_file(file_path)
                
                # Convert to LSP document symbols
                document_symbols = []
                for symbol in symbols:
                    if not symbol.children:  # Only top-level symbols
                        doc_symbol = symbol.to_lsp_document_symbol()
                        document_symbols.append(doc_symbol)
                
                return document_symbols
                
            except Exception as e:
                logger.error(f"Error in document symbol: {e}")
                return []
    
    async def _analyze_document(self, uri: str, content: str) -> None:
        """Analyze a document and publish diagnostics."""
        try:
            file_path = uri_to_path(uri)
            
            # Analyze the file
            errors = self.analysis_engine.analyze_file(file_path, content)
            
            # Run linting if enabled
            if self.lint_engine and self.config.is_linting_enabled():
                # Get file analysis for linting
                analysis = self.analysis_engine.file_analyses.get(file_path)
                if analysis:
                    lint_warnings = self.lint_engine.lint_file(file_path, content, analysis)
                    errors.extend(lint_warnings)
            
            # Convert errors to diagnostics
            diagnostics = [error.to_diagnostic().to_lsp_diagnostic() for error in errors]
            
            # Limit diagnostics per file
            max_diagnostics = self.config.get_max_diagnostics_per_file()
            if len(diagnostics) > max_diagnostics:
                diagnostics = diagnostics[:max_diagnostics]
            
            # Publish diagnostics
            self.publish_diagnostics(
                PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
            )
            
        except Exception as e:
            logger.error(f"Error analyzing document {uri}: {e}")
    
    async def _on_file_change(self, change) -> None:
        """Handle file system changes."""
        try:
            from ..vfs import FileChangeType
            
            file_path = change.path
            
            # Invalidate analysis cache
            affected_files = self.analysis_engine.invalidate_file(file_path)
            
            # Re-analyze affected open documents
            for affected_file in affected_files:
                affected_uri = path_to_uri(affected_file)
                if affected_uri in self.open_documents:
                    content = self.open_documents[affected_uri]
                    await self._analyze_document(affected_uri, content)
            
        except Exception as e:
            logger.error(f"Error handling file change: {e}")


async def run_server(vfs: VFS) -> int:
    """
    Run the DML Language Server.
    
    Args:
        vfs: Virtual file system instance
        
    Returns:
        Exit code
    """
    try:
        server = DMLLanguageServer(vfs)
        
        # Start VFS change processing in background
        change_task = asyncio.create_task(vfs.process_changes())
        
        # Start the language server
        await server.start_io()
        
        # Clean up
        change_task.cancel()
        vfs.stop_watching()
        
        return 0
        
    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1


# Export main functions
__all__ = [
    "DMLLanguageServer",
    "run_server"
]