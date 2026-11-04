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
module: atlas_entity_label
short_description: Manage the labels of an Apache Atlas entity
description:
  - Add labels to, or remove labels from, an existing entity in Apache Atlas, such as a Hive table registered by a hook.
  - Identify the entity either by its GUID or by its type name and unique attributes, usually its C(qualifiedName).
  - The entity itself is not created or changed; it must already exist.
  - Labels are plain strings of letters, digits, C(_), and C(-). Atlas rejects any other character.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.1.0"
options:
  guid:
    description:
      - GUID of the entity.
      - Mutually exclusive with O(type_name), O(qualified_name), and O(unique_attributes).
    type: str
  type_name:
    description:
      - Name of the entity type, e.g. V(hive_table).
      - Requires O(qualified_name) or O(unique_attributes).
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
  labels:
    description:
      - Labels to add (O(state=present)) or remove (O(state=absent)).
      - Each label may contain only letters, digits, V(_), and V(-).
      - An empty list with O(exclusive=true) removes every label from the entity.
    type: list
    elements: str
    required: true
  state:
    description:
      - V(present) makes sure the labels are attached to the entity.
      - V(absent) makes sure the labels are not attached to the entity. An entity that does not exist, or is deleted, has nothing to remove and is not an error.
    type: str
    choices:
      - present
      - absent
    default: present
  exclusive:
    description:
      - Make O(labels) the only labels on the entity, removing any others.
      - Only valid with O(state=present).
    type: bool
    default: false
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
notes:
  - Atlas replaces the whole label list on every change, so the module reads the current labels first and only writes when they differ.
  - With O(state=present) the entity must exist and be active; an entity registered asynchronously by a hook may need L(until,https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_loops.html) retries.
seealso:
  - module: cloudera.services.atlas_entity_info
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Add labels to a table
  cloudera.services.atlas_entity_label:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    labels:
      - finance
      - reviewed

- name: Add labels to an entity by its GUID
  cloudera.services.atlas_entity_label:
    guid: fc0fd256-be16-4775-99ad-9e0b7e304ae5
    labels:
      - finance

- name: Make the labels on an entity exactly this list
  cloudera.services.atlas_entity_label:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    labels:
      - finance
    exclusive: true

- name: Remove every label from an entity
  cloudera.services.atlas_entity_label:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    labels: []
    exclusive: true

- name: Remove one label, leaving the others
  cloudera.services.atlas_entity_label:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    labels:
      - reviewed
    state: absent

- name: Label a table as soon as a hook registers it
  cloudera.services.atlas_entity_label:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    labels:
      - finance
  register: labelled
  until: labelled is succeeded
  retries: 12
  delay: 10
"""

RETURN = r"""
labels:
  description:
    - The labels on the entity after the module ran.
    - With O(ignore:check_mode=true) these are the labels the entity would have.
    - Empty when the entity does not exist and O(state=absent).
  type: list
  elements: str
  returned: always
guid:
  description:
    - GUID of the entity.
    - V(null) when the entity does not exist and O(state=absent).
  type: str
  returned: always
"""

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntity,
    AtlasEntityClient,
    validate_labels,
)


class AtlasEntityLabelModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                type_name=dict(type="str", required=False),
                qualified_name=dict(type="str", required=False),
                unique_attributes=dict(type="dict", required=False),
                labels=dict(type="list", elements="str", required=True),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
                exclusive=dict(type="bool", default=False),
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
        self.labels: List[str] = self.get_param("labels")
        self.state: str = self.get_param("state")
        self.exclusive: bool = self.get_param("exclusive")

        self.changed = False
        self.diff: Dict[str, Any] = {}
        self.result_guid: Optional[str] = None
        self.result_labels: List[str] = []

    def process(self) -> None:
        if self.exclusive and self.state == "absent":
            self.module.fail_json(
                msg="'exclusive' can only be used with state 'present'.",
            )
            return

        validate_labels(self.labels)

        client = AtlasEntityClient(self.api_client)

        entity = self._find_entity(client)
        active = entity is not None and entity.status == "ACTIVE"

        if not active:
            if self.state == "present":
                self.module.fail_json(
                    msg="Labels can only be set on an active entity, but the entity was not found or is deleted.",
                )
            return

        assert entity is not None
        self.result_guid = str(entity.guid)
        current: List[str] = entity.labels if isinstance(entity.labels, list) else []

        desired = self._desired_labels(current)

        if set(desired) == set(current):
            self.result_labels = current
            return

        self.result_labels = desired
        self.changed = True

        if self.module._diff:
            self.diff = {
                "before": {"labels": current},
                "after": {"labels": desired},
            }

        if not self.module.check_mode:
            client.set_entity_labels(self.result_guid, desired)

    def _find_entity(self, client: AtlasEntityClient) -> Optional[AtlasEntity]:
        if self.guid:
            return client.get_entity_by_guid(self.guid)

        unique_attributes = self.unique_attributes or (
            {"qualifiedName": self.qualified_name} if self.qualified_name else None
        )
        if not unique_attributes:
            self.module.fail_json(
                msg="Specify 'qualified_name' or 'unique_attributes' with 'type_name'.",
            )
            return None

        return client.get_entity_by_unique_attributes(
            str(self.type_name),
            unique_attributes,
        )

    def _desired_labels(self, current: List[str]) -> List[str]:
        requested = list(dict.fromkeys(self.labels))

        if self.state == "absent":
            return [label for label in current if label not in requested]

        if self.exclusive:
            return requested

        return current + [label for label in requested if label not in current]


def main():
    result = AtlasEntityLabelModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        guid=result.result_guid,
        labels=result.result_labels,
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
