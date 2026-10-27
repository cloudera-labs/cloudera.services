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

from ansible_collections.cloudera.services.plugins.modules import atlas_entity_info
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

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


def test_atlas_entity_info_module_by_guid(atlas_module_args, atlas_deletable_entity):
    """Test a lookup by guid returns the entity."""
    atlas_module_args({"guid": atlas_deletable_entity.guid})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert e.value["changed"] is False
    assert len(e.value["entities"]) == 1
    assert e.value["entities"][0]["guid"] == atlas_deletable_entity.guid
    assert e.value["entities"][0]["status"] == "ACTIVE"


def test_atlas_entity_info_module_by_qualified_name(
    atlas_module_args,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test a lookup by type and qualified name returns the entity, attribute names intact."""
    qualified_name = atlas_deletable_entity.attributes["qualifiedName"]

    atlas_module_args(
        {"type_name": atlas_entity_type.name, "qualified_name": qualified_name},
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert len(e.value["entities"]) == 1
    entity = e.value["entities"][0]
    assert entity["guid"] == atlas_deletable_entity.guid
    assert entity["attributes"]["qualifiedName"] == qualified_name


def test_atlas_entity_info_module_missing_entity(atlas_module_args, atlas_entity_type):
    """Test a missing entity returns no entities and does not fail."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": f"ansible_test_missing_{uuid.uuid4().hex}",
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert e.value["entities"] == []


def test_atlas_entity_info_module_unknown_type_fails(atlas_module_args):
    """Test a mistyped type name fails instead of reporting a missing entity."""
    atlas_module_args(
        {"type_name": "ansible_test_no_such_type", "qualified_name": "q"},
    )
    with pytest.raises(AnsibleFailJson):
        atlas_entity_info.main()


def test_atlas_entity_info_module_deleted_entity(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test a deleted entity shows as DELETED by guid and is absent by qualified name."""
    qualified_name = atlas_deletable_entity.attributes["qualifiedName"]
    atlas_entity_client.delete_entity_by_guid(atlas_deletable_entity.guid)

    atlas_module_args({"guid": atlas_deletable_entity.guid})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()
    assert e.value["entities"][0]["status"] == "DELETED"

    atlas_module_args(
        {"type_name": atlas_entity_type.name, "qualified_name": qualified_name},
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()
    assert e.value["entities"] == []
