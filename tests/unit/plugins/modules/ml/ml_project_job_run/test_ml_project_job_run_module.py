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

from ansible_collections.cloudera.services.plugins.modules import ml_project_job_run
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlJob,
    MlJobRun,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"
JOB_ID = "job-1"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job_run.MlProjectClient"
JOBS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job_run.MlJobClient"
RUNS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job_run.MlJobRunClient"


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def _mock_job(mocker, job=MlJob(id=JOB_ID, name="my-job", project_id=PROJECT_ID)):
    mocker.patch(f"{JOBS}.list_jobs", return_value=[job] if job else [])
    mocker.patch(f"{JOBS}.describe_job", return_value=job)


def _run(status, run_id="run-1"):
    return MlJobRun(
        id=run_id,
        job_id=JOB_ID,
        project_id=PROJECT_ID,
        status=status,
        created_at="2026-07-24T00:00:00Z",
    )


def test_start_new_run(module_args, mocker):
    """Starting a job with no prior runs creates a run."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[])
    mock_create = mocker.patch(
        f"{RUNS}.create_job_run",
        return_value=_run("ENGINE_SCHEDULING"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is True
    assert e.value["job_run"]["status"] == "ENGINE_SCHEDULING"
    mock_create.assert_called_once()


def test_start_terminal_creates_new(module_args, mocker):
    """A terminal latest run triggers a new run on start."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[_run("ENGINE_SUCCEEDED")])
    mock_create = mocker.patch(
        f"{RUNS}.create_job_run",
        return_value=_run("ENGINE_SCHEDULING", run_id="run-2"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is True
    assert e.value["job_run"]["id"] == "run-2"
    mock_create.assert_called_once()


def test_start_active_idempotent(module_args, mocker):
    """An already-active run means start is a no-op."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[_run("ENGINE_RUNNING")])
    mock_create = mocker.patch(f"{RUNS}.create_job_run")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is False
    assert e.value["job_run"]["status"] == "ENGINE_RUNNING"
    mock_create.assert_not_called()


def test_start_with_arguments_env(module_args, mocker):
    """Arguments and env are passed to the new run."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[])
    mock_create = mocker.patch(
        f"{RUNS}.create_job_run",
        return_value=_run("ENGINE_SCHEDULING"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "arguments": "--verbose",
            "env": {"LOG_LEVEL": "debug"},
        },
    )

    with pytest.raises(AnsibleExitJson):
        ml_project_job_run.main()

    _, _, run_arg = mock_create.call_args.args
    assert run_arg.arguments == "--verbose"
    assert run_arg.environment == {"LOG_LEVEL": "debug"}


def test_start_wait_success(module_args, mocker):
    """Waiting on start returns the succeeded run."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[_run("ENGINE_SUCCEEDED")])
    mocker.patch(
        f"{RUNS}.create_job_run",
        return_value=_run("ENGINE_SCHEDULING", run_id="run-2"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "wait": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is True
    assert e.value["job_run"]["status"] == "ENGINE_SUCCEEDED"


def test_stop_active(module_args, mocker):
    """Stopping an active run calls stop_job_run."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[_run("ENGINE_RUNNING")])
    mock_stop = mocker.patch(
        f"{RUNS}.stop_job_run",
        return_value=_run("ENGINE_STOPPING"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "state": "stopped",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is True
    mock_stop.assert_called_once_with(PROJECT_ID, JOB_ID, "run-1")


def test_stop_no_active(module_args, mocker):
    """Stopping when the latest run is terminal is a no-op."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[_run("ENGINE_SUCCEEDED")])
    mock_stop = mocker.patch(f"{RUNS}.stop_job_run")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "state": "stopped",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is False
    assert e.value["job_run"]["status"] == "ENGINE_SUCCEEDED"
    mock_stop.assert_not_called()


def test_stop_no_runs(module_args, mocker):
    """Stopping a job that never ran is a no-op with an empty result."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[])
    mock_stop = mocker.patch(f"{RUNS}.stop_job_run")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "state": "stopped",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is False
    assert e.value["job_run"] == {}
    mock_stop.assert_not_called()


def test_check_mode_start(module_args, mocker):
    """Check mode reports change but does not create a run."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[])
    mock_create = mocker.patch(f"{RUNS}.create_job_run")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()


def test_check_mode_stop(module_args, mocker):
    """Check mode reports change but does not stop a run."""
    _mock_project(mocker)
    _mock_job(mocker)
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[_run("ENGINE_RUNNING")])
    mock_stop = mocker.patch(f"{RUNS}.stop_job_run")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "state": "stopped",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_run.main()

    assert e.value["changed"] is True
    mock_stop.assert_not_called()


def test_by_job_id(module_args, mocker):
    """A job can be addressed by id via describe_job."""
    _mock_project(mocker)
    mock_describe = mocker.patch(
        f"{JOBS}.describe_job",
        return_value=MlJob(id=JOB_ID, name="my-job", project_id=PROJECT_ID),
    )
    mocker.patch(f"{RUNS}.list_job_runs", return_value=[])
    mocker.patch(f"{RUNS}.create_job_run", return_value=_run("ENGINE_SCHEDULING"))

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": PROJECT_ID,
            "id": JOB_ID,
        },
    )

    with pytest.raises(AnsibleExitJson):
        ml_project_job_run.main()

    mock_describe.assert_called_once_with(PROJECT_ID, JOB_ID)


def test_job_not_found(module_args, mocker):
    """A missing job fails."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "ghost",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Job not found"):
        ml_project_job_run.main()


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "nope",
            "name": "my-job",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_job_run.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": "not-valid",
            "name": "my-job",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_job_run.main()
