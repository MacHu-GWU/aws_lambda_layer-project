# -*- coding: utf-8 -*-

"""
This module implements the automation of AWS Lambda Layer building and deployment.
It stores the layer artifacts in an S3 bucket with the following structure::

    s3://bucket/${s3dir_lambda}/layer/000001/layer.zip
    s3://bucket/${s3dir_lambda}/layer/000001/requirements.txt
    s3://bucket/${s3dir_lambda}/layer/000002/layer.zip
    s3://bucket/${s3dir_lambda}/layer/000002/requirements.txt
    s3://bucket/${s3dir_lambda}/layer/000003/layer.zip
    s3://bucket/${s3dir_lambda}/layer/000003/requirements.txt
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


def get_latest_layer_version(
    bsm: "BotoSesManager",
    layer_name: str,
) -> T.Optional[int]:
    """
    Call the AWS Lambda Layer API to retrieve the latest deployed layer version.
    If it returns ``None``, it indicates that no layer has been deployed yet.

    :param bsm: boto session manager object
    :param layer_name: the lambda layer name

    Reference:

    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.list_layer_versions
    """
    # note that this API call always returns the latest version first
    res = bsm.lambda_client.list_layer_versions(LayerName=layer_name, MaxItems=1)
    if len(res.get("LayerVersions", [])):
        return res["LayerVersions"][0]["Version"]
    else:
        return None


def is_current_layer_the_same_as_latest_one(
    bsm: "BotoSesManager",
    latest_layer_version: T.Optional[int],
    path_requirements: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
) -> bool:
    """
    Compare the local version of the requirements with the S3 backup of the
    latest layer requirements. If they are the same, we don't need to publish
    a new layer.

    :param bsm: boto session manager object
    :param latest_layer_version: the latest layer version, if it is None,
        then it indicates that no layer has been deployed yet
    :param path_requirements: example: /path/to/requirements.txt
    :param s3dir_lambda: example: s3://bucket/path/to/lambda/
    """
    # check if there is a lambda layer exists
    if latest_layer_version is None:
        return False

    build_context = BuildContext.new(s3dir_lambda=s3dir_lambda)
    path_requirements = Path(path_requirements).absolute()

    # get the s3 backup of the latest layer requirements
    s3path_layer_requirements_txt = build_context.get_s3path_layer_requirements_txt(
        version=latest_layer_version,
    )
    # this file may not exist
    if s3path_layer_requirements_txt.exists(bsm=bsm) is False:
        return False

    # compare
    local_deps = path_requirements.read_text()
    latest_deps = s3path_layer_requirements_txt.read_text(bsm=bsm)
    return local_deps == latest_deps


def build_layer_artifacts(
    path_requirements: T.Union[str, Path],
    dir_build: T.Union[str, Path],
    bin_pip: T.Union[str, Path],
    quiet: bool = False,
):
    """
    This function builds the AWS Lambda layer artifacts based on the dependencies
    specified in the ``path_requirements``. It utilizes ``bin_pip`` to install
    the dependencies into the ``${dir_build}/python`` folder. Afterward,
    it compresses the ``${dir_build}/python`` folder into ``${dir_build}/layer.zip``.

    Please note that this function is intended to run in an Amazon Linux-like environment,
    such as CodeBuild, EC2, or Cloud9, as the Amazon managed Lambda function
    also uses Amazon Linux. Building the layer on Windows or Mac may result in
    compatibility issues with certain C libraries.

    :param path_requirements: example: ``/path/to/requirements.txt``
    :param dir_build: example: ``/path/to/build/lambda``
    :param bin_pip: example: ``/path/to/.venv/bin/pip``
    :param quiet: whether you want to suppress the output of cli commands
    """
    build_context = BuildContext.new(dir_build=dir_build)
    path_requirements = Path(path_requirements).absolute()
    bin_pip = Path(bin_pip).absolute()

    # remove existing artifacts and temp folder
    build_context.path_layer_zip.unlink(missing_ok=True)
    shutil.rmtree(build_context.dir_python, ignore_errors=True)

    # initialize the build/lambda folder
    build_context.dir_build.mkdir(parents=True, exist_ok=True)

    # do "pip install -r requirements.txt -t ./build/lambda/python"
    args = [
        f"{bin_pip}",
        "install",
        "-r",
        f"{path_requirements}",
        "-t",
        f"{build_context.dir_python}",
    ]
    if quiet:
        args.append("--disable-pip-version-check")
        args.append("--quiet")
    subprocess.run(args, check=True)

    # zip the layer file
    # some packages are pre-installed in AWS Lambda runtime, so we don't need to
    # add them to the layer
    ignore_package_list = [
        "boto3",
        "botocore",
        "s3transfer",
        "setuptools",
        "pip",
        "wheel",
        "twine",
        "_pytest",
        "pytest",
    ]
    args = [
        "zip",
        f"{build_context.path_layer_zip}",
        "-r",
        "-9",
    ]
    if quiet:
        args.append("-q")
    # the glob command and zip command depends on the current working directory
    with utils.temp_cwd(build_context.dir_build):
        args.extend(glob.glob("*"))
        args.append("-x")
        for package in ignore_package_list:
            args.append(f"python/{package}*")
        subprocess.run(args, check=True)


def upload_layer_artifacts(
    bsm: "BotoSesManager",
    path_requirements: T.Union[str, Path],
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
):
    """
    Upload the recently built Lambda layer artifact from ``${dir_build}/layer.zip``
    to a temporary S3 folder. If the creation of a new layer from the temporary location
    is successful, copy it to the final location for the layer artifacts.

    :param bsm: boto session manager object
    :param path_requirements: example: ``/path/to/requirements.txt``
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param tags: S3 object tags
    """
    build_context = BuildContext.new(dir_build=dir_build, s3dir_lambda=s3dir_lambda)
    path_requirements = Path(path_requirements).absolute()

    # upload layer.zip
    extra_args = {"ContentType": "application/zip"}
    if tags is not NOTHING:
        extra_args["Tagging"] = urlencode(tags)
    build_context.s3path_tmp_layer_zip.upload_file(
        build_context.path_layer_zip,
        overwrite=True,
        bsm=bsm,
        extra_args=extra_args,
    )
    # upload requirements.txt
    extra_args = {"ContentType": "text/plain"}
    if tags is not NOTHING:
        extra_args["Tagging"] = urlencode(tags)
    build_context.s3path_tmp_layer_requirements_txt.upload_file(
        path_requirements,
        overwrite=True,
        bsm=bsm,
        extra_args=extra_args,
    )


def publish_layer(
    bsm: "BotoSesManager",
    layer_name: str,
    python_versions: T.List[str],
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
) -> str:
    """
    Publish a new lambda layer version from AWS S3.

    :param bsm: boto session manager object
    :param layer_name: the lambda layer name
    :param python_version: example: ``["python3.8",]``
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param tags: S3 object tags

    :return: The published lambda layer version ARN
    """
    build_context = BuildContext.new(dir_build=dir_build, s3dir_lambda=s3dir_lambda)
    # publish new layer version from temp s3 location
    response = bsm.lambda_client.publish_layer_version(
        LayerName=layer_name,
        Content=dict(
            S3Bucket=build_context.s3path_tmp_layer_zip.bucket,
            S3Key=build_context.s3path_tmp_layer_zip.key,
        ),
        CompatibleRuntimes=python_versions,
    )
    layer_version_arn = response["LayerVersionArn"]
    layer_version = int(layer_version_arn.split(":")[-1])

    # if success, we copy artifacts from temp to the right location
    s3path_layer_zip = build_context.get_s3path_layer_zip(
        version=layer_version,
    )
    s3path_layer_requirements_txt = build_context.get_s3path_layer_requirements_txt(
        version=layer_version,
    )

    # copy from tmp to the final location
    # we don't overwrite existing layer artifacts
    build_context.s3path_tmp_layer_zip.copy_to(
        s3path_layer_zip,
        tags=tags,
        overwrite=False,
    )
    build_context.s3path_tmp_layer_requirements_txt.copy_to(
        s3path_layer_requirements_txt,
        tags=tags,
        overwrite=False,
    )
    return layer_version_arn


def deploy_layer(
    bsm: "BotoSesManager",
    layer_name: str,
    python_versions: T.List[str],
    path_requirements: T.Union[str, Path],
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    bin_pip: T.Union[str, Path],
    quiet: bool = False,
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
) -> T.Optional[str]:
    """
    Assemble the following functions together to build and deploy a new
    Lambda layer version if necessary.

    - :func:`get_latest_layer_version`
    - :func:`is_current_layer_the_same_as_latest_one`
    - :func:`build_layer_artifacts`
    - :func:`upload_layer_artifacts`
    - :func:`publish_layer`

    :param bsm: boto session manager object
    :param layer_name: the lambda layer name
    :param python_version: example: ``["python3.8",]``
    :param path_requirements: example: ``/path/to/requirements.txt``
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param bin_pip: example: ``/path/to/.venv/bin/pip``
    :param quiet: whether you want to suppress the output of cli commands
    :param tags: S3 object tags

    :return: The published lambda layer version ARN. If returns None,
        then no deployment happened.
    """
    latest_layer_version = get_latest_layer_version(bsm=bsm, layer_name=layer_name)

    if is_current_layer_the_same_as_latest_one(
        bsm=bsm,
        latest_layer_version=latest_layer_version,
        path_requirements=path_requirements,
        s3dir_lambda=s3dir_lambda,
    ):
        return None

    build_layer_artifacts(
        path_requirements=path_requirements,
        dir_build=dir_build,
        bin_pip=bin_pip,
        quiet=quiet,
    )

    upload_layer_artifacts(
        bsm=bsm,
        path_requirements=path_requirements,
        dir_build=dir_build,
        s3dir_lambda=s3dir_lambda,
        tags=tags,
    )

    return publish_layer(
        bsm=bsm,
        layer_name=layer_name,
        python_versions=python_versions,
        dir_build=dir_build,
        s3dir_lambda=s3dir_lambda,
        tags=tags,
    )
