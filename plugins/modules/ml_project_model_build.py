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
module: ml_project_model_build
short_description: Manage a Cloudera Machine Learning (CML) project model build
description:
  - Create or delete a Cloudera Machine Learning (CML) project model build.
  - Model builds are immutable; an existing build is never updated in place. To
    change a build, create a new one or delete and recreate it.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  project_name:
    description:
      - The name of the enclosing project for the model.
      - Mutually exclusive with O(project_id).
    type: str
    required: false
  project_id:
    description:
      - The unique identifier of the enclosing project for the model.
      - Mutually exclusive with O(project_name).
    type: str
    required: false
  model_name:
    description:
      - The name of the enclosing model for the build.
      - Mutually exclusive with O(model_id).
    type: str
    required: false
  model_id:
    description:
      - The unique identifier of the enclosing model for the build.
      - Mutually exclusive with O(model_name).
    type: str
    required: false
  id:
    description:
      - The unique identifier of an existing build.
      - Required to reference an existing build, e.g. to delete it.
      - Mutually exclusive with O(file).
    type: str
    required: false
    aliases:
      - build_id
  comment:
    description:
      - A comment for the build.
      - Applied only on build creation.
    type: str
    required: false
  file:
    description:
      - The entrypoint file for the build.
      - Required when creating a build.
      - Mutually exclusive with O(id).
    type: str
    required: false
    aliases:
      - file_path
  function:
    description:
      - The entrypoint function within O(file) for the build.
      - Required when creating a build.
    type: str
    required: false
    aliases:
      - function_name
  kernel:
    description:
      - The kernel to use for the build.
      - Requires O(runtime).
    type: str
    required: false
    choices:
      - python3
      - python2
      - r
  addons:
    description:
      - A list of runtime addon identifiers for the build.
      - Requires O(runtime).
    type: list
    elements: str
    required: false
    aliases:
      - runtime_addon_ids
      - runtime_addon_identifiers
  runtime:
    description:
      - The container runtime identifier for the build.
      - Required when creating a build.
    type: str
    required: false
    aliases:
      - runtime_id
      - runtime_identifier
  state:
    description:
      - The declarative state of the build.
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
- name: Create a model build
  cloudera.services.ml_project_model_build:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    model_name: fraud-detector
    file: predict.py
    function: predict
    runtime: "{{ runtime_id }}"
    comment: Initial build
    state: present

- name: Delete a model build
  cloudera.services.ml_project_model_build:
    project_id: "{{ project_id }}"
    model_id: "{{ model_id }}"
    id: "{{ build_id }}"
    state: absent
"""

RETURN = r"""
build:
  description: The CML model build details.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the build.
      type: str
      returned: always
    model_id:
      description: The identifier of the enclosing model.
      type: str
      returned: when available
    project_id:
      description: The identifier of the enclosing project.
      type: str
      returned: when available
    status:
      description: The status of the build.
      type: str
      returned: when available
    file_path:
      description: The entrypoint file for the build.
      type: str
      returned: when available
    function_name:
      description: The entrypoint function for the build.
      type: str
      returned: when available
    kernel:
      description: The kernel for the build.
      type: str
      returned: when available
    runtime_identifier:
      description: The container runtime identifier for the build.
      type: str
      returned: when available
    runtime_addon_identifiers:
      description: The runtime addon identifiers for the build.
      type: list
      elements: str
      returned: when available
    comment:
      description: The comment for the build.
      type: str
      returned: when available
    crn:
      description: The CRN of the build.
      type: str
      returned: when available
    creator:
      description: Details of the user that created the build.
      type: dict
      returned: when available
    created_at:
      description: The timestamp when the build was created.
      type: str
      returned: when available
    updated_at:
      description: The timestamp when the build was last updated.
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

from typing import Any, Dict, NoReturn, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlModel,
    MlModelClient,
    MlModelBuild,
    MlModelBuildClient,
    MlProject,
    MlProjectClient,
    validate_project_id,
)


class MlProjectModelBuildModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                model_name=dict(type="str", required=False),
                model_id=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["build_id"]),
                comment=dict(type="str", required=False),
                file=dict(type="str", required=False, aliases=["file_path"]),
                function=dict(type="str", required=False, aliases=["function_name"]),
                kernel=dict(
                    type="str",
                    required=False,
                    choices=["python3", "python2", "r"],
                ),
                addons=dict(
                    type="list",
                    elements="str",
                    required=False,
                    aliases=["runtime_addon_ids", "runtime_addon_identifiers"],
                ),
                runtime=dict(
                    type="str",
                    required=False,
                    aliases=["runtime_id", "runtime_identifier"],
                ),
                state=dict(
                    type="str",
                    required=False,
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[
                ["project_name", "project_id"],
                ["model_name", "model_id"],
                ["id", "file"],
            ],
            required_one_of=[
                ["project_name", "project_id"],
                ["model_name", "model_id"],
                ["id", "file"],
            ],
            required_together=[
                ["file", "function", "runtime"],
            ],
            required_by={
                "kernel": ["runtime"],
                "addons": ["runtime"],
            },
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.model_name = self.get_param("model_name")
        self.model_id = self.get_param("model_id")
        self.id = self.get_param("id")
        self.comment = self.get_param("comment")
        self.file = self.get_param("file")
        self.function = self.get_param("function")
        self.kernel = self.get_param("kernel")
        self.addons = self.get_param("addons")
        self.runtime = self.get_param("runtime")
        self.state = self.get_param("state")

        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.build: Optional[MlModelBuild] = None

    def _fail(self, msg: str) -> NoReturn:
        # AnsibleModule.fail_json raises SystemExit at runtime; the trailing
        # raise is unreachable but marks this method as NoReturn so the type
        # checker can narrow values validated ahead of a failure.
        self.module.fail_json(msg=msg)
        raise SystemExit(msg)

    def _resolve_project_id(self) -> str:
        client = MlProjectClient(self.api_client)
        project: Optional[MlProject] = None
        if self.project_id:
            if not validate_project_id(self.project_id):
                self._fail("Invalid Project ID: %s" % self.project_id)
            project = client.describe_project(self.project_id)
        else:
            project = next(
                (p for p in client.list_projects() if p.name == self.project_name),
                None,
            )
        if not project:
            self._fail("Project not found")
        if not isinstance(project.id, str):
            self._fail("Project ID is invalid from resolved project.")
        return project.id

    def _resolve_model_id(self, project_id: str) -> str:
        client = MlModelClient(self.api_client)
        model: Optional[MlModel] = None
        if self.model_id:
            model = client.describe_model(project_id, self.model_id)
        else:
            model = next(
                (
                    m
                    for m in client.list_models(project_id)
                    if m.name == self.model_name
                ),
                None,
            )
        if not model:
            self._fail("Model not found")
        if not isinstance(model.id, str):
            self._fail("Model ID is invalid from resolved model.")
        return model.id

    def _incoming_build(self) -> MlModelBuild:
        incoming = MlModelBuild()
        if self.file is not None:
            incoming.file_path = self.file
        if self.function is not None:
            incoming.function_name = self.function
        if self.kernel is not None:
            incoming.kernel = self.kernel
        if self.addons is not None:
            incoming.runtime_addon_identifiers = self.addons
        if self.runtime is not None:
            incoming.runtime_identifier = self.runtime
        if self.comment is not None:
            incoming.comment = self.comment
        return incoming

    def process(self) -> None:
        project_id = self._resolve_project_id()
        model_id = self._resolve_model_id(project_id)
        client = MlModelBuildClient(self.api_client)

        existing: Optional[MlModelBuild] = None
        if self.id:
            existing = client.describe_build(project_id, model_id, self.id)

        if self.state == "absent":
            if existing:
                if not isinstance(existing.id, str):
                    self._fail("Build ID is invalid from existing build.")
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = to_dict(existing)
                if not self.module.check_mode:
                    client.delete_build(project_id, model_id, existing.id)
            return

        # present implies the build should exist.
        if existing:
            # Model builds are immutable; return the existing build unchanged.
            self.build = existing
            return

        if self.id:
            # An explicit build id was given but no such build exists.
            self._fail("Build not found")

        incoming = self._incoming_build()
        self.changed = True
        if self.module._diff:
            self.diff["after"] = to_dict(incoming)
        if not self.module.check_mode:
            self.build = client.create_build(project_id, model_id, incoming)
        else:
            self.build = incoming


def main():
    result = MlProjectModelBuildModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        build=to_dict(result.build) if result.build else {},
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
