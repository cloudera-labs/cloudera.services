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
module: ml_project_info
short_description: Retrieve information about Cloudera Machine Learning (CML) projects
description:
  - Retrieve information about one or more Cloudera Machine Learning (CML) projects.
  - The module can list all projects or filter by name or id.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  name:
    description:
      - The name of the project to retrieve.
      - This parameter is mutually exclusive with O(id).
    type: str
    required: false
    aliases:
      - project
  id:
    description:
      - The unique identifier of the project to retrieve.
      - This parameter is mutually exclusive with O(name).
    type: str
    required: false
    aliases:
      - project_id
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: List all CML projects
  cloudera.services.ml_project_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
  register: all_projects

- name: Get information about a specific project by name
  cloudera.services.ml_project_info:
    name: my-project
  register: project_by_name

- name: Get information about a specific project by id
  cloudera.services.ml_project_info:
    id: abcd-1234-efgh-5678
  register: project_by_id
"""

RETURN = r"""
projects:
  description: List of CML projects.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the project.
      type: str
      returned: always
    name:
      description: The name of the project.
      type: str
      returned: always
    description:
      description: The description of the project.
      type: str
      returned: when available
    visibility:
      description: The visibility of the project.
      type: str
      returned: when available
    environment:
      description: The environment variables of the project.
      type: dict
      returned: when available
    organization_permission:
      description: The organization permission for the project.
      type: str
      returned: when available
    parent_project:
      description: The name of the parent project.
      type: str
      returned: when available
    shared_memory_limit:
      description: The additional shared memory limit, in MB, for each engine in the project.
      type: int
      returned: when available
    default_project_engine_type:
      description: The default engine type set when the project was created.
      type: str
      returned: when available
    default_engine_type:
      description: The default engine type of the project.
      type: str
      returned: when available
    template:
      description: The template used to create the project.
      type: str
      returned: when available
    git_url:
      description: The URL of the Git repository backing the project.
      type: str
      returned: when available
    git_ref:
      description: The Git repository branch or reference backing the project.
      type: str
      returned: when available
    creator:
      description: Details of the user that created the project.
      type: dict
      returned: when available
      contains:
        username:
          description: The username of the creator.
          type: str
          returned: when available
        name:
          description: The display name of the creator.
          type: str
          returned: when available
        email:
          description: The email address of the creator.
          type: str
          returned: when available
    created_at:
      description: The timestamp when the project was created.
      type: str
      returned: when available
    updated_at:
      description: The timestamp when the project was last updated.
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
    MlProject,
    MlProjectClient,
    validate_project_id,
)


class MlProjectInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                name=dict(type="str", required=False, aliases=["project"]),
                id=dict(type="str", required=False, aliases=["project_id"]),
            ),
            mutually_exclusive=[["name", "id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.id = self.get_param("id")

        # Initialize result variables
        self.project_list: List[MlProject] = []

    def process(self) -> None:
        client = MlProjectClient(self.api_client)
        if self.id:
            if not validate_project_id(self.id):
                self.module.fail_json(msg="Invalid Project ID: %s" % self.id)
            project = client.describe_project(self.id)
            if project:
                self.project_list.append(project)
        else:
            projects = client.list_projects()
            if self.name:
                projects = [p for p in projects if p.name == self.name]
            self.project_list.extend(projects)


def main():
    result = MlProjectInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        projects=[to_dict(project) for project in result.project_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
