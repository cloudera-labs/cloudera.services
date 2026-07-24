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
    ml_project_job_run_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlJob,
    MlJobRun,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"
JOB_ID = "job-1"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job_run_info.MlProjectClient"
JOBS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job_run_info.MlJobClient"
RUNS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job_run_info.MlJobRunClient"

RUN_ONE = MlJobRun(
    id="run-1",
    job_id=JOB_ID,
    project_id=PROJECT_ID,
    status="ENGINE_SUCCEEDED",
    creator={"email": "a@example.com", "username": "alice"},
)
RUN_TWO = MlJobRun(
    id="run-2",
    job_id=JOB_ID,
    project_id=PROJECT_ID,
    status="ENGINE_FAILED",
    creator={"email": "b@example.com", "username": "bob"},
)


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def _mock_job(mocker, job=MlJob(id=JOB_ID, name="my-job", project_id=PROJECT_ID)):
    mocker.patch(f"{JOBS}.list_jobs", return_value=[job] if job else [])
    mocker.patch(f"{JOBS}.describe_job", return_value=job)


def _base_args(overrides=None):
    args = {
        "url": BASE_URL,
        "api_key": API_KEY,
        "project_name": "proj",
        "job_name": "my-job",
    }
    if overrides:
        args.update(overrides)
    return args


def test_list_all(module_args, mocker):
    """All runs of a job are returned when no filter is given."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[RUN_ONE, RUN_TWO])

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    assert e.value["changed"] is False
    assert len(e.value["job_runs"]) == 2


def test_filter_by_status(module_args, mocker):
    """Runs can be filtered by friendly status."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[RUN_ONE, RUN_TWO])

    module_args(_base_args({"status": "succeeded"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    runs = e.value["job_runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == "run-1"


def test_filter_by_status_no_match(module_args, mocker):
    """A status with no matching runs returns an empty list."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[RUN_ONE, RUN_TWO])

    module_args(_base_args({"status": "running"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    assert e.value["job_runs"] == []


def test_filter_by_creator_email(module_args, mocker):
    """Runs can be filtered by creator email."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[RUN_ONE, RUN_TWO])

    module_args(_base_args({"creator": {"email": "b@example.com"}}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    runs = e.value["job_runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == "run-2"


def test_by_id(module_args, mocker):
    """A single run can be retrieved by id."""
    _mock_project(mocker)
    _mock_job(mocker)
    mock_describe = mocker.patch(f"{RUNS}.describe_job_run", return_value=RUN_ONE)
    mock_list = mocker.patch(f"{RUNS}.list_job_runs")

    module_args(_base_args({"id": "run-1"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    runs = e.value["job_runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == "run-1"
    mock_describe.assert_called_once_with(PROJECT_ID, JOB_ID, "run-1")
    mock_list.assert_not_called()


def test_by_id_not_found(module_args, mocker):
    """A missing run by id returns an empty list."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.describe_job_run", return_value=None)

    module_args(_base_args({"id": "run-x"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run_info.main()

    assert e.value["job_runs"] == []


def test_job_not_found(module_args, mocker):
    """A missing job fails."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])

    module_args(_base_args({"job_name": "ghost"}))

    with pytest.raises(AnsibleFailJson, match="Job not found"):
        ml_project_job_run_info.main()


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(_base_args({"project_name": "nope"}))

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_job_run_info.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": "not-valid",
            "job_name": "my-job",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_job_run_info.main()


def test_job_required(module_args, mocker):
    """One of job_name/job_id is required."""
    module_args({"url": BASE_URL, "api_key": API_KEY, "project_name": "proj"})

    with pytest.raises(AnsibleFailJson):
        ml_project_job_run_info.main()
