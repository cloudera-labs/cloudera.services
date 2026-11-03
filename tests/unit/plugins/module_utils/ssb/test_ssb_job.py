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

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbJobClient,
    SsbJobState,
    SsbJob,
    SsbJobRequest,
    SsbJobStart,
    SsbJobResponse,
    SsbJobStateResponse,
    SsbJobStop,
)

ENDPOINT_URL = "https://cloudera.internal"

JOB_RESPONSE = dict(
    job_id=123,
    name="test_job",
    sql="SELECT * FROM table",
    state=SsbJobState.RUNNING.value,
    project_id="proj123",
    user_id="user123",
    username="testuser",
    created_at="2024-06-01T12:00:00Z",
    start_time=1717243200000,
)

JOB_LIST_RESPONSE = dict(
    jobs=[JOB_RESPONSE],
)

PROJECT_ID = "proj123"


def test_list_jobs(mocker):
    """Test listing all jobs."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = JOB_LIST_RESPONSE

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.list_jobs(project_id=PROJECT_ID)

    assert isinstance(response, list)
    assert isinstance(response[0], SsbJob)
    assert response[0] == from_dict(SsbJob, JOB_RESPONSE)

    # Verify that the get method was called with correct parameters
    api_client.get.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs",
        params={},
    )


def test_list_jobs_with_state(mocker):
    """Test listing all jobs with a specific state."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = JOB_LIST_RESPONSE

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.list_jobs(project_id=PROJECT_ID, state=SsbJobState.RUNNING.value)
    assert isinstance(response, list)
    assert isinstance(response[0], SsbJob)
    assert response[0] == from_dict(SsbJob, JOB_RESPONSE)

    # Verify that the get method was called with correct parameters
    api_client.get.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs",
        params={"state": SsbJobState.RUNNING.value},
    )


def test_list_jobs_with_invalid_state(mocker):
    """Test listing all jobs with an invalid state raises ValueError."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    invalid_state = "INVALID_STATE"

    with pytest.raises(ValueError) as excinfo:
        client.list_jobs(project_id=PROJECT_ID, state=invalid_state)

    assert str(excinfo.value) == f"Invalid job state: {invalid_state}"


def test_create_job_minimal(mocker):
    """Test creating a job with minimal parameters."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = JOB_RESPONSE

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.create_job(
        project_id=PROJECT_ID,
        job=SsbJobRequest(
            sql="SELECT * FROM table",
        ),
    )

    assert response == from_dict(SsbJob, JOB_RESPONSE)

    # Verify that the post method was called with correct parameters
    api_client.post.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs",
        data={
            "sql": "SELECT * FROM table",
        },
    )


def test_create_job_with_config(mocker):
    """Test creating a job with job config."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = JOB_RESPONSE

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.create_job(
        project_id=PROJECT_ID,
        job=SsbJobRequest(
            sql="SELECT * FROM table",
            selection=True,
            add_to_history=True,
        ),
    )

    assert response == from_dict(SsbJob, JOB_RESPONSE)

    # Verify that the post method was called with correct parameters
    api_client.post.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs",
        data={
            "sql": "SELECT * FROM table",
            "selection": True,
            "add_to_history": True,
        },
    )


def test_describe_job(mocker):
    """Test describing a specific job."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = JOB_RESPONSE

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.describe_job(project_id=PROJECT_ID, job_id=123)

    assert response == from_dict(SsbJob, JOB_RESPONSE)

    # Verify that the get method was called with correct parameters
    api_client.get.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/123",
        squelch={
            403: None,
            404: None,
        },
    )


def test_update_job(mocker):
    """Test updating a job."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = JOB_RESPONSE

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.update_job(
        project_id=PROJECT_ID,
        job=SsbJob(
            job_id=123,
            name="test_job",
            sql="SELECT * FROM updated_table",
            state=SsbJobState.RUNNING.value,
        ),
    )

    assert response == from_dict(SsbJob, JOB_RESPONSE)

    # Verify that the put method was called with correct parameters
    api_client.put.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/123",
        data={
            "job_id": 123,
            "name": "test_job",
            "sql": "SELECT * FROM updated_table",
            "state": SsbJobState.RUNNING.value,
        },
    )


def test_delete_job(mocker):
    """Test deleting a job."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = None

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.delete_job(PROJECT_ID, 123)

    assert response is None

    # Verify that the delete method was called with correct parameters
    api_client.delete.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/123",
        squelch={
            403: {},
            404: {},
        },
    )


def test_stop_job(mocker):
    """Test stopping a job with minimal configuration."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {}

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.stop_job(
        project_id=PROJECT_ID,
        job_id=123,
        config=SsbJobStop(),
    )

    assert response is None

    # Verify that the post method was called with correct parameters
    api_client.post.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/123/stop",
        data={
            "savepoint": False,
        },
    )


def test_stop_job_with_savepoint(mocker):
    """Test stopping a job with savepoint."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"savepoint_id": 456}

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.stop_job(
        project_id=PROJECT_ID,
        job_id=123,
        config=SsbJobStop(
            savepoint=True,
            savepoint_path="/path/to/savepoint",
            timeout=60,
        ),
    )

    assert response == 456
    assert isinstance(response, int)

    # Verify that the post method was called with correct parameters
    api_client.post.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/123/stop",
        data={
            "savepoint": True,
            "savepoint_path": "/path/to/savepoint",
            "timeout": 60,
        },
    )


