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
module: ml_project_file
short_description: Manage a file within a Cloudera Machine Learning (CML) project
description:
  - Upload or delete a file within a Cloudera Machine Learning (CML) project.
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
      - The destination path of the file within the project, relative to the project root.
    type: str
    required: true
    aliases:
      - dest
      - file
  src:
    description:
      - The path to a local file whose contents are uploaded.
      - Mutually exclusive with O(content).
      - Required when creating a file unless O(content) is set.
    type: path
    required: false
  content:
    description:
      - The literal contents to upload to the file.
      - Mutually exclusive with O(src).
      - Required when creating a file unless O(src) is set.
    type: str
    required: false
  force:
    description:
      - Whether to re-upload the file even when it already exists.
    type: bool
    required: false
    default: false
  state:
    description:
      - The declarative state of the file.
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
- name: Upload a file from literal content
  cloudera.services.ml_project_file:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    path: app.py
    content: |
      print("hello")
    state: present

- name: Upload a local file to a nested path
  cloudera.services.ml_project_file:
    project_id: "{{ project_id }}"
    path: src/run.py
    src: ./files/run.py

- name: Force re-upload of an existing file
  cloudera.services.ml_project_file:
    project_id: "{{ project_id }}"
    path: app.py
    content: "print('updated')"
    force: true

- name: Delete a file
  cloudera.services.ml_project_file:
    project_id: "{{ project_id }}"
    path: app.py
    state: absent
"""

RETURN = r"""
file:
  description: The project file details.
  returned: always
  type: dict
  contains:
    path:
      description: The path of the file, relative to the project root.
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

from typing import Any, Dict, Optional

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


class MlProjectFileModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                path=dict(type="str", required=True, aliases=["dest", "file"]),
                src=dict(type="path", required=False),
                content=dict(type="str", required=False),
                force=dict(type="bool", required=False, default=False),
                state=dict(
                    type="str",
                    required=False,
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[
                ["project_name", "project_id"],
                ["src", "content"],
            ],
            required_one_of=[["project_name", "project_id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.path = self.get_param("path").lstrip("/")
        self.src = self.get_param("src")
        self.content = self.get_param("content")
        self.force = self.get_param("force")
        self.state = self.get_param("state")

        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.file: Optional[MlFile] = None

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

    def _exists(self, client: MlProjectFileClient, project_id: str) -> bool:
        parent = self.path.rsplit("/", 1)[0] if "/" in self.path else ""
        base = self.path.rsplit("/", 1)[-1]
        return any(
            f.path.rsplit("/", 1)[-1] == base
            for f in client.list_files(project_id, parent)
        )

    def process(self) -> None:
        project_id = self._resolve_project_id()
        client = MlProjectFileClient(self.api_client)

        existing = self._exists(client, project_id)
        self.file = MlFile(path=self.path)

        if self.state == "absent":
            if existing:
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = {"path": self.path}
                if not self.module.check_mode:
                    client.delete_file(project_id, self.path)
            return

        # state == "present"
        if existing and not self.force:
            self.changed = False
            return

        if self.src is None and self.content is None:
            self.module.fail_json(
                msg="One of 'src' or 'content' is required to upload a file.",
            )

        self.changed = True
        if self.module._diff:
            self.diff["before"] = {"path": self.path} if existing else {}
            self.diff["after"] = {"path": self.path}
        if not self.module.check_mode:
            client.upload_file(
                project_id,
                self.path,
                content=self.content,
                src=self.src,
            )


def main():
    result = MlProjectFileModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        file=to_dict(result.file) if result.file else {},
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
