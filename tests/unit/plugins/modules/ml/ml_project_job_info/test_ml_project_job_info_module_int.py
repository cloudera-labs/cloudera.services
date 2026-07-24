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

from typing import Callable

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_project_job_info

REQUIRED_ENV_VARS = [
    "CML_ENDPOINT",
    "CML_API_KEY",
]


@pytest.fixture
def ml_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args (endpoint + bearer token) for CML tests."""

    def _ml_module_args(overrides: dict = {}) -> None:
        args = {
            "url": env_context["CML_ENDPOINT"],
            "api_key": env_context["CML_API_KEY"],
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _ml_module_args


def test_list_all(ml_module_args, existing_ml_project, existing_ml_job):
    """List all jobs within a project."""

    ml_module_args({"project_id": existing_ml_project.id})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    result = e.value
    assert result["changed"] is False
    assert any(j["id"] == existing_ml_job.id for j in result["jobs"])


def test_filter_by_name(ml_module_args, existing_ml_project, existing_ml_job):
    """Filter jobs by name."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "name": existing_ml_job.name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    jobs = e.value["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["name"] == existing_ml_job.name


def test_filter_by_name_no_match(ml_module_args, existing_ml_project, existing_ml_job):
    """Filtering by a non-existent name returns no jobs."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "name": "nonexistent-job-name-12345",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    assert e.value["jobs"] == []


def test_by_id(ml_module_args, existing_ml_project, existing_ml_job):
    """Retrieve a single job by id."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "id": existing_ml_job.id,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    jobs = e.value["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["id"] == existing_ml_job.id


def test_by_id_not_found(ml_module_args, existing_ml_project):
    """A missing job by id returns an empty list."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "id": "0000-0000-0000-0000",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_job_info.main()

    assert e.value["jobs"] == []
