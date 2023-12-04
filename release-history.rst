.. _release_history:

Release and Version History
==============================================================================


Backlog (TODO)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


0.4.2 (2023-12-04)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Bugfixes**

- Fix a bug that the ``publish_layer`` method failed to use the right AWS boto session.


0.4.1 (2023-12-01)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**
- add the following public api:
    - ``aws_lambda_layer.api.grant_layer_permission``
    - ``aws_lambda_layer.api.revoke_layer_permission``


0.3.1 (2023-07-03)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- add the following public api:
    - ``aws_lambda_layer.api.do_we_include``
    - ``aws_lambda_layer.api.build_source_python_lib``


0.2.4 (2023-05-27)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Minor Improvements**

- now the ``deploy_layer`` method returns a ``LayerDeployment`` object.
- now the ``publish_source_artifacts`` method returns a ``SourceArtifactsDeployment`` object.


0.2.3 (2023-05-26)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Minor Improvements**

- also add source sha256 and layer sha256 to S3 object metadata for integrity check.


0.2.2 (2023-05-26)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Bugfixes**

- fix a bug that ``aws_lambda_layer.api.sha256_of_paths`` forget to ignore dir in calculation.


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
