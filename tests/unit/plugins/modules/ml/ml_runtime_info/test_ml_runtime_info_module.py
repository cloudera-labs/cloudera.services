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

from ansible_collections.cloudera.services.plugins.modules import ml_runtime_info
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlRuntime

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"

RUNTIMES = "ansible_collections.cloudera.services.plugins.modules.ml_runtime_info.MlRuntimeClient"

RT_ONE = MlRuntime(
    image_identifier="img-1",
    editor="PBJ Workbench",
    kernel="Python 3.11",
    edition="Standard",
    full_version="2026.04.1",
    status="ENABLED",
)
RT_TWO = MlRuntime(
    image_identifier="img-2",
    editor="JupyterLab",
    kernel="Python 3.14",
    edition="Nvidia GPU",
    full_version="2026.04.1",
    status="DISABLED",
)


def _base_args(overrides=None):
    args = {"url": BASE_URL, "api_key": API_KEY}
    if overrides:
        args.update(overrides)
    return args


def test_list_all(module_args, mocker):
    """All runtimes are returned when no filter is given."""
    mocker.patch(f"{RUNTIMES}.list_runtimes", return_value=[RT_ONE, RT_TWO])

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["runtimes"]) == 2


def test_filter_by_editor(module_args, mocker):
    """Runtimes can be filtered by editor."""
    mocker.patch(f"{RUNTIMES}.list_runtimes", return_value=[RT_ONE, RT_TWO])

    module_args(_base_args({"editor": "PBJ Workbench"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_info.main()

    runtimes = e.value["runtimes"]
    assert len(runtimes) == 1
    assert runtimes[0]["image_identifier"] == "img-1"


def test_filter_by_status(module_args, mocker):
    """Runtimes can be filtered by status."""
    mocker.patch(f"{RUNTIMES}.list_runtimes", return_value=[RT_ONE, RT_TWO])

    module_args(_base_args({"status": "DISABLED"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_info.main()

    runtimes = e.value["runtimes"]
    assert len(runtimes) == 1
    assert runtimes[0]["image_identifier"] == "img-2"


def test_filter_by_image_alias(module_args, mocker):
    """The image alias maps to image_identifier."""
    mocker.patch(f"{RUNTIMES}.list_runtimes", return_value=[RT_ONE, RT_TWO])

    module_args(_base_args({"image": "img-1"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_info.main()

    assert len(e.value["runtimes"]) == 1


def test_filter_no_match(module_args, mocker):
    """A non-matching filter returns no runtimes."""
    mocker.patch(f"{RUNTIMES}.list_runtimes", return_value=[RT_ONE, RT_TWO])

    module_args(_base_args({"kernel": "R 4.1"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_info.main()

    assert e.value["runtimes"] == []
