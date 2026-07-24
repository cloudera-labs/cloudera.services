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
module: ml_project_model_info
short_description: Retrieve information about Cloudera Machine Learning (CML) project models
description:
  - Retrieve information about one or more Cloudera Machine Learning (CML) project models.
  - The module can list all models within a project or filter by a number of criteria.
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
  id:
    description:
      - The unique identifier of a single model to retrieve.
    type: str
    required: false
    aliases:
      - model_id
  name:
    description:
      - Filter the models by name.
    type: str
    required: false
    aliases:
      - model
  desc:
    description:
      - Filter the models by description.
    type: str
    required: false
    aliases:
      - description
  auth:
    description:
      - Filter the models by whether authentication is enabled.
    type: bool
    required: false
    aliases:
      - auth_enabled
  creator:
    description:
      - Filter the models by creator details.
    type: dict
    required: false
    suboptions:
      name:
        description:
          - The display name of the creator.
        type: str
        required: false
      username:
        description:
          - The username of the creator.
        type: str
        required: false
      email:
        description:
          - The email address of the creator.
        type: str
        required: false
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: List all models within a project
  cloudera.services.ml_project_model_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
  register: all_models

- name: Get a single model by id
  cloudera.services.ml_project_model_info:
    project_id: "{{ project_id }}"
    id: "{{ model_id }}"

- name: List models created by a user
  cloudera.services.ml_project_model_info:
    project_name: my-project
    creator:
      username: jdoe

- name: List models with authentication enabled
  cloudera.services.ml_project_model_info:
    project_name: my-project
    auth: true
"""

RETURN = r"""
models:
  description: List of CML models.
  returned: always
  type: list
  elements: dict
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

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
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


class MlProjectModelInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["model_id"]),
                name=dict(type="str", required=False, aliases=["model"]),
                desc=dict(type="str", required=False, aliases=["description"]),
                auth=dict(type="bool", required=False, aliases=["auth_enabled"]),
                creator=dict(
                    type="dict",
                    required=False,
                    options=dict(
                        name=dict(type="str", required=False),
                        username=dict(type="str", required=False),
                        email=dict(type="str", required=False),
                    ),
                ),
            ),
            mutually_exclusive=[["project_name", "project_id"]],
            required_one_of=[["project_name", "project_id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.id = self.get_param("id")
        self.name = self.get_param("name")
        self.desc = self.get_param("desc")
        self.auth = self.get_param("auth")
        self.creator = self.get_param("creator")

        # Initialize result variables
        self.model_list: List[MlModel] = []

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

    def _matches(self, model: MlModel) -> bool:
        checks = {
            "name": self.name,
            "description": self.desc,
        }
        for attr, wanted in checks.items():
            if wanted is not None and getattr(model, attr) != wanted:
                return False

        if self.auth is not None and model.auth_enabled != self.auth:
            return False

        if self.creator:
            creator = model.creator
            if not isinstance(creator, dict):
                return False
            for key, wanted in self.creator.items():
                if wanted is not None and creator.get(key) != wanted:
                    return False

        return True

    def process(self) -> None:
        project_id = self._resolve_project_id()
        client = MlModelClient(self.api_client)

        if self.id:
            model = client.describe_model(project_id, self.id)
            if model:
                self.model_list.append(model)
            return

        self.model_list = [
            m for m in client.list_models(project_id) if self._matches(m)
        ]


def main():
    result = MlProjectModelInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        models=[to_dict(model) for model in result.model_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
