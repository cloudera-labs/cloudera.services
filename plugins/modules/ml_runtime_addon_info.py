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
module: ml_runtime_addon_info
short_description: Retrieve information about Cloudera Machine Learning (CML) runtime addons
description:
  - Retrieve information about the available Cloudera Machine Learning (CML) runtime addons.
  - The module can list all runtime addons or filter by a number of criteria.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  identifier:
    description:
      - Filter the runtime addons by identifier.
    type: str
    required: false
  component:
    description:
      - Filter the runtime addons by component.
    type: str
    required: false
    choices:
      - HadoopCLI
      - Spark
  name:
    description:
      - Filter the runtime addons by display name.
    type: str
    required: false
    aliases:
      - display_name
  status:
    description:
      - Filter the runtime addons by status.
    type: str
    required: false
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: List all runtime addons
  cloudera.services.ml_runtime_addon_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
  register: all_addons

- name: Filter runtime addons by component
  cloudera.services.ml_runtime_addon_info:
    component: Spark
"""

RETURN = r"""
runtime_addons:
  description: List of CML runtime addons.
  returned: always
  type: list
  elements: dict
  contains:
    identifier:
      description: The identifier of the runtime addon.
      type: str
      returned: always
    component:
      description: The component of the runtime addon.
      type: str
      returned: when available
    display_name:
      description: The display name of the runtime addon.
      type: str
      returned: when available
    status:
      description: The status of the runtime addon.
      type: str
      returned: when available
    manageable:
      description: Whether the runtime addon is manageable.
      type: bool
      returned: when available
    id:
      description: The numeric identifier of the runtime addon.
      type: int
      returned: when available
    created_at:
      description: The timestamp when the runtime addon was created.
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

from typing import Any, Dict, List

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlRuntimeAddon,
    MlRuntimeAddonClient,
)


class MlRuntimeAddonInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                identifier=dict(type="str", required=False),
                component=dict(
                    type="str",
                    required=False,
                    choices=["HadoopCLI", "Spark"],
                ),
                name=dict(type="str", required=False, aliases=["display_name"]),
                status=dict(type="str", required=False),
            ),
            supports_check_mode=True,
        )

        # Set parameters
        self.identifier = self.get_param("identifier")
        self.component = self.get_param("component")
        self.name = self.get_param("name")
        self.status = self.get_param("status")

        # Initialize result variables
        self.addon_list: List[MlRuntimeAddon] = []

    def _matches(self, addon: MlRuntimeAddon) -> bool:
        checks = {
            "identifier": self.identifier,
            "component": self.component,
            "display_name": self.name,
            "status": self.status,
        }
        for attr, wanted in checks.items():
            if wanted is not None and getattr(addon, attr) != wanted:
                return False
        return True

    def process(self) -> None:
        client = MlRuntimeAddonClient(self.api_client)
        self.addon_list = [a for a in client.list_runtime_addons() if self._matches(a)]


def main():
    result = MlRuntimeAddonInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        runtime_addons=[to_dict(addon) for addon in result.addon_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
