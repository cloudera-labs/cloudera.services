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
module: ml_project_application
short_description: Manage a Cloudera Machine Learning (CML) project application
description:
  - Create, update, restart, stop, or delete a Cloudera Machine Learning (CML) project application.
  - The V(restarted) and V(stopped) states imply V(present); if the application does not exist it is created (requiring O(subdomain), O(script), and O(runtime)) and then transitioned to the requested state.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  project_name:
    description:
      - The name of the enclosing project for the application.
      - Mutually exclusive with O(project_id).
    type: str
    required: false
  project_id:
    description:
      - The unique identifier of the enclosing project for the application.
      - Mutually exclusive with O(project_name).
    type: str
    required: false
  name:
    description:
      - The name of the application.
      - Required when creating an application.
      - Mutually exclusive with O(id).
    type: str
    required: false
  id:
    description:
      - The unique identifier of an existing application.
      - Mutually exclusive with O(name).
    type: str
    required: false
    aliases:
      - application_id
  auth:
    description:
      - Whether user authentication is required to access the application.
      - When V(false), the application is publicly accessible.
    type: bool
    required: false
    aliases:
      - auth_enabled
  cpu:
    description:
      - The vCPU allocated to the application.
    type: float
    required: false
  desc:
    description:
      - The description of the application.
    type: str
    required: false
    aliases:
      - description
  env:
    description:
      - Environment variables to set on the application.
      - On update, the provided variables are merged with the application's existing variables.
    type: dict
    required: false
    aliases:
      - env_vars
  kernel:
    description:
      - The kernel to use for the application.
    type: str
    required: false
    choices:
      - python3
      - python2
      - r
      - scala
  memory:
    description:
      - The RAM allocated to the application, in GB.
    type: float
    required: false
  gpu:
    description:
      - The count of Nvidia GPUs allocated to the application.
    type: int
    required: false
    aliases:
      - nvidia_gpu
  addons:
    description:
      - A list of runtime addon identifiers for the application.
    type: list
    elements: str
    required: false
    aliases:
      - runtime_addons
      - runtime_addon_identifiers
  runtime:
    description:
      - The container runtime identifier for the application.
      - Required when creating an application.
    type: str
    required: false
    aliases:
      - runtime_image_id
      - runtime_identifier
  script:
    description:
      - The entrypoint script for the application.
      - Required when creating an application.
    type: str
    required: false
  subdomain:
    description:
      - The DNS subdomain for the application.
      - Required when creating an application.
    type: str
    required: false
  state:
    description:
      - The declarative state of the application.
    type: str
    required: false
    default: present
    choices:
      - present
      - restarted
      - stopped
      - absent
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Create an application
  cloudera.services.ml_project_application:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    name: my-application
    subdomain: my-app
    script: app.py
    runtime: "{{ runtime_id }}"
    auth: true
    env:
      LOG_LEVEL: debug
    state: present

- name: Restart an application
  cloudera.services.ml_project_application:
    project_id: "{{ project_id }}"
    id: "{{ application_id }}"
    state: restarted

- name: Stop an application
  cloudera.services.ml_project_application:
    project_id: "{{ project_id }}"
    name: my-application
    state: stopped

- name: Delete an application
  cloudera.services.ml_project_application:
    project_id: "{{ project_id }}"
    id: "{{ application_id }}"
    state: absent
"""

RETURN = r"""
application:
  description: The CML application details.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the application.
      type: str
      returned: always
    name:
      description: The name of the application.
      type: str
      returned: always
    project_id:
      description: The identifier of the enclosing project.
      type: str
      returned: when available
    subdomain:
      description: The DNS subdomain of the application.
      type: str
      returned: when available
    description:
      description: The description of the application.
      type: str
      returned: when available
    script:
      description: The entrypoint script for the application.
      type: str
      returned: when available
    kernel:
      description: The kernel for the application.
      type: str
      returned: when available
    cpu:
      description: The vCPU allocated to the application.
      type: float
      returned: when available
    memory:
      description: The RAM allocated to the application, in GB.
      type: float
      returned: when available
    nvidia_gpu:
      description: The count of Nvidia GPUs allocated to the application.
      type: int
      returned: when available
    runtime_identifier:
      description: The container runtime identifier for the application.
      type: str
      returned: when available
    runtime_addon_identifiers:
      description: The runtime addon identifiers for the application.
      type: list
      elements: str
      returned: when available
    bypass_authentication:
      description: Whether application access is public (unauthenticated).
      type: bool
      returned: when available
    environment:
      description: The environment variables of the application.
      type: dict
      returned: when available
    status:
      description: The current runtime state of the application.
      type: str
      returned: when available
    creator:
      description: Details of the user that created the application.
      type: dict
      returned: when available
    created_at:
      description: The timestamp when the application was created.
      type: str
      returned: when available
    updated_at:
      description: The timestamp when the application was last updated.
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
from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    diff_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlApplication,
    MlApplicationClient,
    MlProject,
    MlProjectClient,
    validate_project_id,
    validate_subdomain,
)

CREATE_REQUIRED = ["subdomain", "script", "runtime"]


class MlProjectApplicationModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                name=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["application_id"]),
                auth=dict(type="bool", required=False, aliases=["auth_enabled"]),
                cpu=dict(type="float", required=False),
                desc=dict(type="str", required=False, aliases=["description"]),
                env=dict(type="dict", required=False, aliases=["env_vars"]),
                kernel=dict(
                    type="str",
                    required=False,
                    choices=["python3", "python2", "r", "scala"],
                ),
                memory=dict(type="float", required=False),
                gpu=dict(type="int", required=False, aliases=["nvidia_gpu"]),
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
                script=dict(type="str", required=False),
                subdomain=dict(type="str", required=False),
                state=dict(
                    type="str",
                    required=False,
                    choices=["present", "restarted", "stopped", "absent"],
                    default="present",
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
        self.auth = self.get_param("auth")
        self.cpu = self.get_param("cpu")
        self.desc = self.get_param("desc")
        self.env = self.get_param("env")
        self.kernel = self.get_param("kernel")
        self.memory = self.get_param("memory")
        self.gpu = self.get_param("gpu")
        self.addons = self.get_param("addons")
        self.runtime = self.get_param("runtime")
        self.script = self.get_param("script")
        self.subdomain = self.get_param("subdomain")
        self.state = self.get_param("state")

        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.application: Optional[MlApplication] = None

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

    def _merged_environment(self, existing: MlApplication) -> Any:
        if self.env is None:
            return existing.environment
        current = existing.environment
        if not isinstance(current, dict):
            current = {}
        return {**current, **self.env}

    def _incoming_application(self) -> MlApplication:
        incoming = MlApplication(name=self.name)
        if self.desc is not None:
            incoming.description = self.desc
        if self.script is not None:
            incoming.script = self.script
        if self.subdomain is not None:
            incoming.subdomain = self.subdomain
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
            incoming.runtime_addon_identifiers = self.addons
        if self.auth is not None:
            incoming.bypass_authentication = not self.auth
        if self.env is not None:
            incoming.environment = self.env
        return incoming

    def process(self) -> None:
        project_id = self._resolve_project_id()
        client = MlApplicationClient(self.api_client)

        existing: Optional[MlApplication] = None
        if self.id:
            existing = client.describe_application(project_id, self.id)
        else:
            applications = client.list_applications(project_id)
            existing = next(
                (a for a in applications if a.name == self.name),
                None,
            )
            # Subdomains are unique within the workspace, so fall back to a
            # subdomain match. This keeps re-applies idempotent and avoids a
            # create that would violate the unique-subdomain constraint.
            if existing is None and self.subdomain is not None:
                existing = next(
                    (a for a in applications if a.subdomain == self.subdomain),
                    None,
                )

        if self.subdomain is not None and not validate_subdomain(self.subdomain):
            self.module.fail_json(msg="Invalid subdomain format")

        if self.state == "absent":
            if existing:
                if not isinstance(existing.id, str):
                    self.module.fail_json(
                        msg="Application ID is invalid from existing application.",
                    )
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = to_dict(existing)
                if not self.module.check_mode:
                    client.delete_application(project_id, existing.id)
            return

        # present, restarted, and stopped all imply the application should exist.
        if not existing:
            missing = [k for k in CREATE_REQUIRED if self.get_param(k) is None]
            if missing:
                self.module.fail_json(
                    msg="Missing required parameters for creation: %s"
                    % ", ".join(sorted(missing)),
                )

            incoming = self._incoming_application()
            self.changed = True
            if self.module._diff:
                self.diff["after"] = to_dict(incoming)
            if not self.module.check_mode:
                self.application = client.create_application(project_id, incoming)
            else:
                self.application = incoming
        else:
            # Update an existing application
            desired = replace(
                existing,
                description=(
                    self.desc if self.desc is not None else existing.description
                ),
                script=self.script if self.script is not None else existing.script,
                kernel=self.kernel if self.kernel is not None else existing.kernel,
                cpu=self.cpu if self.cpu is not None else existing.cpu,
                memory=self.memory if self.memory is not None else existing.memory,
                nvidia_gpu=self.gpu if self.gpu is not None else existing.nvidia_gpu,
                runtime_identifier=(
                    self.runtime
                    if self.runtime is not None
                    else existing.runtime_identifier
                ),
                runtime_addon_identifiers=(
                    self.addons
                    if self.addons is not None
                    else existing.runtime_addon_identifiers
                ),
                bypass_authentication=(
                    (not self.auth)
                    if self.auth is not None
                    else existing.bypass_authentication
                ),
                environment=self._merged_environment(existing),
            )

            prev_config, next_config = diff_dict(existing, desired)

            self.application = existing
            if prev_config or next_config:
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = prev_config
                    self.diff["after"] = next_config
                if not self.module.check_mode:
                    self.application = client.update_application(project_id, desired)
                else:
                    self.application = desired

        # Apply lifecycle transitions to the resolved (created or updated) application.
        if self.state in ("restarted", "stopped") and not self.module.check_mode:
            if self.application is None or not isinstance(self.application.id, str):
                self.module.fail_json(
                    msg="Application ID is invalid from resolved application.",
                )
            app_id = self.application.id
            self.changed = True
            if self.state == "restarted":
                self.application = client.restart_application(project_id, app_id)
            else:
                self.application = client.stop_application(project_id, app_id)


def main():
    result = MlProjectApplicationModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        application=to_dict(result.application) if result.application else {},
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
