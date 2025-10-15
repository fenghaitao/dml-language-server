"""
Configuration management for the DML Language Server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels supported by the server."""
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


@dataclass
class CompileInfo:
    """Information about how to compile a DML device."""
    includes: List[Path] = field(default_factory=list)
    dmlc_flags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompileInfo':
        """Create CompileInfo from dictionary."""
        return cls(
            includes=[Path(p) for p in data.get('includes', [])],
            dmlc_flags=data.get('dmlc_flags', [])
        )


@dataclass
class LintConfig:
    """Configuration for linting rules."""
    enabled_rules: List[str] = field(default_factory=list)
    disabled_rules: List[str] = field(default_factory=list)
    rule_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LintConfig':
        """Create LintConfig from dictionary."""
        return cls(
            enabled_rules=data.get('enabled_rules', []),
            disabled_rules=data.get('disabled_rules', []),
            rule_configs=data.get('rule_configs', {})
        )


@dataclass
class InitializationOptions:
    """Options that can be passed during LSP initialization."""
    compile_commands_dir: Optional[Path] = None
    compile_commands_file: Optional[Path] = None
    linting_enabled: bool = True
    lint_config_file: Optional[Path] = None
    max_diagnostics_per_file: int = 100
    log_level: LogLevel = LogLevel.INFO
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InitializationOptions':
        """Create InitializationOptions from dictionary."""
        log_level = LogLevel.INFO
        if 'log_level' in data:
            try:
                log_level = LogLevel(data['log_level'])
            except ValueError:
                logger.warning(f"Invalid log level: {data['log_level']}")
        
        return cls(
            compile_commands_dir=Path(data['compile_commands_dir']) if data.get('compile_commands_dir') else None,
            compile_commands_file=Path(data['compile_commands_file']) if data.get('compile_commands_file') else None,
            linting_enabled=data.get('linting_enabled', True),
            lint_config_file=Path(data['lint_config_file']) if data.get('lint_config_file') else None,
            max_diagnostics_per_file=data.get('max_diagnostics_per_file', 100),
            log_level=log_level
        )


