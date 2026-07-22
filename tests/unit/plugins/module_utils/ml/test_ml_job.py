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
    MlJob,
    MlJobClient,
    API_VERSION,
)

PROJECT_ID = "aaaa-bbbb-cccc-dddd"

JOB = dict(
    id="job-1",
    name="test-job",
    project_id=PROJECT_ID,
    script="analysis.py",
    kernel="python3",
)


def test_job_dataclass_roundtrip():
    job = from_dict(MlJob, JOB)
    assert isinstance(job, MlJob)
    assert to_dict(job) == JOB


def test_list_jobs(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(jobs=[JOB])

    client = MlJobClient(api_client=api_client)
    response = client.list_jobs(PROJECT_ID)

    assert response == [from_dict(MlJob, JOB)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs",
        params={"page_size": 100},
    )


def test_describe_job(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = JOB

    client = MlJobClient(api_client=api_client)
    response = client.describe_job(PROJECT_ID, "job-1")

    assert response == from_dict(MlJob, JOB)
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs/job-1",
        squelch={403: None, 404: None},
    )


def test_create_job(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = JOB

    client = MlJobClient(api_client=api_client)
    client.create_job(PROJECT_ID, MlJob(name="test-job", script="analysis.py"))

    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs",
        data={"name": "test-job", "script": "analysis.py"},
    )


def test_update_job(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.patch.return_value = JOB

    client = MlJobClient(api_client=api_client)
    client.update_job(PROJECT_ID, MlJob(name="test-job", id="job-1", kernel="python3"))

    api_client.patch.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs/job-1",
        data={"name": "test-job", "id": "job-1", "kernel": "python3"},
    )


def test_delete_job(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlJobClient(api_client=api_client)
    client.delete_job(PROJECT_ID, "job-1")

    api_client.delete.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/jobs/job-1",
    )
