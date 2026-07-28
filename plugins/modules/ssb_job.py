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
module: ssb_job
short_description: Manage SSB jobs
description:
  - Create, execute, stop, and delete Cloudera SQL Stream Builder (SSB) jobs.
  - Jobs are scoped to a project identified by O(project_id).
  - Job names must contain only letters, numbers, and underscores and start with a letter or underscore.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  project_id:
    description:
      - The unique identifier of the project containing the job.
      - Required for all operations.
    type: str
    required: true
  job_id:
    description:
      - The unique identifier of an existing job.
      - Use this to reference an existing job for O(state=stopped), O(state=started), O(state=restarted), or O(state=absent).
      - This parameter is mutually exclusive with O(name).
    type: int
    required: false
  name:
    description:
      - The name of the job.
      - Required when creating a new job (O(state=present), O(state=started), or O(state=restarted)).
      - Job names must contain only letters, numbers, and underscores and start with a letter or underscore.
      - This parameter is mutually exclusive with O(job_id).
    type: str
    required: false
  sql:
    description:
      - The SQL query to execute for the job.
      - Required when creating a new job (O(state=present), O(state=started), or O(state=restarted)).
    type: str
    required: false
  savepoint:
    description:
      - Whether to create a savepoint when stopping the job.
      - Only used when O(state=stopped) or O(state=absent).
    type: bool
    default: false
  savepoint_path:
    description:
      - The path to the savepoint directory.
      - Only used when O(savepoint=true).
    type: str
    required: false
  stop_timeout:
    description:
      - Timeout in seconds for stopping the job.
      - Only used when O(state=stopped) or O(state=absent).
    type: int
    required: false
  state:
    description:
      - The desired state of the job.
      - C(present) creates the job if it doesn't exist but does NOT execute it.
      - C(started) creates the job if needed and executes it to an active state.
      - C(stopped) ensures the job exists and stops it if running.
      - C(restarted) ensures the job exists and executes it (stopping first if needed).
      - C(absent) stops and deletes the job.
    type: str
    choices:
      - present
      - started
      - stopped
      - restarted
      - absent
    default: present
extends_documentation_fragment:
  - ansible.builtin.action_common_attributes
  - cloudera.services.services_client
attributes:
  check_mode:
    support: full
  diff_mode:
    support: full
  platform:
    platforms: all
"""

EXAMPLES = r"""
- name: Create an SSB job (without executing)
  cloudera.services.ssb_job:
    project_id: "12345"
    name: "my_streaming_job"
    sql: "SELECT * FROM orders WHERE amount > 100"
    state: present

- name: Create and start an SSB job
  cloudera.services.ssb_job:
    project_id: "12345"
    name: "my_streaming_job"
    sql: "SELECT * FROM orders WHERE amount > 100"
    state: started

- name: Stop a running job
  cloudera.services.ssb_job:
    project_id: "12345"
    job_id: 67890
    state: stopped

- name: Stop a running job with savepoint
  cloudera.services.ssb_job:
    project_id: "12345"
    name: "my_streaming_job"
    state: stopped
    savepoint: true
    savepoint_path: "/savepoints/my_job"

- name: Restart a job (stop if running, then start)
  cloudera.services.ssb_job:
    project_id: "12345"
    name: "my_streaming_job"
    state: restarted

- name: Delete a job
  cloudera.services.ssb_job:
    project_id: "12345"
    name: "my_streaming_job"
    state: absent
