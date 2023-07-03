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
import dataclasses
from pathlib import Path
from urllib.parse import urlencode

from s3pathlib import S3Path
from func_args import NOTHING
from boto_session_manager import BotoSesManager

from .vendor.better_pathlib import temp_cwd
from .vendor.hashes import hashes
from .vendor.build_dist import (
    build_dist_with_python_build,
    build_dist_with_poetry_build,
)
from .utils import ensure_exact_one_true
from .context import BuildContext


def _build_source_from_tar_gz(
    package_name: str,
    dir_dist: Path,
    dir_tmp: Path,
    dir_deploy: Path,
):
    # validate arguments
    if dir_dist.is_dir() is False:
        raise ValueError(f"dir_dist {dir_dist} is not a directory")
    if dir_tmp.is_dir() is False:
        raise ValueError(f"dir_tmp {dir_tmp} is not a directory")
    if dir_deploy.is_dir() is False:
        raise ValueError(f"dir_deploy {dir_deploy} is not a directory")

    # locate the ${dir_dist}/${package_name}-${version}.tar.gz file
    path_tar: T.Optional[Path] = None
    for p in dir_dist.iterdir():
        if p.name.endswith(".tar.gz"):
            path_tar = p
    if path_tar is None:
        raise FileNotFoundError

    # extract the tar.gz file to ${dir_tmp}/${package_name}
    extracted_folder_name = path_tar.name.replace(".tar.gz", "")
    dir_extracted_folder = dir_tmp / extracted_folder_name
    shutil.rmtree(dir_extracted_folder, ignore_errors=True)
    dir_tmp.mkdir(parents=True, exist_ok=True)
    args = [
        "tar",
        "-xzf",
        f"{path_tar}",
        "-C",
        f"{dir_tmp}",
    ]
    subprocess.run(args, check=True)
    # move the source code
    # from ${dir_tmp}/${extracted_folder_name}/${package_name}
    # to ${dir_deploy}/${package_name}
    before_dir = dir_extracted_folder / package_name
    after_dir = dir_deploy / package_name
    dir_deploy.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(after_dir, ignore_errors=True)
    shutil.move(f"{before_dir}", f"{after_dir}")


def do_we_include(
    relpath: Path,
    include: T.List[str],
    exclude: T.List[str],
) -> bool:
    """
    Based on the include and exclude pattern, do we ignore this file?

    explicit exclude > explicit include > implicit include
    """
    if len(include) == 0 and len(exclude) == 0:
        return True
    elif len(include) > 0 and len(exclude) > 0:
        match_any_include = any([relpath.match(pattern) for pattern in include])
        match_any_exclude = any([relpath.match(pattern) for pattern in exclude])
        if match_any_exclude:
            return False
        else:
            return match_any_include
    elif len(include) > 0 and len(exclude) == 0:
        return any([relpath.match(pattern) for pattern in include])
    elif len(include) == 0 and len(exclude) > 0:
        return not any([relpath.match(pattern) for pattern in exclude])
    else:  # pragma: no cover
        raise NotImplementedError


def build_source_python_lib(
    dir_python_lib_source: T.Union[str, Path],
    dir_python_lib_target: T.Union[str, Path],
    include: T.Optional[T.Union[str, T.List[str]]] = None,
    exclude: T.Optional[T.Union[str, T.List[str]]] = None,
):
    """
    This function build python library source code distribution. It walks through
    the python library source code directory, include and exclude files based on
    definition, and copy the files to the target directory.

    :param dir_python_lib_source: where your python library source code is.
    :param dir_python_lib_target: where you want to copy the source code to.
    :param include: list of glob patterns to include.
    :param exclude: list of glob patterns to exclude.
    """
    dir_python_lib_source = Path(dir_python_lib_source).absolute()
    dir_python_lib_target = Path(dir_python_lib_target).absolute()
    if include is None:  # pragma: no cover
        include = []
    elif isinstance(include, str):  # pragma: no cover
        include = [include]
    else:  # pragma: no cover
        include = include
    if exclude is None:  # pragma: no cover
        exclude = []
    elif isinstance(exclude, str):  # pragma: no cover
        exclude = [exclude]
    else:  # pragma: no cover
        exclude = exclude
    exclude.extend(["__pycache__", "*.pyc", "*.pyo"])

    if dir_python_lib_target.exists():
        shutil.rmtree(dir_python_lib_target)

    for path in dir_python_lib_source.glob("**/*"):
        if path.is_file():
            relpath = path.relative_to(dir_python_lib_source)
            if do_we_include(relpath, include=include, exclude=exclude):
                path_new = dir_python_lib_target.joinpath(relpath)
                try:
                    path_new.write_bytes(path.read_bytes())
                except FileNotFoundError:
                    path_new.parent.mkdir(parents=True, exist_ok=True)
                    path_new.write_bytes(path.read_bytes())
        else:
            pass


