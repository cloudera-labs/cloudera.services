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
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_runtime_addon

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"

ADDONS = "ansible_collections.cloudera.services.plugins.modules.ml_runtime_addon.MlRuntimeAddonClient"


def _base_args(overrides=None):
    args = {"url": BASE_URL, "api_key": API_KEY}
    if overrides:
        args.update(overrides)
    return args


def test_status_by_identifiers(module_args, mocker):
    """Setting status by identifiers updates and reports changed."""
    mock_status = mocker.patch(f"{ADDONS}.update_addon_status", return_value=1)

    module_args(
        _base_args({"identifiers": ["hadoop-cli-7.2.18"], "status": "DISABLED"}),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_addon.main()

    assert e.value["changed"] is True
    assert e.value["runtime_addon"]["rows_affected"] == 1
    mock_status.assert_called_once_with(
        "DISABLED",
        ids=None,
        identifiers=["hadoop-cli-7.2.18"],
    )


def test_status_by_ids(module_args, mocker):
    """Setting status by numeric ids passes them through."""
    mock_status = mocker.patch(f"{ADDONS}.update_addon_status", return_value=2)

    module_args(_base_args({"ids": [1, 2], "status": "AVAILABLE"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_addon.main()

    assert e.value["changed"] is True
    mock_status.assert_called_once_with("AVAILABLE", ids=[1, 2], identifiers=None)


def test_no_rows_is_idempotent(module_args, mocker):
    """A status change affecting no rows reports no change."""
    mocker.patch(f"{ADDONS}.update_addon_status", return_value=0)

    module_args(_base_args({"ids": [1], "status": "DISABLED"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_addon.main()

    assert e.value["changed"] is False


def test_check_mode(module_args, mocker):
    """Check mode does not call the API."""
    mock_status = mocker.patch(f"{ADDONS}.update_addon_status")

    module_args(
        _base_args({"ids": [1], "status": "DISABLED", "_ansible_check_mode": True}),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_addon.main()

    assert e.value["changed"] is True
    mock_status.assert_not_called()


def test_status_required(module_args, mocker):
    """status is required."""
    module_args(_base_args({"ids": [1]}))

    with pytest.raises(AnsibleFailJson):
        ml_runtime_addon.main()


def test_requires_ids_or_identifiers(module_args, mocker):
    """One of ids/identifiers is required."""
    module_args(_base_args({"status": "DISABLED"}))

    with pytest.raises(AnsibleFailJson):
        ml_runtime_addon.main()


def test_ids_identifiers_mutually_exclusive(module_args, mocker):
    """ids and identifiers cannot be combined."""
    module_args(
        _base_args({"ids": [1], "identifiers": ["x"], "status": "DISABLED"}),
    )

    with pytest.raises(AnsibleFailJson):
        ml_runtime_addon.main()
