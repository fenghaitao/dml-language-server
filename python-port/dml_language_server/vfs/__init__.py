"""
Virtual File System for the DML Language Server.

Handles file operations, caching, and change detection for the language server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Set, List, Protocol
from dataclasses import dataclass
from enum import Enum
import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

logger = logging.getLogger(__name__)


class FileChangeType(Enum):
    """Types of file system changes."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class FileChange:
    """Represents a file system change."""
    path: Path
    change_type: FileChangeType
    content: Optional[str] = None


class FileLoader(Protocol):
    """Protocol for loading files from different sources."""
    
    async def load_file(self, path: Path) -> str:
        """Load file content from the given path."""
        ...
    
    def exists(self, path: Path) -> bool:
        """Check if a file exists."""
        ...


class RealFileLoader:
    """File loader that reads from the actual file system."""
    
    async def load_file(self, path: Path) -> str:
        """Load file content from disk."""
        try:
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            raise
    
    def exists(self, path: Path) -> bool:
        """Check if file exists on disk."""
        return path.exists() and path.is_file()


class MemoryFileLoader:
    """File loader that reads from memory cache."""
    
    def __init__(self):
        self._files: Dict[Path, str] = {}
    
    async def load_file(self, path: Path) -> str:
        """Load file content from memory."""
        if path not in self._files:
            raise FileNotFoundError(f"File not found in memory: {path}")
        return self._files[path]
    
    def exists(self, path: Path) -> bool:
        """Check if file exists in memory."""
        return path in self._files
    
    def set_file(self, path: Path, content: str) -> None:
        """Store file content in memory."""
        self._files[path] = content
    
    def remove_file(self, path: Path) -> None:
        """Remove file from memory."""
        self._files.pop(path, None)


class FileSystemWatcher(FileSystemEventHandler):
    """Watches for file system changes."""
    
    def __init__(self, vfs: 'VFS'):
        self.vfs = vfs
        self._change_queue: asyncio.Queue[FileChange] = asyncio.Queue()
    
    def on_modified(self, event):
        if not event.is_directory and self._is_dml_file(event.src_path):
            change = FileChange(Path(event.src_path), FileChangeType.MODIFIED)
            asyncio.create_task(self._change_queue.put(change))
    
    def on_created(self, event):
        if not event.is_directory and self._is_dml_file(event.src_path):
            change = FileChange(Path(event.src_path), FileChangeType.CREATED)
            asyncio.create_task(self._change_queue.put(change))
    
    def on_deleted(self, event):
        if not event.is_directory and self._is_dml_file(event.src_path):
            change = FileChange(Path(event.src_path), FileChangeType.DELETED)
            asyncio.create_task(self._change_queue.put(change))
    
    def _is_dml_file(self, path: str) -> bool:
        """Check if the file is a DML file."""
        return Path(path).suffix.lower() == '.dml'
    
    async def get_change(self) -> FileChange:
        """Get the next file change."""
        return await self._change_queue.get()


