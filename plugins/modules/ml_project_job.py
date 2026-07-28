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
module: ml_project_job
short_description: Manage a Cloudera Machine Learning (CML) project job
description:
  - Create, update, or delete a Cloudera Machine Learning (CML) project job.
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
  name:
    description:
      - The name of the job.
      - Required when creating a job.
      - Mutually exclusive with O(id).
    type: str
    required: false
    aliases:
      - job
  id:
    description:
      - The unique identifier of an existing job.
      - Mutually exclusive with O(name).
    type: str
    required: false
    aliases:
      - job_id
  arguments:
    description:
      - The command-line arguments passed to the job script.
    type: str
    required: false
  attachments:
    description:
      - A list of file attachments (project file paths) delivered with job run notifications.
      - Applied only on job creation.
    type: list
    elements: str
    required: false
  cpu:
    description:
      - The vCPU allocated to the job.
    type: float
    required: false
  env:
    description:
      - Environment variables to set on the job.
      - On update, the provided variables are merged with the job's existing variables.
    type: dict
    required: false
    aliases:
      - env_vars
  kernel:
    description:
      - The kernel to use for the job.
      - Not valid for projects whose default engine type is C(ml_runtime); use O(runtime) instead.
      - Mutually exclusive with O(runtime).
    type: str
    required: false
    choices:
      - python3
      - python2
      - r
      - scala
  kill:
    description:
      - Whether to kill the job when it exceeds O(job_timeout).
      - Requires O(job_timeout).
    type: bool
    required: false
    aliases:
      - kill_on_timeout
  memory:
    description:
      - The RAM allocated to the job, in GB.
    type: float
    required: false
  gpu:
    description:
      - The count of Nvidia GPUs allocated to the job.
    type: int
    required: false
    aliases:
      - nvidia_gpu
  parent:
    description:
      - The unique identifier of a parent job that triggers this job on completion.
      - Mutually exclusive with O(schedule).
    type: str
    required: false
    aliases:
      - parent_job_id
  paused:
    description:
      - Whether the job schedule is paused.
    type: bool
    required: false
  addons:
    description:
      - A list of runtime addon identifiers for the job.
      - On update, the provided addons are merged with the job's existing addons.
    type: list
    elements: str
    required: false
    aliases:
      - runtime_addons
      - runtime_addon_identifiers
  runtime:
    description:
      - The container runtime identifier for the job.
      - Required on creation for projects whose default engine type is C(ml_runtime).
      - Mutually exclusive with O(kernel).
    type: str
    required: false
    aliases:
      - runtime_image_id
      - runtime_identifier
  schedule:
    description:
      - The cron schedule for the job.
      - Mutually exclusive with O(parent).
    type: str
    required: false
  script:
    description:
      - The entrypoint script for the job.
      - Required when creating a job.
    type: str
    required: false
  job_timeout:
    description:
      - The job timeout, in seconds.
    type: int
    required: false
    aliases:
      - execution_timeout
  recipients:
    description:
      - A list of email notification recipients for job runs.
      - Applied only on job creation.
    type: list
    elements: dict
    required: false
    suboptions:
      email:
        description:
          - The email address of the recipient.
        type: str
        required: true
      success:
        description:
          - Whether to notify on job success.
        type: bool
        required: false
        default: true
      failure:
        description:
          - Whether to notify on job failure.
        type: bool
        required: false
        default: true
      timeout:
        description:
          - Whether to notify on job timeout.
        type: bool
        required: false
        default: true
      stopped:
        description:
          - Whether to notify when a job is stopped.
        type: bool
        required: false
        default: true
  state:
    description:
      - The declarative state of the job.
    type: str
    required: false
    default: present
    choices:
      - present
      - absent
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Create a job
  cloudera.services.ml_project_job:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    name: nightly-etl
    script: etl.py
    runtime: "{{ runtime_id }}"
    schedule: "0 2 * * *"
    env:
      LOG_LEVEL: info
    state: present

- name: Update a job's timeout
  cloudera.services.ml_project_job:
    project_id: "{{ project_id }}"
    name: nightly-etl
    job_timeout: 3600
    kill: true

- name: Delete a job
  cloudera.services.ml_project_job:
    project_id: "{{ project_id }}"
    id: "{{ job_id }}"
    state: absent
