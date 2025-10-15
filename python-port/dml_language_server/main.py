"""
Main entry point for the DML Language Server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from . import version
from .cmd import run_cli
from .server import run_server
from .vfs import VFS


logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--cli",
    is_flag=True,
    help="Starts the DLS in command line mode"
)
@click.option(
    "--compile-info",
    type=click.Path(exists=True, path_type=Path),
    help="Optional DML compile-info file (cli only)"
)
@click.option(
    "--linting/--no-linting",
    default=True,
    help="Turn linting on or off (default on)"
)
@click.option(
    "--lint-cfg",
    type=click.Path(exists=True, path_type=Path),
    help="Optional Lint CFG (cli only)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.version_option(version=version())
def main(
    cli: bool,
    compile_info: Optional[Path],
    linting: bool,
    lint_cfg: Optional[Path],
    verbose: bool
) -> None:
    """
    The DML language server binary.
    
    Communicates over stdin/stdout using the Language Server Protocol
    to provide syntactic and semantic analysis and feedback for DML files.
    """
    # Set up logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    logger.debug("DML Language Server starting")
    
    try:
        if cli:
            # Run in CLI mode
            logger.info("Starting DLS in CLI mode")
            exit_code = run_cli(compile_info, linting, lint_cfg)
            sys.exit(exit_code)
        else:
            # Run as LSP server
            logger.info("Starting DLS as LSP server")
            vfs = VFS()
            exit_code = asyncio.run(run_server(vfs))
            sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("DLS interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"DLS failed with error: {e}", exc_info=True)
        sys.exit(1)


def main_inner() -> int:
    """Internal main function for testing."""
    try:
        main()
        return 0
    except SystemExit as e:
        return e.code or 0
    except Exception:
        logger.exception("Unexpected error in main")
        return 1


if __name__ == "__main__":
    main()