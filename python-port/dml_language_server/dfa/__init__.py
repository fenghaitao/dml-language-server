"""
DFA (Device File Analyzer) - Analysis tool for DML files.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..config import Config
from ..file_management import FileManager, FileInfo
from ..analysis import DeviceAnalysis, DMLError
from ..lsp_data import DMLSymbol, DMLSymbolKind

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Types of analysis that can be performed."""
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    DEPENDENCIES = "dependencies"
    SYMBOLS = "symbols"
    METRICS = "metrics"


@dataclass
class AnalysisResult:
    """Result of file analysis."""
    file_path: Path
    analysis_types: List[AnalysisType]
    errors: List[DMLError]
    symbols: List[DMLSymbol]
    dependencies: Set[Path]
    dependents: Set[Path]
    metrics: Dict[str, Any]


@dataclass
class CodeMetrics:
    """Code metrics for a DML file."""
    lines_of_code: int
    comment_lines: int
    blank_lines: int
    symbol_count: int
    complexity_score: int
    device_count: int
    register_count: int
    field_count: int
    method_count: int


class DMLAnalyzer:
    """Analyzer for DML files."""
    
    def __init__(self, config: Config):
        self.config = config
        self.file_manager = FileManager(config)
        self.analysis_engine = DeviceAnalysis(config, self.file_manager)
    
    def analyze_file(
        self, 
        file_path: Path, 
        analysis_types: List[AnalysisType] = None
    ) -> AnalysisResult:
        """
        Analyze a single DML file.
        
        Args:
            file_path: Path to the file to analyze
            analysis_types: Types of analysis to perform (default: all)
            
        Returns:
            Analysis result
        """
        if analysis_types is None:
            analysis_types = list(AnalysisType)
        
        file_path = file_path.resolve()
        
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return AnalysisResult(
                file_path=file_path,
                analysis_types=analysis_types,
                errors=[],
                symbols=[],
                dependencies=set(),
                dependents=set(),
                metrics={}
            )
        
        # Perform analysis
        errors = []
        symbols = []
        dependencies = set()
        dependents = set()
        metrics = {}
        
        # Syntax and semantic analysis
        if AnalysisType.SYNTAX in analysis_types or AnalysisType.SEMANTIC in analysis_types:
            try:
                from ..analysis.types import DMLErrorKind
                file_errors = self.analysis_engine.analyze_file(file_path, content)
                # Filter out import errors if no compile commands are provided
                # (matching Rust DFA behavior which doesn't report import errors)
                # Import errors require compile_commands.json with include paths to resolve
                if not self.config._compile_commands:
                    file_errors = [e for e in file_errors if e.kind != DMLErrorKind.IMPORT_ERROR]
                errors.extend(file_errors)
                symbols = self.analysis_engine.get_all_symbols_in_file(file_path)
            except Exception as e:
                logger.error(f"Analysis failed for {file_path}: {e}")
        
        # Dependency analysis
        if AnalysisType.DEPENDENCIES in analysis_types:
            dependencies = self.file_manager.get_dependencies(file_path)
            dependents = self.file_manager.get_dependents(file_path)
        
        # Metrics analysis
        if AnalysisType.METRICS in analysis_types:
            metrics = self._calculate_metrics(file_path, content, symbols)
        
        return AnalysisResult(
            file_path=file_path,
            analysis_types=analysis_types,
            errors=errors,
            symbols=symbols,
            dependencies=dependencies,
            dependents=dependents,
            metrics=metrics
        )
    
    def analyze_directory(
        self, 
        directory_path: Path, 
        recursive: bool = True,
        analysis_types: List[AnalysisType] = None
    ) -> List[AnalysisResult]:
        """
        Analyze all DML files in a directory.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to search recursively
            analysis_types: Types of analysis to perform
            
        Returns:
            List of analysis results
        """
        dml_files = self.file_manager.discover_dml_files(directory_path, recursive)
        results = []
        
        for file_path in dml_files:
            result = self.analyze_file(file_path, analysis_types)
            results.append(result)
        
        return results
    
    def _calculate_metrics(self, file_path: Path, content: str, symbols: List[DMLSymbol]) -> Dict[str, Any]:
        """Calculate code metrics for a file."""
        lines = content.splitlines()
        
        # Count different types of lines
        lines_of_code = 0
        comment_lines = 0
        blank_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith('//') or stripped.startswith('/*'):
                comment_lines += 1
            else:
                lines_of_code += 1
        
        # Count symbols by type
        symbol_counts = {}
        for symbol_kind in DMLSymbolKind:
            symbol_counts[symbol_kind.value] = 0
        
        for symbol in symbols:
            symbol_counts[symbol.kind.value] += 1
        
        # Calculate complexity (simplified)
        complexity_score = len(symbols) + len([s for s in symbols if s.children])
        
        metrics = CodeMetrics(
            lines_of_code=lines_of_code,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            symbol_count=len(symbols),
            complexity_score=complexity_score,
            device_count=symbol_counts.get('device', 0),
            register_count=symbol_counts.get('register', 0),
            field_count=symbol_counts.get('field', 0),
            method_count=symbol_counts.get('method', 0)
        )
        
        return {
            'lines_of_code': metrics.lines_of_code,
            'comment_lines': metrics.comment_lines,
            'blank_lines': metrics.blank_lines,
            'total_lines': len(lines),
            'symbol_count': metrics.symbol_count,
            'complexity_score': metrics.complexity_score,
            'symbol_breakdown': symbol_counts,
            'comment_ratio': metrics.comment_lines / max(1, len(lines)),
            'code_density': metrics.lines_of_code / max(1, len(lines))
        }
    
    def generate_dependency_graph(self, files: List[Path]) -> Dict[str, List[str]]:
        """
        Generate a dependency graph for a set of files.
        
        Args:
            files: List of file paths
            
        Returns:
            Dictionary mapping file paths to their dependencies
        """
        graph = {}
        
        for file_path in files:
            dependencies = self.file_manager.get_dependencies(file_path)
            graph[str(file_path)] = [str(dep) for dep in dependencies]
        
        return graph
    
    def find_circular_dependencies(self, files: List[Path]) -> List[List[Path]]:
        """
        Find circular dependencies among files.
        
        Args:
            files: List of file paths to check
            
        Returns:
            List of circular dependency chains
        """
        circular_deps = []
        visited = set()
        
        def dfs(file_path: Path, path: List[Path], rec_stack: Set[Path]):
            if file_path in rec_stack:
                # Found a cycle
                cycle_start = path.index(file_path)
                cycle = path[cycle_start:] + [file_path]
                circular_deps.append(cycle)
                return
            
            if file_path in visited:
                return
            
            visited.add(file_path)
            rec_stack.add(file_path)
            path.append(file_path)
            
            dependencies = self.file_manager.get_dependencies(file_path)
            for dep in dependencies:
                dfs(dep, path.copy(), rec_stack.copy())
            
            rec_stack.remove(file_path)
        
        for file_path in files:
            if file_path not in visited:
                dfs(file_path, [], set())
        
        return circular_deps
    
    def get_orphaned_files(self, files: List[Path]) -> List[Path]:
        """
        Find files that are not referenced by any other file.
        
        Args:
            files: List of file paths to check
            
        Returns:
            List of orphaned files
        """
        orphaned = []
        
        for file_path in files:
            dependents = self.file_manager.get_dependents(file_path)
            if not dependents:
                file_info = self.file_manager.get_file_info(file_path)
                # Skip device files as they are typically top-level
                if file_info and not file_info.is_device:
                    orphaned.append(file_path)
        
        return orphaned


