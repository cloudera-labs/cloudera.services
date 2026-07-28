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
module: ssb_data_source
short_description: Manage SSB project data sources
description:
  - Create, update, delete, or manage Cloudera SSB project data sources.
  - Data sources define connections to external systems like Kafka, databases, etc.
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
      - The name of the data source.
      - Required when creating a new data source (O(state=present)).
      - This parameter is mutually exclusive with O(id).
    type: str
    required: false
  id:
    description:
      - The unique identifier of the data source.
      - This parameter is mutually exclusive with O(name).
      - This field is read-only and cannot be modified after creation.
    type: str
    required: false
    aliases:
      - data_source_id
  type:
    description:
      - The type of the data source (e.g., KAFKA, POSTGRES, MYSQL).
      - Required when creating a new data source.
    type: str
    required: false
  properties:
    description:
      - Dictionary of configuration properties for the data source.
      - Required properties depend on the data source type.
      - For example, V(KAFKA) typically includes V(bootstrap.servers).
    type: dict
    required: false
  custom_truststore:
    description:
      - Path to a custom truststore file for secure connections to the data source.
    type: str
    required: false
  delete_dependents:
    description:
      - Whether to delete dependent resources when deleting this data source.
      - Only applies when O(state=absent).
    type: bool
    default: false
  state:
    description:
      - The desired state of the data source.
      - Use C(present) to create or update a data source.
      - Use C(absent) to delete a data source.
    type: str
    choices:
      - present
      - absent
    default: present
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Create a minimal Kafka data source
  cloudera.services.ssb_data_source:
    project_id: "12345"
    name: "my-kafka-source"
    type: "KAFKA"
    properties:
      brokers: "localhost:9092"
    state: present

- name: Create a Kafka data source with SASL security
  cloudera.services.ssb_data_source:
    project_id: "12345"
    name: "my-kafka-source"
    type: "KAFKA"
    properties:
      brokers: "localhost:9092"
      protocol: "sasl"
      mechanism: "KERBEROS"
    state: present

- name: Create a data source with custom truststore
  cloudera.services.ssb_data_source:
    project_id: "12345"
    name: "secure-kafka-source"
    type: "KAFKA"
    properties:
      brokers: "kafka:9093"
    custom_truststore: "/path/to/truststore.jks"
    state: present

- name: Update data source properties
  cloudera.services.ssb_data_source:
    project_id: "12345"
    name: "my-kafka-source"
    type: "KAFKA"
    properties:
      brokers: "kafka:9092"
    state: present

- name: Delete a data source by name
  cloudera.services.ssb_data_source:
    project_id: "12345"
    name: "my-kafka-source"
    state: absent

- name: Delete a data source by id with dependents
  cloudera.services.ssb_data_source:
    project_id: "12345"
    id: 42
    delete_dependents: true
    state: absent
"""

RETURN = r"""
data_source:
  description: The data source details.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The unique identifier of the data source.
      type: str
      returned: always
    name:
      description: The name of the data source.
      type: str
      returned: always
    type:
      description: The type of the data source.
      type: str
      returned: always
    properties:
      description: Dictionary of configuration properties for the data source.
      type: dict
      returned: when available
    custom_truststore:
      description: Path to custom truststore file.
      type: str
      returned: when available
    created_at:
      description: The timestamp when the data source was created.
      type: str
      returned: when available
    updated_at:
      description: The timestamp when the data source was last updated.
      type: str
      returned: when available
    project_id:
      description: The project identifier this data source belongs to.
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
    SsbDataSource,
    SsbDataSourceClient,
)


class SsbDataSourceModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_id=dict(type="str", required=True),
                name=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["data_source_id"]),
                type=dict(type="str", required=False),
                properties=dict(type="dict", required=False),
                custom_truststore=dict(type="str", required=False),
                delete_dependents=dict(type="bool", required=False, default=False),
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
        self.data_source_id = self.get_param("id")
        self.ds_type = self.get_param("type")
        self.properties = self.get_param("properties")
        self.custom_truststore = self.get_param("custom_truststore")
        self.delete_dependents = self.get_param("delete_dependents")
        self.state = self.get_param("state")

        # Initialize result variables
        self.changed = False
        self.diff = {"before": "", "after": ""}
        self.data_source: Optional[SsbDataSource] = None

    def process(self) -> None:
        client = SsbDataSourceClient(self.api_client)

        existing: Optional[SsbDataSource] = None

        if self.data_source_id:
            existing = client.describe_data_source(self.project_id, self.data_source_id)
        else:
            existing_list = client.list_data_sources(self.project_id)
            existing = next((ds for ds in existing_list if ds.name == self.name), None)

        if self.state == "absent":
            if existing:
                self.changed = True

                if not isinstance(existing.id, str):
                    self.module.fail_json(
                        msg="Data source ID is invalid from existing data source.",
                    )

                if self.module._diff:
                    self.diff = {
                        "before": to_dict(existing),
                        "after": "",
                    }

                if not self.module.check_mode:
                    client.delete_data_source(
                        self.project_id,
                        existing.id,
                        delete_dependents=self.delete_dependents,
                    )
        elif self.state == "present":
            # Create the data source if it doesn't exist
            if not existing:
                if not self.name:
                    self.module.fail_json(
                        msg="Parameter 'name' is required when creating a new data source.",
                    )
                if not self.ds_type:
                    self.module.fail_json(
                        msg="Parameter 'type' is required when creating a new data source.",
                    )
                if not self.properties:
                    self.module.fail_json(
                        msg="Parameter 'properties' is required when creating a new data source.",
                    )

                incoming = SsbDataSource(
                    name=self.name,
                    type=self.ds_type,
                    properties=self.properties,
                    custom_truststore=self.custom_truststore,
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {
                        "before": "",
                        "after": to_dict(incoming),
                    }

                if not self.module.check_mode:
                    self.data_source = client.create_data_source(
                        project_id=self.project_id,
                        data_source=incoming,
                    )

            # Update the data source if needed
            else:
                if not isinstance(existing.id, str):
                    self.module.fail_json(
                        msg="Data source ID is invalid from existing data source.",
                    )

                # Build the updated data source configuration
                incoming = SsbDataSource(
                    id=existing.id,
                    name=existing.name,
                    project_id=existing.project_id,
                    type=self.ds_type if self.ds_type else existing.type,
                    properties=(
                        self.properties if self.properties else existing.properties
                    ),
                    custom_truststore=(
                        self.custom_truststore
                        if self.custom_truststore is not None
                        else existing.custom_truststore
                    ),
                )

                # Compare the two data source configurations
                prev_config, next_config = diff_dict(existing, incoming)

                # Ignore the timestamp fields
                for field in ["created_at", "updated_at"]:
                    prev_config.pop(field, None)
                    next_config.pop(field, None)

                if prev_config or next_config:
                    self.changed = True

                    if self.module._diff:
                        self.diff = {
                            "before": prev_config,
                            "after": next_config,
                        }

                    if not self.module.check_mode:
                        self.data_source = client.update_data_source(
                            self.project_id,
                            incoming,
                        )
                else:
                    self.data_source = existing
        else:
            self.module.fail_json(msg="Invalid state '{}'.".format(self.state))


def main():
    result = SsbDataSourceModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        data_source=to_dict(result.data_source) if result.data_source else {},
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
