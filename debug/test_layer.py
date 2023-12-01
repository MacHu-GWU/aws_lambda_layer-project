# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from s3pathlib import S3Path, context
from boto_session_manager import BotoSesManager
from aws_lambda_layer.layer import (
    deploy_layer,
    get_latest_layer_version,
    grant_layer_permission,
    revoke_layer_permission,
)

_dir_here = Path(__file__).absolute().parent

bsm = BotoSesManager(profile_name="bmt_app_dev_us_east_1")
layer_name = "aws_lambda_layer_test"
python_versions = ["python3.8"]
dir_build = _dir_here.joinpath("build")
s3dir_lambda = S3Path(
    f"s3://{bsm.aws_account_id}-{bsm.aws_region}-artifacts/projects/aws_lambda_layer/lambda/"
).to_dir()
path_requirements = _dir_here.joinpath("requirements.txt")
bin_pip = Path(sys.executable).parent.joinpath("pip")
quiet = True
metadata = {"project": "aws_lambda_layer_test"}
tags = {"project": "aws_lambda_layer_test"}

context.attach_boto_session(bsm.boto_ses)
layer_deployment = deploy_layer(
    bsm=bsm,
    layer_name=layer_name,
    python_versions=python_versions,
    path_requirements=path_requirements,
    dir_build=dir_build,
    s3dir_lambda=s3dir_lambda,
    bin_pip=bin_pip,
    quiet=quiet,
    metadata=metadata,
    tags=tags,
)
lambda_layer_console_url = f"https://{bsm.aws_region}.console.aws.amazon.com/lambda/home?region={bsm.aws_region}#/layers/{layer_name}?tab=versions"
if layer_deployment:
    print(
        f"published a new layer version, preview lambda layer: {lambda_layer_console_url}"
    )
    print(f"preview s3: {s3dir_lambda.console_url}")
    print(f"layer_sha256: {layer_deployment.layer_sha256}")
    print(f"layer_version: {layer_deployment.layer_version}")
    print(f"layer_version_arn: {layer_deployment.layer_version_arn}")
    print(f"s3path_layer_zip: {layer_deployment.s3path_layer_zip.console_url}")
    print(
        f"s3path_layer_requirements_txt: {layer_deployment.s3path_layer_requirements_txt.console_url}"
    )
else:
    print(
        f"no new layer version published, preview lambda layer: {lambda_layer_console_url}"
    )

version = get_latest_layer_version(bsm, layer_name)

grant_layer_permission(
    bsm=bsm,
    layer_name=layer_name,
    version_number=version,
    principal=bsm.aws_account_id,
)

revoke_layer_permission(
    bsm=bsm,
    layer_name=layer_name,
    version_number=version,
    principal=bsm.aws_account_id,
)
