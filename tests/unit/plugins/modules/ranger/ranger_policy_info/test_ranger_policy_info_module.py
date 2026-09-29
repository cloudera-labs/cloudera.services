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

from ansible_collections.cloudera.services.plugins.modules import (
    ranger_policy_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
)

BASE_URL = "https://ranger.internal"

GET_BY_ID = (
    "ansible_collections.cloudera.services.plugins.modules.ranger_policy_info"
    ".RangerPolicyClient.get_policy_by_id"
)
GET_BY_NAME = (
    "ansible_collections.cloudera.services.plugins.modules.ranger_policy_info"
    ".RangerPolicyClient.get_policy_by_name"
)
LIST = (
    "ansible_collections.cloudera.services.plugins.modules.ranger_policy_info"
    ".RangerPolicyClient.list_policies"
)

POLICY_ONE = RangerPolicy(
    id=1,
    guid="policy-guid-1",
    name="hdfs_policy",
    service="cm_hdfs",
    is_enabled=True,
)

POLICY_TWO = RangerPolicy(
    id=2,
    guid="policy-guid-2",
    name="hive_policy",
    service="cm_hive",
    is_enabled=True,
)


def test_ranger_policy_info_module_list_all(module_args, mocker):
    """Test RangerPolicyInfoModule listing all policies."""
    mock_list = mocker.patch(LIST, return_value=[POLICY_ONE, POLICY_TWO])

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 2
    assert result["policies"][0]["id"] == 1
    assert result["policies"][1]["id"] == 2

    mock_list.assert_called_once_with()


def test_ranger_policy_info_module_by_id(module_args, mocker):
    """Test RangerPolicyInfoModule retrieval by id."""
    mock_get_by_id = mocker.patch(GET_BY_ID, return_value=POLICY_ONE)
    mock_list = mocker.patch(LIST)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "policy_id": 1,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 1
    assert result["policies"][0]["id"] == 1

    mock_get_by_id.assert_called_once_with(policy_id=1)
    mock_list.assert_not_called()


def test_ranger_policy_info_module_by_id_not_found(module_args, mocker):
    """Test RangerPolicyInfoModule retrieval by id when the policy doesn't exist."""
    mock_get_by_id = mocker.patch(GET_BY_ID, return_value=None)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "policy_id": 999,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["policies"] == []

    mock_get_by_id.assert_called_once_with(policy_id=999)


def test_ranger_policy_info_module_by_name_and_service(module_args, mocker):
    """Test RangerPolicyInfoModule retrieval by name within a service."""
    mock_get_by_name = mocker.patch(GET_BY_NAME, return_value=POLICY_TWO)
    mock_list = mocker.patch(LIST)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "hive_policy",
            "service": "cm_hive",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 1
    assert result["policies"][0]["id"] == 2

    mock_get_by_name.assert_called_once_with(
        service_name="cm_hive",
        policy_name="hive_policy",
    )
    mock_list.assert_not_called()


def test_ranger_policy_info_module_by_name_only(module_args, mocker):
    """Test RangerPolicyInfoModule retrieval by name searches all policies."""
    mock_list = mocker.patch(LIST, return_value=[POLICY_ONE, POLICY_TWO])

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "hive_policy",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 1
    assert result["policies"][0]["name"] == "hive_policy"

    mock_list.assert_called_once_with()


def test_ranger_policy_info_module_by_service(module_args, mocker):
    """Test RangerPolicyInfoModule listing all policies for a service."""
    mock_list = mocker.patch(LIST, return_value=[POLICY_ONE])

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "service": "cm_hdfs",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 1
    assert result["policies"][0]["service"] == "cm_hdfs"

    mock_list.assert_called_once_with(service_name="cm_hdfs")


def test_ranger_policy_info_module_empty_list(module_args, mocker):
    """Test RangerPolicyInfoModule with no policies present."""
    mock_list = mocker.patch(LIST, return_value=[])

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["policies"] == []

    mock_list.assert_called_once_with()


def test_ranger_policy_info_module_check_mode(module_args, mocker):
    """Test RangerPolicyInfoModule in check mode still returns data (read-only)."""
    mock_list = mocker.patch(LIST, return_value=[POLICY_ONE])

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 1

    mock_list.assert_called_once_with()


def test_ranger_policy_info_module_name_and_id_mutually_exclusive(module_args, mocker):
    """Test RangerPolicyInfoModule fails when both name and policy_id are given."""
    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "hive_policy",
            "policy_id": 2,
        },
    )

    with pytest.raises(AnsibleFailJson):
        ranger_policy_info.main()
