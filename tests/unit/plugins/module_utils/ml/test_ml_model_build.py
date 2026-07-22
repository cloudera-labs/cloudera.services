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
    MlModelBuild,
    MlModelBuildClient,
    API_VERSION,
)

PROJECT_ID = "aaaa-bbbb-cccc-dddd"
MODEL_ID = "model-1"

BUILD = dict(
    id="build-1",
    model_id=MODEL_ID,
    project_id=PROJECT_ID,
    status="built",
)


def test_build_dataclass_roundtrip():
    build = from_dict(MlModelBuild, BUILD)
    assert isinstance(build, MlModelBuild)
    assert to_dict(build) == BUILD


def test_list_builds(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(model_builds=[BUILD])

    client = MlModelBuildClient(api_client=api_client)
    response = client.list_builds(PROJECT_ID, MODEL_ID)

    assert response == [from_dict(MlModelBuild, BUILD)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/models/{MODEL_ID}/builds",
        params={"page_size": 100},
    )


def test_find_latest_build(mocker):
    """find_latest_build queries built builds newest-first and returns the first."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(
        model_builds=[BUILD, {**BUILD, "id": "build-0"}],
    )

    client = MlModelBuildClient(api_client=api_client)
    response = client.find_latest_build(PROJECT_ID, MODEL_ID)

    assert response == from_dict(MlModelBuild, BUILD)
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/models/{MODEL_ID}/builds",
        params={"sort": "-created_at", "search_filter": '{"status":"built"}'},
    )


def test_find_latest_build_none(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(model_builds=[])

    client = MlModelBuildClient(api_client=api_client)
    assert client.find_latest_build(PROJECT_ID, MODEL_ID) is None


def test_describe_build(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = BUILD

    client = MlModelBuildClient(api_client=api_client)
    response = client.describe_build(PROJECT_ID, MODEL_ID, "build-1")

    assert response == from_dict(MlModelBuild, BUILD)
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/models/{MODEL_ID}/builds/build-1",
        squelch={403: None, 404: None},
    )
