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
module: atlas_relationship_def
short_description: Manage relationship type definitions in Apache Atlas
description:
  - Create, update, or delete relationship type definitions in Apache Atlas.
  - A relationship type connects two entity types through named ends.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the relationship type definition.
      - Required when O(state=present) or O(state=absent).
    type: str
  description:
    description:
      - Description of the relationship type definition.
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
  end_def1:
    description:
      - First end of the relationship.
      - Atlas requires both ends when creating a relationship type.
      - Unset suboptions keep the value Atlas already holds.
    type: dict
    suboptions:
      type:
        description:
          - Name of the entity type at this end.
        type: str
        required: true
      name:
        description:
          - Name of the relationship attribute Atlas adds to the entity type at this end.
        type: str
        required: true
      cardinality:
        description:
          - Cardinality of this end.
        type: str
        choices:
          - SINGLE
          - LIST
          - SET
      is_container:
        description:
          - Whether this end is the container of the relationship.
        type: bool
      is_legacy_attribute:
        description:
          - Whether this end is backed by an existing entity attribute.
        type: bool
      description:
        description:
          - Description of this end.
        type: str
  end_def2:
    description:
      - Second end of the relationship.
      - Atlas requires both ends when creating a relationship type.
      - Unset suboptions keep the value Atlas already holds.
    type: dict
    suboptions:
      type:
        description:
          - Name of the entity type at this end.
        type: str
        required: true
      name:
        description:
          - Name of the relationship attribute Atlas adds to the entity type at this end.
        type: str
        required: true
      cardinality:
        description:
          - Cardinality of this end.
        type: str
        choices:
          - SINGLE
          - LIST
          - SET
      is_container:
        description:
          - Whether this end is the container of the relationship.
        type: bool
      is_legacy_attribute:
        description:
          - Whether this end is backed by an existing entity attribute.
        type: bool
      description:
        description:
          - Description of this end.
        type: str
  relationship_category:
    description:
      - UML-style category of the relationship.
      - V(COMPOSITION) and V(AGGREGATION) require one end to be the container.
    type: str
    choices:
      - ASSOCIATION
      - AGGREGATION
      - COMPOSITION
  relationship_label:
    description:
      - Label Atlas uses for edges of this relationship.
      - Atlas assigns a label when unset.
    type: str
  propagate_tags:
    description:
      - Direction in which classifications propagate across the relationship.
    type: str
    choices:
      - NONE
      - ONE_TO_TWO
      - TWO_TO_ONE
      - BOTH
  attribute_defs:
    description:
      - Attributes of the relationship; Atlas only allows primitive types.
      - Replaces the existing attributes; Atlas may reject removing attributes that are in use.
      - Unset suboptions keep the value Atlas already holds for an attribute of the same name.
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
          - Name of the attribute type, e.g. V(string) or V(int).
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
      - Whether the relationship type definition should be present or absent.
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
- name: Create a relationship type definition
  cloudera.services.atlas_relationship_def:
    name: team_members
    description: Members of a team
    relationship_category: ASSOCIATION
    propagate_tags: NONE
    end_def1:
      type: team
      name: members
      cardinality: SET
      is_container: true
    end_def2:
      type: person
      name: teams
      cardinality: SET

- name: Create a composition relationship where deleting the container deletes its parts
  cloudera.services.atlas_relationship_def:
    name: table_columns
    relationship_category: COMPOSITION
    end_def1:
      type: table
      name: columns
      cardinality: SET
      is_container: true
    end_def2:
      type: column
      name: table
      cardinality: SINGLE

- name: Create a relationship that propagates classifications in both directions
  cloudera.services.atlas_relationship_def:
    name: dataset_consumers
    relationship_category: ASSOCIATION
    propagate_tags: BOTH
    end_def1:
      type: dataset
      name: consumers
      cardinality: SET
    end_def2:
      type: application
      name: datasets
      cardinality: SET

- name: Create a relationship with attributes of its own
  cloudera.services.atlas_relationship_def:
    name: team_members
    relationship_category: ASSOCIATION
    end_def1:
      type: team
      name: members
      cardinality: SET
    end_def2:
      type: person
      name: teams
      cardinality: SET
    attribute_defs:
      - name: role
        type_name: string
        is_optional: true
      - name: joined
        type_name: date
        is_optional: true

- name: Change only how classifications propagate, keeping the ends as they are
  cloudera.services.atlas_relationship_def:
    name: team_members
    propagate_tags: ONE_TO_TWO

- name: Change the cardinality of one end, keeping its other fields as they are
  cloudera.services.atlas_relationship_def:
    name: team_members
    end_def1:
      type: team
      name: members
      cardinality: LIST

- name: Preview a change without applying it
  cloudera.services.atlas_relationship_def:
    name: team_members
    description: Members of a team, with their roles
  check_mode: true
  diff: true
  register: preview

