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


def sha256_of_paths(paths: T.List[Path]) -> str:
    """
    Get the sha256 of list of paths, in the order you specified.

    If a path is a dir, then the sha256 of the dir is the sha256 of all files
    in a sorted order, which is deterministic.
    """
    hashes = list()

    for path in paths:
        if path.is_dir():
            for p in sorted(path.glob("**/*"), key=lambda x: str(x)):
                hashes.append(sha256_of_bytes(p.read_bytes()))
        elif path.is_file():
            hashes.append(sha256_of_bytes(path.read_bytes()))
        else:
            pass
    return sha256_of_bytes("".join(hashes).encode("utf-8"))


def ensure_exact_one_true(lst: T.List[bool]):
    if sum(lst) != 1:
        raise ValueError(f"Expected exactly one True, but got {lst}")


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
