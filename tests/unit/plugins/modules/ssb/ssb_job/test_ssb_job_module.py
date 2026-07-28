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

from ansible_collections.cloudera.services.plugins.modules import ssb_job
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbJob,
    SsbJobConfig,
    SsbJobRequest,
    SsbJobStart,
    SsbJobStop,
    SsbJobResponse,
)

BASE_URL = "https://api.cloudera.internal"
PROJECT_ID = "test_project_123"


def test_ssb_job_create_present(module_args, mocker):
    """Test creating a job with state=present (doesn't execute)."""
    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[],
    )
    mock_create_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.create_job",
        return_value=SsbJob(
            job_id=1,
            name="test_job",
            sql="SELECT * FROM orders",
            state="CREATED",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "test_job",
            "sql": "SELECT * FROM orders",
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["job_id"] == 1
    assert result["job"]["name"] == "test_job"
    assert result["job"]["sql"] == "SELECT * FROM orders"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_create_job.assert_called_once()


def test_ssb_job_create_started(module_args, mocker):
    """Test creating and starting a job with state=started."""
    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[],
    )
    mock_create_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.create_job",
        return_value=SsbJob(
            job_id=1,
            name="test_job",
            sql="SELECT * FROM orders",
            state="CREATED",
        ),
    )
    mock_start_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.start_job",
        return_value=[SsbJobResponse(type="info", ssb_job_id=1)],
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="test_job",
            sql="SELECT * FROM orders",
            state="RUNNING",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "test_job",
            "sql": "SELECT * FROM orders",
            "state": "started",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["job_id"] == 1
    assert result["job"]["state"] == "RUNNING"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_create_job.assert_called_once()
    mock_start_job.assert_called_once()
    mock_describe_job.assert_called_once()


def test_ssb_job_present_idempotent(module_args, mocker):
    """Test that existing job with same parameters doesn't change."""
    existing_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "existing_job",
            "sql": "SELECT * FROM orders",
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is False
    assert result["job"]["job_id"] == 1
    assert result["job"]["name"] == "existing_job"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)


def test_ssb_job_update_sql(module_args, mocker):
    """Test updating job SQL triggers update_job and marks changed."""
    existing_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    updated_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM customers",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_update_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.update_job",
        return_value=updated_job,
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "existing_job",
            "sql": "SELECT * FROM customers",
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["sql"] == "SELECT * FROM customers"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_update_job.assert_called_once()


def test_ssb_job_start_existing_stopped_job(module_args, mocker):
    """Test starting an existing job that is in created state."""
    existing_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_start_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.start_job",
        return_value=[SsbJobResponse(type="info", ssb_job_id=1)],
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="existing_job",
            sql="SELECT * FROM orders",
            state="RUNNING",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "existing_job",
            "sql": "SELECT * FROM orders",
            "state": "started",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["state"] == "RUNNING"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_start_job.assert_called_once()
    mock_describe_job.assert_called_once()


def test_ssb_job_start_idempotent(module_args, mocker):
    """Test that starting an already running job is idempotent."""
    existing_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM orders",
        state="RUNNING",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "running_job",
            "sql": "SELECT * FROM orders",
            "state": "started",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is False
    assert result["job"]["state"] == "RUNNING"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)


def test_ssb_job_stop_running_job(module_args, mocker):
    """Test stopping a running job."""
    existing_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM orders",
        state="RUNNING",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_stop_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.stop_job",
        return_value=None,
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="running_job",
            sql="SELECT * FROM orders",
            state="CANCELED",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "running_job",
            "state": "stopped",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["state"] == "CANCELED"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_stop_job.assert_called_once()
    mock_describe_job.assert_called_once()


def test_ssb_job_stop_with_savepoint(module_args, mocker):
    """Test stopping a job with savepoint."""
    existing_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM orders",
        state="RUNNING",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_stop_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.stop_job",
        return_value=42,  # savepoint_id
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="running_job",
            sql="SELECT * FROM orders",
            state="CANCELED",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "running_job",
            "state": "stopped",
            "savepoint": True,
            "savepoint_path": "/savepoints",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["savepoint_id"] == 42

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_stop_job.assert_called_once_with(
        PROJECT_ID,
        1,
        SsbJobStop(
            savepoint=True,
            savepoint_path="/savepoints",
            timeout=None,
        ),
    )
    mock_describe_job.assert_called_once_with(PROJECT_ID, 1)
    # Verify stop config had savepoint parameters
    call_args = mock_stop_job.call_args
    assert call_args[0][2].savepoint is True
    assert call_args[0][2].savepoint_path == "/savepoints"
    assert call_args[0][2].timeout is None


