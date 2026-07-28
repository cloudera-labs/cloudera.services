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

from dataclasses import replace

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_project_job
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlJob,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_job.MlProjectClient"
JOBS = (
    "ansible_collections.cloudera.services.plugins.modules.ml_project_job.MlJobClient"
)


def _mock_project(
    mocker,
    project=MlProject(id=PROJECT_ID, name="proj", default_engine_type="ml_runtime"),
):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def test_create_job(module_args, mocker):
    """A new job is created with the required fields."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])
    mock_create = mocker.patch(
        f"{JOBS}.create_job",
        return_value=MlJob(id="job-1", name="my-job", project_id=PROJECT_ID),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "script": "job.py",
            "runtime": "rt-1",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["id"] == "job-1"

    mock_create.assert_called_once()
    project_id_arg, job_arg = mock_create.call_args.args
    assert project_id_arg == PROJECT_ID
    assert job_arg.name == "my-job"
    assert job_arg.script == "job.py"
    assert job_arg.runtime_identifier == "rt-1"


def test_create_missing_script(module_args, mocker):
    """Creating without a script fails."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])
    mock_create = mocker.patch(f"{JOBS}.create_job")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "runtime": "rt-1",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Missing required parameters"):
        ml_project_job.main()

    mock_create.assert_not_called()


def test_create_runtime_required_for_ml_runtime(module_args, mocker):
    """An ml_runtime project requires a runtime on creation."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])
    mock_create = mocker.patch(f"{JOBS}.create_job")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "script": "job.py",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Missing parameter, 'runtime'"):
        ml_project_job.main()

    mock_create.assert_not_called()


def test_create_kernel_rejected_for_ml_runtime(module_args, mocker):
    """kernel is invalid for an ml_runtime project."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])
    mock_create = mocker.patch(f"{JOBS}.create_job")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "script": "job.py",
            "kernel": "python3",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid parameter, 'kernel'"):
        ml_project_job.main()

    mock_create.assert_not_called()


def test_create_kernel_legacy_engine(module_args, mocker):
    """kernel is accepted (and runtime not required) for a legacy-engine project."""
    _mock_project(
        mocker,
        project=MlProject(
            id=PROJECT_ID,
            name="proj",
            default_engine_type="legacy_engine",
        ),
    )
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])
    mock_create = mocker.patch(
        f"{JOBS}.create_job",
        return_value=MlJob(id="job-1", name="my-job"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "script": "job.py",
            "kernel": "python3",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is True
    _, job_arg = mock_create.call_args.args
    assert job_arg.kernel == "python3"


def test_present_idempotent(module_args, mocker):
    """No field changes means no update and no change."""
    _mock_project(mocker)
    existing = MlJob(
        id="job-1",
        name="my-job",
        project_id=PROJECT_ID,
        script="job.py",
        runtime_identifier="rt-1",
    )
    mocker.patch(f"{JOBS}.list_jobs", return_value=[existing])
    mock_update = mocker.patch(f"{JOBS}.update_job")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is False
    assert e.value["job"]["id"] == "job-1"
    mock_update.assert_not_called()


def test_update_schedule(module_args, mocker):
    """A changed schedule triggers an update."""
    _mock_project(mocker)
    existing = MlJob(
        id="job-1",
        name="my-job",
        project_id=PROJECT_ID,
        script="job.py",
        schedule="0 1 * * *",
    )
    mocker.patch(f"{JOBS}.list_jobs", return_value=[existing])
    mock_update = mocker.patch(
        f"{JOBS}.update_job",
        return_value=replace(existing, schedule="0 2 * * *"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "schedule": "0 2 * * *",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is True
    _, job_arg = mock_update.call_args.args
    assert job_arg.schedule == "0 2 * * *"


def test_update_env_merged(module_args, mocker):
    """Provided env is merged with the job's existing environment."""
    _mock_project(mocker)
    existing = MlJob(
        id="job-1",
        name="my-job",
        project_id=PROJECT_ID,
        script="job.py",
        environment={"A": "1"},
    )
    mocker.patch(f"{JOBS}.list_jobs", return_value=[existing])
    mock_update = mocker.patch(f"{JOBS}.update_job", return_value=existing)

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "env": {"B": "2"},
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is True
    _, job_arg = mock_update.call_args.args
    assert job_arg.environment == {"A": "1", "B": "2"}


def test_update_addons_merged(module_args, mocker):
    """Provided addons are merged (user-first) with existing addons and sorted."""
    _mock_project(mocker)
    existing = MlJob(
        id="job-1",
        name="my-job",
        project_id=PROJECT_ID,
        script="job.py",
        runtime_addon_identifiers=["addon-c"],
    )
    mocker.patch(f"{JOBS}.list_jobs", return_value=[existing])
    mock_update = mocker.patch(f"{JOBS}.update_job", return_value=existing)

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "addons": ["addon-a"],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is True
    _, job_arg = mock_update.call_args.args
    assert job_arg.runtime_addon_identifiers == ["addon-a", "addon-c"]


def test_check_mode_create(module_args, mocker):
    """Check mode reports change but does not create."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])
    mock_create = mocker.patch(f"{JOBS}.create_job")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "script": "job.py",
            "runtime": "rt-1",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is True
    assert e.value["job"]["name"] == "my-job"
    mock_create.assert_not_called()


def test_absent_existing(module_args, mocker):
    """Deleting an existing job removes it."""
    _mock_project(mocker)
    existing = MlJob(id="job-1", name="my-job", project_id=PROJECT_ID)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[existing])
    mock_delete = mocker.patch(f"{JOBS}.delete_job")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-job",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is True
    mock_delete.assert_called_once_with(PROJECT_ID, "job-1")


def test_absent_missing(module_args, mocker):
    """Deleting a non-existent job is a no-op."""
    _mock_project(mocker)
    mocker.patch(f"{JOBS}.list_jobs", return_value=[])
    mock_delete = mocker.patch(f"{JOBS}.delete_job")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "ghost",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_by_id(module_args, mocker):
    """A job can be addressed by id via describe_job."""
    _mock_project(mocker)
    existing = MlJob(id="job-1", name="my-job", project_id=PROJECT_ID)
    mock_describe = mocker.patch(f"{JOBS}.describe_job", return_value=existing)
    mock_delete = mocker.patch(f"{JOBS}.delete_job")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": PROJECT_ID,
            "id": "job-1",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job.main()

    assert e.value["changed"] is True
    mock_describe.assert_called_once_with(PROJECT_ID, "job-1")
    mock_delete.assert_called_once_with(PROJECT_ID, "job-1")


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
        ml_project_job.main()


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
        ml_project_job.main()
