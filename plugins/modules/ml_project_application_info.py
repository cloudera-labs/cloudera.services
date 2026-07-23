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
module: ml_project_application_info
short_description: Retrieve information about Cloudera Machine Learning (CML) project applications
description:
  - Retrieve information about one or more Cloudera Machine Learning (CML) project applications.
  - The module can list all applications within a project or filter by a number of criteria.
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
      - The unique identifier of a single application to retrieve.
    type: str
    required: false
    aliases:
      - application_id
  name:
    description:
      - Filter the applications by name.
    type: str
    required: false
  kernel:
    description:
      - Filter the applications by kernel.
    type: str
    required: false
  subdomain:
    description:
      - Filter the applications by DNS subdomain.
    type: str
    required: false
  desc:
    description:
      - Filter the applications by description.
    type: str
    required: false
    aliases:
      - description
  script:
    description:
      - Filter the applications by entrypoint script.
    type: str
    required: false
  status:
    description:
      - Filter the applications by runtime state.
    type: str
    required: false
    choices:
      - running
      - stopping
      - stopped
      - starting
      - failed
  auth:
    description:
      - Filter the applications by whether user authentication is required.
      - When V(false), only publicly accessible applications are returned.
    type: bool
    required: false
    aliases:
      - auth_enabled
  creator:
    description:
      - Filter the applications by creator details.
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
- name: List all applications within a project
  cloudera.services.ml_project_application_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
  register: all_applications

- name: Get a single application by id
  cloudera.services.ml_project_application_info:
    project_id: "{{ project_id }}"
    id: "{{ application_id }}"

- name: List applications created by a user
  cloudera.services.ml_project_application_info:
    project_name: my-project
    creator:
      username: jdoe

- name: List stopped applications
  cloudera.services.ml_project_application_info:
    project_name: my-project
    status: stopped
"""

RETURN = r"""
applications:
  description: List of CML applications.
  returned: always
  type: list
  elements: dict
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

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlApplication,
    MlApplicationClient,
    MlProject,
    MlProjectClient,
    validate_project_id,
)


class MlProjectApplicationInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["application_id"]),
                name=dict(type="str", required=False),
                kernel=dict(type="str", required=False),
                subdomain=dict(type="str", required=False),
                desc=dict(type="str", required=False, aliases=["description"]),
                script=dict(type="str", required=False),
                status=dict(
                    type="str",
                    required=False,
                    choices=["running", "stopping", "stopped", "starting", "failed"],
                ),
                auth=dict(type="bool", required=False, aliases=["auth_enabled"]),
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
        self.subdomain = self.get_param("subdomain")
        self.desc = self.get_param("desc")
        self.script = self.get_param("script")
        self.status = self.get_param("status")
        self.auth = self.get_param("auth")
        self.creator = self.get_param("creator")

        # Initialize result variables
        self.application_list: List[MlApplication] = []

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

    def _matches(self, app: MlApplication) -> bool:
        checks = {
            "name": self.name,
            "kernel": self.kernel,
            "subdomain": self.subdomain,
            "description": self.desc,
            "script": self.script,
            "status": self.status,
        }
        for attr, wanted in checks.items():
            if wanted is not None and getattr(app, attr) != wanted:
                return False

        if self.auth is not None:
            if app.bypass_authentication != (not self.auth):
                return False

        if self.creator:
            creator = app.creator
            if not isinstance(creator, dict):
                return False
            for key, wanted in self.creator.items():
                if wanted is not None and creator.get(key) != wanted:
                    return False

        return True

    def process(self) -> None:
        project_id = self._resolve_project_id()
        client = MlApplicationClient(self.api_client)

        if self.id:
            app = client.describe_application(project_id, self.id)
            if app:
                self.application_list.append(app)
            return

        self.application_list = [
            app for app in client.list_applications(project_id) if self._matches(app)
        ]


def main():
    result = MlProjectApplicationInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        applications=[to_dict(app) for app in result.application_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
