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

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_runtime_addon_info
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlRuntimeAddon

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"

ADDONS = "ansible_collections.cloudera.services.plugins.modules.ml_runtime_addon_info.MlRuntimeAddonClient"

ADDON_ONE = MlRuntimeAddon(
    identifier="hadoop-cli-7.2.18",
    component="HadoopCLI",
    display_name="Hadoop CLI",
    status="AVAILABLE",
    id=1,
)
ADDON_TWO = MlRuntimeAddon(
    identifier="spark-3.3",
    component="Spark",
    display_name="Spark 3.3",
    status="DISABLED",
    id=2,
)


def _base_args(overrides=None):
    args = {"url": BASE_URL, "api_key": API_KEY}
    if overrides:
        args.update(overrides)
    return args


def test_list_all(module_args, mocker):
    """All runtime addons are returned when no filter is given."""
    mocker.patch(f"{ADDONS}.list_runtime_addons", return_value=[ADDON_ONE, ADDON_TWO])

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_addon_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["runtime_addons"]) == 2


def test_filter_by_component(module_args, mocker):
    """Runtime addons can be filtered by component."""
    mocker.patch(f"{ADDONS}.list_runtime_addons", return_value=[ADDON_ONE, ADDON_TWO])

    module_args(_base_args({"component": "Spark"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_addon_info.main()

    addons = e.value["runtime_addons"]
    assert len(addons) == 1
    assert addons[0]["identifier"] == "spark-3.3"


def test_filter_by_name_alias(module_args, mocker):
    """The name alias maps to display_name."""
    mocker.patch(f"{ADDONS}.list_runtime_addons", return_value=[ADDON_ONE, ADDON_TWO])

    module_args(_base_args({"name": "Hadoop CLI"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_addon_info.main()

    addons = e.value["runtime_addons"]
    assert len(addons) == 1
    assert addons[0]["identifier"] == "hadoop-cli-7.2.18"


def test_filter_by_status(module_args, mocker):
    """Runtime addons can be filtered by status."""
    mocker.patch(f"{ADDONS}.list_runtime_addons", return_value=[ADDON_ONE, ADDON_TWO])

    module_args(_base_args({"status": "DISABLED"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_addon_info.main()

    addons = e.value["runtime_addons"]
    assert len(addons) == 1
    assert addons[0]["identifier"] == "spark-3.3"
