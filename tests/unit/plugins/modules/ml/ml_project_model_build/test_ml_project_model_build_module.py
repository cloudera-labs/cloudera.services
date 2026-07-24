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

from ansible_collections.cloudera.services.plugins.modules import ml_project_model_build
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlModel,
    MlModelBuild,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"
MODEL_ID = "model-1"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_build.MlProjectClient"
MODELS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_build.MlModelClient"
BUILDS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_build.MlModelBuildClient"


def _mock_project_model(mocker):
    project = MlProject(id=PROJECT_ID, name="proj")
    model = MlModel(id=MODEL_ID, name="my-model", project_id=PROJECT_ID)
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)
    mocker.patch(f"{MODELS}.list_models", return_value=[model])
    mocker.patch(f"{MODELS}.describe_model", return_value=model)


def test_create_build(module_args, mocker):
    """A new build is created with the required fields."""
    _mock_project_model(mocker)
    mock_create = mocker.patch(
        f"{BUILDS}.create_build",
        return_value=MlModelBuild(id="build-1", model_id=MODEL_ID, status="pending"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "my-model",
            "file": "predict.py",
            "function": "predict",
            "runtime": "rt-1",
            "comment": "first build",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build.main()

    result = e.value
    assert result["changed"] is True
    assert result["build"]["id"] == "build-1"

    mock_create.assert_called_once()
    project_id_arg, model_id_arg, build_arg = mock_create.call_args.args
    assert project_id_arg == PROJECT_ID
    assert model_id_arg == MODEL_ID
    assert build_arg.file_path == "predict.py"
    assert build_arg.function_name == "predict"
    assert build_arg.runtime_identifier == "rt-1"
    assert build_arg.comment == "first build"


def test_create_requires_file_function_runtime(module_args, mocker):
    """file, function, and runtime are required together for creation."""
    _mock_project_model(mocker)
    mocker.patch(f"{BUILDS}.create_build")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "my-model",
            "file": "predict.py",
        },
    )

    with pytest.raises(AnsibleFailJson):
        ml_project_model_build.main()


def test_kernel_requires_runtime(module_args, mocker):
    """kernel requires runtime."""
    _mock_project_model(mocker)

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "my-model",
            "file": "predict.py",
            "function": "predict",
            "kernel": "python3",
        },
    )

    with pytest.raises(AnsibleFailJson):
        ml_project_model_build.main()


def test_present_by_id_idempotent(module_args, mocker):
    """An existing build referenced by id is returned unchanged (immutable)."""
    _mock_project_model(mocker)
    existing = MlModelBuild(id="build-1", model_id=MODEL_ID, status="built")
    mocker.patch(f"{BUILDS}.describe_build", return_value=existing)
    mock_create = mocker.patch(f"{BUILDS}.create_build")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "my-model",
            "id": "build-1",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build.main()

    assert e.value["changed"] is False
    assert e.value["build"]["id"] == "build-1"
    mock_create.assert_not_called()


def test_present_by_id_not_found(module_args, mocker):
    """A present build referenced by a missing id fails."""
    _mock_project_model(mocker)
    mocker.patch(f"{BUILDS}.describe_build", return_value=None)

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "my-model",
            "id": "build-x",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Build not found"):
        ml_project_model_build.main()


def test_check_mode_create(module_args, mocker):
    """Check mode reports change but does not create."""
    _mock_project_model(mocker)
    mock_create = mocker.patch(f"{BUILDS}.create_build")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "my-model",
            "file": "predict.py",
            "function": "predict",
            "runtime": "rt-1",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build.main()

    assert e.value["changed"] is True
    assert e.value["build"]["file_path"] == "predict.py"
    mock_create.assert_not_called()


def test_absent_existing(module_args, mocker):
    """Deleting an existing build removes it."""
    _mock_project_model(mocker)
    existing = MlModelBuild(id="build-1", model_id=MODEL_ID)
    mocker.patch(f"{BUILDS}.describe_build", return_value=existing)
    mock_delete = mocker.patch(f"{BUILDS}.delete_build")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "my-model",
            "id": "build-1",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build.main()

    assert e.value["changed"] is True
    mock_delete.assert_called_once_with(PROJECT_ID, MODEL_ID, "build-1")


def test_absent_missing(module_args, mocker):
    """Deleting a non-existent build is a no-op."""
    _mock_project_model(mocker)
    mocker.patch(f"{BUILDS}.describe_build", return_value=None)
    mock_delete = mocker.patch(f"{BUILDS}.delete_build")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "my-model",
            "id": "build-x",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_model_not_found(module_args, mocker):
    """A missing model fails."""
    project = MlProject(id=PROJECT_ID, name="proj")
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)
    mocker.patch(f"{MODELS}.list_models", return_value=[])

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "model_name": "ghost",
            "file": "predict.py",
            "function": "predict",
            "runtime": "rt-1",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Model not found"):
        ml_project_model_build.main()


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "nope",
            "model_name": "my-model",
            "file": "predict.py",
            "function": "predict",
            "runtime": "rt-1",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_model_build.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": "not-valid",
            "model_name": "my-model",
            "file": "predict.py",
            "function": "predict",
            "runtime": "rt-1",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_model_build.main()
