# -*- coding: utf-8 -*-

"""
This module defines the Lambda artifacts build context.
"""

import typing as T
import dataclasses
from pathlib import Path
from s3pathlib import S3Path

ZFILL = 6


@dataclasses.dataclass
class BuildContext:
    """
    This object defines where the lambda artifacts should locate at on local
    laptop and on S3 bucket.

    :param dir_build: the root directory of the build folder on local
    :param s3dir_lambda: the root directory of the lambda artifacts on S3
    """

    dir_build: T.Optional[Path] = dataclasses.field(default=None)
    s3dir_lambda: T.Optional[S3Path] = dataclasses.field(default=None)

    @classmethod
    def new(
        cls,
        dir_build: T.Optional[T.Union[str, Path]] = None,
        s3dir_lambda: T.Optional[T.Union[str, S3Path]] = None,
    ) -> "BuildContext":
        if dir_build is not None:
            dir_build = Path(dir_build).absolute()
        if s3dir_lambda is not None:
            s3dir_lambda = S3Path(s3dir_lambda).to_dir()
        return cls(dir_build=dir_build, s3dir_lambda=s3dir_lambda)

    @property
    def dir_python(self) -> Path:
        """
        This folder will be the temporary folder for installing python dependencies.

        example: ``${dir_build}/python``
        """
        return self.dir_build.joinpath("python")

    @property
    def dir_deploy(self) -> Path:
        return self.dir_build.joinpath("deploy")

    @property
    def path_source_zip(self) -> Path:
        """
        This file will be the Lambda source code zip file.

        example: ``${dir_build}/source.zip``
        """
        return self.dir_build.joinpath("source.zip")

    @property
    def path_layer_zip(self) -> Path:
        """
        This file will be the Lambda layer zip file.

        example: ``${dir_build}/layer.zip``
        """
        return self.dir_build.joinpath("layer.zip")

    @property
    def s3dir_tmp(self) -> S3Path:
        """
        A temporary folder on S3 for deployment. If deployment succeeded,
        then the content of this folder will be copied to the final location.

        example: ``${s3dir_lambda}/tmp/``
        """
        return self.s3dir_lambda.joinpath("tmp").to_dir()

    @property
    def s3path_tmp_source_zip(self) -> S3Path:
        """
        example: ``${s3dir_lambda}/tmp/source.zip``
        """
        return self.s3dir_tmp.joinpath("source.zip")

    @property
    def s3path_tmp_layer_zip(self) -> S3Path:
        """
        example: ``${s3dir_lambda}/tmp/layer.zip``
        """
        return self.s3dir_tmp.joinpath("layer.zip")

    @property
    def s3path_tmp_layer_requirements_txt(self) -> S3Path:
        """
        example: ``${s3dir_lambda}/tmp/requirements.txt``
        """
        return self.s3dir_tmp.joinpath("requirements.txt")

    @property
    def s3dir_source(self) -> S3Path:
        """
        The final location of the lambda source code artifacts history.

        example: ``${s3dir_lambda}/source/``
        """
        return self.s3dir_lambda.joinpath("source").to_dir()

    @property
    def s3dir_layer(self) -> S3Path:
        """
        The final location of the lambda layer artifacts history.

        example: ``${s3dir_lambda}/layer/``
        """
        return self.s3dir_lambda.joinpath("layer").to_dir()

    def get_s3path_layer_zip(self, version: int) -> S3Path:
        """
        This version is a integer number.

        example: ``${s3dir_lambda}/layer/${layer_version}/layer.zip``
        """
        return self.s3dir_layer.joinpath(
            str(version).zfill(ZFILL),
            "layer.zip",
        )

    def get_s3path_layer_requirements_txt(self, version: int) -> S3Path:
        """
        This version is a integer number.

        example: ``${s3dir_lambda}/layer/${layer_version}/requirements.txt``
        """
        return self.s3dir_layer.joinpath(
            str(version).zfill(ZFILL),
            "requirements.txt",
        )

    def get_s3dir_source(self, version: str) -> S3Path:
        """
        This version is a semantic version string.

        example: ``${s3dir_lambda}/source/${source_version}/``
        """
        return self.s3dir_source.joinpath(version).to_dir()
