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
module: ssb_table
short_description: Manage SSB project tables
description:
  - Create or delete Cloudera SSB project tables.
  - Tables define virtual tables that can be used in SQL queries.
  - Note that SSB tables cannot be updated in-place; you must delete and recreate them.
  - The module supports C(check_mode).
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
  table_name:
    description:
      - The name of the table.
      - Required when creating a new table (O(state=present)).
      - This parameter is mutually exclusive with O(id).
    type: str
    required: false
  id:
    description:
      - The unique identifier of the table.
      - This parameter is mutually exclusive with O(table_name).
      - This field is read-only and cannot be modified after creation.
    type: int
    required: false
    aliases:
      - table_id
  type:
    description:
      - The type of the table, e.g. "kafka".
      - Required when creating a new table.
    type: str
    required: false
  metadata:
    description:
      - Dictionary of metadata for the table.
      - The structure depends on the table type.
      - Required when creating a new table.
    type: dict
    required: false
  transform_code:
    description:
      - Optional transformation code for the table.
    type: str
    required: false
  transform_code_base64:
    description:
      - Whether the transform_code is base64 encoded.
    type: bool
    default: false
  update_enabled:
    description:
      - Whether to enable updates by deleting and rebuilding the table.
      - When C(true), if a table exists but has different properties, it will be deleted and recreated.
      - When C(false), if a table exists, it will not be modified even if properties differ.
      - SSB tables cannot be updated in-place; this parameter emulates updates via delete-and-rebuild.
    type: bool
    default: true
  state:
    description:
      - The desired state of the table.
      - Use C(present) to create a table.
      - Use C(absent) to delete a table.
      - See O(update_enabled) for handling updates to existing tables.
    type: str
    choices:
      - present
      - absent
    default: present
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Create a minimal SSB table
  cloudera.services.ssb_table:
    project_id: "12345"
    table_name: "my_table"
    type: "TABLE"
    metadata:
      columns:
        - name: "id"
          type: "INT"
        - name: "name"
          type: "STRING"
    state: present

- name: Create a table with transformation code
  cloudera.services.ssb_table:
    project_id: "12345"
    table_name: "transformed_table"
    type: "TABLE"
    metadata:
      columns:
        - name: "id"
          type: "INT"
    transform_code: "SELECT * FROM source_table"
    state: present

- name: Delete a table by name
  cloudera.services.ssb_table:
    project_id: "12345"
    table_name: "my_table"
    state: absent

- name: Delete a table by id
  cloudera.services.ssb_table:
    project_id: "12345"
    id: 42
    state: absent

- name: Update a table by deleting and rebuilding
  cloudera.services.ssb_table:
    project_id: "12345"
    table_name: "my_table"
    type: "TABLE"
    metadata:
      columns:
        - name: "id"
          type: "INT"
        - name: "updated_column"
          type: "STRING"
    update_enabled: true
    state: present

- name: Prevent updates to an existing table
  cloudera.services.ssb_table:
    project_id: "12345"
    table_name: "my_table"
    type: "TABLE"
    metadata:
      columns:
        - name: "id"
          type: "INT"
    update_enabled: false
    state: present
"""

RETURN = r"""
table:
  description: The table details.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The unique identifier of the table.
      type: int
      returned: always
    table_name:
      description: The name of the table.
      type: str
      returned: always
    type:
      description: The type of the table.
      type: str
      returned: always
    metadata:
      description: Dictionary of metadata for the table.
      type: dict
      returned: when available
    transform_code:
      description: Optional transformation code for the table.
      type: str
      returned: when available
    transform_code_base64:
      description: Whether the transform_code is base64 encoded.
      type: bool
      returned: when available
    project_id:
      description: The project identifier this table belongs to.
      type: str
      returned: when available
    created_at:
      description: The timestamp when the table was created.
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
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbTable,
    SsbTableClient,
)


class SsbTableModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_id=dict(type="str", required=True),
                table_name=dict(type="str", required=False),
                id=dict(type="int", required=False, aliases=["table_id"]),
                type=dict(type="str", required=False),
                metadata=dict(type="dict", required=False),
                transform_code=dict(type="str", required=False),
                transform_code_base64=dict(type="bool", required=False, default=False),
                update_enabled=dict(type="bool", required=False, default=True),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[["table_name", "id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_id = self.get_param("project_id")
        self.table_name = self.get_param("table_name")
        self.table_id = self.get_param("id")
        self.table_type = self.get_param("type")
        self.metadata = self.get_param("metadata")
        self.transform_code = self.get_param("transform_code")
        self.transform_code_base64 = self.get_param("transform_code_base64")
        self.update_enabled = self.get_param("update_enabled")
        self.state = self.get_param("state")

        # Initialize result variables
        self.changed = False
        self.diff = {"before": "", "after": ""}
        self.table: Optional[SsbTable] = None

    def process(self) -> None:
        client = SsbTableClient(self.api_client)

        existing: Optional[SsbTable] = None

        if self.table_id:
            existing = client.describe_table(self.project_id, self.table_id)
        else:
            existing_list = client.list_tables(self.project_id)
            existing = next(
                (t for t in existing_list if t.table_name == self.table_name),
                None,
            )

        if self.state == "absent":
            if existing:
                self.changed = True

                if not isinstance(existing.id, int):
                    self.module.fail_json(
                        msg="Table ID is invalid from existing table.",
                    )

                if self.module._diff:
                    self.diff = {
                        "before": to_dict(existing),
                        "after": "",
                    }

                if not self.module.check_mode:
                    client.delete_table(self.project_id, existing.id)
        elif self.state == "present":
            # Create the table if it doesn't exist
            if not existing:
                if not self.table_name:
                    self.module.fail_json(
                        msg="Parameter 'table_name' is required when creating a new table.",
                    )
                if not self.table_type:
                    self.module.fail_json(
                        msg="Parameter 'type' is required when creating a new table.",
                    )
                if not self.metadata:
                    self.module.fail_json(
                        msg="Parameter 'metadata' is required when creating a new table.",
                    )

                incoming = SsbTable(
                    table_name=self.table_name,
                    type=self.table_type,
                    metadata=self.metadata,
                    transform_code=self.transform_code,
                    transform_code_b64_encoded=self.transform_code_base64,
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {
                        "before": "",
                        "after": to_dict(incoming),
                    }

                if not self.module.check_mode:
                    self.table = client.create_table(
                        self.project_id,
                        incoming,
                    )

            # Table already exists - check if update is needed
            else:
                if not isinstance(existing.id, int):
                    self.module.fail_json(
                        msg="Table ID is invalid from existing table.",
                    )

                # Build the updated table configuration
                incoming = SsbTable(
                    table_name=existing.table_name,
                    type=self.table_type if self.table_type else existing.type,
                    metadata=self.metadata if self.metadata else existing.metadata,
                    transform_code=(
                        self.transform_code
                        if self.transform_code is not None
                        else existing.transform_code
                    ),
                    transform_code_b64_encoded=(
                        self.transform_code_base64
                        if self.transform_code_base64 is not None
                        else existing.transform_code_b64_encoded
                    ),
                    # Preserve read-only fields
                    id=existing.id,
                    project_id=existing.project_id,
                    created_at=existing.created_at,
                )

                # Compare the two table configurations
                prev_config, next_config = diff_dict(existing, incoming)

                if prev_config or next_config:
                    if self.update_enabled:
                        # Delete and rebuild
                        self.changed = True

                        if self.module._diff:
                            self.diff = {
                                "before": prev_config,
                                "after": next_config,
                            }

                        if not self.module.check_mode:
                            client.delete_table(self.project_id, existing.id)
                            self.table = client.create_table(
                                self.project_id,
                                incoming,
                            )
                    else:
                        # Changes detected but update_enabled=False
                        self.module.warn(
                            "Table differences detected but update_enabled is False. "
                            "Table cannot be updated in-place; set update_enabled=true to delete and rebuild.",
                        )
                        self.table = existing
                else:
                    self.table = existing
        else:
            self.module.fail_json(msg="Invalid state '{}'.".format(self.state))


def main():
    result = SsbTableModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        table=to_dict(result.table) if result.table else {},
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
