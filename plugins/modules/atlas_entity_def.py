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
module: atlas_entity_def
short_description: Manage entity type definitions in Apache Atlas
description:
  - Create, update, or delete entity type definitions in Apache Atlas.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the entity type definition.
      - Required when O(state=present) or O(state=absent).
    type: str
  description:
    description:
      - Description of the entity type definition.
    type: str
  type_version:
    description:
      - Version label of the type definition, e.g. V(1.0).
    type: str
  service_type:
    description:
      - Name of the service that owns the type definition.
    type: str
  options:
    description:
      - Free-form map of string options for the type definition.
      - Keys are sent to Atlas verbatim.
    type: dict
  super_types:
    description:
      - Names of the entity types this entity type inherits from.
    type: list
    elements: str
  attribute_defs:
    description:
      - Attributes of the entity type.
      - Replaces the existing attributes; Atlas may reject removing attributes that are in use.
      - Unset suboptions keep the value Atlas already holds for an attribute of the same name.
      - Atlas rejects adding an attribute to an existing entity type unless O(attribute_defs[].is_optional=true).
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Name of the attribute.
        type: str
        required: true
      type_name:
        description:
          - Name of the attribute type, e.g. V(string), V(int), or the name of an enum.
        type: str
        required: true
      is_optional:
        description:
          - Whether a value is optional.
        type: bool
      is_unique:
        description:
          - Whether values must be unique.
        type: bool
      is_indexable:
        description:
          - Whether the attribute is indexed.
        type: bool
      cardinality:
        description:
          - Cardinality of the attribute.
        type: str
        choices:
          - SINGLE
          - LIST
          - SET
      values_min_count:
        description:
          - Minimum number of values.
        type: int
      values_max_count:
        description:
          - Maximum number of values.
        type: int
      default_value:
        description:
          - Default value of the attribute.
        type: str
      description:
        description:
          - Description of the attribute.
        type: str
      display_name:
        description:
          - Display name of the attribute.
        type: str
      include_in_notification:
        description:
          - Whether changes to the attribute are included in notifications.
        type: bool
      index_type:
        description:
          - Index type of the attribute.
        type: str
        choices:
          - DEFAULT
          - STRING
      search_weight:
        description:
          - Search weight of the attribute.
        type: int
      options:
        description:
          - Free-form map of string options for the attribute.
          - Keys are sent to Atlas verbatim.
        type: dict
      constraints:
        description:
          - Constraints on the attribute.
        type: list
        elements: dict
        suboptions:
          type:
            description:
              - Type of the constraint, e.g. V(ownedRef) or V(inverseRef).
            type: str
            required: true
          params:
            description:
              - Parameters of the constraint.
              - Keys are sent to Atlas verbatim.
            type: dict
  state:
    description:
      - Whether the entity type definition should be present or absent.
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
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Create an entity type definition
  cloudera.services.atlas_entity_def:
    name: customer_record
    description: Customer record dataset
    attribute_defs:
      - name: owner
        type_name: string
        is_optional: true

- name: Remove an entity type definition
  cloudera.services.atlas_entity_def:
    name: customer_record
    state: absent
