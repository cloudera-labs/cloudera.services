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
module: ml_project_model
short_description: Manage a Cloudera Machine Learning (CML) project model
description:
  - Create, update, or delete a Cloudera Machine Learning (CML) project model.
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
  name:
    description:
      - The name of the model.
      - Required when creating a model.
      - Mutually exclusive with O(id).
    type: str
    required: false
    aliases:
      - model_name
  id:
    description:
      - The unique identifier of an existing model.
      - Mutually exclusive with O(name).
    type: str
    required: false
    aliases:
      - model_id
  desc:
    description:
      - The description of the model.
      - Required when creating a model.
    type: str
    required: false
    aliases:
      - description
  auth:
    description:
      - Whether authentication is enabled for the model.
    type: bool
    required: false
    aliases:
      - auth_enabled
  state:
    description:
      - The declarative state of the model.
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
- name: Create a model
  cloudera.services.ml_project_model:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    name: fraud-detector
    desc: Detects fraudulent transactions
    auth: true
    state: present

- name: Update a model's description
  cloudera.services.ml_project_model:
    project_id: "{{ project_id }}"
    name: fraud-detector
    desc: Detects fraudulent transactions (v2)

- name: Delete a model
  cloudera.services.ml_project_model:
    project_id: "{{ project_id }}"
    id: "{{ model_id }}"
    state: absent
"""

RETURN = r"""
model:
  description: The CML model details.
  returned: always
  type: dict
  contains:
    id:
      description: The unique identifier of the model.
      type: str
      returned: always
    name:
      description: The name of the model.
      type: str
      returned: always
    project_id:
      description: The identifier of the enclosing project.
      type: str
      returned: when available
    description:
      description: The description of the model.
      type: str
      returned: when available
    access_key:
      description: The access key of the model.
      type: str
      returned: when available
    auth_enabled:
      description: Whether authentication is enabled for the model.
      type: bool
      returned: when available
    creator:
      description: Details of the user that created the model.
      type: dict
      returned: when available
    created_at:
      description: The timestamp when the model was created.
      type: str
      returned: when available
    updated_at:
      description: The timestamp when the model was last updated.
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
    MlModel,
    MlModelClient,
    MlProject,
    MlProjectClient,
    validate_project_id,
)

CREATE_REQUIRED = ["desc"]


class MlProjectModelModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                name=dict(type="str", required=False, aliases=["model_name"]),
                id=dict(type="str", required=False, aliases=["model_id"]),
                desc=dict(type="str", required=False, aliases=["description"]),
                auth=dict(type="bool", required=False, aliases=["auth_enabled"]),
                state=dict(
                    type="str",
                    required=False,
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[
                ["name", "id"],
                ["project_name", "project_id"],
            ],
            required_one_of=[
                ["name", "id"],
                ["project_name", "project_id"],
            ],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.name = self.get_param("name")
        self.id = self.get_param("id")
        self.desc = self.get_param("desc")
        self.auth = self.get_param("auth")
        self.state = self.get_param("state")

        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.model: Optional[MlModel] = None

    def _fail(self, msg: str) -> NoReturn:
        # AnsibleModule.fail_json raises SystemExit at runtime; the trailing
        # raise is unreachable but marks this method as NoReturn so the type
        # checker can narrow values validated ahead of a failure.
        self.module.fail_json(msg=msg)
        raise SystemExit(msg)

    def _resolve_project(self) -> MlProject:
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
        return project

    def _incoming_model(self) -> MlModel:
        incoming = MlModel(name=self.name)
        if self.desc is not None:
            incoming.description = self.desc
        if self.auth is not None:
            incoming.auth_enabled = self.auth
        return incoming

    def process(self) -> None:
        project = self._resolve_project()
        project_id = project.id
        if not isinstance(project_id, str):
            self._fail("Project ID is invalid from resolved project.")
        client = MlModelClient(self.api_client)

        existing: Optional[MlModel] = None
        if self.id:
            existing = client.describe_model(project_id, self.id)
        else:
            existing = next(
                (m for m in client.list_models(project_id) if m.name == self.name),
                None,
            )

        if self.state == "absent":
            if existing:
                if not isinstance(existing.id, str):
                    self._fail("Model ID is invalid from existing model.")
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = to_dict(existing)
                if not self.module.check_mode:
                    client.delete_model(project_id, existing.id)
            return

        # present implies the model should exist.
        if not existing:
            missing = [k for k in CREATE_REQUIRED if self.get_param(k) is None]
            if missing:
                self.module.fail_json(
                    msg="Missing required parameters for creation: %s"
                    % ", ".join(sorted(missing)),
                )

            incoming = self._incoming_model()
            self.changed = True
            if self.module._diff:
                self.diff["after"] = to_dict(incoming)
            if not self.module.check_mode:
                self.model = client.create_model(project_id, incoming)
            else:
                self.model = incoming
        else:
            # Update an existing model
            desired = replace(
                existing,
                description=(
                    self.desc if self.desc is not None else existing.description
                ),
                auth_enabled=(
                    self.auth if self.auth is not None else existing.auth_enabled
                ),
            )

            prev_config, next_config = diff_dict(existing, desired)

            self.model = existing
            if prev_config or next_config:
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = prev_config
                    self.diff["after"] = next_config
                if not self.module.check_mode:
                    self.model = client.update_model(project_id, desired)
                else:
                    self.model = desired


def main():
    result = MlProjectModelModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        model=to_dict(result.model) if result.model else {},
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
