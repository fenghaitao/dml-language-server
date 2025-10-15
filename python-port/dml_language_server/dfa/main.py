"""
Main entry point for DFA (Device File Analyzer).

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

import click

from . import DMLAnalyzer, ReportGenerator, AnalysisType
from ..config import Config
from .. import version

logger = logging.getLogger(__name__)


@click.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    '--recursive', '-r',
    is_flag=True,
    help='Recursively analyze directories'
)
@click.option(
    '--analysis-type', '-t',
    type=click.Choice(['syntax', 'semantic', 'dependencies', 'symbols', 'metrics', 'all']),
    multiple=True,
    default=['all'],
    help='Types of analysis to perform (can be specified multiple times)'
)
@click.option(
    '--compile-info',
    type=click.Path(exists=True, path_type=Path),
    help='Path to DML compile commands file'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file for the report (default: stdout)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['summary', 'detailed', 'json']),
    default='summary',
    help='Report format'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
@click.option(
    '--quiet', '-q',
    is_flag=True,
    help='Suppress all output except errors'
)
@click.option(
    '--check-deps',
    is_flag=True,
    help='Check for circular dependencies'
)
@click.option(
    '--find-orphans',
    is_flag=True,
    help='Find orphaned files (not referenced by others)'
)
@click.option(
    '--errors-only',
    is_flag=True,
    help='Only report files with errors'
)
@click.version_option(version=version())
def main(
    paths: tuple,
    recursive: bool,
    analysis_type: tuple,
    compile_info: Optional[Path],
    output: Optional[Path],
    format: str,
    verbose: bool,
    quiet: bool,
    check_deps: bool,
    find_orphans: bool,
    errors_only: bool
) -> None:
    """
    DFA (Device File Analyzer) - Analyze DML device files.
    
    Analyzes DML files for syntax errors, semantic issues, dependencies,
    and code metrics. Can analyze individual files or entire directories.
    
    PATHS: One or more files or directories to analyze
    """
    # Set up logging
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING
    
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s',
        stream=sys.stderr
    )
    
    # Validate arguments
    if not paths:
        click.echo("Error: No paths specified", err=True)
        sys.exit(1)
    
    # Parse analysis types
    analysis_types = []
    if 'all' in analysis_type:
        analysis_types = list(AnalysisType)
    else:
        type_map = {
            'syntax': AnalysisType.SYNTAX,
            'semantic': AnalysisType.SEMANTIC,
            'dependencies': AnalysisType.DEPENDENCIES,
            'symbols': AnalysisType.SYMBOLS,
            'metrics': AnalysisType.METRICS
        }
        analysis_types = [type_map[t] for t in analysis_type]
    
    try:
        # Initialize configuration
        config = Config()
        
        # Load compile commands if provided
        if compile_info:
            config.load_compile_commands(compile_info)
            if not quiet:
                click.echo(f"Loaded compile commands from {compile_info}", err=True)
        
        # Initialize analyzer
        analyzer = DMLAnalyzer(config)
        
        # Collect all files to analyze
        all_files = []
        for path in paths:
            if path.is_file():
                if analyzer.file_manager.is_dml_file(path):
                    all_files.append(path)
                else:
                    logger.warning(f"Skipping non-DML file: {path}")
            elif path.is_dir():
                dml_files = analyzer.file_manager.discover_dml_files(path, recursive)
                all_files.extend(dml_files)
                if not quiet:
                    click.echo(f"Found {len(dml_files)} DML files in {path}", err=True)
            else:
                logger.error(f"Invalid path: {path}")
                sys.exit(1)
        
        if not all_files:
            click.echo("No DML files found to analyze", err=True)
            sys.exit(1)
        
        if not quiet:
            click.echo(f"Analyzing {len(all_files)} files...", err=True)
        
        # Perform analysis
        results = []
        for file_path in all_files:
            if not quiet and verbose:
                click.echo(f"Analyzing {file_path}...", err=True)
            
            try:
                result = analyzer.analyze_file(file_path, analysis_types)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze {file_path}: {e}")
        
        # Filter results if requested
        if errors_only:
            results = [r for r in results if r.errors]
        
        # Special analysis modes
        if check_deps:
            circular_deps = analyzer.find_circular_dependencies(all_files)
            if circular_deps:
                click.echo("\nCircular Dependencies Found:", err=True)
                for cycle in circular_deps:
                    cycle_str = " -> ".join(str(p) for p in cycle)
                    click.echo(f"  {cycle_str}", err=True)
            else:
                if not quiet:
                    click.echo("No circular dependencies found", err=True)
        
        if find_orphans:
            orphans = analyzer.get_orphaned_files(all_files)
            if orphans:
                click.echo("\nOrphaned Files:", err=True)
                for orphan in orphans:
                    click.echo(f"  {orphan}", err=True)
            else:
                if not quiet:
                    click.echo("No orphaned files found", err=True)
        
        # Generate report
        report_generator = ReportGenerator()
        
        if format == 'json':
            import json
            report_data = []
            for result in results:
                report_data.append({
                    'file_path': str(result.file_path),
                    'analysis_types': [t.value for t in result.analysis_types],
                    'error_count': len(result.errors),
                    'errors': [
                        {
                            'kind': error.kind.value,
                            'message': error.message,
                            'severity': error.severity.value,
                            'line': error.span.start.line + 1,
                            'column': error.span.start.column + 1
                        }
                        for error in result.errors
                    ],
                    'symbol_count': len(result.symbols),
                    'symbols': [
                        {
                            'name': symbol.name,
                            'kind': symbol.kind.value,
                            'line': symbol.location.span.start.line + 1,
                            'column': symbol.location.span.start.column + 1
                        }
                        for symbol in result.symbols
                    ],
                    'dependencies': [str(dep) for dep in result.dependencies],
                    'dependents': [str(dep) for dep in result.dependents],
                    'metrics': result.metrics
                })
            
            report = json.dumps({
                'summary': {
                    'total_files': len(results),
                    'total_errors': sum(len(r.errors) for r in results),
                    'total_symbols': sum(len(r.symbols) for r in results)
                },
                'files': report_data
            }, indent=2)
        
        elif format == 'detailed':
            report = report_generator.generate_detailed_report(results)
        else:  # summary
            report = report_generator.generate_summary_report(results)
        
        # Output report
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(report)
            if not quiet:
                click.echo(f"Report written to {output}", err=True)
        else:
            click.echo(report)
        
        # Exit with error code if there were errors
        total_errors = sum(len(result.errors) for result in results)
        if total_errors > 0:
            if not quiet:
                click.echo(f"Analysis completed with {total_errors} errors", err=True)
            sys.exit(1)
        else:
            if not quiet:
                click.echo("Analysis completed successfully", err=True)
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=verbose)
        sys.exit(1)


@click.command()
@click.argument('file_path', type=click.Path(exists=True, path_type=Path))
@click.option('--format', type=click.Choice(['text', 'dot', 'json']), default='text')
def deps(file_path: Path, format: str) -> None:
    """Show dependencies for a specific DML file."""
    try:
        config = Config()
        analyzer = DMLAnalyzer(config)
        
        dependencies = analyzer.file_manager.get_dependencies(file_path)
        dependents = analyzer.file_manager.get_dependents(file_path)
        
        if format == 'json':
            import json
            data = {
                'file': str(file_path),
                'dependencies': [str(dep) for dep in dependencies],
                'dependents': [str(dep) for dep in dependents]
            }
            click.echo(json.dumps(data, indent=2))
        
        elif format == 'dot':
            click.echo("digraph dependencies {")
            click.echo(f'  "{file_path}";')
            for dep in dependencies:
                click.echo(f'  "{file_path}" -> "{dep}";')
            for dependent in dependents:
                click.echo(f'  "{dependent}" -> "{file_path}";')
            click.echo("}")
        
        else:  # text
            click.echo(f"Dependencies for {file_path}:")
            click.echo(f"  Depends on ({len(dependencies)}):")
            for dep in dependencies:
                click.echo(f"    {dep}")
            click.echo(f"  Depended on by ({len(dependents)}):")
            for dependent in dependents:
                click.echo(f"    {dependent}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.group()
def cli():
    """DFA (Device File Analyzer) - DML analysis tools."""
    pass


cli.add_command(main, name='analyze')
cli.add_command(deps, name='deps')


if __name__ == "__main__":
    cli()