- name: Remove a relationship type definition
  cloudera.services.atlas_relationship_def:
    name: team_members
    state: absent
"""

RETURN = r"""
relationship_def:
  description: The relationship type definition.
  type: dict
  returned: when O(state=present)
  contains:
    name:
      description: Name of the relationship type definition.
      type: str
    guid:
      description: Atlas-assigned identifier.
      type: str
    category:
      description: Type category, always V(RELATIONSHIP).
      type: str
    description:
      description: Description of the relationship type definition.
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
    relationship_category:
      description: UML-style category of the relationship.
      type: str
    relationship_label:
      description: Label Atlas uses for edges of this relationship.
      type: str
    propagate_tags:
      description: Direction in which classifications propagate.
      type: str
    end_def1:
      description: First end of the relationship.
      type: dict
      contains:
        type:
          description: Name of the entity type at this end.
          type: str
        name:
          description: Name of the relationship attribute at this end.
          type: str
        cardinality:
          description: Cardinality of this end.
          type: str
        is_container:
          description: Whether this end is the container of the relationship.
          type: bool
        is_legacy_attribute:
          description: Whether this end is backed by an existing entity attribute.
          type: bool
        description:
          description: Description of this end.
          type: str
    end_def2:
      description: Second end of the relationship.
      type: dict
      contains:
        type:
          description: Name of the entity type at this end.
          type: str
        name:
          description: Name of the relationship attribute at this end.
          type: str
        cardinality:
          description: Cardinality of this end.
          type: str
        is_container:
          description: Whether this end is the container of the relationship.
          type: bool
        is_legacy_attribute:
          description: Whether this end is backed by an existing entity attribute.
          type: bool
        description:
          description: Description of this end.
          type: str
    attribute_defs:
      description: Attributes of the relationship.
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
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasTypeDefClient,
    align_attribute_defs,
    align_relationship_end_def,
    extract_relationship_def_params,
)


class AtlasRelationshipDefModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                **AtlasRelationshipDef.argument_spec(),
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
        # keep in sync with AtlasRelationshipDef.argument_spec().
        self.name: Optional[str] = self.get_param("name")
        self.description: Optional[str] = self.get_param("description")
        self.type_version: Optional[str] = self.get_param("type_version")
        self.service_type: Optional[str] = self.get_param("service_type")
        self.options: Optional[Dict[str, Any]] = self.get_param("options")
        self.attribute_defs: Optional[List[Dict[str, Any]]] = self.get_param(
            "attribute_defs",
        )
        self.end_def1: Optional[Dict[str, Any]] = self.get_param("end_def1")
        self.end_def2: Optional[Dict[str, Any]] = self.get_param("end_def2")
        self.relationship_category: Optional[str] = self.get_param(
            "relationship_category",
        )
        self.relationship_label: Optional[str] = self.get_param("relationship_label")
        self.propagate_tags: Optional[str] = self.get_param("propagate_tags")
        self.state: str = self.get_param("state")

        self.changed = False
        self.diff = {}
        self.relationship_def: Optional[AtlasRelationshipDef] = None

    def process(self) -> None:
        client = AtlasTypeDefClient(self.api_client)

        existing: Optional[AtlasRelationshipDef] = None
        if self.name:
            existing = client.get_relationship_def_by_name(self.name)

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
                    AtlasRelationshipDef,
                    extract_relationship_def_params(self),
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {"before": {}, "after": to_dict(incoming)}

                if not self.module.check_mode:
                    self.relationship_def = client.create_relationship_def(incoming)
                else:
                    self.relationship_def = incoming

            else:
                incoming = build_from_params(
                    AtlasRelationshipDef,
                    extract_relationship_def_params(self),
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

                for end in ("end_def1", "end_def2"):
                    incoming_end = getattr(incoming, end)
                    existing_end = getattr(existing, end)
                    if isinstance(incoming_end, AtlasRelationshipEndDef) and isinstance(
                        existing_end,
                        AtlasRelationshipEndDef,
                    ):
                        setattr(
                            incoming,
                            end,
                            align_relationship_end_def(incoming_end, existing_end),
                        )

                prev_config, next_config = diff_dict(existing, incoming)

                if prev_config or next_config:
                    self.changed = True

                    if self.module._diff:
                        self.diff = {"before": prev_config, "after": next_config}

                    if not self.module.check_mode:
                        self.relationship_def = client.update_relationship_def(incoming)
                    else:
                        self.relationship_def = incoming
                else:
                    self.relationship_def = existing

        else:
            self.module.fail_json(msg=f"Invalid state '{self.state}'.")


def main():
    result = AtlasRelationshipDefModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        relationship_def=(
            to_dict(result.relationship_def) if result.relationship_def else {}
        ),
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
