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
module: ranger_role
short_description: Manage roles in Apache Ranger
description:
  - Create, update, or delete roles in Apache Ranger.
author:
  - "Ronald Suplina (@rsuplina)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the Ranger role.
    required: true
    type: str
  description:
    description:
      - Description of the role.
    type: str
    required: false
  is_enabled:
    description:
      - Whether the role is enabled.
    type: bool
    default: true
    aliases:
      - enabled
  options:
    description:
      - A dictionary of additional role options.
    type: dict
    required: false
  users:
    description:
      - List of users assigned to the role.
    type: list
    elements: dict
    required: false
    suboptions:
      name:
        description:
          - Name of the user.
        type: str
        required: true
      is_admin:
        description:
          - Whether the user has administrative privileges over the role.
        type: bool
        default: false
  groups:
    description:
      - List of groups assigned to the role.
    type: list
    elements: dict
    required: false
    suboptions:
      name:
        description:
          - Name of the group.
        type: str
        required: true
      is_admin:
        description:
          - Whether the group has administrative privileges over the role.
        type: bool
        default: false
  roles:
    description:
      - List of nested roles assigned to the role.
    type: list
    elements: dict
    required: false
    suboptions:
      name:
        description:
          - Name of the nested role.
        type: str
        required: true
      is_admin:
        description:
          - Whether the nested role has administrative privileges over the role.
        type: bool
        default: false
  ensure_members_exist:
    description:
      - Whether to create users or groups referenced by the role that do not yet exist.
    type: bool
    default: false
    aliases:
      - create_non_exist_user_group
  state:
    description:
      - Whether the role should be present or absent.
    type: str
    required: false
    default: present
    choices: ["present", "absent"]
extends_documentation_fragment:
  - cloudera.services.services_client
attributes:
  check_mode:
    description:
      - This module supports check mode.
    support: full
  diff_mode:
    description:
      - This module supports diff mode.
    support: full
    platforms:
      - all
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields

- name: Create a Ranger role with users and groups
  cloudera.services.ranger_role:
    name: "test_role"
    description: "A test role"
    users:
      - name: "admin"
        is_admin: true
      - name: "alice"
    groups:
      - name: "data_engineers"

- name: Create a Ranger role with nested roles
  cloudera.services.ranger_role:
    name: "parent_role"
    description: "A role containing other roles"
    roles:
      - name: "viewer_role"
        is_admin: false
      - name: "editor_role"
        is_admin: true

- name: Create a Ranger role and auto-create non-existent users
  cloudera.services.ranger_role:
    name: "new_role"
    description: "Create non-existent users automatically"
    users:
      - name: "bob"
        is_admin: false
      - name: "charlie"
        is_admin: false
    ensure_members_exist: true

- name: Create a Ranger role and auto-create non-existent users and groups
  cloudera.services.ranger_role:
    name: "comprehensive_role"
    description: "Create non-existent users and groups automatically"
    users:
      - name: "dave"
        is_admin: true
      - name: "john"
        is_admin: false
    groups:
      - name: "analytics_team"
        is_admin: false
      - name: "security_team"
        is_admin: true
    ensure_members_exist: true

- name: Delete a Ranger role
  cloudera.services.ranger_role:
    name: "test_role"
    state: "absent"
