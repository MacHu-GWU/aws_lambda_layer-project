# -*- coding: utf-8 -*-

import os
import pytest
from pathlib import Path
from aws_lambda_layer.utils import sha256_of_paths


def test_sha256_of_paths():
    dir_project_root = Path(__file__).parent.parent
    paths = [
        dir_project_root / "aws_lambda_layer",
        dir_project_root / "tests",
        dir_project_root / "setup.py",
    ]
    sha256_1 = sha256_of_paths(paths)
    sha256_2 = sha256_of_paths(paths)
    assert sha256_1 == sha256_2


if __name__ == "__main__":
    basename = os.path.basename(__file__)
    pytest.main([basename, "-s", "--tb=native"])
