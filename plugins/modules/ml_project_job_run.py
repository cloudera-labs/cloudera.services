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
module: ml_project_job_run
short_description: Start or stop a Cloudera Machine Learning (CML) project job run
description:
  - Start or stop a run of a Cloudera Machine Learning (CML) project job.
  - The module is idempotent with respect to the job's most recent run.
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
      - The name of the job to run.
      - Mutually exclusive with O(id).
    type: str
    required: false
    aliases:
      - job
  id:
    description:
      - The unique identifier of the job to run.
      - Mutually exclusive with O(name).
    type: str
    required: false
    aliases:
      - job_id
  arguments:
    description:
      - The command-line arguments passed to the job run.
      - Applied only when starting a new run.
    type: str
    required: false
  env:
    description:
      - Environment variables to set on the job run.
      - Applied only when starting a new run.
    type: dict
    required: false
    aliases:
      - env_vars
  wait:
    description:
      - Whether to wait for the run to reach a terminal state.
    type: bool
    required: false
    default: false
  delay:
    description:
      - The interval, in seconds, between status checks when O(wait=true).
    type: int
    required: false
    default: 15
  wait_timeout:
    description:
      - The maximum time, in seconds, to wait for a terminal state when O(wait=true).
    type: int
    required: false
    default: 3600
    aliases:
      - execution_timeout
  state:
    description:
      - The declarative state of the job run.
      - V(started) ensures a run is active, starting one if the latest run is not already active.
      - V(stopped) ensures the latest run is not active, stopping it if necessary.
    type: str
    required: false
    default: started
    choices:
      - started
      - stopped
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Start a job run
  cloudera.services.ml_project_job_run:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    name: nightly-etl
    state: started

- name: Start a job run and wait for it to succeed
  cloudera.services.ml_project_job_run:
    project_id: "{{ project_id }}"
    id: "{{ job_id }}"
    arguments: "--verbose"
    wait: true
    wait_timeout: 1800

- name: Stop the active run of a job
  cloudera.services.ml_project_job_run:
    project_id: "{{ project_id }}"
    name: nightly-etl
    state: stopped
"""

RETURN = r"""
job_run:
  description: The CML job run details.
  returned: always
  type: dict
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

import time

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

# States in which a run is considered active (i.e. not yet in a terminal state).
ACTIVE_STATES = [
    "ENGINE_SCHEDULING",
    "ENGINE_STARTING",
    "ENGINE_RUNNING",
]


class MlProjectJobRunModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                name=dict(type="str", required=False, aliases=["job"]),
                id=dict(type="str", required=False, aliases=["job_id"]),
                arguments=dict(type="str", required=False),
                env=dict(type="dict", required=False, aliases=["env_vars"]),
                wait=dict(type="bool", required=False, default=False),
                delay=dict(type="int", required=False, default=15),
                wait_timeout=dict(
                    type="int",
                    required=False,
                    default=3600,
                    aliases=["execution_timeout"],
                ),
                state=dict(
                    type="str",
                    required=False,
                    choices=["started", "stopped"],
                    default="started",
                ),
            ),
            mutually_exclusive=[
                ["name", "id"],
                ["project_name", "project_id"],
            ],
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
        self.env = self.get_param("env")
        self.wait = self.get_param("wait")
        self.delay = self.get_param("delay")
        self.run_timeout = self.get_param("wait_timeout")
        self.state = self.get_param("state")

        # Initialize the return values
        self.changed = False
        self.job_run: Optional[MlJobRun] = None

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
        if self.id:
            job = client.describe_job(project_id, self.id)
        else:
            job = next(
                (j for j in client.list_jobs(project_id) if j.name == self.name),
                None,
            )
        if not job:
            self._fail("Job not found")
        if not isinstance(job.id, str):
            self._fail("Job ID is invalid from resolved job.")
        return job.id

    def _latest_run(
        self,
        client: MlJobRunClient,
        project_id: str,
        job_id: str,
    ) -> Optional[MlJobRun]:
        runs = client.list_job_runs(project_id, job_id)
        # The list endpoint does not guarantee ordering; sort by creation time
        # (most recent first) so the "latest" run is deterministic.
        runs.sort(
            key=lambda r: r.created_at if isinstance(r.created_at, str) else "",
            reverse=True,
        )
        return runs[0] if runs else None

    def _incoming_run(self) -> MlJobRun:
        incoming = MlJobRun()
        if self.arguments is not None:
            incoming.arguments = self.arguments
        if self.env is not None:
            incoming.environment = self.env
        return incoming

    def _wait_for_state(
        self,
        client: MlJobRunClient,
        project_id: str,
        job_id: str,
        success_status: List[str],
        error_status: List[str],
    ) -> MlJobRun:
        deadline = time.time() + self.run_timeout
        while time.time() < deadline:
            latest = self._latest_run(client, project_id, job_id)
            if latest is not None:
                if latest.status in success_status:
                    return latest
                if latest.status in error_status:
                    self._fail(
                        "Failed to reach target status. Status: %s" % latest.status,
                    )
            time.sleep(self.delay)
        self._fail("Failed to reach target status. Status: module timeout")

    def process(self) -> None:
        project_id = self._resolve_project_id()
        job_client = MlJobClient(self.api_client)
        job_id = self._resolve_job_id(project_id, job_client)

        client = MlJobRunClient(self.api_client)
        latest = self._latest_run(client, project_id, job_id)

        if self.state == "started":
            if latest is None or latest.status not in ACTIVE_STATES:
                # No run yet, or the latest run is in a terminal state.
                self.changed = True
                if not self.module.check_mode:
                    self.job_run = client.create_job_run(
                        project_id,
                        job_id,
                        self._incoming_run(),
                    )
                else:
                    self.job_run = self._incoming_run()
            else:
                # A run is already active; re-applying is a no-op.
                self.job_run = latest

            if self.wait and not self.module.check_mode:
                self.job_run = self._wait_for_state(
                    client,
                    project_id,
                    job_id,
                    ["ENGINE_SUCCEEDED"],
                    ["ENGINE_FAILED", "ENGINE_UNKNOWN", "ENGINE_STOPPED"],
                )
        else:
            # state == "stopped"
            if latest is not None and latest.status in ACTIVE_STATES:
                if not isinstance(latest.id, str):
                    self._fail("Job run ID is invalid from latest run.")
                self.changed = True
                if not self.module.check_mode:
                    self.job_run = client.stop_job_run(project_id, job_id, latest.id)
                else:
                    self.job_run = latest
            elif latest is not None:
                # Already stopped or in another terminal state.
                self.job_run = latest

            if self.wait and not self.module.check_mode:
                self.job_run = self._wait_for_state(
                    client,
                    project_id,
                    job_id,
                    ["ENGINE_STOPPED", "ENGINE_SUCCEEDED"],
                    [
                        "ENGINE_FAILED",
                        "ENGINE_TIMEDOUT",
                        "ENGINE_RUNNING",
                        "ENGINE_UNKNOWN",
                    ],
                )


def main():
    result = MlProjectJobRunModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        job_run=to_dict(result.job_run) if result.job_run else {},
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
