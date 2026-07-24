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

from dataclasses import replace

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_project_model
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlModel,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model.MlProjectClient"
MODELS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model.MlModelClient"


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def test_create_model(module_args, mocker):
    """A new model is created with the required fields."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[])
    mock_create = mocker.patch(
        f"{MODELS}.create_model",
        return_value=MlModel(id="model-1", name="my-model", project_id=PROJECT_ID),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-model",
            "desc": "a model",
            "auth": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    result = e.value
    assert result["changed"] is True
    assert result["model"]["id"] == "model-1"

    mock_create.assert_called_once()
    project_id_arg, model_arg = mock_create.call_args.args
    assert project_id_arg == PROJECT_ID
    assert model_arg.name == "my-model"
    assert model_arg.description == "a model"
    assert model_arg.auth_enabled is True


def test_create_missing_desc(module_args, mocker):
    """Creating without a description fails."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[])
    mock_create = mocker.patch(f"{MODELS}.create_model")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-model",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Missing required parameters"):
        ml_project_model.main()

    mock_create.assert_not_called()


def test_present_idempotent(module_args, mocker):
    """No field changes means no update and no change."""
    _mock_project(mocker)
    existing = MlModel(
        id="model-1",
        name="my-model",
        project_id=PROJECT_ID,
        description="a model",
        auth_enabled=True,
    )
    mocker.patch(f"{MODELS}.list_models", return_value=[existing])
    mock_update = mocker.patch(f"{MODELS}.update_model")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-model",
            "desc": "a model",
            "auth": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    assert e.value["changed"] is False
    assert e.value["model"]["id"] == "model-1"
    mock_update.assert_not_called()


def test_update_description(module_args, mocker):
    """A changed description triggers an update."""
    _mock_project(mocker)
    existing = MlModel(
        id="model-1",
        name="my-model",
        project_id=PROJECT_ID,
        description="old",
    )
    mocker.patch(f"{MODELS}.list_models", return_value=[existing])
    mock_update = mocker.patch(
        f"{MODELS}.update_model",
        return_value=replace(existing, description="new"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-model",
            "desc": "new",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    assert e.value["changed"] is True
    _, model_arg = mock_update.call_args.args
    assert model_arg.description == "new"


def test_update_auth(module_args, mocker):
    """A changed auth flag triggers an update."""
    _mock_project(mocker)
    existing = MlModel(
        id="model-1",
        name="my-model",
        project_id=PROJECT_ID,
        auth_enabled=True,
    )
    mocker.patch(f"{MODELS}.list_models", return_value=[existing])
    mock_update = mocker.patch(
        f"{MODELS}.update_model",
        return_value=replace(existing, auth_enabled=False),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-model",
            "auth": False,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    assert e.value["changed"] is True
    _, model_arg = mock_update.call_args.args
    assert model_arg.auth_enabled is False


def test_check_mode_create(module_args, mocker):
    """Check mode reports change but does not create."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[])
    mock_create = mocker.patch(f"{MODELS}.create_model")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-model",
            "desc": "a model",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    assert e.value["changed"] is True
    assert e.value["model"]["name"] == "my-model"
    mock_create.assert_not_called()


def test_absent_existing(module_args, mocker):
    """Deleting an existing model removes it."""
    _mock_project(mocker)
    existing = MlModel(id="model-1", name="my-model", project_id=PROJECT_ID)
    mocker.patch(f"{MODELS}.list_models", return_value=[existing])
    mock_delete = mocker.patch(f"{MODELS}.delete_model")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-model",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    assert e.value["changed"] is True
    mock_delete.assert_called_once_with(PROJECT_ID, "model-1")


def test_absent_missing(module_args, mocker):
    """Deleting a non-existent model is a no-op."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[])
    mock_delete = mocker.patch(f"{MODELS}.delete_model")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "ghost",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_by_id(module_args, mocker):
    """A model can be addressed by id via describe_model."""
    _mock_project(mocker)
    existing = MlModel(id="model-1", name="my-model", project_id=PROJECT_ID)
    mock_describe = mocker.patch(f"{MODELS}.describe_model", return_value=existing)
    mock_delete = mocker.patch(f"{MODELS}.delete_model")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": PROJECT_ID,
            "id": "model-1",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model.main()

    assert e.value["changed"] is True
    mock_describe.assert_called_once_with(PROJECT_ID, "model-1")
    mock_delete.assert_called_once_with(PROJECT_ID, "model-1")


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "nope",
            "name": "my-model",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_model.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": "not-valid",
            "name": "my-model",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_model.main()
