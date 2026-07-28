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
module: ml_project_model_deployment
short_description: Manage a Cloudera Machine Learning (CML) project model deployment
description:
  - Start, stop, restart, or delete a Cloudera Machine Learning (CML) project model deployment.
  - Deployments are immutable; a running deployment is never updated in place. Use
    O(state=restarted) to stop the current deployment and start a new one on the build.
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
  model_name:
    description:
      - The name of the enclosing model.
      - Mutually exclusive with O(model_id).
    type: str
    required: false
  model_id:
    description:
      - The unique identifier of the enclosing model.
      - Mutually exclusive with O(model_name).
    type: str
    required: false
  build_id:
    description:
      - The unique identifier of the build to deploy.
      - If not set, the most recent successful build is used.
    type: str
    required: false
  id:
    description:
      - The unique identifier of an existing deployment.
    type: str
    required: false
    aliases:
      - deployment_id
  cpu:
    description:
      - The vCPU allocated to the deployment.
    type: int
    required: false
  memory:
    description:
      - The RAM allocated to the deployment, in GB.
    type: int
    required: false
  gpu:
    description:
      - The count of Nvidia GPUs allocated to the deployment.
    type: int
    required: false
    aliases:
      - nvidia_gpus
  env:
    description:
      - Environment variables to set on the deployment.
    type: dict
    required: false
    aliases:
      - env_vars
  state:
    description:
      - The declarative state of the deployment.
      - V(present) is an alias for V(started).
    type: str
    required: false
    default: started
    choices:
      - started
      - present
      - stopped
      - restarted
      - absent
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Deploy the latest build of a model
  cloudera.services.ml_project_model_deployment:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    project_name: my-project
    model_name: fraud-detector
    cpu: 1
    memory: 2
    state: started

- name: Stop a deployment
  cloudera.services.ml_project_model_deployment:
    project_id: "{{ project_id }}"
    model_id: "{{ model_id }}"
    id: "{{ deployment_id }}"
    state: stopped

- name: Restart (stop then redeploy) a model
  cloudera.services.ml_project_model_deployment:
    project_id: "{{ project_id }}"
    model_id: "{{ model_id }}"
    state: restarted

- name: Delete a deployment
  cloudera.services.ml_project_model_deployment:
    project_id: "{{ project_id }}"
    model_id: "{{ model_id }}"
    id: "{{ deployment_id }}"
    state: absent
"""

RETURN = r"""
deployment:
  description: The CML model deployment details.
  returned: always
  type: dict
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
    MlModelDeployment,
    MlModelDeploymentClient,
    MlProject,
    MlProjectClient,
    validate_project_id,
)


class MlProjectModelDeploymentModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                project_name=dict(type="str", required=False),
                project_id=dict(type="str", required=False),
                model_name=dict(type="str", required=False),
                model_id=dict(type="str", required=False),
                build_id=dict(type="str", required=False),
                id=dict(type="str", required=False, aliases=["deployment_id"]),
                cpu=dict(type="int", required=False),
                memory=dict(type="int", required=False),
                gpu=dict(type="int", required=False, aliases=["nvidia_gpus"]),
                env=dict(type="dict", required=False, aliases=["env_vars"]),
                state=dict(
                    type="str",
                    required=False,
                    choices=["started", "present", "stopped", "restarted", "absent"],
                    default="started",
                ),
            ),
            mutually_exclusive=[
                ["project_name", "project_id"],
                ["model_name", "model_id"],
            ],
            required_one_of=[
                ["project_name", "project_id"],
                ["model_name", "model_id"],
            ],
            supports_check_mode=True,
        )

        # Set parameters
        self.project_name = self.get_param("project_name")
        self.project_id = self.get_param("project_id")
        self.model_name = self.get_param("model_name")
        self.model_id = self.get_param("model_id")
        self.build_id = self.get_param("build_id")
        self.id = self.get_param("id")
        self.cpu = self.get_param("cpu")
        self.memory = self.get_param("memory")
        self.gpu = self.get_param("gpu")
        self.env = self.get_param("env")
        self.state = self.get_param("state")
        if self.state == "present":
            self.state = "started"

        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.deployment: Optional[MlModelDeployment] = None

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

    def _resolve_build_id(self, project_id: str, model_id: str) -> str:
        client = MlModelBuildClient(self.api_client)
        build: Optional[MlModelBuild] = None
        if self.build_id:
            build = client.describe_build(project_id, model_id, self.build_id)
        else:
            build = client.find_latest_build(project_id, model_id)
        if not build:
            self._fail("Model build not found")
        if not isinstance(build.id, str):
            self._fail("Build ID is invalid from resolved build.")
        return build.id

    def _find_existing(
        self,
        client: MlModelDeploymentClient,
        project_id: str,
        model_id: str,
        build_id: str,
    ) -> Optional[MlModelDeployment]:
        if self.id:
            return client.describe_deployment(project_id, model_id, build_id, self.id)
        deployed = [
            d
            for d in client.list_deployments(project_id, model_id, build_id)
            if d.status == "deployed"
        ]
        deployed.sort(
            key=lambda d: d.created_at if isinstance(d.created_at, str) else "",
            reverse=True,
        )
        return deployed[0] if deployed else None

    def _incoming_deployment(
        self,
        build_id: str,
        base: Optional[MlModelDeployment] = None,
    ) -> MlModelDeployment:
        incoming = MlModelDeployment(build_id=build_id)
        if self.cpu is not None:
            incoming.cpu = self.cpu
        elif base is not None and isinstance(base.cpu, (int, float)):
            incoming.cpu = base.cpu
        if self.memory is not None:
            incoming.memory = self.memory
        elif base is not None and isinstance(base.memory, (int, float)):
            incoming.memory = base.memory
        if self.gpu is not None:
            incoming.nvidia_gpus = self.gpu
        elif base is not None and isinstance(base.nvidia_gpus, int):
            incoming.nvidia_gpus = base.nvidia_gpus
        if self.env is not None:
            incoming.environment = self.env
        elif base is not None and isinstance(base.environment, dict):
            incoming.environment = base.environment
        return incoming

    def process(self) -> None:
        project_id = self._resolve_project_id()
        model_id = self._resolve_model_id(project_id)
        build_id = self._resolve_build_id(project_id, model_id)
        client = MlModelDeploymentClient(self.api_client)

        existing = self._find_existing(client, project_id, model_id, build_id)

        if self.state == "started":
            if existing:
                # Deployments are immutable; return the running deployment.
                self.deployment = existing
                return
            self._create(client, project_id, model_id, build_id)
            return

        if self.state == "stopped":
            self.deployment = existing
            if existing:
                if not isinstance(existing.id, str):
                    self._fail("Deployment ID is invalid from existing deployment.")
                self.changed = True
                if self.module._diff:
                    # TODO Fix the diff to show the stopped deployment "after"
                    self.diff["before"] = to_dict(existing)
                if not self.module.check_mode:
                    self.deployment = client.stop_deployment(
                        project_id,
                        model_id,
                        build_id,
                        existing.id,
                    )
            return

        if self.state == "absent":
            self.deployment = existing
            if existing:
                if not isinstance(existing.id, str):
                    self._fail("Deployment ID is invalid from existing deployment.")
                self.changed = True
                if self.module._diff:
                    self.diff["before"] = to_dict(existing)
                if not self.module.check_mode:
                    client.delete_deployment(
                        project_id,
                        model_id,
                        build_id,
                        existing.id,
                    )
                    self.deployment = None
            return

        # restarted: stop the running deployment (if any) then start a new one.
        if existing:
            if not isinstance(existing.id, str):
                self._fail("Deployment ID is invalid from existing deployment.")
            self.changed = True
            if not self.module.check_mode:
                client.stop_deployment(project_id, model_id, build_id, existing.id)
        self._create(client, project_id, model_id, build_id, base=existing)

    def _create(
        self,
        client: MlModelDeploymentClient,
        project_id: str,
        model_id: str,
        build_id: str,
        base: Optional[MlModelDeployment] = None,
    ) -> None:
        incoming = self._incoming_deployment(build_id, base=base)
        self.changed = True
        if self.module._diff:
            self.diff["after"] = to_dict(incoming)
        if not self.module.check_mode:
            self.deployment = client.create_deployment(
                project_id,
                model_id,
                build_id,
                incoming,
            )
        else:
            self.deployment = incoming


def main():
    result = MlProjectModelDeploymentModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        deployment=to_dict(result.deployment) if result.deployment else {},
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
