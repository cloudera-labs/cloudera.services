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
module: ranger_role_info
short_description: Retrieve role details from Apache Ranger
description:
  - Retrieve details of a specific role by ID or name.
  - If no identifier is provided, retrieves all roles.
  - The module supports C(check_mode).
version_added: "1.1.0"
author:
  - "Ronald Suplina (@rsuplina)"
options:
  name:
    description:
      - Name of the Ranger role.
      - This parameter is mutually exclusive with O(id).
    type: str
    required: false
  id:
    description:
      - ID of the Ranger role to retrieve.
      - This parameter is mutually exclusive with O(name).
    type: int
    required: false
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields

- name: Retrieve role by ID
  cloudera.services.ranger_role_info:
    id: 5

- name: Retrieve role by name
  cloudera.services.ranger_role_info:
    name: "test_role"

- name: Retrieve all roles
  cloudera.services.ranger_role_info:
"""

RETURN = r"""
roles:
  description:
    - List of roles matching the given criteria, or all roles if no filter is applied.
  type: list
  elements: dict
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

from typing import Any, Dict, List

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerRole,
    RangerRoleClient,
)


class RangerRoleInfoModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                name=dict(type="str", required=False),
                id=dict(type="int", required=False),
            ),
            mutually_exclusive=[["name", "id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.id = self.get_param("id")

        # Initialize result variables
        self.role_list: List[RangerRole] = []

    def process(self) -> None:
        client = RangerRoleClient(self.api_client)

        if self.id:
            role = client.get_role_by_id(role_id=self.id)
            if role:
                self.role_list.append(role)

        elif self.name:
            role = client.get_role_by_name(role_name=self.name)
            if role:
                self.role_list.append(role)

        else:
            self.role_list.extend(client.list_roles())


def main():
    result = RangerRoleInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        roles=[to_dict(role) for role in result.role_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
