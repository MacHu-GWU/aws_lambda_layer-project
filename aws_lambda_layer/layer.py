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
import enum
import glob
import shutil
import subprocess
import dataclasses
from pathlib import Path
from urllib.parse import urlencode

import botocore.exceptions
from s3pathlib import S3Path
from func_args import NOTHING, resolve_kwargs
from boto_session_manager import BotoSesManager

from .vendor.better_pathlib import temp_cwd
from .vendor.hashes import hashes
from .context import BuildContext

if T.TYPE_CHECKING:
    from mypy_boto3_lambda.type_defs import (
        AddLayerVersionPermissionResponseTypeDef,
        RemoveLayerVersionPermissionResponseTypeDef,
    )


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
) -> str:
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

    :return: the layer content sha256, it is sha256 of the requirements.txt file
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
    with temp_cwd(build_context.dir_build):
        args.extend(glob.glob("*"))
        args.append("-x")
        for package in ignore_package_list:
            args.append(f"python/{package}*")
        subprocess.run(args, check=True)
    layer_sha256 = hashes.of_bytes(path_requirements.read_bytes())
    return layer_sha256


def upload_layer_artifacts(
    bsm: "BotoSesManager",
    path_requirements: T.Union[str, Path],
    layer_sha256: str,
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    metadata: T.Optional[T.Dict[str, str]] = NOTHING,
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
) -> T.Tuple[S3Path, S3Path]:
    """
    Upload the recently built Lambda layer artifact from ``${dir_build}/layer.zip``
    to a temporary S3 folder. If the creation of a new layer from the temporary location
    is successful, copy it to the final location for the layer artifacts.

    :param bsm: boto session manager object
    :param path_requirements: example: ``/path/to/requirements.txt``
    :param layer_sha256: layer content sha256
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param metadata: S3 object metadata
    :param tags: S3 object tags

    :return: s3path_tmp_layer_zip and s3path_tmp_layer_requirements_txt
    """
    build_context = BuildContext.new(dir_build=dir_build, s3dir_lambda=s3dir_lambda)
    path_requirements = Path(path_requirements).absolute()

    if metadata is NOTHING:
        metadata = {}
    metadata["layer_sha256"] = layer_sha256

    # upload layer.zip
    extra_args = {"ContentType": "application/zip"}
    extra_args["Metadata"] = metadata
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
    extra_args["Metadata"] = metadata
    if tags is not NOTHING:
        extra_args["Tagging"] = urlencode(tags)
    build_context.s3path_tmp_layer_requirements_txt.upload_file(
        path_requirements,
        overwrite=True,
        bsm=bsm,
        extra_args=extra_args,
    )
    s3path_tmp_layer_zip = build_context.s3path_tmp_layer_zip
    s3path_tmp_layer_requirements_txt = build_context.s3path_tmp_layer_requirements_txt
    return (
        s3path_tmp_layer_zip,
        s3path_tmp_layer_requirements_txt,
    )


