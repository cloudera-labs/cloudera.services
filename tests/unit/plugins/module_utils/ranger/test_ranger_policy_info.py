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

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
    RangerPolicyClient,
)

ENDPOINT_URL = "https://ranger.internal"

POLICY_RESPONSE = {
    "id": 67,
    "guid": "policy-guid-67",
    "isEnabled": True,
    "version": 1,
    "service": "cm_hdfs",
    "name": "test_policy",
    "policyType": 0,
    "description": "Test policy",
    "isAuditEnabled": True,
    "resources": {"path": {"values": ["/tmp/test"]}},
    "policyItems": [
        {"accesses": [{"type": "read", "isAllowed": True}], "users": ["admin"]},
    ],
    "serviceType": "hdfs",
}

POLICY_RESPONSE_TWO = {
    "id": 68,
    "guid": "policy-guid-68",
    "isEnabled": True,
    "version": 1,
    "service": "cm_hdfs",
    "name": "other_policy",
    "policyType": 0,
    "serviceType": "hdfs",
}

POLICIES_LIST = {"policies": [POLICY_RESPONSE, POLICY_RESPONSE_TWO]}

# A Ranger 400 response with a DATA_NOT_FOUND body (Ranger's "not found" signal).
RANGER_NOT_FOUND_400 = {
    "status": 400,
    "body": {
        "statusCode": 1,
        "messageList": [{"name": "DATA_NOT_FOUND"}],
    },
}

# A Ranger 400 response for some other (non "not found") error.
RANGER_ERROR_400 = {
    "status": 400,
    "body": {
        "statusCode": 2,
        "messageList": [{"name": "VALIDATION_ERROR"}],
    },
}


def test_list_policies(mocker):
    """Test listing all policies."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = POLICIES_LIST

    client = RangerPolicyClient(api_client=api_client)

    response = client.list_policies()

    assert isinstance(response, list)
    assert len(response) == 2
    assert all(isinstance(p, RangerPolicy) for p in response)
    assert response[0].id == 67
    assert response[1].id == 68

    api_client.get.assert_called_once_with(
        "/service/plugins/policies",
        params=None,
        squelch={404: {"policies": []}},
    )


def test_list_policies_by_service(mocker):
    """Test listing policies filtered by service name."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {"policies": [POLICY_RESPONSE]}

    client = RangerPolicyClient(api_client=api_client)

    response = client.list_policies(service_name="cm_hdfs")

    assert len(response) == 1
    assert response[0].service == "cm_hdfs"

    api_client.get.assert_called_once_with(
        "/service/plugins/policies",
        params={"serviceName": "cm_hdfs"},
        squelch={404: {"policies": []}},
    )


def test_list_policies_empty(mocker):
    """Test listing policies when none exist."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {"policies": []}

    client = RangerPolicyClient(api_client=api_client)

    assert client.list_policies() == []


def test_get_policy_by_id(mocker):
    """Test getting a policy by id."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = POLICY_RESPONSE

    client = RangerPolicyClient(api_client=api_client)

    response = client.get_policy_by_id(policy_id=67)

    assert isinstance(response, RangerPolicy)
    assert response.id == 67
    assert response.name == "test_policy"

    api_client.get.assert_called_once_with(
        "/service/plugins/policies/67",
        squelch={404: None},
        passthru=[400],
    )


def test_get_policy_by_id_not_found_squelched(mocker):
    """Test getting a non-existent policy by id (squelched 404) returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = RangerPolicyClient(api_client=api_client)

    assert client.get_policy_by_id(policy_id=999) is None


def test_get_policy_by_id_not_found_400(mocker):
    """Test getting a non-existent policy by id (Ranger 400 DATA_NOT_FOUND) returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = RANGER_NOT_FOUND_400

    client = RangerPolicyClient(api_client=api_client)

    assert client.get_policy_by_id(policy_id=999) is None


def test_get_policy_by_id_error(mocker):
    """Test that a non "not found" Ranger 400 raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = RANGER_ERROR_400

    client = RangerPolicyClient(api_client=api_client)

    with pytest.raises(ServicesError):
        client.get_policy_by_id(policy_id=67)


def test_get_policy_by_name(mocker):
    """Test getting a policy by service and name filters the service list."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = POLICIES_LIST

    client = RangerPolicyClient(api_client=api_client)

    response = client.get_policy_by_name(
        service_name="cm_hdfs",
        policy_name="other_policy",
    )

    assert isinstance(response, RangerPolicy)
    assert response.id == 68
    assert response.name == "other_policy"

    # It lists policies for the service and filters client-side.
    api_client.get.assert_called_once_with(
        "/service/plugins/policies",
        params={"serviceName": "cm_hdfs"},
        squelch={404: {"policies": []}},
    )


def test_get_policy_by_name_not_found(mocker):
    """Test getting a policy by a name absent from the service returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = POLICIES_LIST

    client = RangerPolicyClient(api_client=api_client)

    response = client.get_policy_by_name(
        service_name="cm_hdfs",
        policy_name="nonexistent_policy",
    )

    assert response is None
