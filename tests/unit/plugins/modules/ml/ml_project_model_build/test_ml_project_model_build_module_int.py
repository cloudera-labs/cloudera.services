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

from ansible_collections.cloudera.services.plugins.modules import ml_project_model_build
from ansible_collections.cloudera.services.plugins.module_utils.common import from_dict
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlModelBuild

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


def test_create_build(
    ml_module_args,
    existing_ml_project,
    existing_ml_model,
    ml_runtime_identifier,
    ml_project_script,
    purge_ml_model_build,
):
    """Create a build within a model."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "model_id": existing_ml_model.id,
            "file": ml_project_script,
            "function": "predict",
            "runtime": ml_runtime_identifier,
            "comment": "integration create",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build.main()

    result = e.value
    purge_ml_model_build(
        existing_ml_project.id,
        existing_ml_model.id,
        from_dict(MlModelBuild, result["build"]),
    )

    assert result["changed"] is True
    assert "id" in result["build"]


def test_present_by_id_idempotent(
    ml_module_args,
    existing_ml_project,
    existing_ml_model,
    existing_ml_model_build,
):
    """Referencing an existing build by id is idempotent (builds are immutable)."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "model_id": existing_ml_model.id,
            "id": existing_ml_model_build.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build.main()

    result = e.value
    assert result["changed"] is False
    assert result["build"]["id"] == existing_ml_model_build.id


@pytest.mark.xfail(
    reason="The CML v2 API returns 501 (not yet implemented) for model build deletion.",
)
def test_delete_build(
    ml_module_args,
    existing_ml_project,
    existing_ml_model,
    deletable_ml_model_build,
):
    """Delete a build."""

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "model_id": existing_ml_model.id,
            "id": deletable_ml_model_build.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_model_build.main()

    result = e.value
    assert result["changed"] is True
