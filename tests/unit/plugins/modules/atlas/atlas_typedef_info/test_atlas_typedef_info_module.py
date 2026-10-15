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

from ansible_collections.cloudera.services.tests.unit import AnsibleExitJson

from ansible_collections.cloudera.services.plugins.modules import atlas_typedef_info

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_typedef_info.AtlasTypeDefClient"

HEADERS = [
    {"guid": "g1", "name": "test_enum", "category": "ENUM"},
    {"guid": "g2", "name": "test_tag", "category": "CLASSIFICATION"},
    {"guid": "g3", "name": "test_enum2", "category": "ENUM"},
]


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_typedef_info_module_list(module_args, mocker):
    """Test listing returns all typedef headers."""
    mocker.patch(f"{CLIENT}.list_typedef_headers", return_value=HEADERS)

    module_args(_args())

    with pytest.raises(AnsibleExitJson) as e:
        atlas_typedef_info.main()

    assert e.value["changed"] is False
    assert e.value["typedefs"] == HEADERS


def test_atlas_typedef_info_module_list_category(module_args, mocker):
    """Test the category filter narrows the listed headers."""
    mocker.patch(f"{CLIENT}.list_typedef_headers", return_value=HEADERS)

    module_args(_args(category="enum"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_typedef_info.main()

    assert [t["name"] for t in e.value["typedefs"]] == ["test_enum", "test_enum2"]


def test_atlas_typedef_info_module_name(module_args, mocker):
    """Test a name returns the full typedef as a one-element list."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_typedef_by_name",
        return_value={"name": "test_enum", "category": "ENUM", "element_defs": []},
    )

    module_args(_args(name="test_enum"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_typedef_info.main()

    assert e.value["typedefs"] == [
        {"name": "test_enum", "category": "ENUM", "element_defs": []},
    ]
    mock_get.assert_called_once_with("test_enum")


def test_atlas_typedef_info_module_name_missing(module_args, mocker):
    """Test an unknown name returns an empty list."""
    mocker.patch(f"{CLIENT}.get_typedef_by_name", return_value=None)

    module_args(_args(name="missing"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_typedef_info.main()

    assert e.value["changed"] is False
    assert e.value["typedefs"] == []