def publish_layer(
    bsm: "BotoSesManager",
    layer_name: str,
    python_versions: T.List[str],
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
) -> T.Tuple[int, str, S3Path, S3Path]:
    """
    Publish a new lambda layer version from AWS S3.

    :param bsm: boto session manager object
    :param layer_name: the lambda layer name
    :param python_version: example: ``["python3.8",]``
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``

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
        overwrite=False,
        bsm=bsm,
    )
    build_context.s3path_tmp_layer_requirements_txt.copy_to(
        s3path_layer_requirements_txt,
        overwrite=False,
        bsm=bsm,
    )
    return (
        layer_version,
        layer_version_arn,
        s3path_layer_zip,
        s3path_layer_requirements_txt,
    )


@dataclasses.dataclass
class LayerDeployment:
    """
    Layer deployment information.

    :param layer_sha256: the layer content sha256, it is sha256 of the requirements.txt file
    :param layer_version: integer layer version
    :param layer_version_arn: lambda layer arn
    :param s3path_layer_zip: the S3Path object of the layer.zip file
    :param s3path_layer_requirements_txt: the S3Path object of the requirements.txt file
    """

    layer_sha256: str = dataclasses.field()
    layer_version: int = dataclasses.field()
    layer_version_arn: str = dataclasses.field()
    s3path_layer_zip: S3Path = dataclasses.field()
    s3path_layer_requirements_txt: S3Path = dataclasses.field()


def deploy_layer(
    bsm: "BotoSesManager",
    layer_name: str,
    python_versions: T.List[str],
    path_requirements: T.Union[str, Path],
    dir_build: T.Union[str, Path],
    s3dir_lambda: T.Union[str, S3Path],
    bin_pip: T.Union[str, Path],
    quiet: bool = False,
    metadata: T.Optional[T.Dict[str, str]] = NOTHING,
    tags: T.Optional[T.Dict[str, str]] = NOTHING,
) -> T.Optional[LayerDeployment]:
    """
    Assemble the following functions together to build and deploy a new
    Lambda layer version if necessary.

    - :func:`get_latest_layer_version`
    - :func:`is_current_layer_the_same_as_latest_one`
    - :func:`build_layer_artifacts`
    - :func:`upload_layer_artifacts`
    - :func:`publish_layer`

    This function uses requirements.txt file to determine the dependencies.
    If you use poetry, pdm, pipenv or any other dependency management tool,
    you should export your dependencies to requirements.txt file first.
    I recommend poetry because the layer is supposed to be deterministic.

    :param bsm: boto session manager object
    :param layer_name: the lambda layer name
    :param python_version: example: ``["python3.8",]``
    :param path_requirements: example: ``/path/to/requirements.txt``
    :param dir_build: example: ``/path/to/build/lambda``
    :param s3dir_lambda: example: ``s3://bucket/path/to/lambda/``
    :param bin_pip: example: ``/path/to/.venv/bin/pip``
    :param quiet: whether you want to suppress the output of cli commands
    :param metadata: S3 object metadata
    :param tags: S3 object tags

    :return: The :class:`LayerDeployment` object. If returns None, then no
        deployment happened.
    """
    latest_layer_version = get_latest_layer_version(bsm=bsm, layer_name=layer_name)

    if is_current_layer_the_same_as_latest_one(
        bsm=bsm,
        latest_layer_version=latest_layer_version,
        path_requirements=path_requirements,
        s3dir_lambda=s3dir_lambda,
    ):
        return None

    layer_sha256 = build_layer_artifacts(
        path_requirements=path_requirements,
        dir_build=dir_build,
        bin_pip=bin_pip,
        quiet=quiet,
    )

    (s3path_tmp_layer_zip, s3path_tmp_layer_requirements_txt) = upload_layer_artifacts(
        bsm=bsm,
        path_requirements=path_requirements,
        layer_sha256=layer_sha256,
        dir_build=dir_build,
        s3dir_lambda=s3dir_lambda,
        metadata=metadata,
        tags=tags,
    )

    (
        layer_version,
        layer_version_arn,
        s3path_layer_zip,
        s3path_layer_requirements_txt,
    ) = publish_layer(
        bsm=bsm,
        layer_name=layer_name,
        python_versions=python_versions,
        dir_build=dir_build,
        s3dir_lambda=s3dir_lambda,
    )

    return LayerDeployment(
        layer_sha256=layer_sha256,
        layer_version=layer_version,
        layer_version_arn=layer_version_arn,
        s3path_layer_zip=s3path_layer_zip,
        s3path_layer_requirements_txt=s3path_layer_requirements_txt,
    )


class LayerPermissionActionEnum(str, enum.Enum):
    get_layer_version = "lambda:GetLayerVersion"
    list_layer_versions = "lambda:ListLayerVersions"


action_to_statement_mapper: T.Dict[str, str] = {
    LayerPermissionActionEnum.get_layer_version: "GetLayerVersion",
    LayerPermissionActionEnum.list_layer_versions: "ListLayerVersions",
}


def build_statement_id(
    action: str,
    principal: str,
    organization_id: str = NOTHING,
) -> str:
    if organization_id is NOTHING:
        return f"principal-{principal}-action-{action_to_statement_mapper[action]}"
    else:
        return f"principal-{principal}-organization-{organization_id}-action-{action_to_statement_mapper[action]}"


def grant_layer_permission(
    bsm: "BotoSesManager",
    layer_name: str,
    version_number: int,
    principal: str,
    statement_id: T.Optional[str] = None,
    action: str = LayerPermissionActionEnum.get_layer_version.value,
    organization_id: str = NOTHING,
    revision_id: str = NOTHING,
) -> "AddLayerVersionPermissionResponseTypeDef":
    """
    An Idempotent version of the original
    ``lambda_client.add_layer_version_permission`` API, it also handles
    the statement id automatically. If the statement already exists, delete it
    then create a new one.

    :param bsm: boto session manager object
    :param layer_name: the lambda layer name
    :param version_number: see official API
    :param principal: see official doc
    :param statement_id: if provided, use the provided statement id, otherwise,
        build one automatically based on combination of action, principal and
        organization id.
    :param action: lambda layer action syntax
    :param organization_id: see official doc
    :param revision_id: see official doc

    :return: the response of the original API.
    """
    if statement_id is None:
        statement_id = build_statement_id(
            action=action,
            principal=principal,
            organization_id=organization_id,
        )

    def add_layer_version_permission() -> dict:
        return bsm.lambda_client.add_layer_version_permission(
            **resolve_kwargs(
                LayerName=layer_name,
                VersionNumber=version_number,
                StatementId=statement_id,
                Principal=bsm.aws_account_id,
                Action=action,
                OrganizationId=organization_id,
                RevisionId=revision_id,
            )
        )

    try:
        res = add_layer_version_permission()
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            bsm.lambda_client.remove_layer_version_permission(
                **resolve_kwargs(
                    LayerName=layer_name,
                    VersionNumber=version_number,
                    StatementId=statement_id,
                    RevisionId=revision_id,
                )
            )
            res = add_layer_version_permission()
        else:
            raise e
    return res


def revoke_layer_permission(
    bsm: "BotoSesManager",
    layer_name: str,
    version_number: int,
    statement_id: T.Optional[str] = None,
    action: str = LayerPermissionActionEnum.get_layer_version.value,
    principal: str = NOTHING,
    organization_id: str = NOTHING,
    revision_id: str = NOTHING,
) -> T.Optional["RemoveLayerVersionPermissionResponseTypeDef"]:
    """
    An Idempotent version of the original
    ``lambda_client.remove_layer_version_permission`` API, it also handles
    the statement id automatically.

    :param bsm: boto session manager object
    :param layer_name: the lambda layer name
    :param version_number: see official API
    :param statement_id: if provided, use the provided statement id, otherwise,
        build one automatically based on combination of action, principal and
        organization id.
    :param action: lambda layer action syntax
    :param principal: see official doc
    :param organization_id: see official doc
    :param revision_id: see official doc

    :return: None if there's no permission to revoke, otherwise, the response
        of the original API.
    """
    if statement_id is None:
        if principal is NOTHING:
            raise ValueError("principal must be provided if statement_id is None")
        statement_id = build_statement_id(
            action=action,
            principal=principal,
            organization_id=organization_id,
        )
    try:
        return bsm.lambda_client.remove_layer_version_permission(
            **resolve_kwargs(
                LayerName=layer_name,
                VersionNumber=version_number,
                StatementId=statement_id,
                RevisionId=revision_id,
            )
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return None
        else:
            raise e
