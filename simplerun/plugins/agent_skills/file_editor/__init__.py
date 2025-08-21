"""Local shim for openhands_aci.editor.file_editor to reduce dependency size."""

from .._aci.editor import file_editor

__all__ = ['file_editor']
