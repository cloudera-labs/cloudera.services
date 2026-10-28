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
module: atlas_entity_info
short_description: Retrieve an entity from Apache Atlas
description:
  - Retrieve a single entity instance from Apache Atlas, with its attributes, labels, classifications, and business metadata.
  - Identify the entity either by its GUID or by its type name and unique attributes, usually its C(qualifiedName).
  - Returns no entities, and does not fail, when the entity does not exist.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.1.0"
options:
  guid:
    description:
      - GUID of the entity.
      - Atlas deletes entities softly, so a GUID lookup can return an entity whose RV(entities[].status) is V(DELETED).
      - Mutually exclusive with O(type_name), O(qualified_name), and O(unique_attributes).
    type: str
  type_name:
    description:
      - Name of the entity type, e.g. V(hive_table).
      - Requires O(qualified_name) or O(unique_attributes).
      - A type name that does not exist fails the module, so a misspelled type is not mistaken for a missing entity.
      - A lookup by unique attributes never returns a deleted entity.
    type: str
  qualified_name:
    description:
      - Value of the V(qualifiedName) unique attribute of the entity.
      - Shorthand for O(unique_attributes=qualifiedName).
      - Requires O(type_name); mutually exclusive with O(unique_attributes).
    type: str
  unique_attributes:
    description:
      - Unique attribute names and values that identify the entity within O(type_name).
      - Attribute names are Atlas names and are used as given, e.g. V(qualifiedName).
      - Requires O(type_name); mutually exclusive with O(qualified_name).
    type: dict
extends_documentation_fragment:
  - cloudera.services.services_client
attributes:
  check_mode:
    description:
      - This module supports check mode.
    support: full
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Retrieve an entity by its qualified name
  cloudera.services.atlas_entity_info:
    type_name: hive_table
    qualified_name: default.sales@cluster1
  register: table

- name: Retrieve an entity by its GUID
  cloudera.services.atlas_entity_info:
    guid: fc0fd256-be16-4775-99ad-9e0b7e304ae5
  register: entity

- name: Retrieve an entity by several unique attributes
  cloudera.services.atlas_entity_info:
    type_name: my_custom_type
    unique_attributes:
      qualifiedName: orders@cluster1
  register: orders

- name: Fail unless the entity exists and is active
  ansible.builtin.assert:
    that:
      - table.entities | length == 1
      - table.entities[0].status == 'ACTIVE'

- name: List the classifications attached to an entity
  ansible.builtin.debug:
    msg: "{{ table.entities[0].classifications | map(attribute='type_name') | list }}"
  when: table.entities | length > 0

- name: Wait for a hook to register a table before using it
  cloudera.services.atlas_entity_info:
    type_name: hive_table
    qualified_name: default.sales@cluster1
  register: table
  until: table.entities | length > 0
  retries: 12
  delay: 10
"""

RETURN = r"""
entities:
  description:
    - The entity, as a list with zero or one item.
    - Top-level keys are snake_case; the names inside the attribute dictionaries are exactly the names Atlas uses (e.g. V(qualifiedName)).
  type: list
  elements: dict
  returned: always
  contains:
    type_name:
      description: Name of the entity type.
      type: str
    guid:
      description: Atlas-assigned identifier.
      type: str
    status:
      description: Entity status, V(ACTIVE) or V(DELETED).
      type: str
    attributes:
      description: The entity attributes, keyed by Atlas attribute name.
      type: dict
    relationship_attributes:
      description: The relationship attributes, keyed by Atlas attribute name.
      type: dict
    custom_attributes:
      description: The user-defined custom attributes.
      type: dict
    business_attributes:
      description: The business metadata attached to the entity, keyed by business metadata name and then attribute name.
      type: dict
    labels:
      description: The labels attached to the entity.
      type: list
      elements: str
    classifications:
      description: The classifications attached to or propagated to the entity.
      type: list
      elements: dict
      contains:
        type_name:
          description: Name of the classification.
          type: str
        attributes:
          description: The classification attributes, keyed by Atlas attribute name.
          type: dict
        propagate:
          description: Whether the classification propagates to related entities.
          type: bool
        remove_propagations_on_entity_delete:
          description: Whether propagations are removed when the entity is deleted.
          type: bool
        validity_periods:
          description: The time windows in which the classification is valid.
          type: list
          elements: dict
        entity_guid:
          description: GUID of the entity the classification is attached to. A different GUID than the entity's own means it was propagated.
          type: str
        entity_status:
          description: Status of the entity the classification is attached to.
          type: str
    is_incomplete:
      description: Whether Atlas holds only a partial copy of the entity.
      type: bool
    version:
      description: Atlas version number of the entity.
      type: int
    create_time:
      description: Creation time in epoch milliseconds.
      type: int
    update_time:
      description: Last update time in epoch milliseconds.
      type: int
    created_by:
      description: User that created the entity.
      type: str
    updated_by:
      description: User that last updated the entity.
      type: str
"""

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntityClient,
)


class AtlasEntityInfoModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                type_name=dict(type="str", required=False),
                qualified_name=dict(type="str", required=False),
                unique_attributes=dict(type="dict", required=False),
            ),
            mutually_exclusive=[
                ["guid", "type_name"],
                ["guid", "qualified_name"],
                ["guid", "unique_attributes"],
                ["qualified_name", "unique_attributes"],
            ],
            required_one_of=[["guid", "type_name"]],
            required_by={
                "qualified_name": ["type_name"],
                "unique_attributes": ["type_name"],
            },
            supports_check_mode=True,
        )

        self.guid: Optional[str] = self.get_param("guid")
        self.type_name: Optional[str] = self.get_param("type_name")
        self.qualified_name: Optional[str] = self.get_param("qualified_name")
        self.unique_attributes: Optional[Dict[str, Any]] = self.get_param(
            "unique_attributes",
        )

        self.entities: List[Dict[str, Any]] = []

    def process(self) -> None:
        client = AtlasEntityClient(self.api_client)

        if self.guid:
            entity = client.get_entity_by_guid(self.guid)
        else:
            unique_attributes = self.unique_attributes or (
                {"qualifiedName": self.qualified_name} if self.qualified_name else None
            )
            if not unique_attributes:
                self.module.fail_json(
                    msg="Specify 'qualified_name' or 'unique_attributes' with 'type_name'.",
                )
                return

            entity = client.get_entity_by_unique_attributes(
                str(self.type_name),
                unique_attributes,
            )

        if entity is not None:
            self.entities.append(to_dict(entity))


def main():
    result = AtlasEntityInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        entities=result.entities,
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
