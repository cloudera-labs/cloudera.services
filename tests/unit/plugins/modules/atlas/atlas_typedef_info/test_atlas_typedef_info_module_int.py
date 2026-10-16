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
from typing import Optional

import pytest

from ansible_collections.cloudera.services.plugins.modules import atlas_typedef_info
from ansible_collections.cloudera.services.tests.unit import AnsibleExitJson

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]


@pytest.fixture
def atlas_module_args(module_args, env_context):
    """Fixture to set common module args for Atlas tests."""

    def _atlas_module_args(overrides: Optional[dict] = None) -> None:
        overrides = overrides or {}
        args = {
            "url": env_context["ATLAS_API_URL"],
            "url_username": env_context["ATLAS_API_USERNAME"],
            "url_password": env_context["ATLAS_API_PASSWORD"],
            "force_basic_auth": True,
            "validate_certs": os.environ.get("ATLAS_VALIDATE_CERTS", "false").lower()
            == "true",
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _atlas_module_args


def test_atlas_typedef_info_module_list_category(
    atlas_module_args,
    atlas_existing_enum_def,
):
    """Test the category filter lists the existing enum and only enums."""
    atlas_module_args({"category": "enum"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_typedef_info.main()

    assert e.value["changed"] is False
    assert {t["category"] for t in e.value["typedefs"]} == {"ENUM"}
    assert atlas_existing_enum_def.name in [t["name"] for t in e.value["typedefs"]]


def test_atlas_typedef_info_module_name(atlas_module_args, atlas_existing_enum_def):
    """Test a name returns the full typedef."""
    atlas_module_args({"name": atlas_existing_enum_def.name})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_typedef_info.main()

    assert len(e.value["typedefs"]) == 1
    assert e.value["typedefs"][0]["name"] == atlas_existing_enum_def.name
    assert "element_defs" in e.value["typedefs"][0]


def test_atlas_typedef_info_module_name_missing(atlas_module_args):
    """Test an unknown name returns an empty list."""
    atlas_module_args({"name": "ansible_test_missing"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_typedef_info.main()

    assert e.value["typedefs"] == []
