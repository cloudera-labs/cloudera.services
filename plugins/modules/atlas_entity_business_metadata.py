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
module: atlas_entity_business_metadata
short_description: Manage business metadata on an Apache Atlas entity
description:
  - Set attributes of one business metadata on an existing entity in Apache Atlas, such as a Hive table registered by a hook, or remove that business metadata from the entity.
  - Identify the entity either by its GUID or by its type name and unique attributes, usually its C(qualifiedName).
  - The entity itself is not created or changed; it must already exist.
  - The business metadata must already be defined, for example with M(cloudera.services.atlas_business_metadata_def), and must apply to the entity's type.
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
  name:
    description:
      - Name of the business metadata, as defined by its typedef.
    type: str
    required: true
  attributes:
    description:
      - Attribute names and values to set on the business metadata.
      - Required with O(state=present); not allowed with O(state=absent).
      - Every name must be an attribute of the business metadata typedef. Atlas silently ignores unknown names, so the module fails on them instead.
      - Values are converted to the type the typedef declares, e.g. V("5") to V(5) for an C(int) attribute, so a repeated run reports no change.
      - Only the attributes listed here are managed. Other attributes of the business metadata, and other business metadata on the entity, are left as they are.
      - An attribute cannot be set to null. To drop it, remove the whole business metadata with O(state=absent) and set the ones to keep again.
    type: dict
  state:
    description:
      - V(present) makes sure the attributes have the given values on the entity.
      - V(absent) removes the whole business metadata, with all of its attributes, from the entity. An entity that does not exist, or is deleted, has nothing to remove and is not an error.
    type: str
    choices:
      - present
      - absent
    default: present
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
  - Atlas ignores a request body on DELETE, so single attributes cannot be removed; V(absent) always removes the whole business metadata.
  - The module never overwrites, so setting one business metadata does not affect the others on the entity.
  - Atlas answers HTTP 404 when the business metadata does not apply to the entity's type; the module reports Atlas's message.
  - With O(state=present) the entity must exist and be active; an entity registered asynchronously by a hook may need L(until,https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_loops.html) retries.
seealso:
  - module: cloudera.services.atlas_business_metadata_def
  - module: cloudera.services.atlas_entity_info
  - module: cloudera.services.atlas_entity_label
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Set business metadata on a table
  cloudera.services.atlas_entity_business_metadata:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: governance
    attributes:
      owner_team: finance
      retention_days: 365

- name: Set business metadata on an entity by its GUID
  cloudera.services.atlas_entity_business_metadata:
    guid: fc0fd256-be16-4775-99ad-9e0b7e304ae5
    name: governance
    attributes:
      owner_team: finance

- name: Change one attribute, leaving the others as they are
  cloudera.services.atlas_entity_business_metadata:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: governance
    attributes:
      retention_days: 730

- name: Remove the business metadata, with all its attributes, from a table
  cloudera.services.atlas_entity_business_metadata:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: governance
    state: absent

- name: Set business metadata as soon as a hook registers the table
  cloudera.services.atlas_entity_business_metadata:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: governance
    attributes:
      owner_team: finance
  register: governed
  until: governed is succeeded
  retries: 12
  delay: 10
"""

RETURN = r"""
business_metadata:
  description:
    - The attributes of the named business metadata on the entity after the module ran.
    - With O(ignore:check_mode=true) these are the attributes the entity would have.
    - Empty when the entity does not exist or the business metadata was removed.
  type: dict
  returned: always
  sample:
    owner_team: finance
    retention_days: 365
guid:
  description:
    - GUID of the entity.
    - V(null) when the entity does not exist and O(state=absent).
  type: str
  returned: always
"""

from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasTypeDefClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntity,
    AtlasEntityClient,
    normalize_business_attributes,
)


class AtlasEntityBusinessMetadataModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                type_name=dict(type="str", required=False),
                qualified_name=dict(type="str", required=False),
                unique_attributes=dict(type="dict", required=False),
                name=dict(type="str", required=True),
                attributes=dict(type="dict", required=False),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
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
            required_if=[["state", "present", ["attributes"]]],
            supports_check_mode=True,
        )

        self.guid: Optional[str] = self.get_param("guid")
        self.type_name: Optional[str] = self.get_param("type_name")
        self.qualified_name: Optional[str] = self.get_param("qualified_name")
        self.unique_attributes: Optional[Dict[str, Any]] = self.get_param(
            "unique_attributes",
        )
        self.name: str = self.get_param("name")
        self.attributes: Optional[Dict[str, Any]] = self.get_param("attributes")
        self.state: str = self.get_param("state")

        self.changed = False
        self.diff: Dict[str, Any] = {}
        self.result_guid: Optional[str] = None
        self.result_business_metadata: Dict[str, Any] = {}

    def process(self) -> None:
        if self.state == "absent" and self.attributes is not None:
            self.module.fail_json(
                msg="'attributes' cannot be used with state 'absent'; Atlas can only remove the whole business metadata.",
            )
            return

        client = AtlasEntityClient(self.api_client)

        entity = self._find_entity(client)
        active = entity is not None and entity.status == "ACTIVE"

        if not active:
            if self.state == "present":
                self.module.fail_json(
                    msg="Business metadata can only be set on an active entity, but the entity was not found or is deleted.",
                )
            return

        assert entity is not None
        self.result_guid = str(entity.guid)
        current = self._current_attributes(entity)

        if self.state == "absent":
            self._remove(client, entity, current)
        else:
            self._set(client, current)

    def _remove(
        self,
        client: AtlasEntityClient,
        entity: AtlasEntity,
        current: Optional[Dict[str, Any]],
    ) -> None:
        if current is None:
            return

        self.changed = True

        if self.module._diff:
            self.diff = {
                "before": {"business_metadata": {self.name: current}},
                "after": {"business_metadata": {}},
            }

        if not self.module.check_mode:
            client.remove_entity_business_metadata(str(self.result_guid), self.name)

    def _set(
        self,
        client: AtlasEntityClient,
        current: Optional[Dict[str, Any]],
    ) -> None:
        existing: Dict[str, Any] = current or {}

        definition = AtlasTypeDefClient(
            self.api_client,
        ).get_business_metadata_def_by_name(
            self.name,
        )
        if definition is None:
            self.module.fail_json(
                msg=f"Business metadata '{self.name}' does not exist.",
            )
            return

        desired = normalize_business_attributes(
            self.name,
            definition.attribute_defs,
            self.attributes or {},
        )
        delta = {
            attribute: value
            for attribute, value in desired.items()
            if attribute not in existing or existing[attribute] != value
        }

        self.result_business_metadata = {**existing, **delta}

        if not delta:
            return

        self.changed = True

        if self.module._diff:
            self.diff = {
                "before": {
                    "business_metadata": {
                        self.name: {k: existing[k] for k in delta if k in existing},
                    },
                },
                "after": {"business_metadata": {self.name: delta}},
            }

        if not self.module.check_mode:
            client.set_entity_business_metadata(
                str(self.result_guid),
                self.name,
                delta,
            )

    def _current_attributes(self, entity: AtlasEntity) -> Optional[Dict[str, Any]]:
        """Attributes of the named business metadata on the entity, or None if it has none."""
        business = (
            entity.business_attributes
            if isinstance(entity.business_attributes, dict)
            else {}
        )
        current = business.get(self.name)
        return current if isinstance(current, dict) else None

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


def main():
    result = AtlasEntityBusinessMetadataModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        guid=result.result_guid,
        business_metadata=result.result_business_metadata,
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
