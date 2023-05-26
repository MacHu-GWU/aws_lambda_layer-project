# -*- coding: utf-8 -*-

"""
Build Python source distribution.
"""

import typing as T
import os
import contextlib
import subprocess
from pathlib import Path


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


def build_dist_with_python(
    dir_project_root: T.Union[str, Path],
    path_bin_python: T.Union[str, Path],
    verbose: bool = False,
):
    """
    Build the source distribution with ``python setup.py ...``.

    :param dir_project_root: the root directory of your project, it should have
        a setup.py or pyproject.toml file
    :param path_bin_python: the path to python executable, usually the
        virtualenv python
    :param verbose: show verbose output or not

    Reference: https://packaging.python.org/en/latest/tutorials/packaging-projects/
    """
    dir_project_root = Path(dir_project_root).absolute()
    path_bin_python = Path(path_bin_python).absolute()

    with temp_cwd(dir_project_root):
        args = [
            f"{path_bin_python}",
            "setup.py",
            "sdist",
            "bdist_wheel",
            "--universal",
        ]
        subprocess.run(args, check=True, capture_output=not verbose)


def build_dist_with_python_build(
    dir_project_root: T.Union[str, Path],
    path_bin_python: T.Union[str, Path],
    verbose: bool = False,
):
    """
    Build the source distribution with ``python-build``.

    :param dir_project_root: the root directory of your project, it should have
        a setup.py or pyproject.toml file
    :param path_bin_python: the path to python executable, usually the
        virtualenv python
    :param verbose: show verbose output or not

    Reference: https://pypa-build.readthedocs.io/en/latest/
    """
    dir_project_root = Path(dir_project_root).absolute()
    path_bin_python = Path(path_bin_python).absolute()
    with temp_cwd(dir_project_root):
        args = [
            f"{path_bin_python}",
            "-m",
            "build",
            "--sdist",
            "--wheel",
        ]
        subprocess.run(args, check=True, capture_output=not verbose)


def build_dist_with_poetry_build(
    dir_project_root: T.Union[str, Path],
    path_bin_poetry: T.Union[str, Path],
    verbose: bool = False,
):
    """
    :param dir_project_root: the root directory of your project, it should have
        a setup.py or pyproject.toml file
    :param path_bin_poetry: the path to poetry executable, could be simply "poetry"
    :param verbose: show verbose output or not

    Reference: https://python-poetry.org/docs/cli/#build
    """
    dir_project_root = Path(dir_project_root).absolute()
    path_bin_poetry = Path(path_bin_poetry)  # poetry could be a global command
    with temp_cwd(dir_project_root):
        args = [
            f"{path_bin_poetry}",
            "build",
        ]
        if verbose is False:
            args.append("--quiet")
        subprocess.run(args, check=True)
