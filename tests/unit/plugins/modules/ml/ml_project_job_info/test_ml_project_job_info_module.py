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

from ansible_collections.cloudera.services.plugins.modules import ml_project_job_info
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlJob,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job_info.MlProjectClient"
JOBS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job_info.MlJobClient"

JOB_ONE = MlJob(
    id="job-1",
    name="etl",
    project_id=PROJECT_ID,
    kernel="python3",
    script="etl.py",
    paused=False,
    creator={"email": "a@example.com", "username": "alice"},
)
JOB_TWO = MlJob(
    id="job-2",
    name="report",
    project_id=PROJECT_ID,
    kernel="r",
    script="report.R",
    paused=True,
    creator={"email": "b@example.com", "username": "bob"},
)


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def _base_args(overrides=None):
    args = {"url": BASE_URL, "api_key": API_KEY, "project_name": "proj"}
    if overrides:
        args.update(overrides)
    return args


def test_list_all(module_args, mocker):
    """All jobs in a project are returned when no filter is given."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[JOB_ONE, JOB_TWO])

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["jobs"]) == 2


def test_filter_by_name(module_args, mocker):
    """Jobs can be filtered by name."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[JOB_ONE, JOB_TWO])

    module_args(_base_args({"name": "etl"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    jobs = e.value["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["name"] == "etl"


def test_filter_by_kernel(module_args, mocker):
    """Jobs can be filtered by kernel."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[JOB_ONE, JOB_TWO])

    module_args(_base_args({"kernel": "r"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    jobs = e.value["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["name"] == "report"


def test_filter_by_paused(module_args, mocker):
    """Jobs can be filtered by paused state."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[JOB_ONE, JOB_TWO])

    module_args(_base_args({"paused": True}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    jobs = e.value["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["name"] == "report"


def test_filter_by_creator_email(module_args, mocker):
    """Jobs can be filtered by creator email."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[JOB_ONE, JOB_TWO])

    module_args(_base_args({"creator": {"email": "a@example.com"}}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    jobs = e.value["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["name"] == "etl"


def test_by_id(module_args, mocker):
    """A single job can be retrieved by id."""
    _mock_project(mocker)
    mock_describe = mocker.patch(f"{JOBS}.describe_job", return_value=JOB_ONE)
    mock_list = mocker.patch(f"{JOBS}.list_jobs")

    module_args(_base_args({"id": "job-1"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    jobs = e.value["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["id"] == "job-1"
    mock_describe.assert_called_once_with(PROJECT_ID, "job-1")
    mock_list.assert_not_called()


def test_by_id_not_found(module_args, mocker):
    """A missing job by id returns an empty list."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.describe_job", return_value=None)

    module_args(_base_args({"id": "job-x"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    assert e.value["jobs"] == []


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(_base_args({"project_name": "nope"}))

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_job_info.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args({"url": BASE_URL, "api_key": API_KEY, "project_id": "not-valid"})

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_job_info.main()


def test_project_required(module_args, mocker):
    """One of project_name/project_id is required."""
    module_args({"url": BASE_URL, "api_key": API_KEY})

    with pytest.raises(AnsibleFailJson):
        ml_project_job_info.main()
