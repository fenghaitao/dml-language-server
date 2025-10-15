"""
DML Language Server - Python Port

The DML Language Server (DLS) provides a server that runs in the background,
providing IDEs, editors, and other tools with information about DML device and
common code. It supports syntax error reporting, symbol search, 'goto-definition',
'goto-implementation', 'goto-reference', and 'goto-base'. It also has configurable
linting support.

This is a Python port of the original Rust implementation.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

__version__ = "0.9.14"
__author__ = "Intel Corporation"
__license__ = "Apache-2.0 OR MIT"

from typing import Optional
import logging

# Set up default logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def version() -> str:
    """Return the version string."""
    return __version__

def internal_error(message: str, *args) -> None:
    """Log an internal error message."""
    logger = logging.getLogger(__name__)
    if args:
        logger.error(f"Internal Error: {message.format(*args)}")
    else:
        logger.error(f"Internal Error: {message}")

# Export commonly used types and functions
__all__ = [
    "version",
    "internal_error",
    "__version__",
    "__author__",
    "__license__",
]