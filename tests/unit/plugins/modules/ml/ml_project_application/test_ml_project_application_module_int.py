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

from ansible_collections.cloudera.services.plugins.modules import ml_project_application
from ansible_collections.cloudera.services.plugins.module_utils.common import from_dict
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlApplication

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


def test_create_application(
    request,
    ml_module_args,
    existing_ml_project,
    ml_runtime_identifier,
    ml_project_script,
    purge_ml_application,
):
    """Create an application within a project."""
    name = request.node.name.lower()[:100]

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": name,
            "subdomain": f"{name.replace('_', '-')}-{existing_ml_project.id}",
            "script": ml_project_script,
            "runtime": ml_runtime_identifier,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    result = e.value
    purge_ml_application(
        existing_ml_project.id,
        from_dict(MlApplication, result["application"]),
    )

    assert result["changed"] is True
    assert result["application"]["name"] == name
    assert "id" in result["application"]


def test_present_idempotent(
    ml_module_args,
    existing_ml_project,
    existing_ml_application,
):
    """Re-applying an existing application is idempotent."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": existing_ml_application.name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    result = e.value
    assert result["changed"] is False
    assert result["application"]["id"] == existing_ml_application.id


def test_by_id(ml_module_args, existing_ml_project, existing_ml_application):
    """Retrieve/refresh an application by id (idempotent)."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "id": existing_ml_application.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    result = e.value
    assert result["changed"] is False
    assert result["application"]["id"] == existing_ml_application.id


def test_update_description(
    ml_module_args,
    existing_ml_project,
    existing_ml_application,
):
    """Update an application's description."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": existing_ml_application.name,
            "desc": "Updated by integration test",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    result = e.value
    assert result["changed"] is True
    assert result["application"]["description"] == "Updated by integration test"


def test_delete_application(
    ml_module_args,
    existing_ml_project,
    deletable_ml_application,
):
    """Delete an application."""

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "id": deletable_ml_application.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    result = e.value
    assert result["changed"] is True


def test_delete_nonexistent(ml_module_args, existing_ml_project):
    """Deleting a non-existent application is a no-op."""

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "name": "nonexistent-application-name-12345",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    result = e.value
    assert result["changed"] is False


def test_check_mode_create(
    request,
    ml_module_args,
    existing_ml_project,
    ml_runtime_identifier,
    ml_project_script,
    ml_application_client,
):
    """Check mode reports change but does not create the application."""
    name = request.node.name.lower()[:100]

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": name,
            "subdomain": f"{name.replace('_', '-')}-{existing_ml_project.id}",
            "script": ml_project_script,
            "runtime": ml_runtime_identifier,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    assert not any(
        a.name == name
        for a in ml_application_client.list_applications(existing_ml_project.id)
    )
