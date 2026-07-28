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
module: ssb_user
short_description: Manage the current SSB user's settings
description:
  - Manage settings for the currently authenticated Cloudera SSB user.
  - Set the user's active project.
  - Change the user's password.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  project_id:
    description:
      - The project ID to set as the user's active project.
      - When provided, sets this project as the current active project for the user.
    type: str
    required: false
  current_password:
    description:
      - The current password for the user.
      - Required when changing the password (when O(new_password) is provided).
    type: str
    required: false
  new_password:
    description:
      - The new password to set for the user.
      - When provided, changes the user's password.
      - O(current_password) must also be provided.
    type: str
    required: false
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Set the user's active project
  cloudera.services.ssb_user:
    project_id: "12345"
  register: user_result

- name: Change the user's password
  cloudera.services.ssb_user:
    current_password: "old-password"
    new_password: "new-secure-password"
  register: password_result
"""

RETURN = r"""
user:
    description: The updated user information.
    returned: always
    type: dict
    contains:
        id:
            description: The unique identifier of the user.
            type: str
            returned: always
        username:
            description: The username of the user.
            type: str
            returned: always
        email:
            description: The email address of the user.
            type: str
            returned: when available
        first_name:
            description: The first name of the user.
            type: str
            returned: when available
        last_name:
            description: The last name of the user.
            type: str
            returned: when available
        is_active:
            description: Whether the user account is active.
            type: bool
            returned: when available
        primary_project_id:
            description: The ID of the user's primary project.
            type: str
            returned: when available
        project_id:
            description: The ID of the user's currently active project.
            type: str
            returned: when available
        keytab:
            description: Base64-encoded keytab data for the user.
            type: str
            returned: when available
        keytab_principal:
            description: The Kerberos principal associated with the user's keytab.
            type: str
            returned: when available
        keytab_last_modified:
            description: Timestamp of when the keytab was last modified.
            type: str
            returned: when available
        granted_authorities:
            description: List of roles and authorities granted to the user.
            type: list
            elements: str
            returned: when available
sdk_out:
    description: Returns the captured CDP SDK log.
    returned: when supported
    type: str
sdk_out_lines:
    description: Returns a list of each line of the captured CDP SDK log.
    returned: when supported
    type: list
    elements: str
"""

from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    to_dict,
    diff_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbUser,
    SsbUserClient,
)


class SsbUserModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_id=dict(type="str", required=False),
                current_password=dict(type="str", required=False, no_log=True),
                new_password=dict(type="str", required=False, no_log=True),
            ),
            required_together=[["current_password", "new_password"]],
            supports_check_mode=True,
        )

        # Get parameters
        self.project_id = self.get_param("project_id")
        self.current_password = self.get_param("current_password")
        self.new_password = self.get_param("new_password")

        # Initialize result variables
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.user: Optional[SsbUser] = None

    def process(self) -> None:
        client = SsbUserClient(self.api_client)

        # Get current user state
        existing = client.get_current_user()

        # Track if any changes are made
        changes_made = False

        # Handle project change
        if self.project_id and self.project_id != existing.project_id:
            changes_made = True

            if self.module._diff:
                self.diff["before"].update({"project_id": existing.project_id})
                self.diff["after"].update({"project_id": self.project_id})

            if not self.module.check_mode:
                existing = client.set_current_user_project(self.project_id)

        # Handle password change
        if self.current_password and self.new_password:
            changes_made = True

            if self.module._diff:
                self.diff["before"].update({"password": "***"})
                self.diff["after"].update({"password": "***"})

            if not self.module.check_mode:
                existing = client.set_current_user_password(
                    self.current_password,
                    self.new_password,
                )

        self.changed = changes_made
        self.user = existing


def main():
    result = SsbUserModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        user=to_dict(result.user) if result.user else {},
        diff=(
            result.diff
            if result.diff["before"] or result.diff["after"]
            else {"before": "", "after": ""}
        ),
    )

    if result.diff:
        output["diff"] = result.diff

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
