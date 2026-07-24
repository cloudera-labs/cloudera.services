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

from ansible_collections.cloudera.services.plugins.modules import (
    ml_project_model_build_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlModel,
    MlModelBuild,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"
MODEL_ID = "model-1"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_build_info.MlProjectClient"
MODELS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_build_info.MlModelClient"
BUILDS = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_build_info.MlModelBuildClient"

BUILD_ONE = MlModelBuild(
    id="build-1",
    model_id=MODEL_ID,
    status="built",
    comment="first",
    crn="crn:build-1",
    updated_at="2026-01-01T00:00:00Z",
    creator={"email": "a@example.com", "username": "alice"},
)
BUILD_TWO = MlModelBuild(
    id="build-2",
    model_id=MODEL_ID,
    status="build failed",
    comment="second",
    crn="crn:build-2",
    updated_at="2026-02-01T00:00:00Z",
    creator={"email": "b@example.com", "username": "bob"},
)


def _mock_project_model(mocker):
    project = MlProject(id=PROJECT_ID, name="proj")
    model = MlModel(id=MODEL_ID, name="my-model", project_id=PROJECT_ID)
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)
    mocker.patch(f"{MODELS}.list_models", return_value=[model])
    mocker.patch(f"{MODELS}.describe_model", return_value=model)


def _base_args(overrides=None):
    args = {
        "url": BASE_URL,
        "api_key": API_KEY,
        "project_name": "proj",
        "name": "my-model",
    }
    if overrides:
        args.update(overrides)
    return args


def test_list_all(module_args, mocker):
    """All builds for a model are returned when no filter is given."""
    _mock_project_model(mocker)
    mocker.patch(f"{BUILDS}.list_builds", return_value=[BUILD_ONE, BUILD_TWO])

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["model_builds"]) == 2
    # Sorted by updated_at descending.
    assert result["model_builds"][0]["id"] == "build-2"


def test_filter_by_status(module_args, mocker):
    """Builds can be filtered by status."""
    _mock_project_model(mocker)
    mocker.patch(f"{BUILDS}.list_builds", return_value=[BUILD_ONE, BUILD_TWO])

    module_args(_base_args({"status": "built"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build_info.main()

    builds = e.value["model_builds"]
    assert len(builds) == 1
    assert builds[0]["id"] == "build-1"


def test_filter_by_comment(module_args, mocker):
    """Builds can be filtered by comment."""
    _mock_project_model(mocker)
    mocker.patch(f"{BUILDS}.list_builds", return_value=[BUILD_ONE, BUILD_TWO])

    module_args(_base_args({"comment": "second"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build_info.main()

    builds = e.value["model_builds"]
    assert len(builds) == 1
    assert builds[0]["id"] == "build-2"


def test_filter_by_crn_no_match(module_args, mocker):
    """Filtering by a non-existent CRN returns no builds."""
    _mock_project_model(mocker)
    mocker.patch(f"{BUILDS}.list_builds", return_value=[BUILD_ONE, BUILD_TWO])

    module_args(_base_args({"crn": "boom"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build_info.main()

    assert e.value["model_builds"] == []


def test_filter_by_creator_email(module_args, mocker):
    """Builds can be filtered by creator email."""
    _mock_project_model(mocker)
    mocker.patch(f"{BUILDS}.list_builds", return_value=[BUILD_ONE, BUILD_TWO])

    module_args(_base_args({"creator": {"email": "a@example.com"}}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build_info.main()

    builds = e.value["model_builds"]
    assert len(builds) == 1
    assert builds[0]["id"] == "build-1"


def test_model_not_found(module_args, mocker):
    """A missing model fails."""
    project = MlProject(id=PROJECT_ID, name="proj")
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)
    mocker.patch(f"{MODELS}.list_models", return_value=[])

    module_args(_base_args({"name": "ghost"}))

    with pytest.raises(AnsibleFailJson, match="Model not found"):
        ml_project_model_build_info.main()


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(_base_args({"project_name": "nope"}))

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_model_build_info.main()


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
        ml_project_model_build_info.main()


def test_model_required(module_args, mocker):
    """One of name/id is required."""
    module_args({"url": BASE_URL, "api_key": API_KEY, "project_name": "proj"})

    with pytest.raises(AnsibleFailJson):
        ml_project_model_build_info.main()
