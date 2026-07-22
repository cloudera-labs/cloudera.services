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
    MlRuntime,
    MlRuntimeClient,
    MlRuntimeAddon,
    MlRuntimeAddonClient,
    API_VERSION,
)

RUNTIME = dict(
    image_identifier="docker.repository/runtime:1",
    edition="Standard",
    kernel="Python 3.10",
    editor="Workbench",
)

ADDON = dict(
    identifier="spark-3.2",
    component="Spark",
    display_name="Spark 3.2",
    status="AVAILABLE",
)


def test_runtime_dataclass_roundtrip():
    runtime = from_dict(MlRuntime, RUNTIME)
    assert isinstance(runtime, MlRuntime)
    assert to_dict(runtime) == RUNTIME


def test_list_runtimes(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(runtimes=[RUNTIME])

    client = MlRuntimeClient(api_client=api_client)
    response = client.list_runtimes()

    assert response == [from_dict(MlRuntime, RUNTIME)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/runtimes",
        params={"page_size": 100},
    )


def test_addon_dataclass_roundtrip():
    addon = from_dict(MlRuntimeAddon, ADDON)
    assert isinstance(addon, MlRuntimeAddon)
    assert to_dict(addon) == ADDON


def test_list_runtime_addons(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(runtime_addons=[ADDON])

    client = MlRuntimeAddonClient(api_client=api_client)
    response = client.list_runtime_addons()

    assert response == [from_dict(MlRuntimeAddon, ADDON)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/runtimeaddons",
        params={"page_size": 100},
    )