class VFS:
    """Virtual File System for managing DML files."""
    
    def __init__(self, use_real_files: bool = True):
        self._file_cache: Dict[Path, str] = {}
        self._dirty_files: Set[Path] = set()
        self._watched_directories: Set[Path] = set()
        self._file_loader: FileLoader = RealFileLoader() if use_real_files else MemoryFileLoader()
        self._watcher: Optional[FileSystemWatcher] = None
        self._observer: Optional[Observer] = None
        self._change_callbacks: List[callable] = []
    
    async def read_file(self, path: Path) -> str:
        """
        Read file content, using cache if available.
        
        Args:
            path: Path to the file
            
        Returns:
            File content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = path.resolve()
        
        # Check cache first
        if path in self._file_cache and path not in self._dirty_files:
            logger.debug(f"Reading {path} from cache")
            return self._file_cache[path]
        
        # Load from file system
        logger.debug(f"Loading {path} from disk")
        content = await self._file_loader.load_file(path)
        
        # Update cache
        self._file_cache[path] = content
        self._dirty_files.discard(path)
        
        return content
    
    def write_file(self, path: Path, content: str) -> None:
        """
        Write file content to cache (not to disk immediately).
        
        Args:
            path: Path to the file
            content: Content to write
        """
        path = path.resolve()
        self._file_cache[path] = content
        self._dirty_files.add(path)
        logger.debug(f"Cached changes for {path}")
    
    async def save_file(self, path: Path) -> None:
        """
        Save cached file content to disk.
        
        Args:
            path: Path to the file to save
        """
        path = path.resolve()
        
        if path not in self._file_cache:
            raise ValueError(f"No cached content for {path}")
        
        content = self._file_cache[path]
        
        # Write to disk
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        self._dirty_files.discard(path)
        logger.debug(f"Saved {path} to disk")
    
    def remove_file(self, path: Path) -> None:
        """
        Remove file from cache.
        
        Args:
            path: Path to the file to remove
        """
        path = path.resolve()
        self._file_cache.pop(path, None)
        self._dirty_files.discard(path)
        logger.debug(f"Removed {path} from cache")
    
    def file_exists(self, path: Path) -> bool:
        """
        Check if a file exists (in cache or on disk).
        
        Args:
            path: Path to check
            
        Returns:
            True if file exists
        """
        path = path.resolve()
        return path in self._file_cache or self._file_loader.exists(path)
    
    def is_dirty(self, path: Path) -> bool:
        """
        Check if a file has unsaved changes.
        
        Args:
            path: Path to check
            
        Returns:
            True if file has unsaved changes
        """
        return path.resolve() in self._dirty_files
    
    def get_dirty_files(self) -> Set[Path]:
        """Get all files with unsaved changes."""
        return self._dirty_files.copy()
    
    def watch_directory(self, directory: Path) -> None:
        """
        Start watching a directory for changes.
        
        Args:
            directory: Directory to watch
        """
        directory = directory.resolve()
        
        if directory in self._watched_directories:
            return
        
        if self._observer is None:
            self._observer = Observer()
            self._watcher = FileSystemWatcher(self)
            self._observer.start()
        
        self._observer.schedule(self._watcher, str(directory), recursive=True)
        self._watched_directories.add(directory)
        logger.info(f"Watching directory: {directory}")
    
    def stop_watching(self) -> None:
        """Stop watching all directories."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            self._watcher = None
            self._watched_directories.clear()
            logger.info("Stopped file watching")
    
    def add_change_callback(self, callback: callable) -> None:
        """
        Add a callback to be called when files change.
        
        Args:
            callback: Function to call with FileChange objects
        """
        self._change_callbacks.append(callback)
    
    async def process_changes(self) -> None:
        """Process file system changes continuously."""
        if not self._watcher:
            return
        
        while True:
            try:
                change = await self._watcher.get_change()
                logger.debug(f"File change detected: {change}")
                
                # Invalidate cache for changed files
                if change.change_type in (FileChangeType.MODIFIED, FileChangeType.DELETED):
                    self._file_cache.pop(change.path, None)
                    self._dirty_files.discard(change.path)
                
                # Notify callbacks
                for callback in self._change_callbacks:
                    try:
                        await callback(change)
                    except Exception as e:
                        logger.error(f"Error in change callback: {e}")
                        
            except Exception as e:
                logger.error(f"Error processing file changes: {e}")
    
    def clear_cache(self) -> None:
        """Clear the file cache."""
        self._file_cache.clear()
        self._dirty_files.clear()
        logger.debug("Cleared file cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_files": len(self._file_cache),
            "dirty_files": len(self._dirty_files),
            "watched_directories": len(self._watched_directories)
        }


# Export main classes
__all__ = [
    "VFS",
    "FileLoader",
    "RealFileLoader",
    "MemoryFileLoader",
    "FileChange",
    "FileChangeType",
    "FileSystemWatcher"
]