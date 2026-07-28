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

from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbProject,
)
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleFailJson,
)

REQUIRED_ENV_VARS = [
    "SSB_SSE_API_URL",
    "SSB_SSE_API_USERNAME",
    "SSB_SSE_API_PASSWORD",
]


def test_list_projects(ssb_project_client, existing_project):
    """Test listing all projects."""
    response = ssb_project_client.list_projects()

    assert isinstance(response, list)
    assert isinstance(response[0], SsbProject)
    assert any(proj.id == existing_project.id for proj in response)


def test_create_project_minimal(ssb_project_client, purge_project):
    """Test creating a project with minimal parameters."""
    project_name = "ansible-test-minimal"

    # Create the project
    response = ssb_project_client.create_project(SsbProject(name=project_name))

    # Set up for cleanup
    purge_project(response)

    assert isinstance(response, SsbProject)
    assert response.name == project_name
    assert response.id is not None


def test_create_project_with_description(ssb_project_client, purge_project):
    """Test creating a project with description and mv_prefix."""
    project_name = "ansible-test-description"
    description = "Test project with description"
    mv_prefix = "test_mv"

    # Create the project
    response = ssb_project_client.create_project(
        SsbProject(
            name=project_name,
            description=description,
            mv_prefix=mv_prefix,
        ),
    )

    # Set up for cleanup
    purge_project(response)

    assert isinstance(response, SsbProject)
    assert response.name == project_name
    assert response.description == description
    assert response.mv_prefix == mv_prefix
    assert response.id is not None


def test_create_project_existing_name(ssb_project_client, existing_project):
    """Test creating a project with an existing name."""
    project_name = existing_project.name

    with pytest.raises(AnsibleFailJson):
        ssb_project_client.create_project(SsbProject(name=project_name))


def test_describe_project(ssb_project_client, existing_project):
    """Test describing a specific project."""
    response = ssb_project_client.describe_project(existing_project.id)

    assert isinstance(response, SsbProject)
    assert response.id == existing_project.id
    assert response.name == existing_project.name


def test_describe_project_nonexistent(ssb_project_client):
    """Test describing a specific project."""
    response = ssb_project_client.describe_project("nonexistent-project-id-12345")

    assert response is None


def test_delete_project(ssb_project_client, deletable_project):
    """Test deleting a specific project."""

    # Delete the project
    response = ssb_project_client.delete_project(deletable_project)
    assert response is None

    # Verify the project is deleted by trying to describe it
    projects = ssb_project_client.list_projects()
    assert not any(p.id == deletable_project.id for p in projects)


@pytest.mark.skip(reason="Requires Git repository configuration")
def test_create_project_with_git_sync(ssb_project_client, purge_project):
    """Test creating a project with Git sync configuration."""
    project_name = "ansible-test-git-sync"

    # Create the project with Git sync
    response = ssb_project_client.create_project(
        name=project_name,
        scm_type="git",
        scm_url="https://github.com/example/repo.git",
        scm_branch="main",
        scm_auth_type="basic",
        scm_username="user",
        scm_password="pass",
    )

    # Set up for cleanup
    purge_project(response)

    assert isinstance(response, dict)
    assert response["name"] == project_name
    assert "sync_source_config" in response
    assert response["sync_source_config"]["type"] == "git"


@pytest.mark.skip(reason="Requires Git repository configuration")
def test_import_project(ssb_project_client, purge_project):
    """Test importing a project from Git."""
    project_name = "ansible-test-import"

    # Import the project
    response = ssb_project_client.import_project(
        name=project_name,
        scm_type="git",
        scm_url="https://github.com/example/repo.git",
        scm_branch="main",
    )

    # Set up for cleanup
    purge_project(response)

    assert isinstance(response, dict)
    assert response["name"] == project_name
    assert "id" in response
