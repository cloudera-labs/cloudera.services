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
module: atlas_enum_def
short_description: Manage enum type definitions in Apache Atlas
description:
  - Create, update, or delete enum type definitions in Apache Atlas.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the enum type definition.
      - Required when O(state=present).
    type: str
  description:
    description:
      - Description of the enum type definition.
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
  default_value:
    description:
      - Value of the element used as the default.
    type: str
  element_defs:
    description:
      - Elements of the enum.
      - Replaces the existing elements; Atlas may reject removing elements that are in use.
    type: list
    elements: dict
    suboptions:
      value:
        description:
          - Value of the element.
        type: str
        required: true
      ordinal:
        description:
          - Position of the element. Assigned by Atlas when omitted.
        type: int
      description:
        description:
          - Description of the element.
        type: str
  state:
    description:
      - Whether the enum type definition should be present or absent.
    type: str
    choices:
      - present
      - absent
    default: present
extends_documentation_fragment:
  - cloudera.services.services_client
attributes:
  check_mode:
    support: full
  diff_mode:
    support: full
    platforms: all
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Create an enum type definition
  cloudera.services.atlas_enum_def:
    name: traffic_light
    description: Traffic light colors
    element_defs:
      - value: RED
      - value: GREEN

- name: Remove an enum type definition
  cloudera.services.atlas_enum_def:
    name: traffic_light
    state: absent
"""

RETURN = r"""
enum_def:
  description: The enum type definition.
  type: dict
  returned: when O(state=present)
  contains:
    name:
      description: Name of the enum type definition.
      type: str
    guid:
      description: Atlas-assigned identifier.
      type: str
    category:
      description: Type category, always V(ENUM).
      type: str
    description:
      description: Description of the enum type definition.
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
    default_value:
      description: Value of the default element.
      type: str
    element_defs:
      description: Elements of the enum.
      type: list
      elements: dict
      contains:
        value:
          description: Value of the element.
          type: str
        ordinal:
          description: Position of the element.
          type: int
        description:
          description: Description of the element.
          type: str
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
    AtlasEnumDef,
    AtlasTypeDefClient,
    align_enum_elements,
    extract_enum_def_params,
)


class AtlasEnumDefModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                **AtlasEnumDef.argument_spec(),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            required_if=[
                ["state", "present", ["name"]],
            ],
            supports_check_mode=True,
        )

        # Explicit attributes (not setattr) so type checkers can see them;
        # keep in sync with AtlasEnumDef.argument_spec().
        self.name: Optional[str] = self.get_param("name")
        self.description: Optional[str] = self.get_param("description")
        self.type_version: Optional[str] = self.get_param("type_version")
        self.service_type: Optional[str] = self.get_param("service_type")
        self.options: Optional[Dict[str, Any]] = self.get_param("options")
        self.default_value: Optional[str] = self.get_param("default_value")
        self.element_defs: Optional[List[Dict[str, Any]]] = self.get_param(
            "element_defs",
        )
        self.state: str = self.get_param("state")

        self.changed = False
        self.diff = {}
        self.enum_def: Optional[AtlasEnumDef] = None

    def process(self) -> None:
        client = AtlasTypeDefClient(self.api_client)

        existing: Optional[AtlasEnumDef] = None
        if self.name:
            existing = client.get_enum_def_by_name(self.name)

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
                    AtlasEnumDef,
                    extract_enum_def_params(self),
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {"before": {}, "after": to_dict(incoming)}

                if not self.module.check_mode:
                    self.enum_def = client.create_enum_def(incoming)
                else:
                    self.enum_def = incoming

            else:
                incoming = build_from_params(
                    AtlasEnumDef,
                    extract_enum_def_params(self),
                    existing=existing,
                )

                if isinstance(incoming.element_defs, list) and isinstance(
                    existing.element_defs,
                    list,
                ):
                    incoming.element_defs = align_enum_elements(
                        incoming.element_defs,
                        existing.element_defs,
                    )

                prev_config, next_config = diff_dict(existing, incoming)

                if prev_config or next_config:
                    self.changed = True

                    if self.module._diff:
                        self.diff = {"before": prev_config, "after": next_config}

                    if not self.module.check_mode:
                        self.enum_def = client.update_enum_def(incoming)
                    else:
                        self.enum_def = incoming
                else:
                    self.enum_def = existing

        else:
            self.module.fail_json(msg=f"Invalid state '{self.state}'.")


def main():
    result = AtlasEnumDefModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        enum_def=to_dict(result.enum_def) if result.enum_def else {},
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
