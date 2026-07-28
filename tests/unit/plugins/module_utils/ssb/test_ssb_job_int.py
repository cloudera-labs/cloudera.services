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
import re

from typing import Generator
from unittest.mock import Mock

from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbExecutionMode,
    SsbJobClient,
    SsbJob,
    SsbJobConfig,
    SsbJobRequest,
    SsbJobStart,
    SsbJobResponse,
    SsbJobState,
    SsbJobStateResponse,
    SsbJobStop,
    SsbRuntimeConfig,
    SsbRuntimeMode,
)
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

REQUIRED_ENV_VARS = [
    "SSB_SSE_API_URL",
    "SSB_SSE_API_USERNAME",
    "SSB_SSE_API_PASSWORD",
]


@pytest.fixture
def ansible_module(env_context) -> Mock:
    """Fixture to create a mock AnsibleModule."""
    module = Mock()
    module.params = {}
    module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "fail_json called"}),
    )
    module.exit_json = Mock(
        side_effect=AnsibleExitJson({"msg": "exit_json called"}),
    )

    module.params.update(
        {
            "url_username": env_context["SSB_SSE_API_USERNAME"],
            "url_password": env_context["SSB_SSE_API_PASSWORD"],
        },
    )
    return module


@pytest.fixture
def existing_streaming_job(
    request,
    job_client,
    existing_project,
    purge_job,
) -> Generator[SsbJob, None, None]:
    """Fixture to create a test streaming Flink job and clean it up after the test."""
    job_name = request.node.name.lower()

    # Clean up any existing test jobs with the same name
    jobs = job_client.list_jobs(existing_project.id)
    for job in jobs:
        if job.name == job_name:
            job_client.delete_job(job.project_id, job.job_id)

    # Create the test job
    flink_streaming_query = f"""
CREATE TABLE {job_name}_src (
    order_id INT,
    price DECIMAL(5, 2),
    buyer_id INT,
    order_time TIMESTAMP(3),
    proctime AS PROCTIME()
) WITH (
    'connector' = 'datagen',
    'rows-per-second' = '1',
    'fields.order_id.kind' = 'sequence',
    'fields.order_id.start' = '1',
    'fields.order_id.end' = '1000000',
    'fields.price.min' = '1.00',
    'fields.price.max' = '100.00'
);
CREATE TABLE {job_name}_snk (
    order_id INT,
    price DECIMAL(5, 2),
    buyer_id INT,
    order_time TIMESTAMP(3)
) WITH (
    'connector' = 'blackhole'
);
INSERT INTO {job_name}_snk
SELECT
    order_id,
    price,
    buyer_id,
    order_time
FROM {job_name}_src;
"""

    job = job_client.create_job(
        project_id=existing_project.id,
        job=SsbJobRequest(
            job_config=SsbJobConfig(
                job_name=job_name,
            ),
            sql=flink_streaming_query,
        ),
    )

    # Register the job for cleanup
    purge_job(job)

    yield job


@pytest.fixture()
def running_streaming_job(
    job_client,
    existing_streaming_job,
) -> Generator[SsbJob, None, None]:
    """Fixture to ensure the existing streaming job is running. (Requires an active keytab.)"""
    # Start the job if it's not already running
    job_state = job_client.get_job_state(
        project_id=existing_streaming_job.project_id,
        job_id=existing_streaming_job.job_id,
    )

    if job_state.state != SsbJobState.RUNNING:
        job_client.start_job(
            project_id=existing_streaming_job.project_id,
            job_id=existing_streaming_job.job_id,
            config=SsbJobStart(
                sql=existing_streaming_job.sql,
                job_config=SsbJobConfig(
                    job_name=existing_streaming_job.name,
                    runtime_config=SsbRuntimeConfig(
                        execution_mode=SsbExecutionMode.PER_JOB.value,
                        runtime_mode=SsbRuntimeMode.STREAMING.value,
                    ),
                ),
            ),
        )

    yield existing_streaming_job


def test_create_job_minimal(
    request,
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    purge_job,
):
    """Test creating a Job with minimal parameters."""
    ssb_rest_client.module = ansible_module

    job_name = request.node.name

    # Create the test job
    job = job_client.create_job(
        project_id=existing_project.id,
        job=SsbJobRequest(
            job_config=SsbJobConfig(
                job_name=job_name,
            ),
            sql="SELECT 1",
        ),
    )

    # Register the job for cleanup
    purge_job(job)

    assert isinstance(job, SsbJob)
    assert job.name == job_name


def test_create_job_with_history(
    request,
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    purge_job,
):
    """Test creating a Job with history."""
    ssb_rest_client.module = ansible_module

    job_name = request.node.name

    # Create the test job
    job = job_client.create_job(
        project_id=existing_project.id,
        job=SsbJobRequest(
            job_config=SsbJobConfig(
                job_name=job_name,
            ),
            sql="SELECT 1",
            add_to_history=True,
        ),
    )

    # Register the job for cleanup
    purge_job(job)

    assert isinstance(job, SsbJob)
    assert job.name == job_name


