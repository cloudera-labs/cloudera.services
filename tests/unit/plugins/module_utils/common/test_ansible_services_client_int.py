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
import re

from ansible_collections.cloudera.services.tests.unit import AnsibleFailJson

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    AnsibleServicesClient,
)

REQUIRED_ENV_VARS = [
    "SSB_SSE_API_URL",
    "SSB_SSE_API_USERNAME",
    "SSB_SSE_API_PASSWORD",
]

# TODO Convert integration tests to use pytest-httpserver to avoid live API calls


def test_services_client_get_200(env_context, mock_ansible_module):
    """Test basic GET request returning 200 status."""

    mock_ansible_module.params.update(
        {
            "url": env_context["SSB_SSE_API_URL"],
            "url_username": env_context["SSB_SSE_API_USERNAME"],
            "url_password": env_context["SSB_SSE_API_PASSWORD"],
        },
    )

    client = AnsibleServicesClient(
        module=mock_ansible_module,
    )

    response = client.get(
        "/api/v2/user",
    )

    assert response is not None
    assert isinstance(response, dict)


def test_services_client_get_401(env_context, mock_ansible_module):
    """Test basic GET request returning 401 status."""

    mock_ansible_module.params.update(
        {
            "url": env_context["SSB_SSE_API_URL"],
            "url_username": env_context["SSB_SSE_API_USERNAME"],
            "url_password": "invalid_password",
        },
    )

    client = AnsibleServicesClient(
        module=mock_ansible_module,
    )

    with pytest.raises(AnsibleFailJson):
        client.get("/api/v2/user")

    mock_ansible_module.fail_json.assert_called_once()

    call_args = mock_ansible_module.fail_json.call_args
    assert re.search(
        r"\[401\] Unauthorized Access; .*?/api/v2/user",
        call_args[1]["msg"],
    )


def test_services_client_get_500(env_context, mock_ansible_module):
    """Test basic GET request returning 404 status."""

    mock_ansible_module.params.update(
        {
            "url": env_context["SSB_SSE_API_URL"],
            "url_username": env_context["SSB_SSE_API_USERNAME"],
            "url_password": env_context["SSB_SSE_API_PASSWORD"],
        },
    )

    client = AnsibleServicesClient(
        module=mock_ansible_module,
    )

    with pytest.raises(AnsibleFailJson):
        client.get("/api/v2/userXYZ")

    mock_ansible_module.fail_json.assert_called_once()

    call_args = mock_ansible_module.fail_json.call_args
    assert re.search(r"\[500\] No endpoint GET .*?/api/v2/userXYZ", call_args[1]["msg"])
