
.. .. image:: https://readthedocs.org/projects/aws_lambda_layer/badge/?version=latest
    :target: https://aws_lambda_layer.readthedocs.io/index.html
    :alt: Documentation Status

.. .. image:: https://github.com/MacHu-GWU/aws_lambda_layer-project/workflows/CI/badge.svg
    :target: https://github.com/MacHu-GWU/aws_lambda_layer-project/actions?query=workflow:CI

.. .. image:: https://codecov.io/gh/MacHu-GWU/aws_lambda_layer-project/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/MacHu-GWU/aws_lambda_layer-project

.. image:: https://img.shields.io/pypi/v/aws_lambda_layer.svg
    :target: https://pypi.python.org/pypi/aws_lambda_layer

.. image:: https://img.shields.io/pypi/l/aws_lambda_layer.svg
    :target: https://pypi.python.org/pypi/aws_lambda_layer

.. image:: https://img.shields.io/pypi/pyversions/aws_lambda_layer.svg
    :target: https://pypi.python.org/pypi/aws_lambda_layer

.. image:: https://img.shields.io/badge/Release_History!--None.svg?style=social
    :target: https://github.com/MacHu-GWU/aws_lambda_layer-project/blob/main/release-history.rst

.. image:: https://img.shields.io/badge/STAR_Me_on_GitHub!--None.svg?style=social
    :target: https://github.com/MacHu-GWU/aws_lambda_layer-project

------

.. .. image:: https://img.shields.io/badge/Link-Document-blue.svg
    :target: https://aws_lambda_layer.readthedocs.io/index.html

.. .. image:: https://img.shields.io/badge/Link-API-blue.svg
    :target: https://aws_lambda_layer.readthedocs.io/py-modindex.html

.. .. image:: https://img.shields.io/badge/Link-Source_Code-blue.svg
    :target: https://aws_lambda_layer.readthedocs.io/py-modindex.html

.. .. image:: https://img.shields.io/badge/Link-Install-blue.svg
    :target: `install`_

.. image:: https://img.shields.io/badge/Link-GitHub-blue.svg
    :target: https://github.com/MacHu-GWU/aws_lambda_layer-project

.. image:: https://img.shields.io/badge/Link-Submit_Issue-blue.svg
    :target: https://github.com/MacHu-GWU/aws_lambda_layer-project/issues

.. image:: https://img.shields.io/badge/Link-Request_Feature-blue.svg
    :target: https://github.com/MacHu-GWU/aws_lambda_layer-project/issues

.. image:: https://img.shields.io/badge/Link-Download-blue.svg
    :target: https://pypi.org/pypi/aws_lambda_layer#files


Welcome to ``aws_lambda_layer`` Documentation
==============================================================================
A simple tool that automates the process of building and deploying AWS Lambda layers and source artifacts. It utilizes a purposefully designed S3 folder structure to store all historical versions of artifacts.

Examples:

- `build_layer.py <./example/build_layer.py>`_
- `build_source.py <./example/build_source.py>`_

You may need additional tools to build your source artifacts:

- do ``pip install build`` to use ``python -m build``
- do ``pip install poetry`` to use ``poetry build``


.. _install:

Install
------------------------------------------------------------------------------

``aws_lambda_layer`` is released on PyPI, so all you need is:

.. code-block:: console

    $ pip install aws_lambda_layer

To upgrade to latest version:

.. code-block:: console

    $ pip install --upgrade aws_lambda_layer
