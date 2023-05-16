# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from s3pathlib import S3Path
from boto_session_manager import BotoSesManager
from aws_lambda_layer.source import publish_source_artifacts

_dir_here = Path(__file__).absolute().parent

bsm = BotoSesManager(profile_name="bmt_app_dev_us_east_1")
dir_build = _dir_here.joinpath("build")
s3dir_lambda = S3Path(
    f"s3://{bsm.aws_account_id}-{bsm.aws_region}-artifacts/projects/aws_lambda_layer/lambda/"
).to_dir()
path_setup_py_or_pyproject_toml = _dir_here.parent.joinpath("setup.py")
path_lambda_function = _dir_here.parent.joinpath("lambda_function.py")
bin_pip = Path(sys.executable).parent.joinpath("pip")
quiet = True
version = "0.1.1"
tags = {"project": "aws_lambda_layer_test"}

s3path_source_zip = publish_source_artifacts(
    bsm=bsm,
    path_setup_py_or_pyproject_toml=path_setup_py_or_pyproject_toml,
    path_lambda_function=path_lambda_function,
    version=version,
    bin_pip=bin_pip,
    dir_build=dir_build,
    s3dir_lambda=s3dir_lambda,
    quiet=quiet,
    tags=tags,
)
print(f"build and upload source artifacts, preview s3: {s3path_source_zip.console_url}")
