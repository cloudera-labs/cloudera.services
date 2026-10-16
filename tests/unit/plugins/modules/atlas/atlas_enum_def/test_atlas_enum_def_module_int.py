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

from ansible_collections.cloudera.services.plugins.modules import atlas_enum_def
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


def test_atlas_enum_def_module_create_idempotent(
    request,
    atlas_module_args,
    atlas_purge_typedef,
):
    """Test create, then an identical re-run reports no change (ordinal handling)."""
    name = atlas_purge_typedef(f"ansible_test_module_{request.node.name.lower()}")
    args = {"name": name, "element_defs": [{"value": "RED"}, {"value": "GREEN"}]}

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()
    assert e.value["changed"] is True
    assert e.value["enum_def"]["guid"] is not None

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()
    assert e.value["changed"] is False


def test_atlas_enum_def_module_check_mode(
    request,
    atlas_module_args,
    atlas_typedef_client,
):
    """Test check mode create leaves Atlas untouched."""
    name = f"ansible_test_check_{request.node.name.lower()}"

    atlas_module_args({"name": name, "_ansible_check_mode": True})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["changed"] is True
    assert atlas_typedef_client.get_enum_def_by_name(name) is None


def test_atlas_enum_def_module_add_element(
    atlas_module_args,
    atlas_deletable_enum_def,
):
    """Test adding an element updates the enum."""
    atlas_module_args(
        {
            "name": atlas_deletable_enum_def.name,
            "element_defs": [{"value": "RED"}, {"value": "BLUE"}],
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["changed"] is True
    assert [el["value"] for el in e.value["enum_def"]["element_defs"]] == [
        "RED",
        "BLUE",
    ]


def test_atlas_enum_def_module_absent(
    atlas_module_args,
    atlas_typedef_client,
    atlas_deletable_enum_def,
):
    """Test absent deletes the enum, then is a no-op."""
    args = {"name": atlas_deletable_enum_def.name, "state": "absent"}

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()
    assert e.value["changed"] is True
    assert (
        atlas_typedef_client.get_enum_def_by_name(atlas_deletable_enum_def.name) is None
    )

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()
    assert e.value["changed"] is False
