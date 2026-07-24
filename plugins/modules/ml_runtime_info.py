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
module: ml_runtime_info
short_description: Retrieve information about Cloudera Machine Learning (CML) runtimes
description:
  - Retrieve information about the available Cloudera Machine Learning (CML) runtimes.
  - The module can list all runtimes or filter by a number of criteria.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  image:
    description:
      - Filter the runtimes by image identifier.
    type: str
    required: false
    aliases:
      - image_identifier
  editor:
    description:
      - Filter the runtimes by editor.
    type: str
    required: false
  kernel:
    description:
      - Filter the runtimes by kernel.
    type: str
    required: false
  edition:
    description:
      - Filter the runtimes by edition.
    type: str
    required: false
  desc:
    description:
      - Filter the runtimes by description.
    type: str
    required: false
    aliases:
      - description
  version:
    description:
      - Filter the runtimes by full version.
    type: str
    required: false
    aliases:
      - full_version
  status:
    description:
      - Filter the runtimes by status.
    type: str
    required: false
    choices:
      - ENABLED
      - DISABLED
      - DEPRECATED
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: List all runtimes
  cloudera.services.ml_runtime_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
  register: all_runtimes

- name: Filter runtimes by editor and kernel
  cloudera.services.ml_runtime_info:
    editor: PBJ Workbench
    kernel: "Python 3.11"
"""

RETURN = r"""
runtimes:
  description: List of CML runtimes.
  returned: always
  type: list
  elements: dict
  contains:
    image_identifier:
      description: The image identifier of the runtime.
      type: str
      returned: always
    editor:
      description: The editor of the runtime.
      type: str
      returned: when available
    kernel:
      description: The kernel of the runtime.
      type: str
      returned: when available
    edition:
      description: The edition of the runtime.
      type: str
      returned: when available
    description:
      description: The description of the runtime.
      type: str
      returned: when available
    full_version:
      description: The full version of the runtime.
      type: str
      returned: when available
    status:
      description: The status of the runtime.
      type: str
      returned: when available
    register_user_id:
      description: The identifier of the user that registered the runtime.
      type: int
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
    MlRuntime,
    MlRuntimeClient,
)


class MlRuntimeInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                image=dict(type="str", required=False, aliases=["image_identifier"]),
                editor=dict(type="str", required=False),
                kernel=dict(type="str", required=False),
                edition=dict(type="str", required=False),
                desc=dict(type="str", required=False, aliases=["description"]),
                version=dict(type="str", required=False, aliases=["full_version"]),
                status=dict(
                    type="str",
                    required=False,
                    choices=["ENABLED", "DISABLED", "DEPRECATED"],
                ),
            ),
            supports_check_mode=True,
        )

        # Set parameters
        self.image = self.get_param("image")
        self.editor = self.get_param("editor")
        self.kernel = self.get_param("kernel")
        self.edition = self.get_param("edition")
        self.desc = self.get_param("desc")
        self.version = self.get_param("version")
        self.status = self.get_param("status")

        # Initialize result variables
        self.runtime_list: List[MlRuntime] = []

    def _matches(self, runtime: MlRuntime) -> bool:
        checks = {
            "image_identifier": self.image,
            "editor": self.editor,
            "kernel": self.kernel,
            "edition": self.edition,
            "description": self.desc,
            "full_version": self.version,
            "status": self.status,
        }
        for attr, wanted in checks.items():
            if wanted is not None and getattr(runtime, attr) != wanted:
                return False
        return True

    def process(self) -> None:
        client = MlRuntimeClient(self.api_client)
        self.runtime_list = [r for r in client.list_runtimes() if self._matches(r)]


def main():
    result = MlRuntimeInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        runtimes=[to_dict(runtime) for runtime in result.runtime_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
