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

from ansible_collections.cloudera.services.plugins.modules import (
    ml_project_model_deployment,
)
from ansible_collections.cloudera.services.plugins.module_utils.common import from_dict
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlModelDeployment,
)

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


@pytest.mark.slow
def test_started_creates_deployment(
    ml_module_args,
    existing_ml_project,
    existing_ml_model,
    built_ml_model_build,
    purge_ml_model_deployment,
):
    """Deploy a built build of a model. Slow: waits for the build to finish."""

    ml_module_args(
        {
            "state": "started",
            "project_id": existing_ml_project.id,
            "model_id": existing_ml_model.id,
            "build_id": built_ml_model_build.id,
            "cpu": 1,
            "memory": 2,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    result = e.value
    purge_ml_model_deployment(
        existing_ml_project.id,
        existing_ml_model.id,
        built_ml_model_build.id,
        from_dict(MlModelDeployment, result["deployment"]),
    )

    assert result["changed"] is True
    assert "id" in result["deployment"]


@pytest.mark.slow
def test_started_idempotent(
    ml_module_args,
    existing_ml_project,
    existing_ml_model,
    built_ml_model_build,
    purge_ml_model_deployment,
    ml_model_deployment_client,
):
    """Re-applying started against a running deployment is idempotent."""

    # Seed a running deployment directly.
    seeded = ml_model_deployment_client.create_deployment(
        existing_ml_project.id,
        existing_ml_model.id,
        built_ml_model_build.id,
        MlModelDeployment(build_id=built_ml_model_build.id, cpu=1, memory=2),
    )
    purge_ml_model_deployment(
        existing_ml_project.id,
        existing_ml_model.id,
        built_ml_model_build.id,
        seeded,
    )

    # Address the deployment by id so the check is deterministic regardless of
    # how far the freshly-seeded deployment has progressed toward "deployed".
    ml_module_args(
        {
            "state": "started",
            "project_id": existing_ml_project.id,
            "model_id": existing_ml_model.id,
            "build_id": built_ml_model_build.id,
            "id": seeded.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    result = e.value
    assert result["changed"] is False
    assert result["deployment"]["id"] == seeded.id


@pytest.mark.slow
def test_stopped_stops_deployment(
    ml_module_args,
    existing_ml_project,
    existing_ml_model,
    built_ml_model_build,
    purge_ml_model_deployment,
    ml_model_deployment_client,
):
    """Stopping a running deployment reports changed."""

    seeded = ml_model_deployment_client.create_deployment(
        existing_ml_project.id,
        existing_ml_model.id,
        built_ml_model_build.id,
        MlModelDeployment(build_id=built_ml_model_build.id, cpu=1, memory=2),
    )
    purge_ml_model_deployment(
        existing_ml_project.id,
        existing_ml_model.id,
        built_ml_model_build.id,
        seeded,
    )

    ml_module_args(
        {
            "state": "stopped",
            "project_id": existing_ml_project.id,
            "model_id": existing_ml_model.id,
            "build_id": built_ml_model_build.id,
            "id": seeded.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_deployment.main()

    assert e.value["changed"] is True