"""

RETURN = r"""
job:
    description: The job details.
    returned: when state is present, started, stopped, or restarted
    type: dict
    contains:
        job_id:
            description: The unique identifier of the job.
            type: int
            returned: always
        name:
            description: The name of the job.
            type: str
            returned: always
        sql:
            description: The SQL query executed by the job.
            type: str
            returned: always
        state:
            description: The current state of the job.
            type: str
            returned: when available
        start_time:
            description: Timestamp when the job was started (epoch milliseconds).
            type: int
            returned: when available
        end_time:
            description: Timestamp when the job ended (epoch milliseconds).
            type: int
            returned: when available
        user_id:
            description: The ID of the user who created the job.
            type: str
            returned: when available
        username:
            description: The username of the user who created the job.
            type: str
            returned: when available
        project_id:
            description: The ID of the project containing this job.
            type: str
            returned: when available
        flink_job_id:
            description: The Flink job ID associated with this SSB job.
            type: str
            returned: when available
        created_at:
            description: Timestamp when the job was created.
            type: str
            returned: when available
        cluster_id:
            description: The ID of the cluster running this job.
            type: str
            returned: when available
        sample_id:
            description: The sample ID for this job.
            type: str
            returned: when available
        jm_url:
            description: The URL to the Flink JobManager for this job.
            type: str
            returned: when available
        mv_endpoints:
            description: List of materialized view API endpoints for this job.
            type: list
            elements: dict
            returned: when available
        mv_config:
            description: Materialized view configuration for this job.
            type: dict
            returned: when available
        checkpoint_config:
            description: Checkpoint configuration for this job.
            type: dict
            returned: when available
        kubernetes_config:
            description: Kubernetes configuration for this job.
            type: dict
            returned: when available
        autoscaler_config:
            description: Autoscaler configuration for this job.
            type: dict
            returned: when available
        savepoint_id:
            description: The ID of the savepoint associated with this job.
            type: int
            returned: when available
savepoint_id:
    description: The savepoint ID created when stopping the job.
    returned: when O(state=stopped) with O(savepoint=true)
    type: int
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

from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    diff_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbJob,
    SsbJobClient,
    SsbJobConfig,
    SsbJobRequest,
    SsbJobStart,
    SsbJobStop,
    SsbRuntimeConfig,
    SsbExecutionMode,
    SsbRuntimeMode,
    SsbJobState,
)


class SsbJobModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_id=dict(type="str", required=True),
                job_id=dict(type="int", required=False),
                name=dict(type="str", required=False),
                sql=dict(type="str", required=False),
                savepoint=dict(type="bool", default=False),
                savepoint_path=dict(type="str", required=False),
                stop_timeout=dict(type="int", required=False),
                state=dict(
                    type="str",
                    choices=["present", "started", "stopped", "restarted", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[["job_id", "name"]],
            required_one_of=[["job_id", "name"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_id = self.get_param("project_id")
        self.job_id = self.get_param("job_id")
        self.name = self.get_param("name")
        self.sql = self.get_param("sql")
        self.savepoint = self.get_param("savepoint")
        self.savepoint_path = self.get_param("savepoint_path")
        self.stop_timeout = self.get_param("stop_timeout")
        self.state = self.get_param("state")

        # Initialize result variables
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.job: Optional[SsbJob] = None
        self.savepoint_id: Optional[int] = None

    def _create_job(
        self,
        client: SsbJobClient,
    ) -> Optional[SsbJob]:
        """Create a job if check_mode is not active."""
        if not self.name or not self.sql:
            self.module.fail_json(
                msg="Parameters 'name' and 'sql' are required when creating a new job.",
            )

        job_config = SsbJobConfig(job_name=self.name)
        job_request = SsbJobRequest(
            sql=self.sql,
            job_config=job_config,
        )

        self.changed = True
        if self.module._diff:
            self.diff["after"] = {"name": self.name, "sql": self.sql}

        if not self.module.check_mode:
            return client.create_job(self.project_id, job_request)

    def _update_job(
        self,
        client: SsbJobClient,
        existing: SsbJob,
    ) -> SsbJob:
        """Update job parameters if they differ from desired state."""
        # Build desired state with only updateable fields
        desired = SsbJob(
            name=existing.name,  # name is read-only, use existing value
            sql=self.sql if self.sql else existing.sql,
            # Preserve all other fields from existing job
            start_time=existing.start_time,
            end_time=existing.end_time,
            state=existing.state,
            job_id=existing.job_id,
            user_id=existing.user_id,
            username=existing.username,
            project_id=existing.project_id,
            flink_job_id=existing.flink_job_id,
            created_at=existing.created_at,
            cluster_id=existing.cluster_id,
            sample_id=existing.sample_id,
            jm_url=existing.jm_url,
            mv_endpoints=existing.mv_endpoints,
            mv_config=existing.mv_config,
            checkpoint_config=existing.checkpoint_config,
            kubernetes_config=existing.kubernetes_config,
            autoscaler_config=existing.autoscaler_config,
            savepoint_id=existing.savepoint_id,
        )

        # Detect changes
        before_dict, after_dict = diff_dict(existing, desired)

        if before_dict or after_dict:
            # Changes detected
            self.changed = True
            if self.module._diff:
                self.diff = {
                    "before": before_dict,
                    "after": after_dict,
                }

            if not self.module.check_mode:
                return client.update_job(self.project_id, desired)

        return existing

    def process(self) -> None:
        client = SsbJobClient(self.api_client)

        existing: Optional[SsbJob] = None

        # Look up existing job by id or name
        if self.job_id:
            existing = client.describe_job(self.project_id, self.job_id)
        elif self.name:
            # List jobs and find by name
            jobs = client.list_jobs(self.project_id)
            existing = next((j for j in jobs if j.name == self.name), None)

        if self.state == "absent":
            if existing:
                # Stop first if in an active state
                if existing.state in SsbJobClient.READY_STATES:
                    self.changed = True
                    if not self.module.check_mode:
                        stop_config = SsbJobStop(
                            savepoint=self.savepoint,
                            savepoint_path=self.savepoint_path,
                            timeout=self.stop_timeout,
                        )
                        self.savepoint_id = client.stop_job(
                            self.project_id,
                            existing.job_id,  # pyright: ignore[reportArgumentType]
                            stop_config,
                        )

                # Delete the job
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = to_dict(existing)

                if not self.module.check_mode:
                    client.delete_job(
                        self.project_id,
                        existing.job_id,  # pyright: ignore[reportArgumentType]
                    )

        elif self.state == "present":
            # Create job if it doesn't exist, but do NOT execute
            if not existing:
                self.job = self._create_job(client)
            else:
                # Check for parameter changes and update if needed
                self.job = self._update_job(client, existing)

        elif self.state == "started":
            # Create if needed, then execute to active state
            created: Optional[SsbJob] = None

            if not existing:
                created = self._create_job(client)
            else:
                # Check for parameter changes and update if needed
                existing = self._update_job(client, existing)

            # Use the created job or the existing/updated job
            job_ref = created if created else existing

            # Execute if not already in an active or terminal state
            if job_ref and job_ref.state not in (
                SsbJobClient.READY_STATES | SsbJobClient.TERMINAL_STATES
            ):
                self.changed = True
                if self.module._diff:
                    # Merge state info into existing diff (if job was created or updated)
                    if created:
                        # Job was just created - add state to "after"
                        self.diff["after"]["state"] = SsbJobState.RUNNING.value
                    elif self.diff:
                        self.diff["before"]["state"] = job_ref.state
                        self.diff["after"]["state"] = SsbJobState.RUNNING.value
                    else:
                        # Job existed but wasn't updated - show state change only
                        self.diff["before"]["state"] = job_ref.state
                        self.diff["after"]["state"] = SsbJobState.RUNNING.value

                if not self.module.check_mode:
                    runtime_config = SsbRuntimeConfig(
                        execution_mode=SsbExecutionMode.PER_JOB.value,
                        runtime_mode=SsbRuntimeMode.STREAMING.value,
                    )
                    job_config = SsbJobConfig(
                        job_name=job_ref.name,
                        runtime_config=runtime_config,
                    )
                    start_config = SsbJobStart(sql=job_ref.sql, job_config=job_config)
                    client.start_job(
                        self.project_id,
                        job_ref.job_id,  # pyright: ignore[reportArgumentType]
                        start_config,
                    )
                    # Refresh job state
                    self.job = client.describe_job(
                        self.project_id,
                        job_ref.job_id,  # pyright: ignore[reportArgumentType]
                    )
            else:
                self.job = job_ref

        elif self.state == "stopped":
            # Create if needed, then stop if in a ready state
            created: Optional[SsbJob] = None

            if not existing:
                created = self._create_job(client)
            else:
                # Check for parameter changes and update if needed
                existing = self._update_job(client, existing)

            # Use the created job or the existing/updated job
            job_ref = created if created else existing

            # Stop if in a ready state
            if job_ref and job_ref.state in SsbJobClient.READY_STATES:
                self.changed = True

                if self.module._diff:
                    # Merge state info into existing diff (if job was created or updated)
                    if created:
                        # Job was just created - add state to "after"
                        self.diff["after"]["state"] = SsbJobState.STOPPED.value
                    elif self.diff:
                        # Job was updated - merge state change into existing diff
                        self.diff["before"]["state"] = job_ref.state
                        self.diff["after"]["state"] = SsbJobState.STOPPED.value
                    else:
                        # Job existed but wasn't updated - show state change only
                        self.diff["before"] = {"state": job_ref.state}
                        self.diff["after"] = {"state": SsbJobState.STOPPED.value}

                if not self.module.check_mode:
                    stop_config = SsbJobStop(
                        savepoint=self.savepoint,
                        savepoint_path=self.savepoint_path,
                        timeout=self.stop_timeout,
                    )
                    self.savepoint_id = client.stop_job(
                        self.project_id,
                        job_ref.job_id,  # pyright: ignore[reportArgumentType]
                        stop_config,
                    )
                    # Refresh job state
                    self.job = client.describe_job(
                        self.project_id,
                        job_ref.job_id,  # pyright: ignore[reportArgumentType]
                    )
            else:
                self.job = job_ref

        elif self.state == "restarted":
            # Create if needed, stop if needed, update parameters, then restart
            created: Optional[SsbJob] = None

            if not existing:
                created = self._create_job(client)

            # Stop the existing job first if in a ready state
            if existing:
                if existing.state in SsbJobClient.READY_STATES:
                    if not self.module.check_mode:
                        stop_config = SsbJobStop(
                            savepoint=self.savepoint,
                            savepoint_path=self.savepoint_path,
                            timeout=self.stop_timeout,
                        )
                        client.stop_job(
                            self.project_id,
                            existing.job_id,  # pyright: ignore[reportArgumentType]
                            stop_config,
                        )

                # Check for parameter changes and update if needed
                existing = self._update_job(client, existing)

            # Use the created job or the existing/updated job
            job_ref = created if created else existing

            # Execute to active state
            self.changed = True

            if self.module._diff:
                # Merge state info into existing diff (if job was created or updated)
                if created:
                    # Job was just created - add state to "after"
                    self.diff["after"]["state"] = SsbJobState.RUNNING.value
                elif self.diff:
                    # Job was updated - merge state change into existing diff
                    self.diff["before"][
                        "state"
                    ] = job_ref.state  # pyright: ignore[reportOptionalMemberAccess]
                    self.diff["after"]["state"] = SsbJobState.RUNNING.value
                else:
                    # Job existed but wasn't updated - show state change only
                    self.diff["before"][
                        "state"
                    ] = job_ref.state  # pyright: ignore[reportOptionalMemberAccess]
                    self.diff["after"]["state"] = SsbJobState.RUNNING.value

            if not self.module.check_mode:
                runtime_config = SsbRuntimeConfig(
                    execution_mode=SsbExecutionMode.PER_JOB.value,
                    runtime_mode=SsbRuntimeMode.STREAMING.value,
                )
                job_config = SsbJobConfig(
                    job_name=job_ref.name,  # pyright: ignore[reportOptionalMemberAccess]
                    runtime_config=runtime_config,
                )
                start_config = SsbJobStart(
                    sql=(
                        job_ref.sql  # pyright: ignore[reportOptionalMemberAccess]
                        if job_ref.sql  # pyright: ignore[reportOptionalMemberAccess]
                        else self.sql  # pyright: ignore[reportOptionalMemberAccess]
                    ),
                    job_config=job_config,
                )
                client.start_job(
                    self.project_id,
                    job_ref.job_id,  # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]
                    start_config,
                )
                # Refresh job state
                self.job = client.describe_job(
                    self.project_id,
                    job_ref.job_id,  # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]
                )


def main():
    result = SsbJobModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
    )

    if result.job:
        output["job"] = to_dict(result.job)

    if result.savepoint_id:
        output["savepoint_id"] = result.savepoint_id

    if result.module._diff and result.diff:
        output["diff"] = result.diff

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
