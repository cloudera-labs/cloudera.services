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

from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlProject,
)

REQUIRED_ENV_VARS = [
    "CML_ENDPOINT",
    "CML_API_KEY",
]


def test_list_projects(ml_project_client, existing_ml_project):
    """List all projects and find the module-scoped one."""
    response = ml_project_client.list_projects()

    assert isinstance(response, list)
    assert all(isinstance(p, MlProject) for p in response)
    assert any(p.id == existing_ml_project.id for p in response)


def test_create_project_minimal(ml_project_client, purge_ml_project):
    """Create a project with minimal parameters."""
    project_name = "ansible-ml-int-minimal"

    response = ml_project_client.create_project(
        MlProject(name=project_name, template="blank"),
    )
    purge_ml_project(response)

    assert isinstance(response, MlProject)
    assert response.name == project_name
    assert isinstance(response.id, str)


def test_create_project_with_description(ml_project_client, purge_ml_project):
    """Create a project with a description."""
    project_name = "ansible-ml-int-description"
    description = "Integration test project with a description"

    response = ml_project_client.create_project(
        MlProject(name=project_name, description=description, template="blank"),
    )
    purge_ml_project(response)

    assert isinstance(response, MlProject)
    assert response.name == project_name
    assert response.description == description
    assert isinstance(response.id, str)


def test_describe_project(ml_project_client, existing_ml_project):
    """Describe a specific project by id."""
    response = ml_project_client.describe_project(existing_ml_project.id)

    assert isinstance(response, MlProject)
    assert response.id == existing_ml_project.id
    assert response.name == existing_ml_project.name


def test_describe_project_nonexistent(ml_project_client):
    """Describing a nonexistent project returns None."""
    response = ml_project_client.describe_project("0000-0000-0000-0000")

    assert response is None


def test_update_project(ml_project_client, deletable_ml_project):
    """Update a project's description."""
    updated = ml_project_client.update_project(
        MlProject(
            id=deletable_ml_project.id,
            name=deletable_ml_project.name,
            description="Updated by integration test",
        ),
    )

    assert isinstance(updated, MlProject)
    assert updated.id == deletable_ml_project.id

    described = ml_project_client.describe_project(deletable_ml_project.id)
    assert described.description == "Updated by integration test"


def test_delete_project(ml_project_client, deletable_ml_project):
    """Delete a project and confirm it is gone."""
    response = ml_project_client.delete_project(deletable_ml_project.id)
    assert response is None

    projects = ml_project_client.list_projects()
    assert not any(p.id == deletable_ml_project.id for p in projects)
