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
    MlModel,
    MlModelClient,
    API_VERSION,
)

PROJECT_ID = "aaaa-bbbb-cccc-dddd"

MODEL = dict(
    id="model-1",
    name="test-model",
    project_id=PROJECT_ID,
    auth_enabled=True,
)


def test_model_dataclass_roundtrip():
    model = from_dict(MlModel, MODEL)
    assert isinstance(model, MlModel)
    assert to_dict(model) == MODEL


def test_list_models(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(models=[MODEL])

    client = MlModelClient(api_client=api_client)
    response = client.list_models(PROJECT_ID)

    assert response == [from_dict(MlModel, MODEL)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/models",
        params={"page_size": 100},
    )


def test_describe_model(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = MODEL

    client = MlModelClient(api_client=api_client)
    response = client.describe_model(PROJECT_ID, "model-1")

    assert response == from_dict(MlModel, MODEL)
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/models/model-1",
        squelch={403: None, 404: None},
    )


def test_create_model(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = MODEL

    client = MlModelClient(api_client=api_client)
    client.create_model(PROJECT_ID, MlModel(name="test-model", auth_enabled=True))

    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/models",
        data={"name": "test-model", "auth_enabled": True},
    )


def test_update_model(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.patch.return_value = MODEL

    client = MlModelClient(api_client=api_client)
    client.update_model(PROJECT_ID, MlModel(name="test-model", id="model-1"))

    api_client.patch.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/models/model-1",
        data={"name": "test-model", "id": "model-1"},
    )


def test_delete_model(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlModelClient(api_client=api_client)
    client.delete_model(PROJECT_ID, "model-1")

    api_client.delete.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/models/model-1",
    )
