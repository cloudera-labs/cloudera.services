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

import pytest

from typing import Generator

from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbUdf,
    SsbUdfTestRun,
    SsbUdfRunResult,
)

REQUIRED_ENV_VARS = [
    "SSB_SSE_API_URL",
    "SSB_SSE_API_USERNAME",
    "SSB_SSE_API_PASSWORD",
]


@pytest.fixture
def existing_python_udf(
    udf_client,
    existing_project,
    purge_udf,
) -> Generator[SsbUdf, None, None]:
    """Fixture to create a test UDF and clean it up after the test."""
    udf_name = "ansible_test_udf_python"

    # Clean up any existing test UDF
    udfs = udf_client.list_udfs(existing_project.id)
    for udf in udfs:
        if udf.name == udf_name:
            udf_client.delete_udf(existing_project.id, udf.id)

    # Create the test UDF TODO Update example to be a realistic UDF
    udf = udf_client.create_udf(
        SsbUdf(
            project_id=existing_project.id,
            name=udf_name,
            language="PYTHON",
            output_type="PYTHON_INFERRED",
            description="Test UDF created by pytest",
            code="print('Hello, World!')",
        ),
    )

    # Clean up after the test
    purge_udf(udf)

    yield udf


@pytest.fixture
def existing_javascript_udf(
    udf_client,
    existing_project,
    purge_udf,
) -> Generator[SsbUdf, None, None]:
    """Fixture to create a test UDF and clean it up after the test."""
    udf_name = "ansible_test_udf_javascript"

    # Clean up any existing test UDF
    udfs = udf_client.list_udfs(existing_project.id)
    for udf in udfs:
        if udf.name == udf_name:
            udf_client.delete_udf(existing_project.id, udf.id)

    # Create the test UDF TODO Update example to be a realistic UDF
    udf = udf_client.create_udf(
        SsbUdf(
            project_id=existing_project.id,
            name=udf_name,
            language="JAVASCRIPT",
            output_type="STRING",
            description="Test UDF created by pytest",
            code="console.log('Hello, World!');",
        ),
    )

    # Clean up after the test
    purge_udf(udf)

    yield udf


def test_list_udfs(udf_client, existing_project, existing_python_udf):
    """Test listing all UDFs for a project."""
    response = udf_client.list_udfs(existing_project.id)

    assert isinstance(response, list)
    assert isinstance(response[0], SsbUdf)
    assert response[0].id == existing_python_udf.id


def test_create_udf_python_minimal(udf_client, existing_project, purge_udf):
    """Test creating a UDF with minimal parameters."""
    udf_name = "ansible_test_minimal_udf"

    # Create the UDF
    response = udf_client.create_udf(
        SsbUdf(
            project_id=existing_project.id,
            name=udf_name,
            output_type="PYTHON_INFERRED",
            language="PYTHON",
        ),
    )

    # Set up for cleanup
    purge_udf(response)

    assert isinstance(response, SsbUdf)
    assert response.name == udf_name.upper()
    assert response.output_type == "PYTHON_INFERRED"
    assert response.id is not None


def test_create_udf_python_with_description(udf_client, existing_project, purge_udf):
    """Test creating a UDF with description."""
    udf_name = "ansible_test_described_udf"
    description = "Test UDF with description"

    # Create the UDF
    response = udf_client.create_udf(
        SsbUdf(
            project_id=existing_project.id,
            name=udf_name,
            language="PYTHON",
            output_type="PYTHON_INFERRED",
            description=description,
        ),
    )

    # Set up for cleanup
    purge_udf(response)

    assert isinstance(response, SsbUdf)
    assert response.name == udf_name.upper()
    assert response.description == description
    assert response.id is not None


def test_update_udf(udf_client, existing_project, existing_python_udf):
    """Test updating a UDF."""
    updated_name = "ansible_test_udf_updated"
    updated_description = "Updated test UDF"

    response = udf_client.update_udf(
        SsbUdf(
            project_id=existing_project.id,
            id=existing_python_udf.id,
            output_type=existing_python_udf.output_type,
            language=existing_python_udf.language,
            name=updated_name,
            description=updated_description,
        ),
    )

    assert isinstance(response, SsbUdf)
    assert response.name == updated_name.upper()
    assert response.description == updated_description


def test_delete_udf(udf_client, existing_project, existing_python_udf):
    """Test deleting a UDF."""
    # Delete the UDF
    response = udf_client.delete_udf(existing_project.id, existing_python_udf.id)

    assert isinstance(response, type(None))

    # Verify the UDF is deleted by listing UDFs
    udfs = udf_client.list_udfs(existing_project.id)
    udf_ids = [u.id for u in udfs]
    assert existing_python_udf.id not in udf_ids
