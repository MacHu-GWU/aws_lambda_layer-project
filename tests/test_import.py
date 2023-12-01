# -*- coding: utf-8 -*-

import pytest


def test():
    from aws_lambda_layer import api

    _ = api.BuildContext
    _ = api.get_latest_layer_version
    _ = api.is_current_layer_the_same_as_latest_one
    _ = api.build_layer_artifacts
    _ = api.upload_layer_artifacts
    _ = api.publish_layer
    _ = api.deploy_layer
    _ = api.LayerDeployment
    _ = api.grant_layer_permission
    _ = api.revoke_layer_permission
    _ = api.do_we_include
    _ = api.build_source_python_lib
    _ = api.build_source_artifacts
    _ = api.upload_source_artifacts
    _ = api.publish_source_artifacts
    _ = api.SourceArtifactsDeployment


if __name__ == "__main__":
    import os

    basename = os.path.basename(__file__)
    pytest.main([basename, "-s", "--tb=native"])
