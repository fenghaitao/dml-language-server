"""
File management utilities for the DML Language Server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
from pathlib import Path
from typing import List, Set, Optional, Dict
import re
from dataclasses import dataclass

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about a DML file."""
    path: Path
    is_device: bool = False
    is_library: bool = False
    dml_version: Optional[str] = None
    imports: List[str] = None
    
    def __post_init__(self):
        if self.imports is None:
            self.imports = []


class FileManager:
    """Manages DML file discovery, categorization, and dependencies."""
    
    def __init__(self, config: Config):
        self.config = config
        self._file_cache: Dict[Path, FileInfo] = {}
        self._dependency_graph: Dict[Path, Set[Path]] = {}
        self._reverse_dependencies: Dict[Path, Set[Path]] = {}
    
    def discover_dml_files(self, root_directory: Path, recursive: bool = True) -> List[Path]:
        """
        Discover all DML files in a directory.
        
        Args:
            root_directory: Directory to search in
            recursive: Whether to search recursively
            
        Returns:
            List of DML file paths
        """
        dml_files = []
        
        if not root_directory.exists() or not root_directory.is_dir():
            logger.warning(f"Directory does not exist or is not a directory: {root_directory}")
            return dml_files
        
        try:
            if recursive:
                pattern = "**/*.dml"
            else:
                pattern = "*.dml"
            
            for file_path in root_directory.glob(pattern):
                if file_path.is_file():
                    dml_files.append(file_path.resolve())
            
            logger.info(f"Discovered {len(dml_files)} DML files in {root_directory}")
            
        except Exception as e:
            logger.error(f"Failed to discover DML files in {root_directory}: {e}")
        
        return dml_files
    
    def get_file_info(self, file_path: Path) -> Optional[FileInfo]:
        """
        Get information about a DML file.
        
        Args:
            file_path: Path to the DML file
            
        Returns:
            FileInfo object or None if file cannot be analyzed
        """
        file_path = file_path.resolve()
        
        # Check cache first
        if file_path in self._file_cache:
            return self._file_cache[file_path]
        
        try:
            info = self._analyze_file(file_path)
            self._file_cache[file_path] = info
            return info
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return None
    
    def _analyze_file(self, file_path: Path) -> FileInfo:
        """
        Analyze a DML file to extract information.
        
        Args:
            file_path: Path to the DML file
            
        Returns:
            FileInfo object
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        info = FileInfo(path=file_path)
        
        # Extract DML version
        version_match = re.search(r'dml\s+(\d+\.\d+)', content)
        if version_match:
            info.dml_version = version_match.group(1)
        
        # Check if it's a device file (contains 'device' keyword)
        if re.search(r'\bdevice\s+\w+', content):
            info.is_device = True
        
        # Check if it's a library file (contains 'library' keyword or is in lib directory)
        if re.search(r'\blibrary\s+\w+', content) or 'lib' in file_path.parts:
            info.is_library = True
        
        # Extract imports
        info.imports = self._extract_imports(content)
        
        # Build dependency information
        self._update_dependencies(file_path, info.imports)
        
        logger.debug(f"Analyzed {file_path}: device={info.is_device}, library={info.is_library}, "
                    f"version={info.dml_version}, imports={len(info.imports)}")
        
        return info
    
    def _extract_imports(self, content: str) -> List[str]:
        """
        Extract import statements from DML content.
        
        Args:
            content: DML file content
            
        Returns:
            List of imported file names
        """
        imports = []
        
        # Match import statements: import "filename.dml"
        import_pattern = r'import\s+"([^"]+)"'
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))
        
        # Match include statements: #include "filename.dml"
        include_pattern = r'#include\s+"([^"]+)"'
        for match in re.finditer(include_pattern, content):
            imports.append(match.group(1))
        
        return imports
    
    def _update_dependencies(self, file_path: Path, imports: List[str]) -> None:
        """
        Update dependency graph for a file.
        
        Args:
            file_path: Path to the file
            imports: List of imported file names
        """
        # Resolve import paths
        resolved_imports = set()
        include_paths = self.config.get_include_paths_for_file(file_path)
        
        for import_name in imports:
            resolved_path = self._resolve_import_path(import_name, file_path, include_paths)
            if resolved_path:
                resolved_imports.add(resolved_path)
        
        # Update forward dependencies
        self._dependency_graph[file_path] = resolved_imports
        
        # Update reverse dependencies
        for imported_file in resolved_imports:
            if imported_file not in self._reverse_dependencies:
                self._reverse_dependencies[imported_file] = set()
            self._reverse_dependencies[imported_file].add(file_path)
    
    def _resolve_import_path(self, import_name: str, current_file: Path, include_paths: List[Path]) -> Optional[Path]:
        """
        Resolve an import statement to an absolute path.
        
        Args:
            import_name: Name of the imported file
            current_file: Path to the file containing the import
            include_paths: List of include directories
            
        Returns:
            Resolved path or None if not found
        """
        # First try relative to current file
        current_dir = current_file.parent
        candidate = current_dir / import_name
        if candidate.exists():
            return candidate.resolve()
        
        # Try include paths
        for include_path in include_paths:
            candidate = include_path / import_name
            if candidate.exists():
                return candidate.resolve()
        
        logger.debug(f"Could not resolve import '{import_name}' from {current_file}")
        return None
    
    def get_dependencies(self, file_path: Path) -> Set[Path]:
        """
        Get files that the given file depends on.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Set of dependency file paths
        """
        file_path = file_path.resolve()
        return self._dependency_graph.get(file_path, set())
    
    def get_dependents(self, file_path: Path) -> Set[Path]:
        """
        Get files that depend on the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Set of dependent file paths
        """
        file_path = file_path.resolve()
        return self._reverse_dependencies.get(file_path, set())
    
    def get_all_dependencies(self, file_path: Path, visited: Optional[Set[Path]] = None) -> Set[Path]:
        """
        Get all dependencies (direct and transitive) of a file.
        
        Args:
            file_path: Path to the file
            visited: Set of already visited files (for cycle detection)
            
        Returns:
            Set of all dependency file paths
        """
        if visited is None:
            visited = set()
        
        file_path = file_path.resolve()
        
        if file_path in visited:
            logger.warning(f"Circular dependency detected involving {file_path}")
            return set()
        
        visited.add(file_path)
        all_deps = set()
        
        direct_deps = self.get_dependencies(file_path)
        all_deps.update(direct_deps)
        
        for dep in direct_deps:
            transitive_deps = self.get_all_dependencies(dep, visited.copy())
            all_deps.update(transitive_deps)
        
        return all_deps
    
    def get_all_dependents(self, file_path: Path, visited: Optional[Set[Path]] = None) -> Set[Path]:
        """
        Get all dependents (direct and transitive) of a file.
        
        Args:
            file_path: Path to the file
            visited: Set of already visited files (for cycle detection)
            
        Returns:
            Set of all dependent file paths
        """
        if visited is None:
            visited = set()
        
        file_path = file_path.resolve()
        
        if file_path in visited:
            return set()
        
        visited.add(file_path)
        all_dependents = set()
        
        direct_dependents = self.get_dependents(file_path)
        all_dependents.update(direct_dependents)
        
        for dependent in direct_dependents:
            transitive_dependents = self.get_all_dependents(dependent, visited.copy())
            all_dependents.update(transitive_dependents)
        
        return all_dependents
    
    def invalidate_file(self, file_path: Path) -> Set[Path]:
        """
        Invalidate cached information for a file and return affected files.
        
        Args:
            file_path: Path to the file that changed
            
        Returns:
            Set of files that need to be re-analyzed
        """
        file_path = file_path.resolve()
        
        # Files that need re-analysis
        affected_files = {file_path}
        
        # Add all files that depend on this file
        affected_files.update(self.get_all_dependents(file_path))
        
        # Remove from caches
        self._file_cache.pop(file_path, None)
        self._dependency_graph.pop(file_path, None)
        self._reverse_dependencies.pop(file_path, None)
        
        # Clean up reverse dependencies
        for deps in self._reverse_dependencies.values():
            deps.discard(file_path)
        
        logger.debug(f"Invalidated {file_path}, {len(affected_files)} files affected")
        
        return affected_files
    
    def get_device_files(self) -> List[Path]:
        """
        Get all device files from the cache.
        
        Returns:
            List of device file paths
        """
        device_files = []
        for file_path, info in self._file_cache.items():
            if info.is_device:
                device_files.append(file_path)
        return device_files
    
    def get_library_files(self) -> List[Path]:
        """
        Get all library files from the cache.
        
        Returns:
            List of library file paths
        """
        library_files = []
        for file_path, info in self._file_cache.items():
            if info.is_library:
                library_files.append(file_path)
        return library_files
    
    def is_dml_file(self, file_path: Path) -> bool:
        """
        Check if a file is a DML file based on extension.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file has .dml extension
        """
        return file_path.suffix.lower() == '.dml'
    
    def clear_cache(self) -> None:
        """Clear all cached file information."""
        self._file_cache.clear()
        self._dependency_graph.clear()
        self._reverse_dependencies.clear()
        logger.debug("Cleared file manager cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_files": len(self._file_cache),
            "dependency_entries": len(self._dependency_graph),
            "reverse_dependency_entries": len(self._reverse_dependencies)
        }