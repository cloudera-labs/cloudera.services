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
module: ml_runtime_repo
short_description: Manage a Cloudera Machine Learning (CML) runtime repository
description:
  - Create, update, or delete a Cloudera Machine Learning (CML) runtime repository.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  name:
    description:
      - The name of the runtime repository.
      - Required when creating a repository.
      - Mutually exclusive with O(id).
    type: str
    required: false
  id:
    description:
      - The unique identifier of an existing runtime repository.
      - Mutually exclusive with O(name).
    type: int
    required: false
  repo_url:
    description:
      - The URL of the runtime repository.
      - Required when creating a repository.
    type: str
    required: false
    aliases:
      - repository_url
  state:
    description:
      - The declarative state of the runtime repository.
    type: str
    required: false
    default: present
    choices:
      - present
      - absent
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Create a runtime repository
  cloudera.services.ml_runtime_repo:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    name: internal-repo
    repo_url: https://repo.example.com/runtimes
    state: present

- name: Delete a runtime repository
  cloudera.services.ml_runtime_repo:
    id: 42
    state: absent
"""

RETURN = r"""
runtime_repo:
  description: The CML runtime repository details.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the runtime repository.
      type: int
      returned: always
    name:
      description: The name of the runtime repository.
      type: str
      returned: when available
    url:
      description: The URL of the runtime repository.
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

from dataclasses import replace
from typing import Any, Dict, NoReturn, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    diff_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlRuntimeRepo,
    MlRuntimeRepoClient,
)

CREATE_REQUIRED = ["name", "repo_url"]


class MlRuntimeRepoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                name=dict(type="str", required=False),
                id=dict(type="int", required=False),
                repo_url=dict(
                    type="str",
                    required=False,
                    aliases=["repository_url"],
                ),
                state=dict(
                    type="str",
                    required=False,
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[["name", "id"]],
            required_one_of=[["name", "id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.id = self.get_param("id")
        self.url = self.get_param("repo_url")
        self.state = self.get_param("state")

        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.runtime_repo: Optional[MlRuntimeRepo] = None

    def _fail(self, msg: str) -> NoReturn:
        # AnsibleModule.fail_json raises SystemExit at runtime; the trailing
        # raise is unreachable but marks this method as NoReturn so the type
        # checker can narrow values validated ahead of a failure.
        self.module.fail_json(msg=msg)
        raise SystemExit(msg)

    def _find_existing(self, client: MlRuntimeRepoClient) -> Optional[MlRuntimeRepo]:
        repos = client.list_runtime_repos()
        if self.id is not None:
            return next((r for r in repos if r.id == self.id), None)
        return next((r for r in repos if r.name == self.name), None)

    def process(self) -> None:
        client = MlRuntimeRepoClient(self.api_client)
        existing = self._find_existing(client)

        if self.state == "absent":
            self.runtime_repo = existing
            if existing:
                if not isinstance(existing.id, int):
                    self._fail("Runtime repo ID is invalid from existing repo.")
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = to_dict(existing)
                if not self.module.check_mode:
                    client.delete_runtime_repo(existing.id)
                    self.runtime_repo = None
            return

        # present implies the repo should exist.
        if not existing:
            missing = [k for k in CREATE_REQUIRED if self.get_param(k) is None]
            if missing:
                self.module.fail_json(
                    msg="Missing required parameters for creation: %s"
                    % ", ".join(sorted(missing)),
                )
            incoming = MlRuntimeRepo(name=self.name, url=self.url)
            self.changed = True
            if self.module._diff:
                self.diff["after"] = to_dict(incoming)
            if not self.module.check_mode:
                self.runtime_repo = client.create_runtime_repo(incoming)
            else:
                self.runtime_repo = incoming
            return

        # Update an existing repo.
        desired = replace(
            existing,
            name=self.name if self.name is not None else existing.name,
            url=self.url if self.url is not None else existing.url,
        )
        prev_config, next_config = diff_dict(existing, desired)

        self.runtime_repo = existing
        if prev_config or next_config:
            self.changed = True
            if self.module._diff:
                self.diff["before"] = prev_config
                self.diff["after"] = next_config
            if not self.module.check_mode:
                self.runtime_repo = client.update_runtime_repo(desired)
            else:
                self.runtime_repo = desired


def main():
    result = MlRuntimeRepoModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        runtime_repo=to_dict(result.runtime_repo) if result.runtime_repo else {},
        diff=result.diff,
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
