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

import os

from typing import Callable

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
)

from ansible_collections.cloudera.services.plugins.modules import (
    ranger_policy_info,
)

REQUIRED_ENV_VARS = [
    "RANGER_API_URL",
    "RANGER_API_USERNAME",
    "RANGER_API_PASSWORD",
]


@pytest.fixture
def ranger_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args for Ranger policy info tests."""

    def _ranger_module_args(overrides: dict = {}) -> None:
        args = {
            "url": env_context["RANGER_API_URL"],
            "url_username": env_context["RANGER_API_USERNAME"],
            "url_password": env_context["RANGER_API_PASSWORD"],
            "force_basic_auth": True,
            "validate_certs": os.environ.get("RANGER_VALIDATE_CERTS", "false").lower()
            == "true",
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _ranger_module_args


def test_ranger_policy_info_module_list_all(ranger_module_args, ranger_existing_policy):
    """Test RangerPolicyInfoModule listing all policies."""

    ranger_module_args({})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert "policies" in result
    assert isinstance(result["policies"], list)
    assert any(
        policy["id"] == ranger_existing_policy.id for policy in result["policies"]
    )


def test_ranger_policy_info_module_by_id(ranger_module_args, ranger_existing_policy):
    """Test RangerPolicyInfoModule get policy by id."""

    ranger_module_args({"policy_id": ranger_existing_policy.id})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 1
    assert result["policies"][0]["id"] == ranger_existing_policy.id
    assert result["policies"][0]["name"] == ranger_existing_policy.name


def test_ranger_policy_info_module_by_name_and_service(
    ranger_module_args,
    ranger_existing_policy,
    ranger_policy_test_service,
):
    """Test RangerPolicyInfoModule get policy by name within a service."""

    ranger_module_args(
        {
            "name": ranger_existing_policy.name,
            "service": ranger_policy_test_service.name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 1
    assert result["policies"][0]["id"] == ranger_existing_policy.id
    assert result["policies"][0]["name"] == ranger_existing_policy.name


def test_ranger_policy_info_module_by_service(
    ranger_module_args,
    ranger_existing_policy,
    ranger_policy_test_service,
):
    """Test RangerPolicyInfoModule listing all policies for a service."""

    ranger_module_args({"service": ranger_policy_test_service.name})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert isinstance(result["policies"], list)
    assert any(
        policy["id"] == ranger_existing_policy.id for policy in result["policies"]
    )
    assert all(
        policy["service"] == ranger_policy_test_service.name
        for policy in result["policies"]
    )


def test_ranger_policy_info_module_nonexistent_id(ranger_module_args):
    """Test RangerPolicyInfoModule with a nonexistent policy id."""

    ranger_module_args({"policy_id": 999999})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["policies"] == []


def test_ranger_policy_info_module_nonexistent_name(
    ranger_module_args,
    ranger_policy_test_service,
):
    """Test RangerPolicyInfoModule with a nonexistent policy name."""

    ranger_module_args(
        {
            "name": f"nonexistent-policy-{os.getpid()}",
            "service": ranger_policy_test_service.name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["policies"] == []


def test_ranger_policy_info_module_check_mode(
    ranger_module_args,
    ranger_existing_policy,
):
    """Test RangerPolicyInfoModule in check mode."""

    ranger_module_args(
        {"policy_id": ranger_existing_policy.id, "_ansible_check_mode": True},
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["policies"]) == 1
    assert result["policies"][0]["id"] == ranger_existing_policy.id
