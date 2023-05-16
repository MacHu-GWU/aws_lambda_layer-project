# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from s3pathlib import S3Path
from boto_session_manager import BotoSesManager
from aws_lambda_layer import api

# ------------------------------------------------------------------------------
# Update your configuration here
bsm = BotoSesManager(profile_name="bmt_app_dev_us_east_1")
layer_name = "aws_lambda_layer_test"
python_versions = ["python3.8"]
s3dir_lambda = S3Path(
    f"s3://{bsm.aws_account_id}-{bsm.aws_region}-artifacts/projects/aws_lambda_layer/lambda/"
).to_dir()
quiet = True
tags = {"project": "aws_lambda_layer_test"}
#
# ------------------------------------------------------------------------------

_dir_here = Path(__file__).absolute().parent
dir_build = _dir_here.joinpath("build")
path_requirements = _dir_here.joinpath("requirements.txt")
bin_pip = Path(sys.executable).parent.joinpath("pip")

lambda_layer_console_url = f"https://{bsm.aws_region}.console.aws.amazon.com/lambda/home?region={bsm.aws_region}#/layers/{layer_name}?tab=versions"
print(f"try to deploy a new lambda layer version for {layer_name}")
print(f"preview lambda layer s3 files: {s3dir_lambda.console_url}")
print(f"preview lambda layer versions: {lambda_layer_console_url}")

latest_layer_version = api.get_latest_layer_version(bsm=bsm, layer_name=layer_name)

if api.is_current_layer_the_same_as_latest_one(
    bsm=bsm,
    latest_layer_version=latest_layer_version,
    path_requirements=path_requirements,
    s3dir_lambda=s3dir_lambda,
):
    print("current layer is the same as the latest one, skip deploying")
    exit(0)

print("build layer artifacts ...")
api.build_layer_artifacts(
    path_requirements=path_requirements,
    dir_build=dir_build,
    bin_pip=bin_pip,
    quiet=quiet,
)

print("upload layer artifacts ...")
api.upload_layer_artifacts(
    bsm=bsm,
    path_requirements=path_requirements,
    dir_build=dir_build,
    s3dir_lambda=s3dir_lambda,
    tags=tags,
)

print("publish new layer version ...")
layer_version_arn = api.publish_layer(
    bsm=bsm,
    layer_name=layer_name,
    python_versions=python_versions,
    dir_build=dir_build,
    s3dir_lambda=s3dir_lambda,
    tags=tags,
)
lambda_layer_console_url = f"https://{bsm.aws_region}.console.aws.amazon.com/lambda/home?region={bsm.aws_region}#/layers/{layer_name}?tab=versions"
print(f"Done! Published: {layer_version_arn}")
