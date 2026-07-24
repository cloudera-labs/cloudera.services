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

from typing import Callable

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_project
from ansible_collections.cloudera.services.plugins.module_utils.common import from_dict
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlProject

REQUIRED_ENV_VARS = [
    "CML_ENDPOINT",
    "CML_API_KEY",
]


@pytest.fixture
def ml_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args (endpoint + bearer token) for CML tests."""

    def _ml_module_args(overrides: dict = {}) -> None:
        args = {
            "url": env_context["CML_ENDPOINT"],
            "api_key": env_context["CML_API_KEY"],
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _ml_module_args


def test_ml_project_module_create_minimal(request, ml_module_args, purge_ml_project):
    """Create a project with minimal parameters."""
    project_name = request.node.name

    ml_module_args({"state": "present", "name": project_name})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value

    # Register the created project for cleanup
    purge_ml_project(from_dict(MlProject, result["project"]))

    assert result["changed"] is True
    assert result["project"]["name"] == project_name
    assert "id" in result["project"]


def test_ml_project_module_create_with_description(
    request,
    ml_module_args,
    purge_ml_project,
):
    """Create a project with a description."""
    project_name = request.node.name
    description = "Test project with description"

    ml_module_args({"state": "present", "name": project_name, "desc": description})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    purge_ml_project(from_dict(MlProject, result["project"]))

    assert result["changed"] is True
    assert result["project"]["name"] == project_name
    assert result["project"]["description"] == description


def test_ml_project_module_present_idempotent(ml_module_args, existing_ml_project):
    """Re-applying an existing project is idempotent."""

    ml_module_args({"state": "present", "name": existing_ml_project.name})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    assert result["changed"] is False
    assert result["project"]["id"] == existing_ml_project.id
    assert result["project"]["name"] == existing_ml_project.name


def test_ml_project_module_by_id(ml_module_args, existing_ml_project):
    """Retrieve a project by ID (idempotent)."""

    ml_module_args({"state": "present", "id": existing_ml_project.id})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    assert result["changed"] is False
    assert result["project"]["id"] == existing_ml_project.id
    assert result["project"]["name"] == existing_ml_project.name


def test_ml_project_module_update_description(ml_module_args, deletable_ml_project):
    """Update a project's description."""

    ml_module_args(
        {
            "state": "present",
            "name": deletable_ml_project.name,
            "desc": "Updated by integration test",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    assert result["changed"] is True
    assert result["project"]["description"] == "Updated by integration test"


def test_ml_project_module_delete(ml_module_args, deletable_ml_project):
    """Delete a project."""

    ml_module_args({"state": "absent", "name": deletable_ml_project.name})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    assert result["changed"] is True


def test_ml_project_module_delete_nonexistent(ml_module_args):
    """Deleting a non-existent project is a no-op."""

    ml_module_args({"state": "absent", "name": "nonexistent-project-name-12345"})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    assert result["changed"] is False


def test_ml_project_module_check_mode_create(
    request,
    ml_module_args,
    ml_project_client,
):
    """Check mode reports change but does not create the project."""
    project_name = request.node.name

    ml_module_args(
        {"state": "present", "name": project_name, "_ansible_check_mode": True},
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    assert result["changed"] is True

    # Nothing should have been persisted
    assert not any(p.name == project_name for p in ml_project_client.list_projects())


def test_ml_project_module_check_mode_delete(
    ml_module_args,
    existing_ml_project,
    ml_project_client,
):
    """Check mode reports change but does not delete the project."""

    ml_module_args(
        {
            "state": "absent",
            "name": existing_ml_project.name,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    assert result["changed"] is True

    # The project must still exist (existing_ml_project teardown will remove it)
    assert any(
        p.id == existing_ml_project.id for p in ml_project_client.list_projects()
    )
