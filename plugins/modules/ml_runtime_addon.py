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
module: ml_runtime_addon
short_description: Manage the status of Cloudera Machine Learning (CML) runtime addons
description:
  - Set the status of one or more Cloudera Machine Learning (CML) runtime addons.
  - Loading custom runtime addons (tarball upload) is not supported by this module.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  ids:
    description:
      - The numeric identifiers of the runtime addons to target.
      - Mutually exclusive with O(identifiers).
    type: list
    elements: int
    required: false
  identifiers:
    description:
      - The string identifiers of the runtime addons to target.
      - Mutually exclusive with O(ids).
    type: list
    elements: str
    required: false
  status:
    description:
      - The status to set on the target runtime addons.
    type: str
    required: true
    choices:
      - AVAILABLE
      - DISABLED
      - DEPRECATED
      - DELETED
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Disable a runtime addon by identifier
  cloudera.services.ml_runtime_addon:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    identifiers:
      - hadoop-cli-7.2.18
    status: DISABLED

- name: Enable runtime addons by id
  cloudera.services.ml_runtime_addon:
    ids:
      - 1
      - 2
    status: AVAILABLE
"""

RETURN = r"""
runtime_addon:
  description: The result of the status change.
  returned: always
  type: dict
  contains:
    rows_affected:
      description: The number of runtime addons whose status changed.
      type: int
      returned: always
    status:
      description: The status applied to the target runtime addons.
      type: str
      returned: always
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

from typing import Any, Dict

from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlRuntimeAddonClient,
)


class MlRuntimeAddonModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                ids=dict(type="list", elements="int", required=False),
                identifiers=dict(type="list", elements="str", required=False),
                status=dict(
                    type="str",
                    required=True,
                    choices=["AVAILABLE", "DISABLED", "DEPRECATED", "DELETED"],
                ),
            ),
            mutually_exclusive=[["ids", "identifiers"]],
            required_one_of=[["ids", "identifiers"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.ids = self.get_param("ids")
        self.identifiers = self.get_param("identifiers")
        self.status = self.get_param("status")

        # TODO Add diff support for runtime addon management and status change operations.
        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.runtime_addon: Dict[str, Any] = {}

    def process(self) -> None:
        client = MlRuntimeAddonClient(self.api_client)

        if self.module.check_mode:
            self.changed = True
            self.runtime_addon = {"status": self.status}
            return

        rows = client.update_addon_status(
            self.status,
            ids=self.ids,
            identifiers=self.identifiers,
        )
        self.changed = rows > 0
        self.runtime_addon = {"rows_affected": rows, "status": self.status}


def main():
    result = MlRuntimeAddonModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        runtime_addon=result.runtime_addon,
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
