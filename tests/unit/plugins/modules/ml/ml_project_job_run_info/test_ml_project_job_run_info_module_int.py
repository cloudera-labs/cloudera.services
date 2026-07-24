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

from ansible_collections.cloudera.services.plugins.modules import (
    ml_project_job_run_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlJobRun

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


@pytest.fixture(scope="module")
def seeded_job_run(existing_ml_project, existing_ml_job, ml_job_run_client) -> MlJobRun:
    """Ensure a single shared run exists for the job across the info tests."""
    return ml_job_run_client.create_job_run(
        existing_ml_project.id,
        existing_ml_job.id,
        MlJobRun(),
    )


def test_list_all(
    ml_module_args,
    existing_ml_project,
    existing_ml_job,
    seeded_job_run,
):
    """List all runs of a job."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "job_id": existing_ml_job.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    result = e.value
    assert result["changed"] is False
    assert any(r["id"] == seeded_job_run.id for r in result["job_runs"])


def test_by_id(
    ml_module_args,
    existing_ml_project,
    existing_ml_job,
    seeded_job_run,
):
    """Retrieve a single run by id."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "job_id": existing_ml_job.id,
            "id": seeded_job_run.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    runs = e.value["job_runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == seeded_job_run.id


def test_by_id_not_found(ml_module_args, existing_ml_project, existing_ml_job):
    """A missing run by id returns an empty list."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "job_id": existing_ml_job.id,
            "id": "0000-0000-0000-0000",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    assert e.value["job_runs"] == []


def test_missing_job(ml_module_args, existing_ml_project):
    """A missing job fails."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "job_name": "nonexistent-job-name-12345",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Job not found"):
        ml_project_job_run_info.main()
