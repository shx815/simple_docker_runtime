from pathlib import Path
import os

import pytest

from simplerun.utils.file import files

_SANDBOX_ROOT = (Path(os.sep) / 'simplerun' / 'workspace').resolve()
SANDBOX_PATH_PREFIX = str(_SANDBOX_ROOT)
CONTAINER_PATH = str(_SANDBOX_ROOT)
HOST_PATH = 'workspace'


def test_resolve_path():
    assert (
        files.resolve_path('test.txt', SANDBOX_PATH_PREFIX, HOST_PATH, CONTAINER_PATH)
        == Path(HOST_PATH) / 'test.txt'
    )
    assert (
        files.resolve_path('subdir/test.txt', SANDBOX_PATH_PREFIX, HOST_PATH, CONTAINER_PATH)
        == Path(HOST_PATH) / 'subdir' / 'test.txt'
    )
    assert (
        files.resolve_path(
            Path(SANDBOX_PATH_PREFIX) / 'test.txt',
            SANDBOX_PATH_PREFIX,
            HOST_PATH,
            CONTAINER_PATH,
        )
        == Path(HOST_PATH) / 'test.txt'
    )
    assert (
        files.resolve_path(
            Path(SANDBOX_PATH_PREFIX) / 'subdir' / 'test.txt',
            SANDBOX_PATH_PREFIX,
            HOST_PATH,
            CONTAINER_PATH,
        )
        == Path(HOST_PATH) / 'subdir' / 'test.txt'
    )
    assert (
        files.resolve_path(
            Path(SANDBOX_PATH_PREFIX) / 'subdir' / '..' / 'test.txt',
            SANDBOX_PATH_PREFIX,
            HOST_PATH,
            CONTAINER_PATH,
        )
        == Path(HOST_PATH) / 'test.txt'
    )
    with pytest.raises(PermissionError):
        files.resolve_path(
            Path(SANDBOX_PATH_PREFIX) / '..' / 'test.txt',
            '/workspace',
            HOST_PATH,
            CONTAINER_PATH,
        )
    with pytest.raises(PermissionError):
        files.resolve_path(
            Path('..') / 'test.txt', SANDBOX_PATH_PREFIX, HOST_PATH, CONTAINER_PATH
        )
    with pytest.raises(PermissionError):
        files.resolve_path(
            Path(os.sep) / 'test.txt', SANDBOX_PATH_PREFIX, HOST_PATH, CONTAINER_PATH
        )
    assert (
        files.resolve_path('test.txt', f"{SANDBOX_PATH_PREFIX}/test", HOST_PATH, CONTAINER_PATH)
        == Path(HOST_PATH) / 'test' / 'test.txt'
    )