def test_ssb_job_stop_idempotent(module_args, mocker):
    """Test that stopping an already stopped job is idempotent."""
    existing_job = SsbJob(
        job_id=1,
        name="stopped_job",
        sql="SELECT * FROM orders",
        state="CANCELED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "stopped_job",
            "state": "stopped",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is False
    assert result["job"]["state"] == "CANCELED"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)


def test_ssb_job_restart(module_args, mocker):
    """Test restarting a running job (stop + start)."""
    existing_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM orders",
        state="RUNNING",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_stop_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.stop_job",
        return_value=None,
    )
    mock_start_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.start_job",
        return_value=[SsbJobResponse(type="info", ssb_job_id=1)],
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="running_job",
            sql="SELECT * FROM orders",
            state="RUNNING",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "running_job",
            "sql": "SELECT * FROM orders",
            "state": "restarted",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["state"] == "RUNNING"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_stop_job.assert_called_once()
    mock_start_job.assert_called_once()
    mock_describe_job.assert_called_once()


def test_ssb_job_restart_updates_sql_first(module_args, mocker):
    """Test restarting a job with SQL changes updates before restart."""
    existing_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM orders",
        state="RUNNING",
    )

    updated_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM customers",
        state="RUNNING",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_update_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.update_job",
        return_value=updated_job,
    )
    mock_stop_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.stop_job",
        return_value=None,
    )
    mock_start_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.start_job",
        return_value=[SsbJobResponse(type="info", ssb_job_id=1)],
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="running_job",
            sql="SELECT * FROM customers",
            state="RUNNING",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "running_job",
            "sql": "SELECT * FROM customers",
            "state": "restarted",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["sql"] == "SELECT * FROM customers"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_update_job.assert_called_once()
    mock_stop_job.assert_called_once()
    mock_start_job.assert_called_once()
    mock_describe_job.assert_called_once()


def test_ssb_job_start_with_sql_update(module_args, mocker):
    """Test starting a job with SQL changes (update then start)."""
    existing_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    updated_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM customers",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_update_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.update_job",
        return_value=updated_job,
    )
    mock_start_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.start_job",
        return_value=[SsbJobResponse(type="info", ssb_job_id=1)],
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="existing_job",
            sql="SELECT * FROM customers",
            state="RUNNING",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "existing_job",
            "sql": "SELECT * FROM customers",
            "state": "started",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["sql"] == "SELECT * FROM customers"
    assert result["job"]["state"] == "RUNNING"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_update_job.assert_called_once()
    mock_start_job.assert_called_once()
    mock_describe_job.assert_called_once()


def test_ssb_job_stop_with_sql_update(module_args, mocker):
    """Test stopping a job with SQL changes (update then stop)."""
    existing_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM orders",
        state="RUNNING",
    )

    updated_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM customers",
        state="RUNNING",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_update_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.update_job",
        return_value=updated_job,
    )
    mock_stop_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.stop_job",
        return_value=None,
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="running_job",
            sql="SELECT * FROM customers",
            state="CANCELED",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "running_job",
            "sql": "SELECT * FROM customers",
            "state": "stopped",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["sql"] == "SELECT * FROM customers"
    assert result["job"]["state"] == "CANCELED"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_update_job.assert_called_once()
    mock_stop_job.assert_called_once()
    mock_describe_job.assert_called_once()


def test_ssb_job_diff_mode_update_and_state_change(module_args, mocker):
    """Test diff mode when both updating SQL and changing state."""
    existing_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    updated_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM customers",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_update_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.update_job",
        return_value=updated_job,
    )
    mock_start_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.start_job",
        return_value=[SsbJobResponse(type="info", ssb_job_id=1)],
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="existing_job",
            sql="SELECT * FROM customers",
            state="RUNNING",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "existing_job",
            "sql": "SELECT * FROM customers",
            "state": "started",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    # Should show both SQL change and state change in diff
    assert result["diff"]["before"]["sql"] == "SELECT * FROM orders"
    assert result["diff"]["after"]["sql"] == "SELECT * FROM customers"
    assert result["diff"]["before"]["state"] == "CREATED"
    assert result["diff"]["after"]["state"] == "RUNNING"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_update_job.assert_called_once()
    mock_start_job.assert_called_once()
    mock_describe_job.assert_called_once()


