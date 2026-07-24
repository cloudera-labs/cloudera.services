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

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_project_model_info
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlModel,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_info.MlProjectClient"
MODELS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_info.MlModelClient"

MODEL_ONE = MlModel(
    id="model-1",
    name="fraud",
    project_id=PROJECT_ID,
    description="fraud detector",
    auth_enabled=True,
    creator={"email": "a@example.com", "username": "alice"},
)
MODEL_TWO = MlModel(
    id="model-2",
    name="churn",
    project_id=PROJECT_ID,
    description="churn predictor",
    auth_enabled=False,
    creator={"email": "b@example.com", "username": "bob"},
)


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def _base_args(overrides=None):
    args = {"url": BASE_URL, "api_key": API_KEY, "project_name": "proj"}
    if overrides:
        args.update(overrides)
    return args


def test_list_all(module_args, mocker):
    """All models in a project are returned when no filter is given."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[MODEL_ONE, MODEL_TWO])

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["models"]) == 2


def test_filter_by_name(module_args, mocker):
    """Models can be filtered by name."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[MODEL_ONE, MODEL_TWO])

    module_args(_base_args({"name": "fraud"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_info.main()

    models = e.value["models"]
    assert len(models) == 1
    assert models[0]["name"] == "fraud"


def test_filter_by_desc(module_args, mocker):
    """Models can be filtered by description."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[MODEL_ONE, MODEL_TWO])

    module_args(_base_args({"desc": "churn predictor"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_info.main()

    models = e.value["models"]
    assert len(models) == 1
    assert models[0]["name"] == "churn"


def test_filter_by_auth(module_args, mocker):
    """Models can be filtered by auth flag."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[MODEL_ONE, MODEL_TWO])

    module_args(_base_args({"auth": True}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_info.main()

    models = e.value["models"]
    assert len(models) == 1
    assert models[0]["name"] == "fraud"


def test_filter_by_creator_email(module_args, mocker):
    """Models can be filtered by creator email."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.list_models", return_value=[MODEL_ONE, MODEL_TWO])

    module_args(_base_args({"creator": {"email": "b@example.com"}}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_info.main()

    models = e.value["models"]
    assert len(models) == 1
    assert models[0]["name"] == "churn"


def test_by_id(module_args, mocker):
    """A single model can be retrieved by id."""
    _mock_project(mocker)
    mock_describe = mocker.patch(f"{MODELS}.describe_model", return_value=MODEL_ONE)
    mock_list = mocker.patch(f"{MODELS}.list_models")

    module_args(_base_args({"id": "model-1"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_info.main()

    models = e.value["models"]
    assert len(models) == 1
    assert models[0]["id"] == "model-1"
    mock_describe.assert_called_once_with(PROJECT_ID, "model-1")
    mock_list.assert_not_called()


def test_by_id_not_found(module_args, mocker):
    """A missing model by id returns an empty list."""
    _mock_project(mocker)
    mocker.patch(f"{MODELS}.describe_model", return_value=None)

    module_args(_base_args({"id": "model-x"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_info.main()

    assert e.value["models"] == []


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(_base_args({"project_name": "nope"}))

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_model_info.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args({"url": BASE_URL, "api_key": API_KEY, "project_id": "not-valid"})

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_model_info.main()


def test_project_required(module_args, mocker):
    """One of project_name/project_id is required."""
    module_args({"url": BASE_URL, "api_key": API_KEY})

    with pytest.raises(AnsibleFailJson):
        ml_project_model_info.main()
