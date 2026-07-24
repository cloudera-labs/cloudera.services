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

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    ServicesClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlJobRun,
    MlJobRunClient,
    API_VERSION,
)

PROJECT_ID = "aaaa-bbbb-cccc-dddd"
JOB_ID = "job-1"

JOB_RUN = dict(
    id="run-1",
    job_id=JOB_ID,
    project_id=PROJECT_ID,
    status="ENGINE_SUCCEEDED",
)


def test_job_run_dataclass_roundtrip():
    run = from_dict(MlJobRun, JOB_RUN)
    assert isinstance(run, MlJobRun)
    assert to_dict(run) == JOB_RUN


def test_list_job_runs(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(job_runs=[JOB_RUN])

    client = MlJobRunClient(api_client=api_client)
    response = client.list_job_runs(PROJECT_ID, JOB_ID)

    assert response == [from_dict(MlJobRun, JOB_RUN)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs/{JOB_ID}/runs",
        params={"page_size": 100},
    )


def test_describe_job_run(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = JOB_RUN

    client = MlJobRunClient(api_client=api_client)
    response = client.describe_job_run(PROJECT_ID, JOB_ID, "run-1")

    assert response == from_dict(MlJobRun, JOB_RUN)
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs/{JOB_ID}/runs/run-1",
        squelch={403: None, 404: None},
    )


def test_create_job_run(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = JOB_RUN

    client = MlJobRunClient(api_client=api_client)
    client.create_job_run(PROJECT_ID, JOB_ID, MlJobRun(status="scheduling"))

    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs/{JOB_ID}/runs",
        data={"status": "scheduling"},
    )


def test_stop_job_run(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = JOB_RUN

    client = MlJobRunClient(api_client=api_client)
    response = client.stop_job_run(PROJECT_ID, JOB_ID, "run-1")

    assert response == from_dict(MlJobRun, JOB_RUN)
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs/{JOB_ID}/runs/run-1:stop",
    )
