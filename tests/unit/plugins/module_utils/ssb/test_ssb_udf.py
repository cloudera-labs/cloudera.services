# -*- coding: utf-8 -*-

# Copyright 2026 Cloudera, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    ServicesClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbUdf,
    SsbUdfClient,
    SsbUdfRunResult,
    SsbUdfTestRun,
    SsbUdfTestParameter,
)

ENDPOINT_URL = "https://cloudera.internal"
PROJECT_ID = "proj123"

UDF_PYTHON = dict(
    id=1,
    project_id=PROJECT_ID,
    name="test_udf",
    output_type="PYTHON_INFERRED",
    description="Test UDF",
    language="PYTHON",
    code="return input",
    created_at="2024-06-01T12:00:00Z",
    updated_at="2024-06-01T12:00:00Z",
)

UDF_LIST = [UDF_PYTHON]

UDF_RUN_RESULT = dict(
    result="test_output",
)


def test_list_udfs(mocker):
    """Test listing all UDFs for a project."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = UDF_LIST

    # Create the SsbUdfClient instance
    client = SsbUdfClient(api_client=api_client)

    response = client.list_udfs(PROJECT_ID)

    assert isinstance(response, list)
    assert response[0] == from_dict(SsbUdf, UDF_PYTHON)

    # Verify that the get method was called with correct parameters
    api_client.get.assert_called_once_with(f"/api/v2/projects/{PROJECT_ID}/udfs")


def test_create_udf_minimal(mocker):
    """Test creating a UDF with minimal parameters."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = UDF_PYTHON

    # Create the SsbUdfClient instance
    client = SsbUdfClient(api_client=api_client)

    response = client.create_udf(
        SsbUdf(
            project_id=PROJECT_ID,
            name="test_udf",
            output_type="PYTHON_INFERRED",
            language="PYTHON",
        ),
    )

    assert response == from_dict(SsbUdf, UDF_PYTHON)

    # Verify that the post method was called with correct parameters
    api_client.post.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/udfs",
        data={
            "name": "test_udf",
            "output_type": "PYTHON_INFERRED",
            "language": "PYTHON",
            "project_id": PROJECT_ID,
        },
    )


def test_create_udf_with_description(mocker):
    """Test creating a UDF with description."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = UDF_PYTHON

    # Create the SsbUdfClient instance
    client = SsbUdfClient(api_client=api_client)

    response = client.create_udf(
        SsbUdf(
            project_id=PROJECT_ID,
            name="test_udf",
            language="PYTHON",
            output_type="PYTHON_INFERRED",
            description="Test UDF description",
        ),
    )

    assert response == from_dict(SsbUdf, UDF_PYTHON)

    # Verify that the post method was called with correct parameters
    api_client.post.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/udfs",
        data={
            "name": "test_udf",
            "language": "PYTHON",
            "output_type": "PYTHON_INFERRED",
            "description": "Test UDF description",
            "project_id": PROJECT_ID,
        },
    )


def test_update_udf(mocker):
    """Test updating a UDF."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = UDF_PYTHON

    # Create the SsbUdfClient instance
    client = SsbUdfClient(api_client=api_client)

    response = client.update_udf(
        SsbUdf(
            project_id=PROJECT_ID,
            id=1,
            output_type="PYTHON_INFERRED",
            language="PYTHON",
            name="updated_udf",
            description="Updated description",
        ),
    )

    assert response == from_dict(SsbUdf, UDF_PYTHON)

    # Verify that the put method was called with correct parameters
    api_client.put.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/udfs",
        data={
            "id": 1,
            "output_type": "PYTHON_INFERRED",
            "language": "PYTHON",
            "name": "updated_udf",
            "description": "Updated description",
            "project_id": PROJECT_ID,
        },
    )


def test_delete_udf(mocker):
    """Test deleting a UDF."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = None

    # Create the SsbUdfClient instance
    client = SsbUdfClient(api_client=api_client)

    response = client.delete_udf(PROJECT_ID, 1)

    assert response == None

    # Verify that the delete method was called with correct parameters
    api_client.delete.assert_called_once_with(f"/api/v2/projects/{PROJECT_ID}/udfs/1")
