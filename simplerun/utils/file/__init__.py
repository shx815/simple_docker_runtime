"""
File utilities package for simple_docker_runtime.

This package contains file viewing and manipulation utilities.
"""

from .file_viewer import generate_file_viewer_html

__all__ = [
    'generate_file_viewer_html'
] 