def test_start_job(mocker):
    """Test starting a job with minimal configuration."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"responses": [{"type": "RESULT"}]}

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.start_job(
        project_id=PROJECT_ID,
        job_id=123,
        config=SsbJobStart(
            sql="SELECT 1",
        ),
    )

    assert isinstance(response, list)
    assert len(response) == 1
    assert isinstance(response[0], SsbJobResponse)
    assert response[0].type == "RESULT"

    # Verify that the post method was called with correct parameters
    api_client.post.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/123/execute",
        data={
            "sql": "SELECT 1",
        },
    )


def test_start_job_with_config(mocker):
    """Test starting a job with full configuration."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"responses": [{"type": "RESULT"}]}

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.start_job(
        project_id=PROJECT_ID,
        job_id=456,
        config=SsbJobStart(
            sql="SELECT * FROM table",
            selection=True,
            add_to_history=True,
        ),
    )

    assert isinstance(response, list)
    assert len(response) == 1
    assert isinstance(response[0], SsbJobResponse)
    assert response[0].type == "RESULT"

    # Verify that the post method was called with correct parameters
    api_client.post.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/456/execute",
        data={
            "sql": "SELECT * FROM table",
            "selection": True,
            "add_to_history": True,
        },
    )


def test_get_job_state(mocker):
    """Test getting the state of a job."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {
        "state": SsbJobState.RUNNING.value,
        "sampleId": "sample-123",
    }

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.get_job_state(
        project_id=PROJECT_ID,
        job_id=123,
    )

    assert isinstance(response, SsbJobStateResponse)
    assert response.state == SsbJobState.RUNNING.value
    assert response.sampleId == "sample-123"

    # Verify that the get method was called with correct parameters
    api_client.get.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/123/state",
    )


def test_get_job_state_without_sample_id(mocker):
    """Test getting the state of a job without a sample ID."""

    # Mock the ServicesClient instance
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {
        "state": SsbJobState.CREATED.value,
    }

    # Create the SsbJobClient instance
    client = SsbJobClient(api_client=api_client)

    response = client.get_job_state(
        project_id=PROJECT_ID,
        job_id=456,
    )

    assert isinstance(response, SsbJobStateResponse)
    assert response.state == SsbJobState.CREATED.value

    # Verify that the get method was called with correct parameters
    api_client.get.assert_called_once_with(
        f"/api/v2/projects/{PROJECT_ID}/jobs/456/state",
    )


WAIT_SLEEP = "ansible_collections.cloudera.services.plugins.module_utils.ssb.time.sleep"


def test_wait_for_job_state_immediate(mocker):
    """Return without sleeping when the job is already in a target state."""
    sleep = mocker.patch(WAIT_SLEEP)
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [
        dict(state=SsbJobState.RUNNING.value),
    ]
    client = SsbJobClient(api_client=api_client)

    response = client.wait_for_job_state(
        PROJECT_ID,
        123,
        SsbJobClient.WAIT_STARTED_STATES,
    )

    assert response.state == SsbJobState.RUNNING.value
    assert api_client.get.call_count == 1
    sleep.assert_not_called()


def test_wait_for_job_state_polls_until_target(mocker):
    """Poll through transitional states, sleeping poll_interval between checks."""
    sleep = mocker.patch(WAIT_SLEEP)
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [
        dict(state=SsbJobState.INITIALIZING.value),
        dict(state=SsbJobState.CREATED.value),
        dict(state=SsbJobState.RUNNING.value),
    ]
    client = SsbJobClient(api_client=api_client)

    response = client.wait_for_job_state(
        PROJECT_ID,
        123,
        SsbJobClient.WAIT_STARTED_STATES,
        poll_interval=3,
    )

    assert response.state == SsbJobState.RUNNING.value
    assert api_client.get.call_count == 3
    assert sleep.call_count == 2
    sleep.assert_called_with(3)


def test_wait_for_job_state_failure_state(mocker):
    """Fail fast when the job enters a failure state."""
    sleep = mocker.patch(WAIT_SLEEP)
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [
        dict(state=SsbJobState.INITIALIZING.value),
        dict(state=SsbJobState.FAILED.value),
    ]
    client = SsbJobClient(api_client=api_client)

    with pytest.raises(ServicesError, match="FAILED"):
        client.wait_for_job_state(
            PROJECT_ID,
            123,
            SsbJobClient.WAIT_STARTED_STATES,
            fail_states=SsbJobClient.WAIT_START_FAIL_STATES,
        )

    assert api_client.get.call_count == 2
    assert sleep.call_count == 1


def test_wait_for_job_state_timeout(mocker):
    """Raise ServicesError when the target state is not reached in time."""
    mocker.patch(WAIT_SLEEP)
    clock = iter([0, 0, 5, 10, 15])
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.module_utils.ssb.time.monotonic",
        side_effect=lambda: next(clock),
    )
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [
        dict(state=SsbJobState.INITIALIZING.value),
        dict(state=SsbJobState.INITIALIZING.value),
        dict(state=SsbJobState.INITIALIZING.value),
        dict(state=SsbJobState.INITIALIZING.value),
    ]
    client = SsbJobClient(api_client=api_client)

    with pytest.raises(ServicesError, match="Timed out"):
        client.wait_for_job_state(
            PROJECT_ID,
            123,
            SsbJobClient.WAIT_STARTED_STATES,
            timeout=10,
            poll_interval=5,
        )


def test_wait_for_job_state_stopped_targets(mocker):
    """Stopped targets accept CANCELED."""
    mocker.patch(WAIT_SLEEP)
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [
        dict(state=SsbJobState.CANCELLING.value),
        dict(state=SsbJobState.CANCELED.value),
    ]
    client = SsbJobClient(api_client=api_client)

    response = client.wait_for_job_state(
        PROJECT_ID,
        123,
        SsbJobClient.WAIT_STOPPED_STATES,
    )

    assert response.state == SsbJobState.CANCELED.value
