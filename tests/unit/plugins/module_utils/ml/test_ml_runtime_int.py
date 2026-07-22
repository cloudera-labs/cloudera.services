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

from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlRuntime,
    MlRuntimeAddon,
)

REQUIRED_ENV_VARS = [
    "CML_ENDPOINT",
    "CML_API_KEY",
]


def test_list_runtimes(ml_runtime_client):
    """List runtimes (read-only) and confirm pagination assembles a list."""
    response = ml_runtime_client.list_runtimes()

    assert isinstance(response, list)
    assert all(isinstance(r, MlRuntime) for r in response)


def test_list_runtime_addons(ml_runtime_addon_client):
    """List runtime addons (read-only)."""
    response = ml_runtime_addon_client.list_runtime_addons()

    assert isinstance(response, list)
    assert all(isinstance(a, MlRuntimeAddon) for a in response)
