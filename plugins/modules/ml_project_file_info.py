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
module: ml_project_file_info
short_description: Retrieve information about files within a Cloudera Machine Learning (CML) project
description:
  - List the files and directories within a Cloudera Machine Learning (CML) project path.
  - Paths are relative to the project root (V(/home/cdsw)).
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  project_name:
    description:
      - The name of the enclosing project.
      - Mutually exclusive with O(project_id).
    type: str
    required: false
  project_id:
    description:
      - The unique identifier of the enclosing project.
      - Mutually exclusive with O(project_name).
    type: str
    required: false
  path:
    description:
      - The path within the project to list, relative to the project root.
      - Defaults to the project root.
    type: str
    required: false
    default: ""
    aliases:
      - dir
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: List files at the project root
  cloudera.services.ml_project_file_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
  register: root_files

- name: List files within a subdirectory
  cloudera.services.ml_project_file_info:
    project_id: "{{ project_id }}"
    path: src
"""

RETURN = r"""
files:
  description: List of files and directories within the project path.
  returned: always
  type: list
  elements: dict
  contains:
    path:
      description: The path of the file or directory, relative to the project root.
      type: str
      returned: always
    is_dir:
      description: Whether the path is a directory.
      type: bool
      returned: when available
    file_size:
      description: The size of the file in bytes.
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

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlFile,
    MlProject,
    MlProjectClient,
    MlProjectFileClient,
    validate_project_id,
)


class MlProjectFileInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                path=dict(type="str", required=False, default="", aliases=["dir"]),
            ),
            mutually_exclusive=[["project_name", "project_id"]],
            required_one_of=[["project_name", "project_id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.path = self.get_param("path").lstrip("/")

        # Initialize result variables
        self.file_list: List[MlFile] = []

    def _resolve_project_id(self) -> str:
        client = MlProjectClient(self.api_client)
        project: Optional[MlProject] = None
        if self.project_id:
            if not validate_project_id(self.project_id):
                self.module.fail_json(msg="Invalid Project ID: %s" % self.project_id)
            project = client.describe_project(self.project_id)
        else:
            project = next(
                (p for p in client.list_projects() if p.name == self.project_name),
                None,
            )
        if not project:
            self.module.fail_json(msg="Project not found")
        if not isinstance(project.id, str):
            self.module.fail_json(msg="Project ID is invalid from resolved project.")
        return project.id

    def process(self) -> None:
        project_id = self._resolve_project_id()
        client = MlProjectFileClient(self.api_client)
        self.file_list = client.list_files(project_id, self.path)


def main():
    result = MlProjectFileInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        files=[to_dict(f) for f in result.file_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
