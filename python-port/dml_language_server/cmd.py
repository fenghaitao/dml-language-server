"""
Command line interface for the DML Language Server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
from pathlib import Path
from typing import Optional

from .config import Config
from .file_management import FileManager
from .analysis import DeviceAnalysis
from .lint import LintEngine


logger = logging.getLogger(__name__)


def run_cli(
    compile_info_path: Optional[Path],
    linting_enabled: bool,
    lint_cfg_path: Optional[Path]
) -> int:
    """
    Run the DLS in command line mode.
    
    Args:
        compile_info_path: Optional path to DML compile commands file
        linting_enabled: Whether to enable linting
        lint_cfg_path: Optional path to lint configuration file
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.debug("Running DLS in CLI mode")
    
    try:
        # Initialize configuration
        config = Config()
        if compile_info_path:
            config.load_compile_commands(compile_info_path)
        
        # Initialize file manager
        file_manager = FileManager(config)
        
        # Initialize lint engine if enabled
        lint_engine = None
        if linting_enabled:
            lint_engine = LintEngine(config)
            if lint_cfg_path:
                lint_engine.load_config(lint_cfg_path)
        
        # Discover DML files in current directory
        dml_files = file_manager.discover_dml_files(Path.cwd())
        
        if not dml_files:
            logger.warning("No DML files found in current directory")
            return 0
        
        logger.info(f"Found {len(dml_files)} DML files to analyze")
        
        # Analyze each file
        total_errors = 0
        total_warnings = 0
        
        for dml_file in dml_files:
            logger.info(f"Analyzing {dml_file}")
            
            try:
                # Read file content
                content = dml_file.read_text(encoding='utf-8')
                
                # Create analysis
                analysis = DeviceAnalysis(config, file_manager)
                
                # Parse and analyze
                errors = analysis.analyze_file(dml_file, content)
                
                # Display syntax errors
                for error in errors:
                    print(f"{dml_file}:{error.line}:{error.column}: error: {error.message}")
                    total_errors += 1
                
                # Run linting if enabled
                if lint_engine:
                    warnings = lint_engine.lint_file(dml_file, content, analysis)
                    for warning in warnings:
                        print(f"{dml_file}:{warning.line}:{warning.column}: warning: {warning.message}")
                        total_warnings += 1
                        
            except Exception as e:
                logger.error(f"Failed to analyze {dml_file}: {e}")
                total_errors += 1
        
        # Print summary
        if total_errors > 0 or total_warnings > 0:
            print(f"\nSummary: {total_errors} errors, {total_warnings} warnings")
        else:
            print(f"\nAll {len(dml_files)} files analyzed successfully")
        
        return 1 if total_errors > 0 else 0
        
    except Exception as e:
        logger.error(f"CLI analysis failed: {e}", exc_info=True)
        return 1


def analyze_single_file(file_path: Path, config: Optional[Config] = None) -> int:
    """
    Analyze a single DML file and print results.
    
    Args:
        file_path: Path to the DML file to analyze
        config: Optional configuration to use
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return 1
    
    if not file_path.suffix.lower() == '.dml':
        logger.error(f"Not a DML file: {file_path}")
        return 1
    
    try:
        # Use default config if none provided
        if config is None:
            config = Config()
        
        # Initialize components
        file_manager = FileManager(config)
        analysis = DeviceAnalysis(config, file_manager)
        
        # Read and analyze file
        content = file_path.read_text(encoding='utf-8')
        errors = analysis.analyze_file(file_path, content)
        
        # Display results
        if errors:
            for error in errors:
                print(f"{file_path}:{error.line}:{error.column}: error: {error.message}")
            return 1
        else:
            print(f"{file_path}: OK")
            return 0
            
    except Exception as e:
        logger.error(f"Failed to analyze {file_path}: {e}")
        return 1