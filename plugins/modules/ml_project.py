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
module: ml_project
short_description: Create and delete Cloudera Machine Learning (CML) projects
description:
  - Create, update, or delete a Cloudera Machine Learning (CML) project.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  name:
    description:
      - The name of the CML project.
      - Required when creating a project.
      - Mutually exclusive with O(id).
    type: str
    required: false
    aliases:
      - project
  id:
    description:
      - The unique identifier of an existing CML project.
      - Mutually exclusive with O(name).
    type: str
    required: false
    aliases:
      - project_id
  desc:
    description:
      - Description of the project.
    type: str
    required: false
    aliases:
      - description
  template:
    description:
      - Template to use when creating the CML project.
      - Only used when creating a project.
      - Local files are not yet supported.
    type: str
    required: false
    choices:
      - R
      - Python
      - PySpark
      - Scala
      - git
      - blank
  visibility:
    description:
      - Visibility of the project.
    type: str
    required: false
    choices:
      - public
      - private
      - organization
  git:
    description:
      - URL of the Git repository.
      - Required for O(template=git). Only used when creating a project.
    type: str
    required: false
    aliases:
      - git_url
  git_branch:
    description:
      - Branch for the Git repository.
      - Only used with O(template=git) when creating a project.
    type: str
    required: false
    aliases:
      - git_ref
  runtime:
    description:
      - Default engine type of the CML project.
    type: str
    required: false
    choices:
      - ml_runtime
      - legacy_engine
    aliases:
      - default_project_engine_type
  env:
    description:
      - Environment variables accessible from scripts within the project.
      - On update, the provided variables are merged with the project's existing variables.
    type: dict
    required: false
    aliases:
      - environment_variables
  permission:
    description:
      - Organization permission for the project.
    type: str
    required: false
    aliases:
      - organization_permission
  parent:
    description:
      - Name of the parent project.
    type: str
    required: false
    aliases:
      - parent_project
  memory:
    description:
      - Additional shared memory limit, in MB, for each engine in the project.
    type: int
    required: false
    aliases:
      - shared_memory_limit
  state:
    description:
      - The declarative state of the CML project.
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
- name: Create a blank CML project
  cloudera.services.ml_project:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    name: my-project
    desc: "Example project"
    state: present

- name: Create a project from a Git repository
  cloudera.services.ml_project:
    name: git-project
    template: git
    git: "https://github.com/example/repo.git"
    git_branch: main

- name: Update a project's environment variables
  cloudera.services.ml_project:
    name: my-project
    env:
      LOG_LEVEL: debug

- name: Delete a project by id
  cloudera.services.ml_project:
    id: abcd-1234-efgh-5678
    state: absent
"""

RETURN = r"""
project:
  description: The CML project details.
  returned: always
  type: dict
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

import json

from dataclasses import replace
from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    diff_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlProject,
    MlProjectClient,
    validate_project_id,
)


class MlProjectModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                name=dict(type="str", required=False, aliases=["project"]),
                id=dict(type="str", required=False, aliases=["project_id"]),
                desc=dict(type="str", required=False, aliases=["description"]),
                template=dict(
                    type="str",
                    required=False,
                    choices=[
                        "R",
                        "Python",
                        "PySpark",
                        "Scala",
                        "git",
                        "blank",
                    ],
                ),
                visibility=dict(
                    type="str",
                    required=False,
                    choices=["public", "organization", "private"],
                ),
                git=dict(type="str", required=False, aliases=["git_url"]),
                git_branch=dict(type="str", required=False, aliases=["git_ref"]),
                runtime=dict(
                    type="str",
                    required=False,
                    choices=["ml_runtime", "legacy_engine"],
                    aliases=["default_project_engine_type"],
                ),
                env=dict(
                    type="dict",
                    required=False,
                    aliases=["environment_variables"],
                ),
                permission=dict(
                    type="str",
                    required=False,
                    aliases=["organization_permission"],
                ),
                parent=dict(type="str", required=False, aliases=["parent_project"]),
                memory=dict(
                    type="int",
                    required=False,
                    aliases=["shared_memory_limit"],
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
            required_if=[
                ["template", "git", ["git"]],
            ],
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.id = self.get_param("id")
        self.desc = self.get_param("desc")
        self.template = self.get_param("template")
        self.visibility = self.get_param("visibility")
        self.git = self.get_param("git")
        self.git_branch = self.get_param("git_branch")
        self.runtime = self.get_param("runtime")
        self.env = self.get_param("env")
        self.permission = self.get_param("permission")
        self.parent = self.get_param("parent")
        self.memory = self.get_param("memory")
        self.state = self.get_param("state")

        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.project: Optional[MlProject] = None

    def _merged_environment(self, existing: MlProject) -> Any:
        """Merge the provided environment variables with the project's existing ones."""
        if self.env is None:
            return existing.environment
        current = existing.environment
        if isinstance(current, str):
            try:
                current = json.loads(current)
            except (ValueError, TypeError):
                current = {}
        if not isinstance(current, dict):
            current = {}
        return {**current, **self.env}

    def process(self) -> None:
        client = MlProjectClient(self.api_client)

        existing: Optional[MlProject] = None
        if self.id:
            if not validate_project_id(self.id):
                self.module.fail_json(msg="Invalid Project ID: %s" % self.id)
            existing = client.describe_project(self.id)
        else:
            existing = next(
                (p for p in client.list_projects() if p.name == self.name),
                None,
            )

        if self.state == "absent":
            if existing:
                if not isinstance(existing.id, str):
                    self.module.fail_json(
                        msg="Project ID is invalid from existing project.",
                    )

                self.changed = True

                if self.module._diff:
                    self.diff["before"] = to_dict(existing)

                if not self.module.check_mode:
                    client.delete_project(existing.id)
            return

        # state == "present"
        if not existing:
            if not self.name:
                self.module.fail_json(
                    msg="Parameter 'name' is required when creating a project.",
                )

            incoming = MlProject(name=self.name)
            if self.desc is not None:
                incoming.description = self.desc
            if self.visibility is not None:
                incoming.visibility = self.visibility
            if self.env is not None:
                incoming.environment = self.env
            if self.permission is not None:
                incoming.organization_permission = self.permission
            if self.parent is not None:
                incoming.parent_project = self.parent
            if self.memory is not None:
                incoming.shared_memory_limit = self.memory
            if self.git is not None:
                incoming.git_url = self.git
            if self.git_branch is not None:
                incoming.git_ref = self.git_branch
            if self.runtime is not None:
                incoming.default_project_engine_type = self.runtime
            incoming.template = self.template if self.template is not None else "blank"

            self.changed = True

            if self.module._diff:
                self.diff["after"] = to_dict(incoming)

            if not self.module.check_mode:
                self.project = client.create_project(incoming)
            else:
                self.project = incoming
            return

        # Update an existing project
        desired = replace(
            existing,
            description=self.desc if self.desc is not None else existing.description,
            visibility=(
                self.visibility if self.visibility is not None else existing.visibility
            ),
            organization_permission=(
                self.permission
                if self.permission is not None
                else existing.organization_permission
            ),
            parent_project=(
                self.parent if self.parent is not None else existing.parent_project
            ),
            shared_memory_limit=(
                self.memory if self.memory is not None else existing.shared_memory_limit
            ),
            default_engine_type=(
                self.runtime
                if self.runtime is not None
                else existing.default_engine_type
            ),
            environment=self._merged_environment(existing),
        )

        prev_config, next_config = diff_dict(existing, desired)

        if prev_config or next_config:
            self.changed = True

            if self.module._diff:
                self.diff["before"] = prev_config
                self.diff["after"] = next_config

            if not self.module.check_mode:
                self.project = client.update_project(desired)
            else:
                self.project = desired
        else:
            self.project = existing


def main():
    result = MlProjectModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        project=to_dict(result.project) if result.project else {},
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
