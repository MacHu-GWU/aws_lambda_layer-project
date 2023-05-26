# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from s3pathlib import S3Path
from boto_session_manager import BotoSesManager
from aws_lambda_layer.source import publish_source_artifacts

_dir_here = Path(__file__).absolute().parent

bsm = BotoSesManager(profile_name="bmt_app_dev_us_east_1")
path_setup_py_or_pyproject_toml = _dir_here.parent.joinpath("setup.py")
package_name = "aws_lambda_layer"
path_lambda_function = _dir_here.parent.joinpath("lambda_function.py")
version = "0.1.1"
dir_build = _dir_here.joinpath("build")
s3dir_lambda = S3Path(
    f"s3://{bsm.aws_account_id}-{bsm.aws_region}-artifacts/projects/{package_name}/lambda/"
).to_dir()
path_bin_python = Path(sys.executable)
path_bin_poetry = "poetry"
verbose = True
metadata = {"project": package_name}
tags = {"project": package_name}

s3path_source_zip = publish_source_artifacts(
    bsm=bsm,
    path_setup_py_or_pyproject_toml=path_setup_py_or_pyproject_toml,
    package_name=package_name,
    path_lambda_function=path_lambda_function,
    version=version,
    dir_build=dir_build,
    s3dir_lambda=s3dir_lambda,
    # path_bin_python=path_bin_python,
    # path_bin_poetry=path_bin_poetry,
    metadata=metadata,
    tags=tags,
    # use_pip=True,
    # use_build=True,
    # use_poetry=True,
    use_pathlib=True,
    verbose=verbose,
)
print(f"build and upload source artifacts, preview s3: {s3path_source_zip.console_url}")
