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

from unittest.mock import Mock

from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    CmlServicesClient,
    validate_project_id,
    validate_subdomain,
)


def test_cml_services_client_sets_bearer_header():
    """CmlServicesClient injects the api_key as a bearer token."""
    module = Mock()
    module.params = {"api_key": "SECRET", "url": "https://ml.example.com"}

    client = CmlServicesClient(module=module, timeout=60)

    assert client.headers["Authorization"] == "Bearer SECRET"


def test_cml_services_client_without_api_key():
    """A missing api_key does not add an Authorization header."""
    module = Mock()
    module.params = {"api_key": None, "url": "https://ml.example.com"}

    client = CmlServicesClient(module=module, timeout=60)

    assert "Authorization" not in client.headers


def test_cml_services_client_preserves_extra_headers():
    """Existing headers are preserved alongside the bearer token."""
    module = Mock()
    module.params = {"api_key": "SECRET", "url": "https://ml.example.com"}

    client = CmlServicesClient(module=module, timeout=60, headers={"X-Test": "1"})

    assert client.headers["X-Test"] == "1"
    assert client.headers["Authorization"] == "Bearer SECRET"


def test_validate_project_id():
    assert validate_project_id("aaaa-bbbb-cccc-dddd") is True
    assert validate_project_id("0a1b-2c3d-4e5f-6a7b") is True
    assert validate_project_id("AAAA-bbbb-cccc-dddd") is False
    assert validate_project_id("aaa-bbbb-cccc-dddd") is False
    assert validate_project_id("nope") is False


def test_validate_subdomain():
    assert validate_subdomain("my-app-1") is True
    assert validate_subdomain("app") is True
    assert validate_subdomain("-bad") is False
    assert validate_subdomain("bad-") is False
    assert validate_subdomain("Bad") is False
