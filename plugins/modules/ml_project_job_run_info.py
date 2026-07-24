#!/usr/bin/python
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

DOCUMENTATION = r"""
module: ml_project_job_run_info
short_description: Retrieve information about Cloudera Machine Learning (CML) project job runs
description:
  - Retrieve information about one or more runs of a Cloudera Machine Learning (CML) project job.
  - The module can list all runs of a job or filter by a number of criteria.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  project_name:
    description:
      - The name of the enclosing project for the job.
      - Mutually exclusive with O(project_id).
    type: str
    required: false
  project_id:
    description:
      - The unique identifier of the enclosing project for the job.
      - Mutually exclusive with O(project_name).
    type: str
    required: false
  job_name:
    description:
      - The name of the enclosing job.
      - Mutually exclusive with O(job_id).
    type: str
    required: false
  job_id:
    description:
      - The unique identifier of the enclosing job.
      - Mutually exclusive with O(job_name).
    type: str
    required: false
  id:
    description:
      - The unique identifier of a single job run to retrieve.
    type: str
    required: false
    aliases:
      - run_id
  status:
    description:
      - Filter the job runs by status.
    type: str
    required: false
    choices:
      - scheduling
      - starting
      - running
      - stopping
      - stopped
      - succeeded
      - failed
      - timedout
      - unknown
  creator:
    description:
      - Filter the job runs by creator details.
    type: dict
    required: false
    suboptions:
      name:
        description:
          - The display name of the creator.
        type: str
        required: false
      username:
        description:
          - The username of the creator.
        type: str
        required: false
      email:
        description:
          - The email address of the creator.
        type: str
        required: false
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: List all runs of a job
  cloudera.services.ml_project_job_run_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    job_name: nightly-etl
  register: all_runs

- name: Get a single job run by id
  cloudera.services.ml_project_job_run_info:
    project_id: "{{ project_id }}"
    job_id: "{{ job_id }}"
    id: "{{ run_id }}"

- name: List failed runs of a job
  cloudera.services.ml_project_job_run_info:
    project_name: my-project
    job_name: nightly-etl
    status: failed

- name: List runs created by a user
  cloudera.services.ml_project_job_run_info:
    project_name: my-project
    job_name: nightly-etl
    creator:
      username: jdoe
"""

RETURN = r"""
job_runs:
  description: List of CML job runs.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the job run.
      type: str
      returned: always
    job_id:
      description: The identifier of the enclosing job.
      type: str
      returned: when available
    project_id:
      description: The identifier of the enclosing project.
      type: str
      returned: when available
    status:
      description: The status of the job run.
      type: str
      returned: when available
    arguments:
      description: The command-line arguments passed to the job run.
      type: str
      returned: when available
    environment:
      description: The environment variables of the job run.
      type: dict
      returned: when available
    creator:
      description: Details of the user that started the job run.
      type: dict
      returned: when available
    created_at:
      description: The timestamp when the job run was created.
      type: str
      returned: when available
    scheduling_at:
      description: The timestamp when the job run was scheduled.
      type: str
      returned: when available
    starting_at:
      description: The timestamp when the job run started.
      type: str
      returned: when available
    finished_at:
      description: The timestamp when the job run finished.
      type: str
      returned: when available
sdk_out:
  description: Returns the captured REST API log.
  returned: when supported
  type: str
sdk_out_lines:
  description: Returns a list of each line of the captured REST API log.
  returned: when supported
  type: list
  elements: str
"""

from typing import Any, Dict, List, NoReturn, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlJob,
    MlJobClient,
    MlJobRun,
    MlJobRunClient,
    MlProject,
    MlProjectClient,
    validate_project_id,
)

# Map the friendly status choices to the raw engine statuses returned by the API.
STATUS_MAP = {
    "scheduling": "ENGINE_SCHEDULING",
    "starting": "ENGINE_STARTING",
    "running": "ENGINE_RUNNING",
    "stopping": "ENGINE_STOPPING",
    "stopped": "ENGINE_STOPPED",
    "succeeded": "ENGINE_SUCCEEDED",
    "failed": "ENGINE_FAILED",
    "timedout": "ENGINE_TIMEDOUT",
    "unknown": "ENGINE_UNKNOWN",
}


class MlProjectJobRunInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                job_name=dict(type="str", required=False),
                job_id=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["run_id"]),
                status=dict(
                    type="str",
                    required=False,
                    choices=list(STATUS_MAP.keys()),
                ),
                creator=dict(
                    type="dict",
                    required=False,
                    options=dict(
                        name=dict(type="str", required=False),
                        username=dict(type="str", required=False),
                        email=dict(type="str", required=False),
                    ),
                ),
            ),
            mutually_exclusive=[
                ["project_name", "project_id"],
                ["job_name", "job_id"],
            ],
            required_one_of=[
                ["project_name", "project_id"],
                ["job_name", "job_id"],
            ],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.job_name = self.get_param("job_name")
        self.job_id = self.get_param("job_id")
        self.id = self.get_param("id")
        self.status = self.get_param("status")
        self.creator = self.get_param("creator")

        # Initialize result variables
        self.job_run_list: List[MlJobRun] = []

    def _fail(self, msg: str) -> NoReturn:
        # AnsibleModule.fail_json raises SystemExit at runtime; the trailing
        # raise is unreachable but marks this method as NoReturn so the type
        # checker can narrow values validated ahead of a failure.
        self.module.fail_json(msg=msg)
        raise SystemExit(msg)

    def _resolve_project_id(self) -> str:
        client = MlProjectClient(self.api_client)
        project: Optional[MlProject] = None
        if self.project_id:
            if not validate_project_id(self.project_id):
                self._fail("Invalid Project ID: %s" % self.project_id)
            project = client.describe_project(self.project_id)
        else:
            project = next(
                (p for p in client.list_projects() if p.name == self.project_name),
                None,
            )
        if not project:
            self._fail("Project not found")
        if not isinstance(project.id, str):
            self._fail("Project ID is invalid from resolved project.")
        return project.id

    def _resolve_job_id(self, project_id: str, client: MlJobClient) -> str:
        job: Optional[MlJob] = None
        if self.job_id:
            job = client.describe_job(project_id, self.job_id)
        else:
            job = next(
                (j for j in client.list_jobs(project_id) if j.name == self.job_name),
                None,
            )
        if not job:
            self._fail("Job not found")
        if not isinstance(job.id, str):
            self._fail("Job ID is invalid from resolved job.")
        return job.id

    def _matches(self, run: MlJobRun) -> bool:
        if self.status is not None and run.status != STATUS_MAP[self.status]:
            return False

        if self.creator:
            creator = run.creator
            if not isinstance(creator, dict):
                return False
            for key, wanted in self.creator.items():
                if wanted is not None and creator.get(key) != wanted:
                    return False

        return True

    def process(self) -> None:
        project_id = self._resolve_project_id()
        job_client = MlJobClient(self.api_client)
        job_id = self._resolve_job_id(project_id, job_client)

        client = MlJobRunClient(self.api_client)

        if self.id:
            run = client.describe_job_run(project_id, job_id, self.id)
            if run:
                self.job_run_list.append(run)
            return

        self.job_run_list = [
            r for r in client.list_job_runs(project_id, job_id) if self._matches(r)
        ]


def main():
    result = MlProjectJobRunInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        job_runs=[to_dict(run) for run in result.job_run_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