"""

RETURN = r"""
entity_def:
  description: The entity type definition.
  type: dict
  returned: when O(state=present)
  contains:
    name:
      description: Name of the entity type definition.
      type: str
    guid:
      description: Atlas-assigned identifier.
      type: str
    category:
      description: Type category, always V(ENTITY).
      type: str
    description:
      description: Description of the entity type definition.
      type: str
    type_version:
      description: Version label of the type definition.
      type: str
    service_type:
      description: Name of the service that owns the type definition.
      type: str
    options:
      description: Free-form options of the type definition.
      type: dict
    super_types:
      description: Names of the entity types this entity type inherits from.
      type: list
      elements: str
    sub_types:
      description: Names of the entity types that inherit from this entity type.
      type: list
      elements: str
    attribute_defs:
      description: Attributes of the entity type.
      type: list
      elements: dict
      contains:
        name:
          description: Name of the attribute.
          type: str
        type_name:
          description: Name of the attribute type.
          type: str
        is_optional:
          description: Whether a value is optional.
          type: bool
        is_unique:
          description: Whether values must be unique.
          type: bool
        is_indexable:
          description: Whether the attribute is indexed.
          type: bool
        cardinality:
          description: Cardinality of the attribute.
          type: str
        values_min_count:
          description: Minimum number of values.
          type: int
        values_max_count:
          description: Maximum number of values.
          type: int
        default_value:
          description: Default value of the attribute.
          type: str
        description:
          description: Description of the attribute.
          type: str
        display_name:
          description: Display name of the attribute.
          type: str
        include_in_notification:
          description: Whether changes are included in notifications.
          type: bool
        index_type:
          description: Index type of the attribute.
          type: str
        search_weight:
          description: Search weight of the attribute.
          type: int
        options:
          description: Free-form options of the attribute.
          type: dict
        constraints:
          description: Constraints on the attribute.
          type: list
          elements: dict
          contains:
            type:
              description: Type of the constraint.
              type: str
            params:
              description: Parameters of the constraint.
              type: dict
    relationship_attribute_defs:
      description:
        - Relationship attributes of the entity type, derived by Atlas from relationship type definitions.
        - Read-only; has the same fields as O(attribute_defs) plus those below.
      type: list
      elements: dict
      contains:
        name:
          description: Name of the attribute.
          type: str
        type_name:
          description: Name of the attribute type.
          type: str
        relationship_type_name:
          description: Name of the relationship type that defines the attribute.
          type: str
        is_legacy_attribute:
          description: Whether the attribute is a legacy attribute.
          type: bool
    business_attribute_defs:
      description:
        - Business metadata attributes of the entity type, keyed by business metadata name.
        - Read-only; managed through business metadata type definitions.
      type: dict
    version:
      description: Atlas version number of the type definition.
      type: int
    create_time:
      description: Creation time in epoch milliseconds.
      type: int
    update_time:
      description: Last update time in epoch milliseconds.
      type: int
    created_by:
      description: User that created the type definition.
      type: str
    updated_by:
      description: User that last updated the type definition.
      type: str
"""

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    build_from_params,
    diff_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasEntityDef,
    AtlasTypeDefClient,
    align_attribute_defs,
    extract_entity_def_params,
)


class AtlasEntityDefModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                **AtlasEntityDef.argument_spec(),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            required_if=[
                ["state", "present", ["name"]],
                ["state", "absent", ["name"]],
            ],
            supports_check_mode=True,
        )

        # Explicit attributes (not setattr) so type checkers can see them;
        # keep in sync with AtlasEntityDef.argument_spec().
        self.name: Optional[str] = self.get_param("name")
        self.description: Optional[str] = self.get_param("description")
        self.type_version: Optional[str] = self.get_param("type_version")
        self.service_type: Optional[str] = self.get_param("service_type")
        self.options: Optional[Dict[str, Any]] = self.get_param("options")
        self.attribute_defs: Optional[List[Dict[str, Any]]] = self.get_param(
            "attribute_defs",
        )
        self.super_types: Optional[List[str]] = self.get_param("super_types")
        self.state: str = self.get_param("state")

        self.changed = False
        self.diff = {}
        self.entity_def: Optional[AtlasEntityDef] = None

    def process(self) -> None:
        client = AtlasTypeDefClient(self.api_client)

        existing: Optional[AtlasEntityDef] = None
        if self.name:
            existing = client.get_entity_def_by_name(self.name)

        if self.state == "absent":
            if existing:
                self.changed = True

                if self.module._diff:
                    self.diff = {"before": to_dict(existing), "after": {}}

                if not self.module.check_mode:
                    client.delete_typedef_by_name(existing.name)

        elif self.state == "present":
            if not existing:
                incoming = build_from_params(
                    AtlasEntityDef,
                    extract_entity_def_params(self),
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {"before": {}, "after": to_dict(incoming)}

                if not self.module.check_mode:
                    self.entity_def = client.create_entity_def(
                        incoming,
                    )
                else:
                    self.entity_def = incoming

            else:
                incoming = build_from_params(
                    AtlasEntityDef,
                    extract_entity_def_params(self),
                    existing=existing,
                )

                if isinstance(incoming.attribute_defs, list) and isinstance(
                    existing.attribute_defs,
                    list,
                ):
                    incoming.attribute_defs = align_attribute_defs(
                        incoming.attribute_defs,
                        existing.attribute_defs,
                    )

                prev_config, next_config = diff_dict(existing, incoming)

                if prev_config or next_config:
                    self.changed = True

                    if self.module._diff:
                        self.diff = {"before": prev_config, "after": next_config}

                    if not self.module.check_mode:
                        self.entity_def = client.update_entity_def(
                            incoming,
                        )
                    else:
                        self.entity_def = incoming
                else:
                    self.entity_def = existing

        else:
            self.module.fail_json(msg=f"Invalid state '{self.state}'.")


def main():
    result = AtlasEntityDefModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        entity_def=(to_dict(result.entity_def) if result.entity_def else {}),
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
