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
module: ml_project_model_deployment_info
short_description: Retrieve information about Cloudera Machine Learning (CML) project model deployments
description:
  - Retrieve information about one or more Cloudera Machine Learning (CML) project model deployments.
  - The module can list all deployments for a build or filter by a number of criteria.
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
      - Mutually exclusive with O(model_id).
    type: str
    required: false
    aliases:
      - model_name
  model_id:
    description:
      - The unique identifier of the enclosing model.
      - Mutually exclusive with O(name).
    type: str
    required: false
  id:
    description:
      - The unique identifier of the build whose deployments to retrieve.
      - If not set, the most recent successful build is used.
    type: str
    required: false
    aliases:
      - build_id
  status:
    description:
      - Filter the deployments by status.
    type: str
    required: false
    choices:
      - pending
      - deployed
  deployer:
    description:
      - Filter the deployments by deployer details.
    type: dict
    required: false
    suboptions:
      name:
        description:
          - The display name of the deployer.
        type: str
        required: false
      username:
        description:
          - The username of the deployer.
        type: str
        required: false
      email:
        description:
          - The email address of the deployer.
        type: str
        required: false
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: List all deployments for the latest build of a model
  cloudera.services.ml_project_model_deployment_info:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    name: fraud-detector
  register: all_deployments

- name: List deployed deployments
  cloudera.services.ml_project_model_deployment_info:
    project_id: "{{ project_id }}"
    model_id: "{{ model_id }}"
    status: deployed

- name: List deployments by a deployer
  cloudera.services.ml_project_model_deployment_info:
    project_name: my-project
    name: fraud-detector
    deployer:
      username: jdoe
"""

RETURN = r"""
model_deployments:
  description: List of CML model deployments.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the deployment.
      type: str
      returned: always
    build_id:
      description: The identifier of the enclosing build.
      type: str
      returned: when available
    model_id:
      description: The identifier of the enclosing model.
      type: str
      returned: when available
    project_id:
      description: The identifier of the enclosing project.
      type: str
      returned: when available
    status:
      description: The status of the deployment.
      type: str
      returned: when available
    cpu:
      description: The vCPU allocated to the deployment.
      type: float
      returned: when available
    memory:
      description: The RAM allocated to the deployment, in GB.
      type: float
      returned: when available
    nvidia_gpus:
      description: The count of Nvidia GPUs allocated to the deployment.
      type: int
      returned: when available
    replicas:
      description: The replica count of the deployment.
      type: int
      returned: when available
    environment:
      description: The environment variables of the deployment.
      type: dict
      returned: when available
    deployer:
      description: Details of the user that deployed the model.
      type: dict
      returned: when available
    created_at:
      description: The timestamp when the deployment was created.
      type: str
      returned: when available
    updated_at:
      description: The timestamp when the deployment was last updated.
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
    MlModelDeployment,
    MlModelDeploymentClient,
    MlProject,
    MlProjectClient,
    validate_project_id,
)


class MlProjectModelDeploymentInfoModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                name=dict(type="str", required=False, aliases=["model_name"]),
                model_id=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["build_id"]),
                status=dict(
                    type="str",
                    required=False,
                    choices=["pending", "deployed"],
                ),
                deployer=dict(
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
                ["name", "model_id"],
            ],
            required_one_of=[
                ["project_name", "project_id"],
                ["name", "model_id"],
            ],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.name = self.get_param("name")
        self.model_id = self.get_param("model_id")
        self.id = self.get_param("id")
        self.status = self.get_param("status")
        self.deployer = self.get_param("deployer")

        # Initialize result variables
        self.deployment_list: List[MlModelDeployment] = []

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
        if self.model_id:
            model = client.describe_model(project_id, self.model_id)
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

    def _resolve_build_id(self, project_id: str, model_id: str) -> str:
        client = MlModelBuildClient(self.api_client)
        build: Optional[MlModelBuild] = None
        if self.id:
            build = client.describe_build(project_id, model_id, self.id)
        else:
            build = client.find_latest_build(project_id, model_id)
        if not build:
            self.module.fail_json(
                msg="Unable to find deployment(s); model has not been built",
            )
        if not isinstance(build.id, str):
            self.module.fail_json(msg="Build ID is invalid from resolved build.")
        return build.id

    def _matches(self, deployment: MlModelDeployment) -> bool:
        if self.status is not None and deployment.status != self.status:
            return False

        if self.deployer:
            deployer = deployment.deployer
            if not isinstance(deployer, dict):
                return False
            for key, wanted in self.deployer.items():
                if wanted is not None and deployer.get(key) != wanted:
                    return False

        return True

    def process(self) -> None:
        project_id = self._resolve_project_id()
        model_id = self._resolve_model_id(project_id)
        build_id = self._resolve_build_id(project_id, model_id)
        client = MlModelDeploymentClient(self.api_client)

        deployments = [
            d
            for d in client.list_deployments(project_id, model_id, build_id)
            if self._matches(d)
        ]
        # Return the most recently created deployments first.
        self.deployment_list = sorted(
            deployments,
            key=lambda d: d.created_at if isinstance(d.created_at, str) else "",
            reverse=True,
        )


def main():
    result = MlProjectModelDeploymentInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        model_deployments=[to_dict(d) for d in result.deployment_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
