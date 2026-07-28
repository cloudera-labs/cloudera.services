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
import time

from typing import Callable

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ssb_job
from ansible_collections.cloudera.services.plugins.module_utils.common import from_dict
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbExecutionMode,
    SsbJob,
    SsbJobConfig,
    SsbJobRequest,
    SsbJobStart,
    SsbJobState,
    SsbRuntimeConfig,
    SsbRuntimeMode,
)

REQUIRED_ENV_VARS = [
    "SSB_SSE_API_URL",
    "SSB_SSE_API_USERNAME",
    "SSB_SSE_API_PASSWORD",
]


@pytest.fixture
def ssb_module_args(
    module_args,
    env_context,
    existing_project,
) -> Callable[[dict], None]:
    """Fixture to set common module args for SSB job tests."""

    def _ssb_module_args(overrides: dict = {}) -> None:
        args = {
            "url": env_context["SSB_SSE_API_URL"],
            "url_username": env_context["SSB_SSE_API_USERNAME"],
            "url_password": env_context["SSB_SSE_API_PASSWORD"],
            "force_basic_auth": True,
            "project_id": existing_project.id,
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _ssb_module_args


@pytest.fixture
def existing_job(request, job_client, set_keytab, existing_project, purge_job):
    """Fixture to create a test job and clean it up after the test."""
    job_name = request.node.name.lower() + "_existing"

    # Clean up any existing test job
    jobs = job_client.list_jobs(existing_project.id)
    for job in jobs:
        if job.name == job_name:
            job_client.delete_job(existing_project.id, job.job_id)

    job_request = SsbJobRequest(
        sql="SELECT 1",
        job_config=SsbJobConfig(
            job_name=job_name,
            runtime_config=SsbRuntimeConfig(
                execution_mode=SsbExecutionMode.PER_JOB.value,
                runtime_mode=SsbRuntimeMode.STREAMING.value,
            ),
        ),
    )
    job = job_client.create_job(existing_project.id, job_request)

    # Register for cleanup
    purge_job(job)

    return job


@pytest.fixture
def running_job(request, job_client, set_keytab, existing_project, purge_job):
    """Fixture to create a running test job and clean it up after the test."""
    job_name = request.node.name.lower() + "_running"

    # Clean up any existing test job
    jobs = job_client.list_jobs(existing_project.id)
    for job in jobs:
        if job.name == job_name:
            job_client.delete_job(existing_project.id, job.job_id)

    job_request = SsbJobRequest(
        sql="SELECT 1",
        job_config=SsbJobConfig(
            job_name=job_name,
            runtime_config=SsbRuntimeConfig(
                execution_mode=SsbExecutionMode.PER_JOB.value,
                runtime_mode=SsbRuntimeMode.STREAMING.value,
            ),
        ),
    )
    job = job_client.create_job(existing_project.id, job_request)

    # Register for cleanup
    purge_job(job)

    # Start the job
    start_config = SsbJobStart(
        sql=job.sql,
        job_config=SsbJobConfig(
            job_name=job_name,
            runtime_config=SsbRuntimeConfig(
                execution_mode=SsbExecutionMode.PER_JOB.value,
                runtime_mode=SsbRuntimeMode.STREAMING.value,
            ),
        ),
    )
    job_client.start_job(existing_project.id, job.job_id, start_config)

    # Wait briefly and refresh job state
    time.sleep(2)
    job = job_client.describe_job(existing_project.id, job.job_id)

    return job


@pytest.fixture
def deletable_job(request, job_client, set_keytab, existing_project, purge_job):
    """Fixture to create a job for deletion tests."""
    job_name = request.node.name.lower() + "_deletable"

    # Clean up any existing test job
    jobs = job_client.list_jobs(existing_project.id)
    for job in jobs:
        if job.name == job_name:
            job_client.delete_job(existing_project.id, job.job_id)

    job_request = SsbJobRequest(
        sql="SELECT 1",
        job_config=SsbJobConfig(
            job_name=job_name,
            runtime_config=SsbRuntimeConfig(
                execution_mode=SsbExecutionMode.PER_JOB.value,
                runtime_mode=SsbRuntimeMode.STREAMING.value,
            ),
        ),
    )
    job = job_client.create_job(existing_project.id, job_request)

    # Register for cleanup (though test will delete it)
    purge_job(job)

    return job


def test_ssb_job_create_present(request, ssb_module_args, purge_job):
    """Test creating a job with state=present (doesn't execute)."""
    job_name = request.node.name

    ssb_module_args(
        {
            "state": "present",
            "name": job_name,
            "sql": "SELECT 1",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value

    purge_job(from_dict(SsbJob, result["job"]))

    assert result["changed"] is True
    assert result["job"]["name"] == job_name
    assert result["job"]["sql"] == "SELECT 1"
    assert result["job"]["state"] == SsbJobState.STOPPED.value
    assert "job_id" in result["job"]


def test_ssb_job_create_started(request, ssb_module_args, set_keytab, purge_job):
    """Test creating and starting a job with state=started."""
    job_name = request.node.name

    ssb_module_args(
        {
            "state": "started",
            "name": job_name,
            "sql": "SELECT 1",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    purge_job(from_dict(SsbJob, result["job"]))

    assert result["changed"] is True
    assert result["job"]["name"] == job_name
    # Job should be in running or initializing state
    assert result["job"]["state"] in [
        SsbJobState.RUNNING.value,
        SsbJobState.INITIALIZING.value,
        SsbJobState.CREATED.value,
    ]


def test_ssb_job_present_idempotent(ssb_module_args, existing_job):
    """Test that existing job with same parameters doesn't change."""
    ssb_module_args(
        {
            "state": "present",
            "name": existing_job.name,
            "sql": existing_job.sql,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is False
    assert result["job"]["job_id"] == existing_job.job_id
    assert result["job"]["name"] == existing_job.name
    assert result["job"]["sql"] == existing_job.sql


def test_ssb_job_update_sql(ssb_module_args, existing_job):
    """Test updating job SQL triggers update_job and marks changed."""
    new_sql = "SELECT 2"

    ssb_module_args(
        {
            "state": "present",
            "name": existing_job.name,
            "sql": new_sql,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["sql"] == new_sql


def test_ssb_job_start_existing_job(ssb_module_args, set_keytab, existing_job):
    """Test starting an existing job that is in created state."""
    ssb_module_args(
        {
            "state": "started",
            "name": existing_job.name,
            "sql": existing_job.sql,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    # Job should be in running or initializing state
    assert result["job"]["state"] in [
        SsbJobState.RUNNING.value,
        SsbJobState.INITIALIZING.value,
        SsbJobState.CREATED.value,
    ]


def test_ssb_job_by_id(ssb_module_args, existing_job):
    """Test retrieving and operating on job by ID."""
    ssb_module_args(
        {
            "state": "present",
            "job_id": existing_job.job_id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is False
    assert result["job"]["job_id"] == existing_job.job_id
    assert result["job"]["name"] == existing_job.name


def test_ssb_job_stop_running_job(ssb_module_args, set_keytab, running_job):
    """Test stopping a running job."""
    ssb_module_args(
        {
            "state": "stopped",
            "name": running_job.name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    # Job should be in a terminal state or transitioning
    assert result["job"]["state"] in [
        SsbJobState.STOPPED.value,
    ]


def test_ssb_job_stop_idempotent(ssb_module_args, existing_job):
    """Test that stopping an already stopped job is idempotent."""
    ssb_module_args(
        {
            "state": "stopped",
            "name": existing_job.name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    # Job is already in created state (not running), so no change
    assert result["changed"] is False


def test_ssb_job_restart(ssb_module_args, set_keytab, running_job):
    """Test restarting a running job (stop + start)."""
    ssb_module_args(
        {
            "state": "restarted",
            "name": running_job.name,
            "sql": running_job.sql,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    # Job should be running or initializing after restart
    assert result["job"]["state"] in [
        SsbJobState.RUNNING.value,
    ]


def test_ssb_job_restart_with_sql_update(ssb_module_args, set_keytab, running_job):
    """Test restarting a job with SQL changes updates before restart."""
    new_sql = "SELECT 99"

    ssb_module_args(
        {
            "state": "restarted",
            "name": running_job.name,
            "sql": new_sql,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert result["job"]["sql"] == new_sql


def test_ssb_job_delete_by_name(ssb_module_args, deletable_job):
    """Test deleting a job by name."""
    ssb_module_args(
        {
            "state": "absent",
            "name": deletable_job.name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True


def test_ssb_job_delete_by_id(ssb_module_args, deletable_job):
    """Test deleting a job by ID."""
    ssb_module_args(
        {
            "state": "absent",
            "job_id": deletable_job.job_id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True


def test_ssb_job_delete_idempotent(ssb_module_args):
    """Test that deleting a non-existent job is idempotent."""
    ssb_module_args(
        {
            "state": "absent",
            "name": "nonexistent-job-12345",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is False


def test_ssb_job_check_mode_create(
    request,
    ssb_module_args,
    job_client,
    existing_project,
):
    """Test check mode when creating a job."""
    job_name = request.node.name

    ssb_module_args(
        {
            "state": "present",
            "name": job_name,
            "sql": "SELECT 1",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True

    # Verify job was not actually created
    jobs = job_client.list_jobs(existing_project.id)
    assert not any(j.name == job_name for j in jobs)


def test_ssb_job_check_mode_delete(ssb_module_args, existing_job, job_client):
    """Test check mode when deleting a job."""
    ssb_module_args(
        {
            "state": "absent",
            "name": existing_job.name,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True

    # Verify job still exists
    job = job_client.describe_job(existing_job.project_id, existing_job.job_id)
    assert job is not None
    assert job.job_id == existing_job.job_id


def test_ssb_job_diff_mode_create(request, ssb_module_args, purge_job):
    """Test diff mode when creating a job."""
    job_name = request.node.name

    ssb_module_args(
        {
            "state": "present",
            "name": job_name,
            "sql": "SELECT 1",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    purge_job(from_dict(SsbJob, result["job"]))

    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"] == {}
    assert result["diff"]["after"]["name"] == job_name
    assert result["diff"]["after"]["sql"] == "SELECT 1"


def test_ssb_job_diff_mode_update(ssb_module_args, existing_job):
    """Test diff mode when updating job SQL."""
    old_sql = existing_job.sql
    new_sql = "SELECT 2"

    ssb_module_args(
        {
            "state": "present",
            "name": existing_job.name,
            "sql": new_sql,
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"]["sql"] == old_sql
    assert result["diff"]["after"]["sql"] == new_sql


def test_ssb_job_diff_mode_state_change(ssb_module_args, existing_job):
    """Test diff mode when changing job state."""
    ssb_module_args(
        {
            "state": "started",
            "name": existing_job.name,
            "sql": existing_job.sql,
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_job.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"]["state"] == SsbJobState.STOPPED.value
    assert result["diff"]["after"]["state"] == SsbJobState.RUNNING.value


def test_ssb_job_missing_sql_for_create(ssb_module_args):
    """Test that missing SQL for create fails."""
    ssb_module_args(
        {
            "state": "present",
            "name": "test-job",
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        ssb_job.main()

    result = e.value
    assert "required" in result["msg"].lower()
    assert "sql" in result["msg"].lower()
