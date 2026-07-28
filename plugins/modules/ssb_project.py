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
module: ssb_project
short_description: Manage SSB projects
description:
  - Create, delete, or manage Cloudera SSB projects.
  - The module supports C(check_mode).
  - Project fields such as O(name), O(description), and O(mv_prefix) are immutable after creation.
  - Updates to O(sync_source_config) are not yet implemented.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  name:
    description:
      - The name of the project.
      - Required when creating a new project (O(state=present) or O(state=synced)).
      - This parameter is mutually exclusive with O(id).
      - This field is immutable after project creation.
    type: str
    required: false
  id:
    description:
      - The unique identifier of the project.
      - This parameter is mutually exclusive with O(name).
      - This field is read-only and cannot be modified after creation.
    type: str
    required: false
    aliases:
      - project_id
  description:
    description:
      - A description of the project.
      - This field is immutable after project creation.
    type: str
    required: false
  mv_prefix:
    description:
      - The materialized view prefix for the project.
      - This field is immutable after project creation.
    type: str
    required: false
  sync_source_config:
    description:
      - Configuration for the project's sync source.
      - Updates to this field are not yet implemented.
    type: dict
    required: false
    suboptions:
      type:
        description:
          - The type of sync source.
        type: str
        required: true
      clone_url:
        description:
          - The URL to clone the sync source repository.
        type: str
        required: true
      branch:
        description:
          - The branch to sync from the repository.
        type: str
        required: false
      allow_deletions:
        description:
          - Whether to allow deletions from the sync source.
        type: bool
        required: false
      credential:
        description:
          - Credentials for accessing the sync source.
        type: dict
        required: false
        suboptions:
          type:
            description:
              - The type of credential.
              - Use C(basic) for username/password authentication.
              - Use C(ssh) for SSH key-based authentication.
            type: str
            required: true
            choices:
              - basic
              - ssh
          username:
            description:
              - The username for authentication.
              - Required when O(sync_source_config.credential.type=basic).
            type: str
            required: false
          password:
            description:
              - The password for authentication.
              - Required when O(sync_source_config.credential.type=basic).
            type: str
            required: false
          ssh_private_key:
            description:
              - The SSH private key for authentication.
              - Required when O(sync_source_config.credential.type=ssh).
            type: str
            required: false
          ssh_public_key:
            description:
              - The SSH public key for authentication.
              - Required when O(sync_source_config.credential.type=ssh).
            type: str
            required: false
          ssh_passphrase:
            description:
              - The passphrase for the SSH key.
              - Optional when O(sync_source_config.credential.type=ssh).
            type: str
            required: false
  state:
    description:
      - The desired state of the project.
      - Use C(present) to create a project if it does not exist.
      - Use C(absent) to delete a project.
      - Use C(synced) to synchronize with external source (not yet implemented).
    type: str
    choices:
      - present
      - absent
      - synced
    default: present
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Create a minimal SSB project
  cloudera.services.ssb_project:
    name: "my-project"
    state: present

- name: Create an SSB project with description and mv_prefix
  cloudera.services.ssb_project:
    name: "my-project"
    description: "My analytics project"
    mv_prefix: "analytics_"
    state: present

- name: Ensure project exists (idempotent)
  cloudera.services.ssb_project:
    name: "my-project"
    state: present

- name: Delete an SSB project by name
  cloudera.services.ssb_project:
    name: "my-project"
    state: absent

- name: Delete an SSB project by id
  cloudera.services.ssb_project:
    id: "12345"
    state: absent
