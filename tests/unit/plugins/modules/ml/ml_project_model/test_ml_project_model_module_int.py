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

from ansible_collections.cloudera.services.plugins.modules import ml_project_model
from ansible_collections.cloudera.services.plugins.module_utils.common import from_dict
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlModel

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


def test_create_model(
    request,
    ml_module_args,
    existing_ml_project,
    purge_ml_model,
):
    """Create a model within a project."""
    name = request.node.name.lower()[:100]

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": name,
            "desc": "Created by integration test.",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    result = e.value
    purge_ml_model(existing_ml_project.id, from_dict(MlModel, result["model"]))

    assert result["changed"] is True
    assert result["model"]["name"] == name
    assert "id" in result["model"]


def test_present_idempotent(ml_module_args, existing_ml_project, existing_ml_model):
    """Re-applying an existing model is idempotent."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": existing_ml_model.name,
            "desc": existing_ml_model.description,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    result = e.value
    assert result["changed"] is False
    assert result["model"]["id"] == existing_ml_model.id


def test_by_id(ml_module_args, existing_ml_project, existing_ml_model):
    """Retrieve/refresh a model by id (idempotent)."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "id": existing_ml_model.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    result = e.value
    assert result["changed"] is False
    assert result["model"]["id"] == existing_ml_model.id


def test_update_description(ml_module_args, existing_ml_project, deletable_ml_model):
    """Update a model's description."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": deletable_ml_model.name,
            "desc": "An updated description.",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    result = e.value
    assert result["changed"] is True
    assert result["model"]["description"] == "An updated description."


@pytest.mark.xfail(
    reason="The CML v2 API returns 501 (not yet implemented) for model deletion.",
)
def test_delete_model(ml_module_args, existing_ml_project, deletable_ml_model):
    """Delete a model."""

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "id": deletable_ml_model.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    result = e.value
    assert result["changed"] is True


def test_delete_nonexistent(ml_module_args, existing_ml_project):
    """Deleting a non-existent model is a no-op."""

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "name": "nonexistent-model-name-12345",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    result = e.value
    assert result["changed"] is False


def test_check_mode_create(
    request,
    ml_module_args,
    existing_ml_project,
    ml_model_client,
):
    """Check mode reports change but does not create the model."""
    name = request.node.name.lower()[:100]

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": name,
            "desc": "Created by check mode integration test.",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    assert e.value["changed"] is True
    assert not any(
        m.name == name for m in ml_model_client.list_models(existing_ml_project.id)
    )
