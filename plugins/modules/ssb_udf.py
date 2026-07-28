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
module: ssb_udf
short_description: Manage SSB User Defined Functions (UDFs)
description:
  - Create, update, or delete Cloudera SSB User Defined Functions (UDFs).
  - UDFs allow custom functions to be used in SQL queries.
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
  name:
    description:
      - The name of the UDF.
      - Required when creating a new UDF (O(state=present)).
      - This parameter is mutually exclusive with O(id).
    type: str
    required: false
  id:
    description:
      - The unique identifier of the UDF.
      - This parameter is mutually exclusive with O(name).
      - This field is read-only and cannot be modified after creation.
    type: int
    required: false
    aliases:
      - udf_id
  language:
    description:
      - The language of the UDF.
      - Required when creating a new UDF.
      - Supported values are C(JAVASCRIPT) and C(PYTHON).
    type: str
    required: false
    choices:
      - JAVASCRIPT
      - PYTHON
  code:
    description:
      - The code for the UDF.
      - Required when creating a new UDF.
      - For JavaScript UDFs, use standard JavaScript function syntax.
      - For Python UDFs, use standard Python function syntax.
    type: str
    required: false
  output_type:
    description:
      - The output data type of the UDF.
      - Required when creating a new UDF.
      - For JavaScript UDFs, valid types are STRING, BOOLEAN, INT, BIGINT, FLOAT, DECIMAL, TIMESTAMP, DATE.
      - For Python UDFs, use PYTHON_INFERRED.
    type: str
    required: false
  input_types:
    description:
      - List of input parameter data types for the UDF.
      - Required when creating a new UDF.
      - For JavaScript UDFs, valid types are STRING, BOOLEAN, INT, BIGINT, FLOAT, DECIMAL, TIMESTAMP, DATE.
      - For Python UDFs, use a list containing only STRING.
    type: list
    elements: str
    required: false
  description:
    description:
      - Optional description of the UDF.
    type: str
    required: false
  state:
    description:
      - The desired state of the UDF.
      - Use C(present) to create or update a UDF.
      - Use C(absent) to delete a UDF.
    type: str
    choices:
      - present
      - absent
    default: present
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Create a JavaScript UDF
  cloudera.services.ssb_udf:
    project_id: "12345"
    name: "upperCase"
    language: "JAVASCRIPT"
    code: "function upperCase(str) { return str.toUpperCase(); }"
    output_type: "STRING"
    input_types:
      - "STRING"
    description: "Converts a string to uppercase"
    state: present

- name: Create a Python UDF
  cloudera.services.ssb_udf:
    project_id: "12345"
    name: "process_data"
    language: "PYTHON"
    code: |
      def process_data(data):
          return data.upper()
    output_type: "PYTHON_INFERRED"
    input_types:
      - "STRING"
    description: "Process data with Python"
    state: present

- name: Update a UDF
  cloudera.services.ssb_udf:
    project_id: "12345"
    name: "upperCase"
    code: "function upperCase(str) { return str.toUpperCase() + '!'; }"
    state: present

- name: Delete a UDF by name
  cloudera.services.ssb_udf:
    project_id: "12345"
    name: "upperCase"
    state: absent

- name: Delete a UDF by id
  cloudera.services.ssb_udf:
    project_id: "12345"
    id: 42
    state: absent
"""

RETURN = r"""
udf:
  description: The UDF details.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The unique identifier of the UDF.
      type: int
      returned: always
    name:
      description: The name of the UDF.
      type: str
      returned: always
    language:
      description: The language of the UDF (JAVASCRIPT or PYTHON).
      type: str
      returned: always
    code:
      description: The code for the UDF.
      type: str
      returned: when available
    output_type:
      description: The output data type of the UDF.
      type: str
      returned: always
    input_types:
      description: List of input parameter data types.
      type: list
      elements: str
      returned: when available
    description:
      description: The description of the UDF.
      type: str
      returned: when available
    project_id:
      description: The project identifier this UDF belongs to.
      type: str
      returned: when available
    created_at:
      description: The timestamp when the UDF was created.
      type: str
      returned: when available
    updated_at:
      description: The timestamp when the UDF was last updated.
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
    SsbUdf,
    SsbUdfClient,
)

# TODO Implement support for Java UDFs when the API supports it, which will require additional parameters for Java class name, jar file, and file name along with file upload.


class SsbUdfModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_id=dict(type="str", required=True),
                name=dict(type="str", required=False),
                id=dict(type="int", required=False, aliases=["udf_id"]),
                language=dict(
                    type="str",
                    required=False,
                    choices=["JAVASCRIPT", "PYTHON"],
                ),
                code=dict(type="str", required=False),
                java_class_name=dict(type="str", required=False),
                jar_file=dict(type="str", required=False),
                file_name=dict(type="str", required=False),
                output_type=dict(type="str", required=False),
                input_types=dict(type="list", elements="str", required=False),
                description=dict(type="str", required=False),
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
        self.udf_id = self.get_param("id")
        self.language = self.get_param("language")
        self.code = self.get_param("code")
        self.output_type = self.get_param("output_type")
        self.input_types = self.get_param("input_types")
        self.description = self.get_param("description")
        self.java_class_name = self.get_param("java_class_name")
        self.jar_file = self.get_param("jar_file")
        self.file_name = self.get_param("file_name")
        self.state = self.get_param("state")

        # Initialize result variables
        self.changed = False
        self.diff = {"before": "", "after": ""}
        self.udf: Optional[SsbUdf] = None

    def process(self) -> None:
        client = SsbUdfClient(self.api_client)

        existing: Optional[SsbUdf] = None

        if self.udf_id:
            existing = client.describe_udf(self.project_id, self.udf_id)
        else:
            existing_list = client.list_udfs(self.project_id)
            existing = next(
                (u for u in existing_list if u.name == self.name),
                None,
            )

        if self.state == "absent":
            if existing:
                self.changed = True

                if not isinstance(existing.id, int):
                    self.module.fail_json(
                        msg="UDF ID is invalid from existing UDF.",
                    )

                if self.module._diff:
                    self.diff = {
                        "before": to_dict(existing),
                        "after": "",
                    }

                if not self.module.check_mode:
                    client.delete_udf(self.project_id, existing.id)
        elif self.state == "present":
            # Create the UDF if it doesn't exist
            if not existing:
                if not self.name:
                    self.module.fail_json(
                        msg="Parameter 'name' is required when creating a new UDF.",
                    )
                if not self.language:
                    self.module.fail_json(
                        msg="Parameter 'language' is required when creating a new UDF.",
                    )
                if not self.code:
                    self.module.fail_json(
                        msg="Parameter 'code' is required when creating a new UDF.",
                    )
                if not self.output_type:
                    self.module.fail_json(
                        msg="Parameter 'output_type' is required when creating a new UDF.",
                    )
                if not self.input_types:
                    self.module.fail_json(
                        msg="Parameter 'input_types' is required when creating a new UDF.",
                    )

                incoming = SsbUdf(
                    name=self.name,
                    project_id=self.project_id,
                    language=self.language,
                    code=self.code,
                    output_type=self.output_type,
                    input_types=self.input_types,
                    description=self.description,
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {
                        "before": "",
                        "after": to_dict(incoming),
                    }

                if not self.module.check_mode:
                    self.udf = client.create_udf(incoming)

            # Update the UDF if needed
            else:
                if not isinstance(existing.id, int):
                    self.module.fail_json(
                        msg="UDF ID is invalid from existing UDF.",
                    )

                # Build the updated UDF configuration
                incoming = SsbUdf(
                    name=existing.name,
                    project_id=existing.project_id,
                    language=self.language if self.language else existing.language,
                    code=self.code if self.code else existing.code,
                    java_class_name=(
                        self.java_class_name
                        if self.java_class_name
                        else existing.java_class_name
                    ),
                    jar_file=self.jar_file if self.jar_file else existing.jar_file,
                    file_name=self.file_name if self.file_name else existing.file_name,
                    output_type=(
                        self.output_type if self.output_type else existing.output_type
                    ),
                    input_types=(
                        self.input_types if self.input_types else existing.input_types
                    ),
                    description=(
                        self.description
                        if self.description is not None
                        else existing.description
                    ),
                    # Preserve read-only fields
                    id=existing.id,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                )

                # Compare the two UDF configurations
                prev_config, next_config = diff_dict(existing, incoming)

                if prev_config or next_config:
                    self.changed = True

                    if self.module._diff:
                        self.diff = {
                            "before": prev_config,
                            "after": next_config,
                        }

                    if not self.module.check_mode:
                        self.udf = client.update_udf(incoming)
                else:
                    self.udf = existing
        else:
            self.module.fail_json(msg="Invalid state '{}'.".format(self.state))


def main():
    result = SsbUdfModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        udf=to_dict(result.udf) if result.udf else {},
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
