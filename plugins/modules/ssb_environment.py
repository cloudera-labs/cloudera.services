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
module: ssb_environment
short_description: Manage SSB project environments
description:
  - Create, update, delete, or manage Cloudera SSB project environments.
  - The module supports C(check_mode).
  - Environments store configuration properties that can be used across jobs in a project.
  - Use O(activated=true) to set an environment as the active environment for a project.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  project_id:
    description:
      - The unique identifier of the project.
      - Required for all operations.
    type: str
    required: true
  name:
    description:
      - The name of the environment.
      - Required when creating a new environment (O(state=present)).
      - This parameter is mutually exclusive with O(id).
    type: str
    required: false
  id:
    description:
      - The unique identifier of the environment.
      - This parameter is mutually exclusive with O(name).
      - This field is read-only and cannot be modified after creation.
    type: int
    required: false
    aliases:
      - environment_id
  properties:
    description:
      - Dictionary of configuration properties for the environment.
      - Each property can have a value and a sensitive flag.
      - Sensitive properties are masked in logs and API responses.
    type: dict
    required: false
    suboptions:
      value:
        description:
          - The value of the property.
        type: str
        required: true
      sensitive:
        description:
          - Whether the property value is sensitive and should be masked.
        type: bool
        required: false
        default: false
  activated:
    description:
      - Whether this environment should be the active environment for the project.
      - When C(true), the environment will be set as active after creation or update.
      - When C(false), the environment state is not changed (default behavior).
    type: bool
    required: false
    default: false
  state:
    description:
      - The desired state of the environment.
      - Use C(present) to create or update an environment.
      - Use C(absent) to delete an environment.
    type: str
    choices:
      - present
      - absent
    default: present
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Create a minimal SSB environment (no properties)
  cloudera.services.ssb_environment:
    project_id: "12345"
    name: "development"
    state: present

- name: Create an environment with properties
  cloudera.services.ssb_environment:
    project_id: "12345"
    name: "production"
    properties:
      database_url:
        value: "jdbc:postgresql://db.example.com:5432/mydb"
        sensitive: false
      database_password:
        value: "secret123"
        sensitive: true
      max_connections:
        value: "100"
        sensitive: false
    state: present

- name: Create and activate an environment
  cloudera.services.ssb_environment:
    project_id: "12345"
    name: "staging"
    properties:
      env_name:
        value: "staging"
        sensitive: false
    activated: true
    state: present

- name: Update environment properties
  cloudera.services.ssb_environment:
    project_id: "12345"
    name: "development"
    properties:
      new_setting:
        value: "new_value"
        sensitive: false
    state: present

- name: Delete an environment by name
  cloudera.services.ssb_environment:
    project_id: "12345"
    name: "development"
    state: absent

- name: Delete an environment by id
  cloudera.services.ssb_environment:
    project_id: "12345"
    id: 42
    state: absent
"""

RETURN = r"""
environment:
  description: The environment details.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The unique identifier of the environment.
      type: int
      returned: always
    name:
      description: The name of the environment.
      type: str
      returned: always
    project:
      description: The project identifier this environment belongs to.
      type: str
      returned: when available
    secured_props:
      description: Dictionary of secured properties for the environment.
      type: dict
      returned: when available
      contains:
        value:
          description: The value of the property.
          type: str
          returned: always
        sensitive:
          description: Whether the property value is sensitive.
          type: bool
          returned: when available
    created_at:
      description: The timestamp when the environment was created.
      type: str
      returned: when available
    last_edited_at:
      description: The timestamp when the environment was last edited.
      type: str
      returned: when available
    last_editor:
      description: The username of the last person to edit the environment.
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

from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    diff_dict,
    from_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbEnvironment,
    SsbEnvironmentClient,
    SsbEnvironmentRequest,
    SsbEnvironmentSecuredProperty,
    SsbProjectClient,
)


class SsbEnvironmentModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_id=dict(type="str", required=True),
                name=dict(type="str", required=False),
                id=dict(type="int", required=False, aliases=["environment_id"]),
                properties=dict(type="dict", required=False),
                activated=dict(type="bool", required=False, default=False),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[["name", "id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_id = self.get_param("project_id")
        self.name = self.get_param("name")
        self.environment_id = self.get_param("id")
        self.properties = self.get_param("properties")
        self.activated = self.get_param("activated")
        self.state = self.get_param("state")

        # Initialize result variables
        self.changed = False
        self.diff = {"before": "", "after": ""}
        self.environment: Optional[SsbEnvironment] = None

    def _build_secured_props(
        self,
        properties: Optional[Dict[str, Any]],
    ) -> Dict[str, SsbEnvironmentSecuredProperty]:
        """Convert properties dict to SsbEnvironmentSecuredProperty objects."""
        secured_props = {}
        if properties:
            for key, value in properties.items():
                if isinstance(value, dict):
                    secured_props[key] = from_dict(
                        SsbEnvironmentSecuredProperty,
                        value,
                    )
                else:
                    # If just a string value, wrap it
                    secured_props[key] = SsbEnvironmentSecuredProperty(
                        value=str(value),
                        sensitive=False,
                    )
        return secured_props

    def process(self) -> None:
        client = SsbEnvironmentClient(self.api_client)

        existing: Optional[SsbEnvironment] = None

        if self.environment_id:
            existing = client.describe_environment(self.project_id, self.environment_id)
        else:
            existing_list = client.list_environments(self.project_id)
            existing = next((e for e in existing_list if e.name == self.name), None)

        if self.state == "absent":
            if existing:
                self.changed = True

                if not isinstance(existing.id, int):
                    self.module.fail_json(
                        msg="Environment ID is invalid from existing environment.",
                    )

                # Check if environment is already active
                project_client = SsbProjectClient(self.api_client)
                project = project_client.describe_project(self.project_id)

                if not project:
                    self.module.fail_json(
                        msg=f"Project {self.project_id} not found.",
                    )

                if self.module._diff:
                    self.diff = {
                        "before": to_dict(existing),
                        "after": "",
                    }

                if not self.module.check_mode:
                    # Deactivate if active in order to avoid a failed internal state (deleting a project with an active environment that also has been deleted)
                    if (
                        isinstance(project.active_environment, int)
                        and project.active_environment == existing.id
                    ):
                        self.changed = True
                        if not self.module.check_mode:
                            client.deactivate_environment(
                                self.project_id,
                            )
                    client.delete_environment(self.project_id, existing.id)
        elif self.state == "present":
            # Create the environment if it doesn't exist
            if not existing:
                if not self.name:
                    self.module.fail_json(
                        msg="Parameter 'name' is required when creating a new environment.",
                    )

                secured_props = self._build_secured_props(self.properties)

                incoming = SsbEnvironmentRequest(
                    name=self.name,
                    properties=secured_props,
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {
                        "before": "",
                        "after": to_dict(incoming),
                    }

                if not self.module.check_mode:
                    self.environment = client.create_environment(
                        self.project_id,
                        incoming,
                    )

            # Update the environment if needed
            else:
                if not isinstance(existing.id, int):
                    self.module.fail_json(
                        msg="Environment ID is invalid from existing environment.",
                    )

                # Build environment requests for comparison
                current = SsbEnvironmentRequest(
                    name=existing.name,
                    properties=existing.secured_props,
                )

                # Use existing properties if none specified
                secured_props = (
                    self._build_secured_props(self.properties)
                    if self.properties
                    else existing.secured_props
                )
                incoming = SsbEnvironmentRequest(
                    name=existing.name,
                    properties=secured_props,
                )

                # Compare the two environment configurations
                prev_config, next_config = diff_dict(current, incoming)

                if prev_config or next_config:
                    self.changed = True

                    if self.module._diff:
                        self.diff = {
                            "before": prev_config,
                            "after": next_config,
                        }

                    if not self.module.check_mode:
                        self.environment = client.update_environment(
                            self.project_id,
                            existing.id,
                            incoming,
                        )
                else:
                    self.environment = existing

            # Handle activation
            if self.activated:
                if not self.environment or not isinstance(self.environment.id, int):
                    self.module.fail_json(
                        msg="Environment ID is invalid for activation.",
                    )

                # Check if environment is already active
                project_client = SsbProjectClient(self.api_client)
                project = project_client.describe_project(self.project_id)

                if not project:
                    self.module.fail_json(
                        msg=f"Project {self.project_id} not found.",
                    )

                # Only activate if not already active
                if (
                    not isinstance(project.active_environment, int)
                    or project.active_environment != self.environment.id
                ):
                    self.changed = True
                    if not self.module.check_mode:
                        client.activate_environment(
                            self.project_id,
                            self.environment.id,
                        )
        else:
            self.module.fail_json(msg="Invalid state '{}'.".format(self.state))


def main():
    result = SsbEnvironmentModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        environment=to_dict(result.environment) if result.environment else {},
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
