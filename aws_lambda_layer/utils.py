# -*- coding: utf-8 -*-

import typing as T
import hashlib
import contextlib
import os
from pathlib import Path


def sha256_of_bytes(b: bytes) -> str:
    """
    Get the sha256 of bytes.
    """
    sha256 = hashlib.sha256()
    sha256.update(b)
    return sha256.hexdigest()


@contextlib.contextmanager
def temp_cwd(path: T.Union[str, Path]):
    """
    Temporarily set the current directory to target path.
    """
    path = Path(path).absolute()
    if not path.is_dir():
        raise ValueError(f"{path} is not a dir!")

    cwd = os.getcwd()
    os.chdir(f"{path}")
    try:
        yield path
    finally:
        os.chdir(cwd)