class Config:
    """Main configuration class for the DML Language Server."""
    
    def __init__(self):
        self._compile_commands: Dict[Path, CompileInfo] = {}
        self._lint_config: Optional[LintConfig] = None
        self._initialization_options: Optional[InitializationOptions] = None
        self._workspace_root: Optional[Path] = None
        self._include_paths: List[Path] = []
        self._dmlc_flags: List[str] = []
    
    @property
    def workspace_root(self) -> Optional[Path]:
        """Get the workspace root directory."""
        return self._workspace_root
    
    @workspace_root.setter
    def workspace_root(self, path: Optional[Path]) -> None:
        """Set the workspace root directory."""
        self._workspace_root = path.resolve() if path else None
        logger.info(f"Workspace root set to: {self._workspace_root}")
    
    @property
    def initialization_options(self) -> Optional[InitializationOptions]:
        """Get initialization options."""
        return self._initialization_options
    
    def set_initialization_options(self, options: Dict[str, Any]) -> None:
        """Set initialization options from LSP initialize request."""
        self._initialization_options = InitializationOptions.from_dict(options)
        logger.info(f"Initialization options set: {self._initialization_options}")
        
        # Apply log level
        log_level_map = {
            LogLevel.ERROR: logging.ERROR,
            LogLevel.WARN: logging.WARNING,
            LogLevel.INFO: logging.INFO,
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.TRACE: logging.DEBUG  # Python doesn't have TRACE, use DEBUG
        }
        logging.getLogger().setLevel(log_level_map[self._initialization_options.log_level])
    
    def load_compile_commands(self, path: Path) -> None:
        """
        Load DML compile commands from a JSON file.
        
        The format is:
        {
          "<full path to device file>": {
            "includes": ["<include folders as full paths>"],
            "dmlc_flags": ["<flags passed to dmlc invocation>"]
          }
        }
        
        Args:
            path: Path to the compile commands JSON file
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._compile_commands.clear()
            
            for device_path_str, compile_info_data in data.items():
                device_path = Path(device_path_str).resolve()
                compile_info = CompileInfo.from_dict(compile_info_data)
                self._compile_commands[device_path] = compile_info
                
                logger.debug(f"Loaded compile info for {device_path}: {compile_info}")
            
            logger.info(f"Loaded compile commands for {len(self._compile_commands)} devices from {path}")
            
        except Exception as e:
            logger.error(f"Failed to load compile commands from {path}: {e}")
            raise
    
    def get_compile_info(self, device_path: Path) -> Optional[CompileInfo]:
        """
        Get compile information for a specific device file.
        
        Args:
            device_path: Path to the device file
            
        Returns:
            CompileInfo if found, None otherwise
        """
        device_path = device_path.resolve()
        return self._compile_commands.get(device_path)
    
    def get_include_paths_for_file(self, file_path: Path) -> List[Path]:
        """
        Get include paths for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of include paths
        """
        # First check if this file has specific compile info
        compile_info = self.get_compile_info(file_path)
        if compile_info:
            return compile_info.includes + self._include_paths
        
        # Check if any parent device includes this file
        file_path = file_path.resolve()
        for device_path, compile_info in self._compile_commands.items():
            if self._is_file_included_by_device(file_path, device_path):
                return compile_info.includes + self._include_paths
        
        # Return default include paths
        return self._include_paths
    
    def get_dmlc_flags_for_file(self, file_path: Path) -> List[str]:
        """
        Get DMLC flags for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of DMLC flags
        """
        # First check if this file has specific compile info
        compile_info = self.get_compile_info(file_path)
        if compile_info:
            return compile_info.dmlc_flags + self._dmlc_flags
        
        # Check if any parent device includes this file
        file_path = file_path.resolve()
        for device_path, compile_info in self._compile_commands.items():
            if self._is_file_included_by_device(file_path, device_path):
                return compile_info.dmlc_flags + self._dmlc_flags
        
        # Return default flags
        return self._dmlc_flags
    
    def _is_file_included_by_device(self, file_path: Path, device_path: Path) -> bool:
        """
        Check if a file is included (directly or indirectly) by a device.
        
        This is a simplified check - in a full implementation, this would
        need to parse the device file and follow all imports.
        """
        # For now, just check if the file is in the same directory or subdirectory
        try:
            file_path.relative_to(device_path.parent)
            return True
        except ValueError:
            return False
    
    def load_lint_config(self, path: Path) -> None:
        """
        Load lint configuration from a JSON file.
        
        Args:
            path: Path to the lint config JSON file
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._lint_config = LintConfig.from_dict(data)
            logger.info(f"Loaded lint config from {path}: {self._lint_config}")
            
        except Exception as e:
            logger.error(f"Failed to load lint config from {path}: {e}")
            raise
    
    @property
    def lint_config(self) -> Optional[LintConfig]:
        """Get lint configuration."""
        return self._lint_config
    
    def is_linting_enabled(self) -> bool:
        """Check if linting is enabled."""
        if self._initialization_options:
            return self._initialization_options.linting_enabled
        return True
    
    def get_max_diagnostics_per_file(self) -> int:
        """Get maximum number of diagnostics per file."""
        if self._initialization_options:
            return self._initialization_options.max_diagnostics_per_file
        return 100
    
    def add_include_path(self, path: Path) -> None:
        """Add a global include path."""
        path = path.resolve()
        if path not in self._include_paths:
            self._include_paths.append(path)
            logger.debug(f"Added include path: {path}")
    
    def add_dmlc_flag(self, flag: str) -> None:
        """Add a global DMLC flag."""
        if flag not in self._dmlc_flags:
            self._dmlc_flags.append(flag)
            logger.debug(f"Added DMLC flag: {flag}")
    
    def get_all_device_files(self) -> List[Path]:
        """Get all device files from compile commands."""
        return list(self._compile_commands.keys())
    
    def clear(self) -> None:
        """Clear all configuration."""
        self._compile_commands.clear()
        self._lint_config = None
        self._initialization_options = None
        self._workspace_root = None
        self._include_paths.clear()
        self._dmlc_flags.clear()
        logger.debug("Configuration cleared")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'workspace_root': str(self._workspace_root) if self._workspace_root else None,
            'compile_commands_count': len(self._compile_commands),
            'has_lint_config': self._lint_config is not None,
            'include_paths': [str(p) for p in self._include_paths],
            'dmlc_flags': self._dmlc_flags,
            'initialization_options': self._initialization_options.__dict__ if self._initialization_options else None
        }