def test_ssb_job_delete_by_name(module_args, mocker):
    """Test deleting a job by name."""
    existing_job = SsbJob(
        job_id=1,
        name="job_to_delete",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_delete_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.delete_job",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "job_to_delete",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_delete_job.assert_called_once_with(PROJECT_ID, 1)


def test_ssb_job_delete_by_id(module_args, mocker):
    """Test deleting a job by ID."""
    existing_job = SsbJob(
        job_id=1,
        name="job_to_delete",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=existing_job,
    )
    mock_delete_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.delete_job",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "job_id": 1,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True

    mock_describe_job.assert_called_once_with(PROJECT_ID, 1)
    mock_delete_job.assert_called_once_with(PROJECT_ID, 1)


def test_ssb_job_delete_running_job(module_args, mocker):
    """Test deleting a running job (should stop first)."""
    existing_job = SsbJob(
        job_id=1,
        name="running_job",
        sql="SELECT * FROM orders",
        state="RUNNING",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_stop_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.stop_job",
        return_value=None,
    )
    mock_delete_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.delete_job",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "running_job",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_stop_job.assert_called_once()
    mock_delete_job.assert_called_once_with(PROJECT_ID, 1)


def test_ssb_job_delete_idempotent(module_args, mocker):
    """Test that deleting a non-existent job is idempotent."""
    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "nonexistent_job",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is False

    mock_list_jobs.assert_called_once_with(PROJECT_ID)


def test_ssb_job_check_mode_create(module_args, mocker):
    """Test check mode when creating a job."""
    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[],
    )
    mock_create_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.create_job",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "test_job",
            "sql": "SELECT * FROM orders",
            "state": "present",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    # Should not call create_job in check mode
    mock_create_job.assert_not_called()


def test_ssb_job_check_mode_delete(module_args, mocker):
    """Test check mode when deleting a job."""
    existing_job = SsbJob(
        job_id=1,
        name="job_to_delete",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_delete_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.delete_job",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "job_to_delete",
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    # Should not call delete_job in check mode
    mock_delete_job.assert_not_called()


def test_ssb_job_diff_mode_create(module_args, mocker):
    """Test diff mode when creating a job."""
    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[],
    )
    mock_create_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.create_job",
        return_value=SsbJob(
            job_id=1,
            name="test_job",
            sql="SELECT * FROM orders",
            state="CREATED",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "test_job",
            "sql": "SELECT * FROM orders",
            "state": "present",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"] == {}
    assert result["diff"]["after"]["name"] == "test_job"
    assert result["diff"]["after"]["sql"] == "SELECT * FROM orders"

    mock_list_jobs.assert_called_once_with(PROJECT_ID)
    mock_create_job.assert_called_once()


def test_ssb_job_diff_mode_update(module_args, mocker):
    """Test diff mode when updating job SQL."""
    existing_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    updated_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM customers",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_update_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.update_job",
        return_value=updated_job,
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "existing_job",
            "sql": "SELECT * FROM customers",
            "state": "present",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"]["sql"] == "SELECT * FROM orders"
    assert result["diff"]["after"]["sql"] == "SELECT * FROM customers"


def test_ssb_job_diff_mode_state_change(module_args, mocker):
    """Test diff mode when changing job state."""
    existing_job = SsbJob(
        job_id=1,
        name="existing_job",
        sql="SELECT * FROM orders",
        state="CREATED",
    )

    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[existing_job],
    )
    mock_start_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.start_job",
        return_value=[SsbJobResponse(type="info", ssb_job_id=1)],
    )
    mock_describe_job = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.describe_job",
        return_value=SsbJob(
            job_id=1,
            name="existing_job",
            sql="SELECT * FROM orders",
            state="RUNNING",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "existing_job",
            "sql": "SELECT * FROM orders",
            "state": "started",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"]["state"] == "CREATED"
    assert result["diff"]["after"]["state"] == "RUNNING"


def test_ssb_job_missing_name_and_id(module_args):
    """Test that missing both name and job_id fails."""
    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        ssb_job.main()

    result = e.value
    assert "one of the following is required" in result["msg"].lower()


def test_ssb_job_both_name_and_id(module_args):
    """Test that providing both name and job_id fails."""
    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "test_job",
            "job_id": 1,
            "state": "present",
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        ssb_job.main()

    result = e.value
    assert "mutually exclusive" in result["msg"].lower()


def test_ssb_job_missing_sql_for_create(module_args, mocker):
    """Test that missing SQL for create fails."""
    mock_list_jobs = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_job.SsbJobClient.list_jobs",
        return_value=[],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": PROJECT_ID,
            "name": "test_job",
            "state": "present",
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        ssb_job.main()

    result = e.value
    assert "required" in result["msg"].lower()
    assert "sql" in result["msg"].lower()
