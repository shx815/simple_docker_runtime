"""Simplerun package root.

This module exposes minimal package metadata and common paths without importing
submodules that may have heavy side-effects. It helps both runtime and tests
resolve the package cleanly in different environments (installed or source).
"""

from importlib import metadata as _metadata
from pathlib import Path as _Path

try:
    __version__ = _metadata.version("simple-docker-runtime")
except _metadata.PackageNotFoundError:  # When running from source without install
    __version__ = "0.1.0"

# Useful package paths
PACKAGE_DIR = _Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent

__all__ = [
    "__version__",
    "PACKAGE_DIR",
    "REPO_ROOT",
]
