# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from s3pathlib import S3Path
from boto_session_manager import BotoSesManager
from aws_lambda_layer.layer import deploy_layer

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
quite = (True,)
tags = {"project": "aws_lambda_layer_test"}

deploy_layer(
    bsm=bsm,
    layer_name=layer_name,
    python_versions=python_versions,
    path_requirements=path_requirements,
    dir_build=dir_build,
    s3dir_lambda=s3dir_lambda,
    bin_pip=bin_pip,
    quite=True,
    tags=tags,
)

print(f"preview s3: {s3dir_lambda.console_url}")
