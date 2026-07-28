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
    ml_project_model_deployment,
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

MOD = (
    "ansible_collections.cloudera.services.plugins.modules.ml_project_model_deployment"
)
PROJECTS = f"{MOD}.MlProjectClient"
MODELS = f"{MOD}.MlModelClient"
BUILDS = f"{MOD}.MlModelBuildClient"
DEPLOYMENTS = f"{MOD}.MlModelDeploymentClient"


def _mock_chain(mocker, deployments=None):
    """Patch project, model, build resolution and deployment listing."""
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
        "model_name": "my-model",
    }
    if overrides:
        args.update(overrides)
    return args


def test_started_creates_when_absent(module_args, mocker):
    """state=started with no existing deployment creates one."""
    _mock_chain(mocker)
    mock_create = mocker.patch(
        f"{DEPLOYMENTS}.create_deployment",
        return_value=MlModelDeployment(
            id="dep-1",
            build_id=BUILD_ID,
            status="deployed",
        ),
    )

    module_args(_base_args({"state": "started", "cpu": 1, "memory": 2}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    result = e.value
    assert result["changed"] is True
    assert result["deployment"]["id"] == "dep-1"

    mock_create.assert_called_once()
    p, m, b, dep = mock_create.call_args.args
    assert (p, m, b) == (PROJECT_ID, MODEL_ID, BUILD_ID)
    assert dep.cpu == 1
    assert dep.memory == 2


def test_create_passes_gpu_and_env(module_args, mocker):
    """cpu/memory/gpu/env flow into the created deployment."""
    _mock_chain(mocker)
    mock_create = mocker.patch(
        f"{DEPLOYMENTS}.create_deployment",
        return_value=MlModelDeployment(id="dep-1", build_id=BUILD_ID),
    )

    module_args(
        _base_args(
            {"cpu": 2, "memory": 4, "gpu": 1, "env": {"LOG": "debug"}},
        ),
    )

    with pytest.raises(AnsibleExitJson):
        ml_project_model_deployment.main()

    _, _, _, dep = mock_create.call_args.args
    assert dep.nvidia_gpus == 1
    assert dep.environment == {"LOG": "debug"}


def test_started_idempotent_when_deployed(module_args, mocker):
    """state=started with a running deployment is a no-op (immutable)."""
    existing = MlModelDeployment(id="dep-1", build_id=BUILD_ID, status="deployed")
    _mock_chain(mocker, deployments=[existing])
    mock_create = mocker.patch(f"{DEPLOYMENTS}.create_deployment")

    module_args(_base_args({"state": "started"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is False
    assert e.value["deployment"]["id"] == "dep-1"
    mock_create.assert_not_called()


def test_stopped_stops_running(module_args, mocker):
    """state=stopped stops the running deployment."""
    existing = MlModelDeployment(id="dep-1", build_id=BUILD_ID, status="deployed")
    _mock_chain(mocker, deployments=[existing])
    mock_stop = mocker.patch(
        f"{DEPLOYMENTS}.stop_deployment",
        return_value=MlModelDeployment(id="dep-1", build_id=BUILD_ID, status="stopped"),
    )

    module_args(_base_args({"state": "stopped"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is True
    mock_stop.assert_called_once_with(PROJECT_ID, MODEL_ID, BUILD_ID, "dep-1")


def test_stopped_noop_when_none(module_args, mocker):
    """state=stopped with no running deployment is a no-op."""
    _mock_chain(mocker, deployments=[])
    mock_stop = mocker.patch(f"{DEPLOYMENTS}.stop_deployment")

    module_args(_base_args({"state": "stopped"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is False
    mock_stop.assert_not_called()


def test_absent_deletes_existing(module_args, mocker):
    """state=absent deletes the deployment."""
    existing = MlModelDeployment(id="dep-1", build_id=BUILD_ID, status="deployed")
    _mock_chain(mocker, deployments=[existing])
    mock_delete = mocker.patch(f"{DEPLOYMENTS}.delete_deployment")

    module_args(_base_args({"state": "absent"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is True
    assert e.value["deployment"] == {}
    mock_delete.assert_called_once_with(PROJECT_ID, MODEL_ID, BUILD_ID, "dep-1")


def test_absent_noop_when_none(module_args, mocker):
    """state=absent with no deployment is a no-op."""
    _mock_chain(mocker, deployments=[])
    mock_delete = mocker.patch(f"{DEPLOYMENTS}.delete_deployment")

    module_args(_base_args({"state": "absent"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_restarted_creates_when_absent(module_args, mocker):
    """state=restarted with no deployment just creates one."""
    _mock_chain(mocker, deployments=[])
    mock_stop = mocker.patch(f"{DEPLOYMENTS}.stop_deployment")
    mock_create = mocker.patch(
        f"{DEPLOYMENTS}.create_deployment",
        return_value=MlModelDeployment(id="dep-2", build_id=BUILD_ID),
    )

    module_args(_base_args({"state": "restarted"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is True
    mock_stop.assert_not_called()
    mock_create.assert_called_once()


def test_restarted_stops_then_creates(module_args, mocker):
    """state=restarted stops the running deployment and starts a new one."""
    existing = MlModelDeployment(
        id="dep-1",
        build_id=BUILD_ID,
        status="deployed",
        cpu=2,
        memory=4,
    )
    _mock_chain(mocker, deployments=[existing])
    mock_stop = mocker.patch(f"{DEPLOYMENTS}.stop_deployment")
    mock_create = mocker.patch(
        f"{DEPLOYMENTS}.create_deployment",
        return_value=MlModelDeployment(id="dep-2", build_id=BUILD_ID),
    )

    module_args(_base_args({"state": "restarted"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is True
    mock_stop.assert_called_once_with(PROJECT_ID, MODEL_ID, BUILD_ID, "dep-1")
    mock_create.assert_called_once()
    # Config carried over from the stopped deployment.
    _, _, _, dep = mock_create.call_args.args
    assert dep.cpu == 2
    assert dep.memory == 4


def test_check_mode_start(module_args, mocker):
    """Check mode reports change but does not create."""
    _mock_chain(mocker, deployments=[])
    mock_create = mocker.patch(f"{DEPLOYMENTS}.create_deployment")

    module_args(_base_args({"state": "started", "_ansible_check_mode": True}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()


def test_build_not_found(module_args, mocker):
    """A missing build fails."""
    project = MlProject(id=PROJECT_ID, name="proj")
    model = MlModel(id=MODEL_ID, name="my-model")
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{MODELS}.list_models", return_value=[model])
    mocker.patch(f"{BUILDS}.find_latest_build", return_value=None)

    module_args(_base_args())

    with pytest.raises(AnsibleFailJson, match="Model build not found"):
        ml_project_model_deployment.main()


def test_model_not_found(module_args, mocker):
    """A missing model fails."""
    project = MlProject(id=PROJECT_ID, name="proj")
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project])
    mocker.patch(f"{MODELS}.list_models", return_value=[])

    module_args(_base_args({"model_name": "ghost"}))

    with pytest.raises(AnsibleFailJson, match="Model not found"):
        ml_project_model_deployment.main()


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(_base_args({"project_name": "nope"}))

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_model_deployment.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": "not-valid",
            "model_name": "my-model",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_model_deployment.main()