"""

RETURN = r"""
role:
  description:
    - A dictionary containing details about the role.
  type: dict
  returned: always
  contains:
    id:
      description:
        - Unique numeric ID of the role.
      type: int
      returned: always
    guid:
      description:
        - Globally unique identifier of the role.
      type: str
      returned: always
    is_enabled:
      description:
        - Whether the role is enabled.
      type: bool
      returned: always
    created_by:
      description:
        - Username of the creator of the role.
      type: str
      returned: always
    updated_by:
      description:
        - Username of the last user who updated the role.
      type: str
      returned: always
    create_time:
      description:
        - Timestamp of when the role was created (epoch millis).
      type: int
      returned: always
    update_time:
      description:
        - Timestamp of the last update (epoch millis).
      type: int
      returned: always
    version:
      description:
        - Version number of the role definition.
      type: int
      returned: always
    name:
      description:
        - Name of the role.
      type: str
      returned: always
    description:
      description:
        - Description of the role.
      type: str
      returned: always
    options:
      description:
        - Dictionary of additional role options.
      type: dict
      returned: always
    users:
      description:
        - List of users assigned to the role.
      type: list
      elements: dict
      returned: always
      contains:
        name:
          description:
            - Name of the user.
          type: str
          returned: always
        is_admin:
          description:
            - Whether the user has administrative privileges over the role.
          type: bool
          returned: always
    groups:
      description:
        - List of groups assigned to the role.
      type: list
      elements: dict
      returned: always
      contains:
        name:
          description:
            - Name of the group.
          type: str
          returned: always
        is_admin:
          description:
            - Whether the group has administrative privileges over the role.
          type: bool
          returned: always
    roles:
      description:
        - List of nested roles assigned to the role.
      type: list
      elements: dict
      returned: always
      contains:
        name:
          description:
            - Name of the nested role.
          type: str
          returned: always
        is_admin:
          description:
            - Whether the nested role has administrative privileges over the role.
          type: bool
          returned: always
    created_by_user:
      description:
        - Username of the role creator, as recorded by Ranger.
      type: str
      returned: sometimes
"""

from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    build_from_params,
    diff_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerRole,
    RangerRoleClient,
    extract_role_params,
)


class RangerRoleModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                **RangerRole.argument_spec(),
                ensure_members_exist=dict(
                    type="bool",
                    required=False,
                    default=False,
                    aliases=["create_non_exist_user_group"],
                ),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.description = self.get_param("description")
        self.is_enabled = self.get_param("is_enabled")
        self.options = self.get_param("options")
        self.users = self.get_param("users")
        self.groups = self.get_param("groups")
        self.roles = self.get_param("roles")
        self.ensure_members_exist = self.get_param("ensure_members_exist")
        self.state = self.get_param("state")

        # Initialize result variables
        self.changed = False
        self.diff = {}
        self.role: Optional[RangerRole] = None

    def process(self) -> None:
        client = RangerRoleClient(self.api_client)

        existing: Optional[RangerRole] = None
        if self.name:
            existing = client.get_role_by_name(self.name)

        if self.state == "absent":
            if existing:
                self.changed = True

                if self.module._diff:
                    self.diff = {"before": to_dict(existing), "after": {}}

                if not self.module.check_mode:
                    client.delete_role_by_id(existing.id)

        elif self.state == "present":
            if not existing:
                incoming = build_from_params(
                    RangerRole,
                    extract_role_params(self),
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {"before": {}, "after": to_dict(incoming)}

                if not self.module.check_mode:
                    self.role = client.create_role(
                        incoming,
                        create_non_exist_user_group=self.ensure_members_exist,
                    )
                else:
                    self.role = incoming

            else:
                incoming = build_from_params(
                    RangerRole,
                    extract_role_params(self),
                    existing=existing,
                )

                prev_config, next_config = diff_dict(existing, incoming)

                if prev_config or next_config:
                    self.changed = True

                    if self.module._diff:
                        self.diff = {
                            "before": prev_config,
                            "after": next_config,
                        }

                    if not self.module.check_mode:
                        self.role = client.update_role(
                            incoming,
                            create_non_exist_user_group=self.ensure_members_exist,
                        )
                    else:
                        self.role = incoming
                else:
                    self.role = existing

        else:
            self.module.fail_json(msg=f"Invalid state '{self.state}'.")


def main():
    result = RangerRoleModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        role=to_dict(result.role) if result.role else {},
    )

    if result.module._diff:
        output.update(diff=result.diff)

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