"""

RETURN = r"""
job:
  description: The CML job details.
  returned: always
  type: dict
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

from dataclasses import replace
from typing import Any, Dict, NoReturn, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    diff_dict,
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

CREATE_REQUIRED = ["script"]


class MlProjectJobModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                name=dict(type="str", required=False, aliases=["job"]),
                id=dict(type="str", required=False, aliases=["job_id"]),
                arguments=dict(type="str", required=False),
                attachments=dict(type="list", elements="str", required=False),
                cpu=dict(type="float", required=False),
                env=dict(type="dict", required=False, aliases=["env_vars"]),
                kernel=dict(
                    type="str",
                    required=False,
                    choices=["python3", "python2", "r", "scala"],
                ),
                kill=dict(type="bool", required=False, aliases=["kill_on_timeout"]),
                memory=dict(type="float", required=False),
                gpu=dict(type="int", required=False, aliases=["nvidia_gpu"]),
                parent=dict(type="str", required=False, aliases=["parent_job_id"]),
                paused=dict(type="bool", required=False),
                addons=dict(
                    type="list",
                    elements="str",
                    required=False,
                    aliases=["runtime_addons", "runtime_addon_identifiers"],
                ),
                runtime=dict(
                    type="str",
                    required=False,
                    aliases=["runtime_image_id", "runtime_identifier"],
                ),
                schedule=dict(type="str", required=False),
                script=dict(type="str", required=False),
                job_timeout=dict(
                    type="int",
                    required=False,
                    aliases=["execution_timeout"],
                ),
                recipients=dict(
                    type="list",
                    elements="dict",
                    required=False,
                    options=dict(
                        email=dict(type="str", required=True),
                        success=dict(type="bool", required=False, default=True),
                        failure=dict(type="bool", required=False, default=True),
                        timeout=dict(type="bool", required=False, default=True),
                        stopped=dict(type="bool", required=False, default=True),
                    ),
                ),
                state=dict(
                    type="str",
                    required=False,
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[
                ["name", "id"],
                ["project_name", "project_id"],
                ["parent", "schedule"],
                ["kernel", "runtime"],
            ],
            required_by={
                "kill": ["job_timeout"],
            },
            required_one_of=[
                ["name", "id"],
                ["project_name", "project_id"],
            ],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.name = self.get_param("name")
        self.id = self.get_param("id")
        self.arguments = self.get_param("arguments")
        self.attachments = self.get_param("attachments")
        self.cpu = self.get_param("cpu")
        self.env = self.get_param("env")
        self.kernel = self.get_param("kernel")
        self.kill = self.get_param("kill")
        self.memory = self.get_param("memory")
        self.gpu = self.get_param("gpu")
        self.parent = self.get_param("parent")
        self.paused = self.get_param("paused")
        self.addons = self.get_param("addons")
        self.runtime = self.get_param("runtime")
        self.schedule = self.get_param("schedule")
        self.script = self.get_param("script")
        self.job_timeout = self.get_param("job_timeout")
        self.recipients = self.get_param("recipients")
        self.state = self.get_param("state")

        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.job: Optional[MlJob] = None

    def _fail(self, msg: str) -> NoReturn:
        # AnsibleModule.fail_json raises SystemExit at runtime; the trailing
        # raise is unreachable but marks this method as NoReturn so the type
        # checker can narrow values validated ahead of a failure.
        self.module.fail_json(msg=msg)
        raise SystemExit(msg)

    def _resolve_project(self) -> MlProject:
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
        return project

    def _merged_environment(self, existing: MlJob) -> Any:
        if self.env is None:
            return existing.environment
        current = existing.environment
        if not isinstance(current, dict):
            current = {}
        return {**current, **self.env}

    def _merged_addons(self, existing: MlJob) -> Any:
        if self.addons is None:
            return existing.runtime_addon_identifiers
        # User-specified addons take priority; existing addons are appended and
        # the result is sorted for stable comparison.
        merged = list(self.addons)
        current = existing.runtime_addon_identifiers
        if isinstance(current, list):
            for addon in current:
                if addon not in merged:
                    merged.append(addon)
        return sorted(merged)

    def _incoming_job(self) -> MlJob:
        incoming = MlJob(name=self.name)
        if self.script is not None:
            incoming.script = self.script
        if self.arguments is not None:
            incoming.arguments = self.arguments
        if self.kernel is not None:
            incoming.kernel = self.kernel
        if self.cpu is not None:
            incoming.cpu = self.cpu
        if self.memory is not None:
            incoming.memory = self.memory
        if self.gpu is not None:
            incoming.nvidia_gpu = self.gpu
        if self.runtime is not None:
            incoming.runtime_identifier = self.runtime
        if self.addons is not None:
            incoming.runtime_addon_identifiers = sorted(self.addons)
        if self.attachments is not None:
            incoming.attachments = self.attachments
        if self.schedule is not None:
            incoming.schedule = self.schedule
        if self.parent is not None:
            incoming.parent_job_id = self.parent
        if self.job_timeout is not None:
            incoming.timeout = self.job_timeout
        if self.kill is not None:
            incoming.kill_on_timeout = self.kill
        if self.paused is not None:
            incoming.paused = self.paused
        if self.recipients is not None:
            incoming.recipients = self.recipients
        if self.env is not None:
            incoming.environment = self.env
        return incoming

    def process(self) -> None:
        project = self._resolve_project()
        project_id = project.id
        if not isinstance(project_id, str):
            self._fail("Project ID is invalid from resolved project.")
        is_ml_runtime = project.default_engine_type == "ml_runtime"
        client = MlJobClient(self.api_client)

        if self.kernel is not None and is_ml_runtime:
            self.module.fail_json(
                msg="Invalid parameter, 'kernel'. Default project engine type is 'ml_runtime'.",
            )

        existing: Optional[MlJob] = None
        if self.id:
            existing = client.describe_job(project_id, self.id)
        else:
            existing = next(
                (j for j in client.list_jobs(project_id) if j.name == self.name),
                None,
            )

        if self.state == "absent":
            if existing:
                if not isinstance(existing.id, str):
                    self._fail("Job ID is invalid from existing job.")
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = to_dict(existing)
                if not self.module.check_mode:
                    client.delete_job(project_id, existing.id)
            return

        # present implies the job should exist.
        if not existing:
            missing = [k for k in CREATE_REQUIRED if self.get_param(k) is None]
            if missing:
                self.module.fail_json(
                    msg="Missing required parameters for creation: %s"
                    % ", ".join(sorted(missing)),
                )
            if self.runtime is None and is_ml_runtime:
                self.module.fail_json(
                    msg="Missing parameter, 'runtime'. Default project engine type is 'ml_runtime'.",
                )

            incoming = self._incoming_job()
            self.changed = True
            if self.module._diff:
                self.diff["after"] = to_dict(incoming)
            if not self.module.check_mode:
                self.job = client.create_job(project_id, incoming)
            else:
                self.job = incoming
        else:
            # Update an existing job
            desired = replace(
                existing,
                script=self.script if self.script is not None else existing.script,
                arguments=(
                    self.arguments if self.arguments is not None else existing.arguments
                ),
                kernel=self.kernel if self.kernel is not None else existing.kernel,
                cpu=self.cpu if self.cpu is not None else existing.cpu,
                memory=self.memory if self.memory is not None else existing.memory,
                nvidia_gpu=self.gpu if self.gpu is not None else existing.nvidia_gpu,
                runtime_identifier=(
                    self.runtime
                    if self.runtime is not None
                    else existing.runtime_identifier
                ),
                runtime_addon_identifiers=self._merged_addons(existing),
                schedule=(
                    self.schedule if self.schedule is not None else existing.schedule
                ),
                parent_job_id=(
                    self.parent if self.parent is not None else existing.parent_job_id
                ),
                timeout=(
                    self.job_timeout
                    if self.job_timeout is not None
                    else existing.timeout
                ),
                kill_on_timeout=(
                    self.kill if self.kill is not None else existing.kill_on_timeout
                ),
                paused=self.paused if self.paused is not None else existing.paused,
                environment=self._merged_environment(existing),
            )

            prev_config, next_config = diff_dict(existing, desired)

            self.job = existing
            if prev_config or next_config:
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = prev_config
                    self.diff["after"] = next_config
                if not self.module.check_mode:
                    self.job = client.update_job(project_id, desired)
                else:
                    self.job = desired


def main():
    result = MlProjectJobModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        job=to_dict(result.job) if result.job else {},
        diff=result.diff,
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
