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
module: ml_project_job_info
short_description: Retrieve information about Cloudera Machine Learning (CML) project jobs
description:
  - Retrieve information about one or more Cloudera Machine Learning (CML) project jobs.
  - The module can list all jobs within a project or filter by a number of criteria.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  project_name:
    description:
      - The name of the enclosing project.
      - Mutually exclusive with O(project_id).
    type: str
    required: false
  project_id:
    description:
      - The unique identifier of the enclosing project.
      - Mutually exclusive with O(project_name).
    type: str
    required: false
  id:
    description:
      - The unique identifier of a single job to retrieve.
    type: str
    required: false
    aliases:
      - job_id
  name:
    description:
      - Filter the jobs by name.
    type: str
    required: false
  kernel:
    description:
      - Filter the jobs by kernel.
    type: str
    required: false
  script:
    description:
      - Filter the jobs by entrypoint script.
    type: str
    required: false
  paused:
    description:
      - Filter the jobs by paused state.
    type: bool
    required: false
  creator:
    description:
      - Filter the jobs by creator details.
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
- name: List all jobs within a project
  cloudera.services.ml_project_job_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
  register: all_jobs

- name: Get a single job by id
  cloudera.services.ml_project_job_info:
    project_id: "{{ project_id }}"
    id: "{{ job_id }}"

- name: List jobs created by a user
  cloudera.services.ml_project_job_info:
    project_name: my-project
    creator:
      username: jdoe

- name: List paused jobs
  cloudera.services.ml_project_job_info:
    project_name: my-project
    paused: true
"""

RETURN = r"""
jobs:
  description: List of CML jobs.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the job.
      type: str
      returned: always
    name:
      description: The name of the job.
      type: str
      returned: always
    project_id:
      description: The identifier of the enclosing project.
      type: str
      returned: when available
    script:
      description: The entrypoint script for the job.
      type: str
      returned: when available
    arguments:
      description: The command-line arguments passed to the job script.
      type: str
      returned: when available
    kernel:
      description: The kernel for the job.
      type: str
      returned: when available
    cpu:
      description: The vCPU allocated to the job.
      type: float
      returned: when available
    memory:
      description: The RAM allocated to the job, in GB.
      type: float
      returned: when available
    nvidia_gpu:
      description: The count of Nvidia GPUs allocated to the job.
      type: int
      returned: when available
    runtime_identifier:
      description: The container runtime identifier for the job.
      type: str
      returned: when available
    runtime_addon_identifiers:
      description: The runtime addon identifiers for the job.
      type: list
      elements: str
      returned: when available
    schedule:
      description: The cron schedule for the job.
      type: str
      returned: when available
    parent_job_id:
      description: The identifier of the parent job that triggers this job.
      type: str
      returned: when available
    timeout:
      description: The job timeout, in seconds.
      type: int
      returned: when available
    kill_on_timeout:
      description: Whether the job is killed on timeout.
      type: bool
      returned: when available
    paused:
      description: Whether the job schedule is paused.
      type: bool
      returned: when available
    environment:
      description: The environment variables of the job.
      type: dict
      returned: when available
    creator:
      description: Details of the user that created the job.
      type: dict
      returned: when available
    created_at:
      description: The timestamp when the job was created.
      type: str
      returned: when available
    updated_at:
      description: The timestamp when the job was last updated.
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

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlJob,
    MlJobClient,
    MlProject,
    MlProjectClient,
    validate_project_id,
)


class MlProjectJobInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["job_id"]),
                name=dict(type="str", required=False),
                kernel=dict(type="str", required=False),
                script=dict(type="str", required=False),
                paused=dict(type="bool", required=False),
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
            mutually_exclusive=[["project_name", "project_id"]],
            required_one_of=[["project_name", "project_id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.id = self.get_param("id")
        self.name = self.get_param("name")
        self.kernel = self.get_param("kernel")
        self.script = self.get_param("script")
        self.paused = self.get_param("paused")
        self.creator = self.get_param("creator")

        # Initialize result variables
        self.job_list: List[MlJob] = []

    def _resolve_project_id(self) -> str:
        client = MlProjectClient(self.api_client)
        project: Optional[MlProject] = None
        if self.project_id:
            if not validate_project_id(self.project_id):
                self.module.fail_json(msg="Invalid Project ID: %s" % self.project_id)
            project = client.describe_project(self.project_id)
        else:
            project = next(
                (p for p in client.list_projects() if p.name == self.project_name),
                None,
            )
        if not project:
            self.module.fail_json(msg="Project not found")
        if not isinstance(project.id, str):
            self.module.fail_json(msg="Project ID is invalid from resolved project.")
        return project.id

    def _matches(self, job: MlJob) -> bool:
        checks = {
            "name": self.name,
            "kernel": self.kernel,
            "script": self.script,
        }
        for attr, wanted in checks.items():
            if wanted is not None and getattr(job, attr) != wanted:
                return False

        if self.paused is not None and job.paused != self.paused:
            return False

        if self.creator:
            creator = job.creator
            if not isinstance(creator, dict):
                return False
            for key, wanted in self.creator.items():
                if wanted is not None and creator.get(key) != wanted:
                    return False

        return True

    def process(self) -> None:
        project_id = self._resolve_project_id()
        client = MlJobClient(self.api_client)

        if self.id:
            job = client.describe_job(project_id, self.id)
            if job:
                self.job_list.append(job)
            return

        self.job_list = [j for j in client.list_jobs(project_id) if self._matches(j)]


def main():
    result = MlProjectJobInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        jobs=[to_dict(job) for job in result.job_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