def test_create_job_invalid_name(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test creating a Job with an invalid name raises ValueError."""
    ssb_rest_client.module = ansible_module

    invalid_job_name = "123invalid-job-name!"

    with pytest.raises(ValueError) as excinfo:
        job_client.create_job(
            project_id=existing_project.id,
            job=SsbJobRequest(
                job_config=SsbJobConfig(
                    job_name=invalid_job_name,
                ),
                sql="SELECT 1",
            ),
        )

    assert str(excinfo.value) == (
        f"Invalid job name: {invalid_job_name}. "
        "Job names may only contain letters, numbers, and underscores "
        "and must start with a letter or underscore."
    )


def test_create_job_existing_name(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_streaming_job,
):
    """Test creating a Job with an existing name raises AnsibleFailJson."""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Job name already exists"}),
    )

    with pytest.raises(AnsibleFailJson):
        job_client.create_job(
            project_id=existing_streaming_job.project_id,
            job=SsbJobRequest(
                job_config=SsbJobConfig(
                    job_name=existing_streaming_job.name,
                ),
                sql="SELECT 1",
            ),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[400\] A job named "
        + existing_streaming_job.name
        + " already exists in the active project",
        call_args.kwargs["msg"],
    )


def test_describe_job(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_streaming_job,
):
    """Test describing a specific Job."""
    ssb_rest_client.module = ansible_module

    response = job_client.describe_job(
        project_id=existing_streaming_job.project_id,
        job_id=existing_streaming_job.job_id,
    )

    assert isinstance(response, SsbJob)
    assert response.job_id == existing_streaming_job.job_id
    assert response.name == existing_streaming_job.name


def test_describe_job_nonexistent(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_streaming_job,
):
    """Test describing a specific Job that does not exist."""
    ssb_rest_client.module = ansible_module

    response = job_client.describe_job(
        project_id="nonexistent_project",
        job_id=existing_streaming_job.job_id,
    )

    assert response is None


def test_describe_job_nonexistent_project(job_client, ansible_module, ssb_rest_client):
    """Test describing a specific Job for a project that does not exist."""
    ssb_rest_client.module = ansible_module

    response = job_client.describe_job(
        project_id="nonexistent_project",
        job_id=1234,
    )

    assert response is None


def test_list_jobs(job_client, ansible_module, ssb_rest_client, existing_streaming_job):
    """Test listing all Jobs for a project."""
    ssb_rest_client.module = ansible_module

    response = job_client.list_jobs(existing_streaming_job.project_id)

    assert isinstance(response, list)
    assert isinstance(response[0], SsbJob)
    assert response[0].job_id == existing_streaming_job.job_id


def test_list_jobs_with_state(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_streaming_job,
):
    """Test listing all Jobs for a project."""
    ssb_rest_client.module = ansible_module

    response = job_client.list_jobs(
        existing_streaming_job.project_id,
        state=SsbJobState.RUNNING,
    )

    assert isinstance(response, list)
    assert len(response) == 0


def test_update_job(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_streaming_job,
):
    """Test updating a Job."""
    ssb_rest_client.module = ansible_module

    new_sql = "SELECT 2 AS updated_sql"

    existing_streaming_job.sql = new_sql

    response = job_client.update_job(
        project_id=existing_project.id,
        job=existing_streaming_job,
    )

    assert isinstance(response, SsbJob)
    assert response.job_id == existing_streaming_job.job_id
    assert response.sql == new_sql


def test_delete_job(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_streaming_job,
):
    """Test deleting a Job."""
    ssb_rest_client.module = ansible_module

    job_client.delete_job(
        project_id=existing_streaming_job.project_id,
        job_id=existing_streaming_job.job_id,
    )

    result = job_client.describe_job(
        project_id=existing_streaming_job.project_id,
        job_id=existing_streaming_job.job_id,
    )

    assert result is None


def test_delete_job_nonexistent(job_client, ansible_module, ssb_rest_client):
    ssb_rest_client.module = ansible_module

    job_client.delete_job(
        project_id="nonexistent_project",
        job_id=1234,
    )


@pytest.mark.usefixtures("set_keytab")
def test_stop_job(job_client, ansible_module, ssb_rest_client, running_streaming_job):
    """Test stopping a Job."""
    ssb_rest_client.module = ansible_module

    response = job_client.stop_job(
        project_id=running_streaming_job.project_id,
        job_id=running_streaming_job.job_id,
        config=SsbJobStop(),
    )

    assert response is None


@pytest.mark.usefixtures("set_keytab")
def test_stop_job_with_savepoint(
    job_client,
    ansible_module,
    ssb_rest_client,
    running_streaming_job,
):
    """Test stopping a Job with savepoint configuration."""
    ssb_rest_client.module = ansible_module

    response = job_client.stop_job(
        project_id=running_streaming_job.project_id,
        job_id=running_streaming_job.job_id,
        config=SsbJobStop(
            savepoint=True,
            timeout=30,
        ),
    )

    assert isinstance(response, int)
    # Response should be a savepoint_id (could be 0 or a positive integer)


def test_stop_job_nonexistent(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test stopping a Job that does not exist raises an exception."""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Job not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        job_client.stop_job(
            project_id=existing_project.id,
            job_id=1234,
            config=SsbJobStop(),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(r"\[404\] Job 1234 not found", call_args.kwargs["msg"])


def test_stop_job_nonexistent_project(job_client, ansible_module, ssb_rest_client):
    """Test stopping a Job that does not exist raises an exception."""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        job_client.stop_job(
            project_id="nonexistent_project",
            job_id=1234,
            config=SsbJobStop(),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent_project doesn't exist",
        call_args.kwargs["msg"],
    )


@pytest.mark.usefixtures("set_keytab")
def test_start_job_minimal(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_streaming_job,
):
    """Test starting a Job with minimal parameters."""
    ssb_rest_client.module = ansible_module

    response = job_client.start_job(
        project_id=existing_streaming_job.project_id,
        job_id=existing_streaming_job.job_id,
        config=SsbJobStart(
            sql=existing_streaming_job.sql,
            job_config=SsbJobConfig(
                job_name=existing_streaming_job.name,
                runtime_config=SsbRuntimeConfig(
                    execution_mode=SsbExecutionMode.PER_JOB.value,
                    runtime_mode=SsbRuntimeMode.STREAMING.value,
                ),
            ),
        ),
    )

    assert isinstance(response, list)
    assert len(response) > 0
    assert all(isinstance(item, SsbJobResponse) for item in response)


@pytest.mark.usefixtures("set_keytab")
def test_start_job_with_config(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_streaming_job,
):
    """Test starting a Job with full configuration."""
    ssb_rest_client.module = ansible_module

    response = job_client.start_job(
        project_id=existing_streaming_job.project_id,
        job_id=existing_streaming_job.job_id,
        config=SsbJobStart(
            sql=existing_streaming_job.sql,  # Represents the selection
            selection=True,
            add_to_history=True,
            job_config=SsbJobConfig(
                job_name=existing_streaming_job.name,
                runtime_config=SsbRuntimeConfig(
                    execution_mode=SsbExecutionMode.PER_JOB.value,
                    runtime_mode=SsbRuntimeMode.STREAMING.value,
                ),
            ),
        ),
    )

    assert isinstance(response, list)
    assert len(response) > 0
    assert all(isinstance(item, SsbJobResponse) for item in response)


def test_start_job_nonexistent_project(job_client, ansible_module, ssb_rest_client):
    """Test starting a Job in a nonexistent project raises an exception."""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        job_client.start_job(
            project_id="nonexistent_project",
            job_id=1234,
            config=SsbJobStart(
                sql="SELECT 1",
            ),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent_project doesn't exist",
        call_args.kwargs["msg"],
    )


@pytest.mark.usefixtures("set_keytab")
def test_start_job_nonexistent_job(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test starting a Job in a nonexistent job raises an exception."""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Job not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        job_client.start_job(
            project_id=existing_project.id,
            job_id=1234,
            config=SsbJobStart(
                sql="SELECT 1",
            ),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(r"\[404\] Job 1234 not found", call_args.kwargs["msg"])


def test_get_job_state(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_streaming_job,
):
    """Test getting the state of an existing Job."""
    ssb_rest_client.module = ansible_module

    response = job_client.get_job_state(
        project_id=existing_streaming_job.project_id,
        job_id=existing_streaming_job.job_id,
    )

    assert isinstance(response, SsbJobStateResponse)
    assert (
        response.state
        in SsbJobClient.ACTIVE_STATES
        | SsbJobClient.TERMINAL_STATES
        | SsbJobClient.TRANSITIONING_STATES
    )


def test_get_job_state_nonexistent_project(job_client, ansible_module, ssb_rest_client):
    """Test getting the state of a nonexistent project raises an exception."""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        job_client.get_job_state(
            project_id="nonexistent_project",
            job_id=9999,
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent_project doesn't exist",
        call_args.kwargs["msg"],
    )


def test_get_job_state_nonexistent_job(
    job_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test getting the state of a nonexistent job raises an exception."""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Job not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        job_client.get_job_state(
            project_id=existing_project.id,
            job_id=9999,
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(r"\[404\] Job 9999 not found", call_args.kwargs["msg"])