def build_source_artifacts(
    path_setup_py_or_pyproject_toml: T.Union[str, Path],
    package_name: str,
    path_lambda_function: T.Union[str, Path],
    dir_build: T.Union[str, Path],
    path_bin_python: T.Optional[T.Union[str, Path]] = None,
    path_bin_poetry: T.Optional[T.Union[str, Path]] = None,
    use_pip: bool = False,
    use_build: bool = False,
    use_poetry: bool = False,
    use_pathlib: bool = False,
    verbose: bool = True,
) -> T.Tuple[str, Path]:
    """
    This function builds the source artifacts for the AWS Lambda deployment package.

    Given the ``path_setup_py_or_pyproject_toml`` path, this function will
    locate the directory where the ``python -m build``, ``pip install`` or ``poetry build``
    command should run, build the distribution package, and then copy the
    ``path_lambda_function`` to the deploy folder in the ``dir_build`` directory,
    and create the ``source.zip`` file.

    :param path_setup_py_or_pyproject_toml: example: ``/path/to/setup.py`` or
        ``/path/to/pyproject.toml``
    :param package_name: example: ``aws_lambda_layer``
    :param path_lambda_function: example: ``/path/to/lambda_function.py``
    :param dir_build: example: ``/path/to/build/lambda``
    :param path_bin_python: example ``/path/to/.venv/bin/python``
    :param path_bin_poetry: example ``/path/to/.venv/bin/poetry`` or the global ``poetry``
    :param use_pip: do you want to use pip to build your source?
    :param use_build: do you want to use python-build to build your source?
    :param use_poetry: do you want to use python-poetry to build your source?
    :param use_pathlib: do you want to use pathlib to build your source?
    :param verbose: whether you want to suppress the output of cli commands

    :return: tuple of two item, first one is the code sha256 hash of the source artifacts,
        second one is the path to the source.zip file
    """
    # validate arguments
    ensure_exact_one_true(
        [
            use_pip,
            use_build,
            use_poetry,
            use_pathlib,
        ]
    )

    # resolve arguments
    path_setup_py_or_pyproject_toml = Path(path_setup_py_or_pyproject_toml).absolute()
    path_lambda_function = Path(path_lambda_function).absolute()
    if path_bin_python is not None:
        path_bin_python = Path(path_bin_python).absolute()
    build_context = BuildContext.new(dir_build=dir_build)
    dir_project_root = path_setup_py_or_pyproject_toml.parent
    dir_dist = dir_project_root.joinpath("dist")
    dir_python_lib = dir_project_root.joinpath(package_name)

    # clean up existing files in build folder
    shutil.rmtree(build_context.dir_build, ignore_errors=True)
    build_context.dir_deploy.mkdir(parents=True, exist_ok=True)

    # install python library
    if use_pip:
        with temp_cwd(dir_project_root):
            args = [
                f"{path_bin_python}",
                "-m",
                "pip",
                "install",
                f"{dir_project_root}",
                "--no-dependencies",
                f"--target={build_context.dir_deploy}",
            ]
            if verbose is False:
                args.append("--disable-pip-version-check")
                args.append("--quiet")
            subprocess.run(args, check=True)
    # ref: https://pypa-build.readthedocs.io/en/latest/
    elif use_build:
        build_dist_with_python_build(
            dir_project_root=dir_project_root,
            path_bin_python=path_bin_python,
            verbose=verbose,
        )
        _build_source_from_tar_gz(
            package_name=package_name,
            dir_dist=dir_dist,
            dir_tmp=build_context.dir_build,
            dir_deploy=build_context.dir_deploy,
        )
    # ref: https://python-poetry.org/docs/cli/#build
    elif use_poetry:
        build_dist_with_poetry_build(
            dir_project_root=dir_project_root,
            path_bin_poetry=path_bin_poetry,
            verbose=verbose,
        )
        _build_source_from_tar_gz(
            package_name=package_name,
            dir_dist=dir_dist,
            dir_tmp=build_context.dir_build,
            dir_deploy=build_context.dir_deploy,
        )
    elif use_pathlib:
        for path in dir_python_lib.glob("**/*"):
            relpath = path.relative_to(dir_python_lib)
            if "__pycache__" not in str(relpath):
                if path.is_file():
                    path_new = build_context.dir_deploy.joinpath(
                        package_name, path.relative_to(dir_python_lib)
                    )
                    try:
                        path_new.write_bytes(path.read_bytes())
                    except FileNotFoundError:
                        path_new.parent.mkdir(parents=True, exist_ok=True)
                        path_new.write_bytes(path.read_bytes())
                else:
                    pass

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
    if verbose is False:
        args.append("-q")

    # has to cd to the deploy dir to run the glob command
    with temp_cwd(build_context.dir_deploy):
        args.extend(glob.glob("*"))
        subprocess.run(args, check=True)

    source_sha256 = hashes.of_paths([build_context.dir_deploy])
    path_source_zip = build_context.path_source_zip
    return source_sha256, path_source_zip


