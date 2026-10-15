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
module: atlas_typedef_info
short_description: Retrieve type definitions from Apache Atlas
description:
  - Retrieve a type definition by name, or list the headers of all type definitions.
  - Without O(name), only the headers (guid, name, category, service type) are returned.
  - With O(name), the full type definition is returned.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the type definition to retrieve.
      - When set, O(category) is ignored.
    type: str
  category:
    description:
      - Only list type definitions of this category.
    type: str
    choices:
      - enum
      - struct
      - classification
      - entity
      - relationship
      - business_metadata
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
- name: List all type definition headers
  cloudera.services.atlas_typedef_info:

- name: List enum type definition headers
  cloudera.services.atlas_typedef_info:
    category: enum

- name: Retrieve a type definition by name
  cloudera.services.atlas_typedef_info:
    name: traffic_light
"""

RETURN = r"""
typedefs:
  description:
    - Type definitions matching the criteria.
    - Headers when listing, the full type definition when O(name) is set.
    - Empty when O(name) does not exist.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Name of the type definition.
      type: str
      returned: always
    guid:
      description: Atlas-assigned identifier.
      type: str
      returned: always
    category:
      description: Type category, e.g. V(ENUM) or V(CLASSIFICATION).
      type: str
      returned: always
    service_type:
      description: Name of the service that owns the type definition.
      type: str
      returned: sometimes
    options:
      description: Free-form options of the type definition. Keys are returned verbatim.
      type: dict
      returned: when O(name) is set
"""

from typing import Any, Dict, List

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasTypeDefClient,
)


class AtlasTypeDefInfoModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                name=dict(type="str", required=False),
                category=dict(
                    type="str",
                    required=False,
                    choices=[
                        "enum",
                        "struct",
                        "classification",
                        "entity",
                        "relationship",
                        "business_metadata",
                    ],
                ),
            ),
            supports_check_mode=True,
        )

        self.name = self.get_param("name")
        self.category = self.get_param("category")

        self.typedefs: List[Dict[str, Any]] = []

    def process(self) -> None:
        client = AtlasTypeDefClient(self.api_client)

        if self.name:
            typedef = client.get_typedef_by_name(self.name)
            if typedef:
                self.typedefs.append(typedef)
        else:
            headers = client.list_typedef_headers()
            if self.category:
                wanted = self.category.upper()
                headers = [h for h in headers if h.get("category") == wanted]
            self.typedefs.extend(headers)


def main():
    result = AtlasTypeDefInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        typedefs=result.typedefs,
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
