.. _release_history:

Release and Version History
==============================================================================


Backlog (TODO)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


0.2.1 (2023-05-26)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- the ``build_source_artifacts`` and ``publish_source_artifacts`` now has four options to build the source artifacts:
    - use ``python setup.py``
    - use ``python -m build ...``
    - use ``poetry build``
    - use ``pathlib``
- add the following public api:
    - ``aws_lambda_layer.api.sha256_of_paths``


0.1.1 (2023-05-15)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- first release, allow you to build and deploy lambda source artifacts and layers.
- add the following public api:
    - ``aws_lambda_layer.api.BuildContext``
    - ``aws_lambda_layer.api.get_latest_layer_version``
    - ``aws_lambda_layer.api.is_current_layer_the_same_as_latest_one``
    - ``aws_lambda_layer.api.build_layer_artifacts``
    - ``aws_lambda_layer.api.upload_layer_artifacts``
    - ``aws_lambda_layer.api.publish_layer``
    - ``aws_lambda_layer.api.deploy_layer``
    - ``aws_lambda_layer.api.build_source_artifacts``
    - ``aws_lambda_layer.api.upload_source_artifacts``
    - ``aws_lambda_layer.api.publish_source_artifacts``