def upload_source_artifacts(
    bsm: "BotoSesManager",
    version: str,
    source_sha256: str,
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    metadata: T.Optional[T.Dict[str, str]] = NOTHING,
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
) -> S3Path:
    """
    Upload the recently built Lambda source artifact from ``${dir_build}/source.zip``
    to S3 folder.

    :param bsm: boto session manager object
    :param version: lambda source code version, example: ``"0.1.1"``
    :param source_sha256: sha256 hash of the source artifacts
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param metadata: S3 object metadata
    :param tags: S3 object tags

    :return: the S3 path of the uploaded ``source.zip`` file
    """
    build_context = BuildContext.new(dir_build=dir_build, s3dir_lambda=s3dir_lambda)
    s3dir_source = build_context.get_s3dir_source(version=version)
    s3path_source_zip = s3dir_source.joinpath("source.zip")
    # upload source.zip
    extra_args = {"ContentType": "application/zip"}
    if metadata is NOTHING:
        metadata = {}
    metadata["source_sha256"] = source_sha256
    extra_args["Metadata"] = metadata
    if tags is not NOTHING:
        extra_args["Tagging"] = urlencode(tags)
    s3path_source_zip.upload_file(
        path=build_context.path_source_zip,
        overwrite=True,
        bsm=bsm,
        extra_args=extra_args,
    )
    return s3path_source_zip


@dataclasses.dataclass
class SourceArtifactsDeployment:
    """
    Source artifacts deployment information.

    :param source_sha256: code sha256 hash of the source artifacts
    :param path_source_zip: path to the source.zip file on local
    :param s3path_source_zip: S3Path object of the source.zip file
    """

    source_sha256: str = dataclasses.field()
    path_source_zip: Path = dataclasses.field()
    s3path_source_zip: S3Path = dataclasses.field()


def publish_source_artifacts(
    bsm: "BotoSesManager",
    path_setup_py_or_pyproject_toml: T.Union[str, Path],
    package_name: str,
    path_lambda_function: T.Union[str, Path],
    version: str,
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    path_bin_python: T.Optional[T.Union[str, Path]] = None,
    path_bin_poetry: T.Optional[T.Union[str, Path]] = None,
    metadata: T.Optional[T.Dict[str, str]] = NOTHING,
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
    use_pip: bool = False,
    use_build: bool = False,
    use_poetry: bool = False,
    use_pathlib: bool = False,
    verbose: bool = True,
) -> SourceArtifactsDeployment:
    """
    Assemble the following functions together to build and then upload the
    source artifacts to S3.

    - :func:`build_source_artifacts`
    - :func:`upload_source_artifacts`

    This function has four options to build the source artifacts. If you are
    lazy, I recommend ``use_pathlib=True``.

    :param bsm: boto session manager object
    :param path_setup_py_or_pyproject_toml: example: ``/path/to/setup.py`` or
        ``/path/to/pyproject.toml``
    :param package_name: example: ``aws_lambda_layer``
    :param path_lambda_function: example: ``/path/to/lambda_function.py``
    :param version: lambda source code version, example: ``"0.1.1"``
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param path_bin_python: example ``/path/to/.venv/bin/python``
    :param path_bin_poetry: example ``/path/to/.venv/bin/poetry`` or the global ``poetry``
    :param metadata: S3 object metadata
    :param tags: S3 object tags
    :param use_pip: do you want to use pip to build your source?
    :param use_build: do you want to use python-build to build your source?
    :param use_poetry: do you want to use python-poetry to build your source?
    :param use_pathlib: do you want to use pathlib to build your source?
    :param verbose: whether you want to suppress the output of cli commands

    :return: :class:`SourceArtifactsDeployment` object.
    """
    source_sha256, path_source_zip = build_source_artifacts(
        path_setup_py_or_pyproject_toml=path_setup_py_or_pyproject_toml,
        package_name=package_name,
        path_lambda_function=path_lambda_function,
        dir_build=dir_build,
        path_bin_python=path_bin_python,
        path_bin_poetry=path_bin_poetry,
        use_pip=use_pip,
        use_build=use_build,
        use_poetry=use_poetry,
        use_pathlib=use_pathlib,
        verbose=verbose,
    )
    s3path_source_zip = upload_source_artifacts(
        bsm=bsm,
        version=version,
        source_sha256=source_sha256,
        dir_build=dir_build,
        s3dir_lambda=s3dir_lambda,
        metadata=metadata,
        tags=tags,
    )
    return SourceArtifactsDeployment(
        source_sha256=source_sha256,
        path_source_zip=path_source_zip,
        s3path_source_zip=s3path_source_zip,
    )
