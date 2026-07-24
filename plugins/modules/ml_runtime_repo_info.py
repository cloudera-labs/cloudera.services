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
module: ml_runtime_repo_info
short_description: Retrieve information about Cloudera Machine Learning (CML) runtime repositories
description:
  - Retrieve information about the Cloudera Machine Learning (CML) runtime repositories.
  - The module can list all repositories or filter by a number of criteria.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  name:
    description:
      - Filter the runtime repositories by name.
    type: str
    required: false
  id:
    description:
      - Filter to a single runtime repository by identifier.
    type: int
    required: false
  repo_url:
    description:
      - Filter the runtime repositories by URL.
    type: str
    required: false
    aliases:
      - repository_url
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: List all runtime repositories
  cloudera.services.ml_runtime_repo_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
  register: all_repos

- name: Get a runtime repository by name
  cloudera.services.ml_runtime_repo_info:
    name: internal-repo
"""

RETURN = r"""
runtime_repos:
  description: List of CML runtime repositories.
  returned: always
  type: list
  elements: dict
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

from typing import Any, Dict, List

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlRuntimeRepo,
    MlRuntimeRepoClient,
)


class MlRuntimeRepoInfoModule(MlServicesModule):
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
            ),
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.id = self.get_param("id")
        self.url = self.get_param("repo_url")

        # Initialize result variables
        self.repo_list: List[MlRuntimeRepo] = []

    def _matches(self, repo: MlRuntimeRepo) -> bool:
        checks = {
            "name": self.name,
            "url": self.url,
        }
        for attr, wanted in checks.items():
            if wanted is not None and getattr(repo, attr) != wanted:
                return False
        if self.id is not None and repo.id != self.id:
            return False
        return True

    def process(self) -> None:
        client = MlRuntimeRepoClient(self.api_client)
        self.repo_list = [r for r in client.list_runtime_repos() if self._matches(r)]


def main():
    result = MlRuntimeRepoInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        runtime_repos=[to_dict(repo) for repo in result.repo_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
