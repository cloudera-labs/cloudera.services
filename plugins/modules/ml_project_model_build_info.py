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
module: ml_project_model_build_info
short_description: Retrieve information about Cloudera Machine Learning (CML) project model builds
description:
  - Retrieve information about one or more Cloudera Machine Learning (CML) project model builds.
  - The module can list all builds for a model or filter by a number of criteria.
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
  name:
    description:
      - The name of the enclosing model.
      - Mutually exclusive with O(id).
    type: str
    required: false
    aliases:
      - model_name
  id:
    description:
      - The unique identifier of the enclosing model.
      - Mutually exclusive with O(name).
    type: str
    required: false
    aliases:
      - model_id
  comment:
    description:
      - Filter the builds by comment.
    type: str
    required: false
  crn:
    description:
      - Filter the builds by CRN.
    type: str
    required: false
  status:
    description:
      - Filter the builds by status.
    type: str
    required: false
    choices:
      - pending
      - succeeded
      - built
      - build failed
      - timedout
      - pushing
      - queued
      - unknown
  creator:
    description:
      - Filter the builds by creator details.
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
- name: List all builds for a model
  cloudera.services.ml_project_model_build_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    name: fraud-detector
  register: all_builds

- name: List successful builds for a model
  cloudera.services.ml_project_model_build_info:
    project_id: "{{ project_id }}"
    id: "{{ model_id }}"
    status: built

- name: List builds created by a user
  cloudera.services.ml_project_model_build_info:
    project_name: my-project
    name: fraud-detector
    creator:
      username: jdoe
"""

RETURN = r"""
model_builds:
  description: List of CML model builds.
  returned: always
  type: list
  elements: dict
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

from typing import Any, Dict, List, Optional

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


class MlProjectModelBuildInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                name=dict(type="str", required=False, aliases=["model_name"]),
                id=dict(type="str", required=False, aliases=["model_id"]),
                comment=dict(type="str", required=False),
                crn=dict(type="str", required=False),
                status=dict(
                    type="str",
                    required=False,
                    choices=[
                        "pending",
                        "succeeded",
                        "built",
                        "build failed",
                        "timedout",
                        "pushing",
                        "queued",
                        "unknown",
                    ],
                ),
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
            mutually_exclusive=[
                ["project_name", "project_id"],
                ["name", "id"],
            ],
            required_one_of=[
                ["project_name", "project_id"],
                ["name", "id"],
            ],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.name = self.get_param("name")
        self.id = self.get_param("id")
        self.comment = self.get_param("comment")
        self.crn = self.get_param("crn")
        self.status = self.get_param("status")
        self.creator = self.get_param("creator")

        # Initialize result variables
        self.build_list: List[MlModelBuild] = []

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

    def _resolve_model_id(self, project_id: str) -> str:
        client = MlModelClient(self.api_client)
        model: Optional[MlModel] = None
        if self.id:
            model = client.describe_model(project_id, self.id)
        else:
            model = next(
                (m for m in client.list_models(project_id) if m.name == self.name),
                None,
            )
        if not model:
            self.module.fail_json(msg="Model not found")
        if not isinstance(model.id, str):
            self.module.fail_json(msg="Model ID is invalid from resolved model.")
        return model.id

    def _matches(self, build: MlModelBuild) -> bool:
        checks = {
            "comment": self.comment,
            "crn": self.crn,
            "status": self.status,
        }
        for attr, wanted in checks.items():
            if wanted is not None and getattr(build, attr) != wanted:
                return False

        if self.creator:
            creator = build.creator
            if not isinstance(creator, dict):
                return False
            for key, wanted in self.creator.items():
                if wanted is not None and creator.get(key) != wanted:
                    return False

        return True

    def process(self) -> None:
        project_id = self._resolve_project_id()
        model_id = self._resolve_model_id(project_id)
        client = MlModelBuildClient(self.api_client)

        builds = [
            b for b in client.list_builds(project_id, model_id) if self._matches(b)
        ]
        # Return the most recently updated builds first.
        self.build_list = sorted(
            builds,
            key=lambda b: b.updated_at if isinstance(b.updated_at, str) else "",
            reverse=True,
        )


def main():
    result = MlProjectModelBuildInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        model_builds=[to_dict(build) for build in result.build_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
