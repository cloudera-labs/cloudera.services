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
    ml_project_model_deployment_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlModel,
    MlModelBuild,
    MlModelDeployment,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"
MODEL_ID = "model-1"
BUILD_ID = "build-1"

MOD = "ansible_collections.cloudera.services.plugins.modules.ml_project_model_deployment_info"
PROJECTS = f"{MOD}.MlProjectClient"
MODELS = f"{MOD}.MlModelClient"
BUILDS = f"{MOD}.MlModelBuildClient"
DEPLOYMENTS = f"{MOD}.MlModelDeploymentClient"

DEP_ONE = MlModelDeployment(
    id="dep-1",
    build_id=BUILD_ID,
    status="deployed",
    created_at="2026-01-01T00:00:00Z",
    deployer={"email": "a@example.com", "username": "alice"},
)
DEP_TWO = MlModelDeployment(
    id="dep-2",
    build_id=BUILD_ID,
    status="pending",
    created_at="2026-02-01T00:00:00Z",
    deployer={"email": "b@example.com", "username": "bob"},
)


def _mock_chain(mocker, deployments=None):
    project = MlProject(id=PROJECT_ID, name="proj")
    model = MlModel(id=MODEL_ID, name="my-model", project_id=PROJECT_ID)
    build = MlModelBuild(id=BUILD_ID, model_id=MODEL_ID, status="built")
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)
    mocker.patch(f"{MODELS}.list_models", return_value=[model])
    mocker.patch(f"{MODELS}.describe_model", return_value=model)
    mocker.patch(f"{BUILDS}.find_latest_build", return_value=build)
    mocker.patch(f"{BUILDS}.describe_build", return_value=build)
    mocker.patch(
        f"{DEPLOYMENTS}.list_deployments",
        return_value=deployments if deployments is not None else [],
    )


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
    """All deployments for a build are returned when no filter is given."""
    _mock_chain(mocker, deployments=[DEP_ONE, DEP_TWO])

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["model_deployments"]) == 2
    # Sorted by created_at descending.
    assert result["model_deployments"][0]["id"] == "dep-2"


def test_filter_by_status(module_args, mocker):
    """Deployments can be filtered by status."""
    _mock_chain(mocker, deployments=[DEP_ONE, DEP_TWO])

    module_args(_base_args({"status": "deployed"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment_info.main()

    deps = e.value["model_deployments"]
    assert len(deps) == 1
    assert deps[0]["id"] == "dep-1"


def test_filter_by_deployer_email(module_args, mocker):
    """Deployments can be filtered by deployer email."""
    _mock_chain(mocker, deployments=[DEP_ONE, DEP_TWO])

    module_args(_base_args({"deployer": {"email": "b@example.com"}}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment_info.main()

    deps = e.value["model_deployments"]
    assert len(deps) == 1
    assert deps[0]["id"] == "dep-2"


def test_build_not_found(module_args, mocker):
    """A model with no build fails."""
    project = MlProject(id=PROJECT_ID, name="proj")
    model = MlModel(id=MODEL_ID, name="my-model")
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{MODELS}.list_models", return_value=[model])
    mocker.patch(f"{BUILDS}.find_latest_build", return_value=None)

    module_args(_base_args())

    with pytest.raises(AnsibleFailJson, match="has not been built"):
        ml_project_model_deployment_info.main()


def test_model_not_found(module_args, mocker):
    """A missing model fails."""
    project = MlProject(id=PROJECT_ID, name="proj")
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{MODELS}.list_models", return_value=[])

    module_args(_base_args({"name": "ghost"}))

    with pytest.raises(AnsibleFailJson, match="Model not found"):
        ml_project_model_deployment_info.main()


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(_base_args({"project_name": "nope"}))

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_model_deployment_info.main()


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
        ml_project_model_deployment_info.main()
