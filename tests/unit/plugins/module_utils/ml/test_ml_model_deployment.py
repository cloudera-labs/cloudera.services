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

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    ServicesClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlModelDeployment,
    MlModelDeploymentClient,
    API_VERSION,
)

PROJECT_ID = "aaaa-bbbb-cccc-dddd"
MODEL_ID = "model-1"
BUILD_ID = "build-1"

BASE = f"/{API_VERSION}/projects/{PROJECT_ID}/models/{MODEL_ID}/builds/{BUILD_ID}/deployments"

DEPLOYMENT = dict(
    id="deploy-1",
    build_id=BUILD_ID,
    model_id=MODEL_ID,
    project_id=PROJECT_ID,
    status="deployed",
    replicas=2,
)


def test_deployment_dataclass_roundtrip():
    deployment = from_dict(MlModelDeployment, DEPLOYMENT)
    assert isinstance(deployment, MlModelDeployment)
    assert to_dict(deployment) == DEPLOYMENT


def test_list_deployments(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(model_deployments=[DEPLOYMENT])

    client = MlModelDeploymentClient(api_client=api_client)
    response = client.list_deployments(PROJECT_ID, MODEL_ID, BUILD_ID)

    assert response == [from_dict(MlModelDeployment, DEPLOYMENT)]
    api_client.get.assert_called_once_with(BASE, params={"page_size": 100})


def test_describe_deployment(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = DEPLOYMENT

    client = MlModelDeploymentClient(api_client=api_client)
    response = client.describe_deployment(PROJECT_ID, MODEL_ID, BUILD_ID, "deploy-1")

    assert response == from_dict(MlModelDeployment, DEPLOYMENT)
    api_client.get.assert_called_once_with(
        f"{BASE}/deploy-1",
        squelch={403: None, 404: None},
    )


def test_create_deployment(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = DEPLOYMENT

    client = MlModelDeploymentClient(api_client=api_client)
    client.create_deployment(
        PROJECT_ID,
        MODEL_ID,
        BUILD_ID,
        MlModelDeployment(replicas=2),
    )

    api_client.post.assert_called_once_with(BASE, data={"replicas": 2})


def test_delete_deployment(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlModelDeploymentClient(api_client=api_client)
    client.delete_deployment(PROJECT_ID, MODEL_ID, BUILD_ID, "deploy-1")

    api_client.delete.assert_called_once_with(f"{BASE}/deploy-1")
