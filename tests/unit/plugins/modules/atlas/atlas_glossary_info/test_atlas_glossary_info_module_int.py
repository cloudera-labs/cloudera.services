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
import uuid
from typing import Optional

import pytest

from ansible_collections.cloudera.services.plugins.modules import atlas_glossary_info
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]

UNKNOWN_GUID = "00000000-0000-0000-0000-000000000000"


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


def test_atlas_glossary_info_module_by_guid(
    atlas_module_args, atlas_deletable_glossary
):
    """Test a guid lookup returns the glossary."""
    atlas_module_args({"guid": atlas_deletable_glossary.guid})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert e.value["changed"] is False
    assert len(e.value["glossaries"]) == 1
    glossary = e.value["glossaries"][0]
    assert glossary["guid"] == atlas_deletable_glossary.guid
    assert glossary["name"] == atlas_deletable_glossary.name
    assert glossary["qualified_name"] == atlas_deletable_glossary.qualified_name


def test_atlas_glossary_info_module_by_name(
    atlas_module_args, atlas_deletable_glossary
):
    """Test a name lookup returns the glossary."""
    atlas_module_args({"name": atlas_deletable_glossary.name})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert [g["guid"] for g in e.value["glossaries"]] == [atlas_deletable_glossary.guid]


def test_atlas_glossary_info_module_by_qualified_name(
    atlas_module_args,
    atlas_deletable_glossary,
):
    """Test a qualified name lookup returns the glossary."""
    atlas_module_args({"qualified_name": atlas_deletable_glossary.qualified_name})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert [g["guid"] for g in e.value["glossaries"]] == [atlas_deletable_glossary.guid]


def test_atlas_glossary_info_module_lists_every_glossary(
    atlas_module_args,
    atlas_deletable_glossary,
):
    """Test no criteria returns all glossaries, including a new one."""
    atlas_module_args()

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert atlas_deletable_glossary.guid in [g["guid"] for g in e.value["glossaries"]]


def test_atlas_glossary_info_module_empty_glossary_has_no_headers(
    atlas_module_args,
    atlas_deletable_glossary,
):
    """Test the empty term and category headers Atlas omits are simply absent."""
    atlas_module_args({"guid": atlas_deletable_glossary.guid})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    glossary = e.value["glossaries"][0]
    assert not glossary.get("terms")
    assert not glossary.get("categories")


def test_atlas_glossary_info_module_unknown_guid(atlas_module_args):
    """Test an unknown guid returns no glossaries."""
    atlas_module_args({"guid": UNKNOWN_GUID})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert e.value["glossaries"] == []


def test_atlas_glossary_info_module_unknown_name(atlas_module_args):
    """Test a name nothing carries returns no glossaries."""
    atlas_module_args({"name": f"ansible_test_missing_{uuid.uuid4().hex[:8]}"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert e.value["glossaries"] == []


def test_atlas_glossary_info_module_guid_with_name_fails(
    atlas_module_args,
    atlas_deletable_glossary,
):
    """Test two ways of identifying the glossary are refused."""
    atlas_module_args(
        {"guid": atlas_deletable_glossary.guid, "name": atlas_deletable_glossary.name},
    )

    with pytest.raises(AnsibleFailJson):
        atlas_glossary_info.main()