class ReportGenerator:
    """Generator for analysis reports."""
    
    def __init__(self):
        pass
    
    def generate_summary_report(self, results: List[AnalysisResult]) -> str:
        """Generate a summary report from analysis results."""
        if not results:
            return "No files analyzed."
        
        total_files = len(results)
        total_errors = sum(len(result.errors) for result in results)
        total_symbols = sum(len(result.symbols) for result in results)
        
        # Count files by type
        device_files = sum(1 for result in results 
                          if any(s.kind == DMLSymbolKind.DEVICE for s in result.symbols))
        
        report = f"""DML Analysis Summary
{'=' * 50}

Files analyzed: {total_files}
Device files: {device_files}
Library files: {total_files - device_files}

Total errors: {total_errors}
Total symbols: {total_symbols}

"""
        
        if total_errors > 0:
            report += "Files with errors:\n"
            for result in results:
                if result.errors:
                    report += f"  {result.file_path}: {len(result.errors)} errors\n"
            report += "\n"
        
        # Metrics summary
        if results and results[0].metrics:
            total_loc = sum(result.metrics.get('lines_of_code', 0) for result in results)
            total_comments = sum(result.metrics.get('comment_lines', 0) for result in results)
            avg_complexity = sum(result.metrics.get('complexity_score', 0) for result in results) / total_files
            
            report += f"Code Metrics:\n"
            report += f"  Total lines of code: {total_loc}\n"
            report += f"  Total comment lines: {total_comments}\n"
            report += f"  Average complexity: {avg_complexity:.1f}\n"
            report += f"  Comment ratio: {total_comments / max(1, total_loc + total_comments):.2%}\n"
        
        return report
    
    def generate_detailed_report(self, results: List[AnalysisResult]) -> str:
        """Generate a detailed report from analysis results."""
        if not results:
            return "No files analyzed."
        
        report = "DML Detailed Analysis Report\n"
        report += "=" * 50 + "\n\n"
        
        for result in results:
            report += f"File: {result.file_path}\n"
            report += "-" * 40 + "\n"
            
            # Errors
            if result.errors:
                report += f"Errors ({len(result.errors)}):\n"
                for error in result.errors:
                    report += f"  {error.severity.value}: {error.message} at {error.span}\n"
                report += "\n"
            
            # Symbols
            if result.symbols:
                report += f"Symbols ({len(result.symbols)}):\n"
                symbol_groups = {}
                for symbol in result.symbols:
                    kind = symbol.kind.value
                    if kind not in symbol_groups:
                        symbol_groups[kind] = []
                    symbol_groups[kind].append(symbol.name)
                
                for kind, names in symbol_groups.items():
                    report += f"  {kind}: {', '.join(names)}\n"
                report += "\n"
            
            # Dependencies
            if result.dependencies:
                report += f"Dependencies ({len(result.dependencies)}):\n"
                for dep in result.dependencies:
                    report += f"  {dep}\n"
                report += "\n"
            
            # Metrics
            if result.metrics:
                report += "Metrics:\n"
                for key, value in result.metrics.items():
                    if isinstance(value, float):
                        report += f"  {key}: {value:.2f}\n"
                    else:
                        report += f"  {key}: {value}\n"
                report += "\n"
            
            report += "\n"
        
        return report


# Export main classes
__all__ = [
    "DMLAnalyzer",
    "ReportGenerator",
    "AnalysisResult",
    "AnalysisType",
    "CodeMetrics"
]