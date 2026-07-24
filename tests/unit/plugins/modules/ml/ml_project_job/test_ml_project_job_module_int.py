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

from ansible_collections.cloudera.services.plugins.modules import ml_project_job
from ansible_collections.cloudera.services.plugins.module_utils.common import from_dict
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlJob

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


def test_create_job(
    request,
    ml_module_args,
    existing_ml_project,
    ml_runtime_identifier,
    ml_project_script,
    purge_ml_job,
):
    """Create a job within a project."""
    name = request.node.name.lower()[:100]

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": name,
            "script": ml_project_script,
            "runtime": ml_runtime_identifier,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    result = e.value
    purge_ml_job(existing_ml_project.id, from_dict(MlJob, result["job"]))

    assert result["changed"] is True
    assert result["job"]["name"] == name
    assert "id" in result["job"]


def test_present_idempotent(ml_module_args, existing_ml_project, existing_ml_job):
    """Re-applying an existing job is idempotent."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": existing_ml_job.name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    result = e.value
    assert result["changed"] is False
    assert result["job"]["id"] == existing_ml_job.id


def test_by_id(ml_module_args, existing_ml_project, existing_ml_job):
    """Retrieve/refresh a job by id (idempotent)."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "id": existing_ml_job.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    result = e.value
    assert result["changed"] is False
    assert result["job"]["id"] == existing_ml_job.id


def test_update_schedule(ml_module_args, existing_ml_project, existing_ml_job):
    """Update a job's schedule."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": existing_ml_job.name,
            "schedule": "0 3 * * *",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["schedule"] == "0 3 * * *"


def test_delete_job(ml_module_args, existing_ml_project, deletable_ml_job):
    """Delete a job."""

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "id": deletable_ml_job.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    result = e.value
    assert result["changed"] is True


def test_delete_nonexistent(ml_module_args, existing_ml_project):
    """Deleting a non-existent job is a no-op."""

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "name": "nonexistent-job-name-12345",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    result = e.value
    assert result["changed"] is False


def test_check_mode_create(
    request,
    ml_module_args,
    existing_ml_project,
    ml_runtime_identifier,
    ml_project_script,
    ml_job_client,
):
    """Check mode reports change but does not create the job."""
    name = request.node.name.lower()[:100]

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "name": name,
            "script": ml_project_script,
            "runtime": ml_runtime_identifier,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is True
    assert not any(
        j.name == name for j in ml_job_client.list_jobs(existing_ml_project.id)
    )
