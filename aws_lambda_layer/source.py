# -*- coding: utf-8 -*-

"""
This module implements the automation of AWS Lambda deployment package building.
It stores the source artifacts in an S3 bucket with the following structure::

    s3://bucket/${s3dir_lambda}/source/0.1.1/source.zip
    s3://bucket/${s3dir_lambda}/source/0.1.2/source.zip
    s3://bucket/${s3dir_lambda}/source/0.1.3/source.zip
"""

import typing as T
import glob
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode

from s3pathlib import S3Path
from func_args import NOTHING
from boto_session_manager import BotoSesManager

from . import utils
from .context import BuildContext


def build_source_artifacts(
    path_setup_py_or_pyproject_toml: T.Union[str, Path],
    path_lambda_function: T.Union[str, Path],
    bin_pip: T.Union[str, Path],
    dir_build: T.Union[str, Path],
    quiet: bool = False,
) -> Path:
    """
    This function builds the source artifacts for the AWS Lambda deployment package.

    :param path_setup_py_or_pyproject_toml: example: ``/path/to/setup.py`` or
        ``/path/to/pyproject.toml``
    :param path_lambda_function: example: ``/path/to/lambda_function.py``
    :param dir_build: example: ``/path/to/build/lambda``
    :param bin_pip: example: ``/path/to/.venv/bin/pip``
    :param quiet: whether you want to suppress the output of cli commands

    :return: the ``/path/to/build/lambda/source.zip`` file
    """
    # resolve arguments
    path_setup_py_or_pyproject_toml = Path(path_setup_py_or_pyproject_toml).absolute()
    path_lambda_function = Path(path_lambda_function).absolute()
    bin_pip = Path(bin_pip).absolute()
    build_context = BuildContext.new(dir_build=dir_build)
    dir_project_root = path_setup_py_or_pyproject_toml.parent

    # clean up existing files
    shutil.rmtree(build_context.dir_deploy, ignore_errors=True)

    # install python library
    with utils.temp_cwd(dir_project_root):
        args = [
            f"{bin_pip}",
            "install",
            f"{dir_project_root}",
            "--no-dependencies",
            f"--target={build_context.dir_deploy}",
        ]
        if quiet:
            args.append("--quiet")
        subprocess.run(args, check=True)
    # copy lambda function entry point script
    shutil.copy(
        path_lambda_function,
        build_context.dir_deploy.joinpath(path_lambda_function.name),
    )

    # build source artifacts
    args = [
        "zip",
        f"{build_context.path_source_zip}",
        "-r",
        "-9",
    ]
    if quiet:
        args.append("-q")
    # the glob command depends on the current working directory
    with utils.temp_cwd(build_context.dir_deploy):
        args.extend(glob.glob("*"))
        subprocess.run(args, check=True)
    return build_context.path_source_zip


def upload_source_artifacts(
    bsm: "BotoSesManager",
    version: str,
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
) -> S3Path:
    """
    Upload the recently built Lambda source artifact from ``${dir_build}/source.zip``
    to S3 folder.

    :param bsm: boto session manager object
    :param version: example: ``"0.1.1"``
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param tags: S3 object tags

    :return: the S3 path of the uploaded ``source.zip`` file
    """
    build_context = BuildContext.new(dir_build=dir_build, s3dir_lambda=s3dir_lambda)
    s3dir_source = build_context.get_s3dir_source(version=version)
    s3path_source_zip = s3dir_source.joinpath("source.zip")
    # upload source.zip
    extra_args = {"ContentType": "application/zip"}
    if tags is not NOTHING:
        extra_args["Tagging"] = urlencode(tags)
    s3path_source_zip.upload_file(
        path=build_context.path_source_zip,
        overwrite=True,
        bsm=bsm,
        extra_args=extra_args,
    )
    return s3path_source_zip


def publish_source_artifacts(
    bsm: "BotoSesManager",
    path_setup_py_or_pyproject_toml: T.Union[str, Path],
    path_lambda_function: T.Union[str, Path],
    version: str,
    bin_pip: T.Union[str, Path],
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    quiet: bool = False,
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
) -> S3Path:
    """
    Build and then upload the source artifacts to S3.

    :param bsm: boto session manager object
    :param path_setup_py_or_pyproject_toml: example: ``/path/to/setup.py`` or
        ``/path/to/pyproject.toml``
    :param path_lambda_function: example: ``/path/to/lambda_function.py``
    :param version: example: ``"0.1.1"``
    :param bin_pip: example: ``/path/to/.venv/bin/pip``
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param quiet: whether you want to suppress the output of cli commands
    :param tags: S3 object tags

    :return: the S3 path of the uploaded ``source.zip`` file
    """
    build_source_artifacts(
        path_setup_py_or_pyproject_toml=path_setup_py_or_pyproject_toml,
        path_lambda_function=path_lambda_function,
        dir_build=dir_build,
        bin_pip=bin_pip,
        quiet=quiet,
    )
    return upload_source_artifacts(
        bsm=bsm,
        version=version,
        dir_build=dir_build,
        s3dir_lambda=s3dir_lambda,
        tags=tags,
    )
