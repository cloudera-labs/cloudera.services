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
module: atlas_business_metadata_def
short_description: Manage business metadata type definitions in Apache Atlas
description:
  - Create, update, or delete business metadata type definitions in Apache Atlas.
  - Business metadata is a named group of attributes that can be attached to entities.
    Each attribute declares the entity types it applies to through its O(attribute_defs[].options).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the business metadata type definition.
      - Required when O(state=present) or O(state=absent).
    type: str
  description:
    description:
      - Description of the business metadata type definition.
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
  attribute_defs:
    description:
      - Attributes of the business metadata.
      - Replaces the existing attributes; Atlas may reject removing attributes that are in use.
      - Unset suboptions keep the value Atlas already holds for an attribute of the same name.
      - Each attribute normally sets V(applicableEntityTypes) in its O(attribute_defs[].options) to say which entity types it applies to.
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
          - Keys and values are sent to Atlas verbatim.
          - When set, the map replaces all of the attribute's existing options, so include every option to keep.
          - All option values are strings, as Atlas stores them. Quote numbers, e.g. V("50"), and convert variables with the P(ansible.builtin.string#filter) filter.
          - V(applicableEntityTypes) is the entity types the attribute applies to, as a JSON list in a string,
            e.g. V('["hive_table", "hive_db"]').
          - To build V(applicableEntityTypes) from a list, use the P(ansible.builtin.to_json#filter) filter as the last filter in the expression, so the result stays a string.
          - To read V(applicableEntityTypes) back as a list, use the P(ansible.builtin.from_json#filter) filter.
          - The value is compared as a string, so keep the same formatting between runs, including spaces after commas, to avoid reporting a change.
          - V(maxStrLength) is the maximum length of a string attribute, e.g. V("50").
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
      - Whether the business metadata type definition should be present or absent.
    type: str
    choices:
      - present
      - absent
    default: present
  force:
    description:
      - Delete the business metadata without Atlas validating that nothing references it.
      - Atlas refuses to delete business metadata that has non-indexable attributes unless this is set.
        The error reads V(Deletion not allowed for non-indexable Business Metadata).
      - Orphaned references to the deleted business metadata may remain on entities.
      - Only used when O(state=absent).
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
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Create business metadata for tables
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    description: Governance details for tables
    attribute_defs:
      - name: owner
        type_name: string
        is_optional: true
        options:
          applicableEntityTypes: '["hive_table"]'
          maxStrLength: "50"

# The option values are plain strings. applicableEntityTypes holds a JSON list
# encoded as a string, so a list of entity types can be written in three ways.

- name: Apply an attribute to several entity types using a literal JSON string
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    attribute_defs:
      - name: owner
        type_name: string
        is_optional: true
        options:
          applicableEntityTypes: '["hive_table", "hive_db"]'

- name: Use a folded block scalar for a long list of entity types
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    attribute_defs:
      - name: owner
        type_name: string
        is_optional: true
        options:
          applicableEntityTypes: >-
            ["hive_table", "hive_db", "hive_column", "hive_storagedesc"]

- name: Build the JSON string from a list variable
  vars:
    governed_types:
      - hive_table
      - hive_db
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    attribute_defs:
      - name: owner
        type_name: string
        is_optional: true
        options:
          # Keep to_json as the last filter so the value stays a string
          # and is not turned back into a list.
          applicableEntityTypes: "{{ governed_types | to_json }}"

- name: Set the maximum string length from a variable
  vars:
    owner_max_length: 50
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    attribute_defs:
      - name: owner
        type_name: string
        is_optional: true
        options:
          applicableEntityTypes: '["hive_table"]'
          # Option values must be strings, so quote literals ("50") and
          # convert variables.
          maxStrLength: "{{ owner_max_length | string }}"

- name: Share one set of options across several attributes
  vars:
    table_scope:
      applicableEntityTypes: '["hive_table"]'
      maxStrLength: "100"
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    attribute_defs:
      - name: owner
        type_name: string
        is_optional: true
        options: "{{ table_scope }}"
      - name: steward
        type_name: string
        is_optional: true
        options: "{{ table_scope }}"

- name: Widen the entity types an existing attribute applies to
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    attribute_defs:
      - name: owner
        type_name: string
        options:
          # The options map is replaced as a whole, so repeat every option
          # the attribute should keep.
          applicableEntityTypes: '["hive_table", "hive_db", "hive_column"]'
          maxStrLength: "50"

- name: Read the entity types back as a list
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
  register: governance

- name: Show the entity types of each attribute
  ansible.builtin.debug:
    msg: >-
      {{ item.name }} applies to
      {{ (item.options.applicableEntityTypes | from_json) | join(', ') }}
  loop: "{{ governance.business_metadata_def.attribute_defs }}"
  loop_control:
    label: "{{ item.name }}"

- name: Create business metadata with several attribute types
  cloudera.services.atlas_business_metadata_def:
    name: data_quality
    attribute_defs:
      - name: score
        type_name: int
        is_optional: true
        options:
          applicableEntityTypes: '["hive_table"]'
      - name: certified
        type_name: boolean
        is_optional: true
        options:
          applicableEntityTypes: '["hive_table"]'
      - name: reviewers
        type_name: array<string>
        is_optional: true
        options:
          applicableEntityTypes: '["hive_table"]'
          maxStrLength: "100"

- name: Preview a change without applying it
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    description: Governance details for tables and databases
  check_mode: true
  diff: true
  register: preview

- name: Remove business metadata
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    state: absent

- name: Remove business metadata that has non-indexable attributes
  cloudera.services.atlas_business_metadata_def:
    name: data_governance
    state: absent
    # Atlas will not validate references for non-indexable attributes, so
    # orphaned references may remain on entities.
    force: true
"""

RETURN = r"""
business_metadata_def:
  description: The business metadata type definition.
  type: dict
  returned: when O(state=present)
  contains:
    name:
      description: Name of the business metadata type definition.
      type: str
    guid:
      description: Atlas-assigned identifier.
      type: str
    category:
      description: Type category, always V(BUSINESS_METADATA).
      type: str
    description:
      description: Description of the business metadata type definition.
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
    attribute_defs:
      description: Attributes of the business metadata.
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
    AtlasBusinessMetadataDef,
    AtlasTypeDefClient,
    align_attribute_defs,
    extract_business_metadata_def_params,
)


class AtlasBusinessMetadataDefModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                **AtlasBusinessMetadataDef.argument_spec(),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
                force=dict(type="bool", default=False),
            ),
            required_if=[
                ["state", "present", ["name"]],
                ["state", "absent", ["name"]],
            ],
            supports_check_mode=True,
        )

        # Explicit attributes (not setattr) so type checkers can see them;
        # keep in sync with AtlasBusinessMetadataDef.argument_spec().
        self.name: Optional[str] = self.get_param("name")
        self.description: Optional[str] = self.get_param("description")
        self.type_version: Optional[str] = self.get_param("type_version")
        self.service_type: Optional[str] = self.get_param("service_type")
        self.options: Optional[Dict[str, Any]] = self.get_param("options")
        self.attribute_defs: Optional[List[Dict[str, Any]]] = self.get_param(
            "attribute_defs",
        )
        self.state: str = self.get_param("state")
        self.force: bool = self.get_param("force")

        self.changed = False
        self.diff = {}
        self.business_metadata_def: Optional[AtlasBusinessMetadataDef] = None

    def process(self) -> None:
        client = AtlasTypeDefClient(self.api_client)

        existing: Optional[AtlasBusinessMetadataDef] = None
        if self.name:
            existing = client.get_business_metadata_def_by_name(self.name)

        if self.state == "absent":
            if existing:
                self.changed = True

                if self.module._diff:
                    self.diff = {"before": to_dict(existing), "after": {}}

                if not self.module.check_mode:
                    client.delete_typedef_by_name(existing.name, force=self.force)

        elif self.state == "present":
            if not existing:
                incoming = build_from_params(
                    AtlasBusinessMetadataDef,
                    extract_business_metadata_def_params(self),
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {"before": {}, "after": to_dict(incoming)}

                if not self.module.check_mode:
                    self.business_metadata_def = client.create_business_metadata_def(
                        incoming,
                    )
                else:
                    self.business_metadata_def = incoming

            else:
                incoming = build_from_params(
                    AtlasBusinessMetadataDef,
                    extract_business_metadata_def_params(self),
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
                        self.business_metadata_def = (
                            client.update_business_metadata_def(incoming)
                        )
                    else:
                        self.business_metadata_def = incoming
                else:
                    self.business_metadata_def = existing

        else:
            self.module.fail_json(msg=f"Invalid state '{self.state}'.")


def main():
    result = AtlasBusinessMetadataDefModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        business_metadata_def=(
            to_dict(result.business_metadata_def)
            if result.business_metadata_def
            else {}
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