"""

RETURN = r"""
project:
  description: The project details.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The unique identifier of the project.
      type: int
      returned: always
    name:
      description: The name of the project.
      type: str
      returned: always
    description:
      description: A description of the project.
      type: str
      returned: when available
    mv_prefix:
      description: The materialized view prefix for the project.
      type: str
      returned: when available
    active_environment:
      description: The ID of the active environment for the project.
      type: int
      returned: when available
    sync_source_config:
      description: Configuration for the project's sync source.
      type: dict
      returned: when available
      contains:
        type:
          description: The type of sync source.
          type: str
          returned: always
        clone_url:
          description: The URL to clone the sync source repository.
          type: str
          returned: always
        branch:
          description: The branch to sync from the repository.
          type: str
          returned: when available
        allow_deletions:
          description: Whether to allow deletions from the sync source.
          type: bool
          returned: when available
        credential:
          description: Credentials for accessing the sync source.
          type: dict
          returned: when available
          contains:
            type:
              description: The type of credential (e.g., password, ssh).
              type: str
              returned: always
            username:
              description: The username for authentication.
              type: str
              returned: when available
            password:
              description: The password for authentication.
              type: str
              returned: when available
            ssh_private_key:
              description: The SSH private key for authentication.
              type: str
              returned: when available
            ssh_public_key:
              description: The SSH public key for authentication.
              type: str
              returned: when available
            ssh_passphrase:
              description: The passphrase for the SSH key.
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
    NULLABLE,
    diff_dict,
    from_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbProject,
    SsbProjectClient,
    SsbSyncSourceConfig,
)


class SsbProjectModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                **SsbProject.argument_spec(),
                state=dict(
                    type="str",
                    choices=["present", "absent", "synced"],
                    default="present",
                ),
            ),
            mutually_exclusive=[["name", "id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.project_id = self.get_param("id")
        self.state = self.get_param("state")
        self.description = self.get_param("description")
        self.mv_prefix = self.get_param("mv_prefix")
        self.sync_source_config = self.get_param("sync_source_config")

        # Initialize result variables
        self.changed = False
        self.diff = {"before": "", "after": ""}
        self.project: Optional[SsbProject] = None

    def process(self) -> None:
        client = SsbProjectClient(self.api_client)

        existing: Optional[SsbProject] = None

        # Look up existing project by id or name
        if self.project_id:
            existing = client.describe_project(self.project_id)
        else:
            existing_list = client.list_projects()
            existing = next((p for p in existing_list if p.name == self.name), None)

        if self.state == "absent":
            if existing:
                self.changed = True

                if self.module._diff:
                    self.diff = {
                        "before": to_dict(existing),
                        "after": "",
                    }

                if not self.module.check_mode:
                    client.delete_project(existing)
        elif self.state == "synced":
            self.module.fail_json(msg="State 'synced' is not yet implemented.")
        elif self.state == "present":
            # Create the project if it does not exist
            if not existing:
                # Validate name is provided for creation
                if not self.name:
                    self.module.fail_json(
                        msg="Parameter 'name' is required when creating a new project.",
                    )

                incoming = SsbProject(
                    name=self.name,
                    description=self.description,
                    mv_prefix=self.mv_prefix,
                    sync_source_config=self.sync_source_config,
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {
                        "before": "",
                        "after": to_dict(incoming),
                    }

                if not self.module.check_mode:
                    self.project = client.create_project(incoming)
            # Update the project if needed
            else:
                # Check for immutable field changes that should fail
                errors = []

                # name and id are exclusive; cannot change name if retrieved by id
                # if self.name and self.name != existing.name:
                #     errors.append("name")

                if self.description and self.description != existing.description:
                    errors.append("description")

                if self.mv_prefix and self.mv_prefix != existing.mv_prefix:
                    errors.append("mv_prefix")

                if errors:
                    self.module.fail_json(
                        msg=f"Cannot update immutable project fields: {', '.join(errors)}.",
                    )

                # Check for sync_source_config changes
                if self.sync_source_config:
                    if existing.sync_source_config is not NULLABLE:
                        prev_config, next_config = diff_dict(
                            existing.sync_source_config,
                            from_dict(SsbSyncSourceConfig, self.sync_source_config),
                        )

                        if prev_config or next_config:
                            if self.module._diff:
                                self.diff = {
                                    "before": {"sync_source_config": prev_config},
                                    "after": {"sync_source_config": next_config},
                                }
                    else:
                        if self.module._diff:
                            self.diff = {
                                "before": {"sync_source_config": None},
                                "after": {
                                    "sync_source_config": self.sync_source_config,
                                },
                            }

                    self.module.fail_json(
                        msg="Updating sync_source_config is not yet implemented.",
                    )

                # No changes detected
                self.project = existing
        else:
            self.module.fail_json(msg="Invalid state '{}'.".format(self.state))


def main():
    result = SsbProjectModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        project=to_dict(result.project) if result.project else {},
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
