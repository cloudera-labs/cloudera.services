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
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_project_job_run

REQUIRED_ENV_VARS = [
    "CML_ENDPOINT",
    "CML_API_KEY",
]

ACTIVE_OR_DONE = [
    "ENGINE_SCHEDULING",
    "ENGINE_STARTING",
    "ENGINE_RUNNING",
    "ENGINE_SUCCEEDED",
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


def test_start_job_run(ml_module_args, existing_ml_project, existing_ml_job):
    """Start a run of a job."""

    ml_module_args(
        {
            "state": "started",
            "project_id": existing_ml_project.id,
            "id": existing_ml_job.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    result = e.value
    assert "id" in result["job_run"]
    assert result["job_run"]["status"] in ACTIVE_OR_DONE


def test_check_mode_start(
    ml_module_args,
    existing_ml_project,
    existing_ml_job,
    ml_job_run_client,
):
    """Check mode reports change but does not create a run."""
    before = ml_job_run_client.list_job_runs(
        existing_ml_project.id,
        existing_ml_job.id,
    )

    ml_module_args(
        {
            "state": "started",
            "project_id": existing_ml_project.id,
            "id": existing_ml_job.id,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    after = ml_job_run_client.list_job_runs(
        existing_ml_project.id,
        existing_ml_job.id,
    )
    # Check mode must never create a run, regardless of whether a run is
    # already active (which would make the operation report no change).
    assert len(after) == len(before)


def test_missing_job(ml_module_args, existing_ml_project):
    """A missing job fails."""

    ml_module_args(
        {
            "state": "started",
            "project_id": existing_ml_project.id,
            "name": "nonexistent-job-name-12345",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Job not found"):
        ml_project_job_run.main()
