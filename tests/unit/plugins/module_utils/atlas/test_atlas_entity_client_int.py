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

import uuid

import pytest

from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntity,
)
from ansible_collections.cloudera.services.tests.unit import AnsibleFailJson

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]

UNKNOWN_GUID = "00000000-0000-0000-0000-000000000000"


def test_create_entity(
    atlas_entity_client,
    atlas_entity_type,
    atlas_purge_entity,
):
    """Test creating an entity returns it as Atlas stored it."""
    qualified_name = f"ansible_test_create_{uuid.uuid4().hex[:8]}"

    entity = atlas_entity_client.create_entity(
        AtlasEntity(
            type_name=atlas_entity_type.name,
            attributes={"qualifiedName": qualified_name, "note": "created"},
        ),
    )
    atlas_purge_entity(str(entity.guid))

    assert isinstance(entity, AtlasEntity)
    assert entity.guid
    assert entity.status == "ACTIVE"
    assert entity.type_name == atlas_entity_type.name
    assert isinstance(entity.attributes, dict)
    assert entity.attributes["qualifiedName"] == qualified_name
    assert entity.attributes["note"] == "created"


def test_get_entity_by_guid(atlas_entity_client, atlas_deletable_entity):
    """Test a guid lookup returns the entity."""
    entity = atlas_entity_client.get_entity_by_guid(str(atlas_deletable_entity.guid))

    assert entity is not None
    assert entity.guid == atlas_deletable_entity.guid
    assert entity.status == "ACTIVE"


def test_get_entity_by_guid_not_found(atlas_entity_client):
    """Test an unknown guid returns None (verifies Atlas 404 behavior)."""
    assert atlas_entity_client.get_entity_by_guid(UNKNOWN_GUID) is None


def test_get_entity_by_unique_attributes(
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test a lookup by type and qualifiedName returns the entity."""
    assert isinstance(atlas_deletable_entity.attributes, dict)

    entity = atlas_entity_client.get_entity_by_unique_attributes(
        atlas_entity_type.name,
        {"qualifiedName": atlas_deletable_entity.attributes["qualifiedName"]},
    )

    assert entity is not None
    assert entity.guid == atlas_deletable_entity.guid


def test_get_entity_by_unique_attributes_not_found(
    atlas_entity_client,
    atlas_entity_type,
):
    """Test a missing entity returns None."""
    assert (
        atlas_entity_client.get_entity_by_unique_attributes(
            atlas_entity_type.name,
            {"qualifiedName": f"ansible_test_missing_{uuid.uuid4().hex}"},
        )
        is None
    )


def test_get_entity_by_unique_attributes_unknown_type_fails(
    atlas_entity_client,
    atlas_rest_client,
):
    """Test a mistyped type name is an error, not a missing entity (Atlas answers HTTP 400)."""
    # The real client reports HTTP errors through module.fail_json(); the fixture's
    # mock raises AnsibleFailJson and keeps Atlas's message in the call arguments.
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.get_entity_by_unique_attributes(
            "ansible_test_no_such_type",
            {"qualifiedName": "q"},
        )

    assert "does not exist" in atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_delete_entity_is_soft(
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test a deleted entity stays visible by guid as DELETED but not by unique attributes."""
    guid = str(atlas_deletable_entity.guid)
    assert isinstance(atlas_deletable_entity.attributes, dict)
    qualified_name = atlas_deletable_entity.attributes["qualifiedName"]

    atlas_entity_client.delete_entity_by_guid(guid)

    by_guid = atlas_entity_client.get_entity_by_guid(guid)
    assert by_guid is not None
    assert by_guid.status == "DELETED"
    assert (
        atlas_entity_client.get_entity_by_unique_attributes(
            atlas_entity_type.name,
            {"qualifiedName": qualified_name},
        )
        is None
    )


def test_purge_entities_removes_a_deleted_entity(
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test purging a deleted entity makes its guid unknown (needs Atlas admin rights)."""
    guid = str(atlas_deletable_entity.guid)

    atlas_entity_client.delete_entity_by_guid(guid)
    atlas_entity_client.purge_entities([guid])

    assert atlas_entity_client.get_entity_by_guid(guid) is None
