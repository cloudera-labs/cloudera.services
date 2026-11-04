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

import json
import uuid

import pytest

from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
)
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

    assert (
        "does not exist" in atlas_rest_client.module.fail_json.call_args.kwargs["msg"]
    )


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


def _business_attributes(atlas_entity_client, guid, name):
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    # Atlas omits businessAttributes once the last business metadata is removed
    business = entity.business_attributes
    return business.get(name) if isinstance(business, dict) else None


def test_set_entity_business_metadata(
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test setting business metadata attributes returns nothing and Atlas stores them."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_business_metadata_def.name

    result = atlas_entity_client.set_entity_business_metadata(
        guid,
        name,
        {"owner_name": "alice", "rank": 3, "reviewed": True},
    )

    assert result is None
    assert _business_attributes(atlas_entity_client, guid, name) == {
        "owner_name": "alice",
        "rank": 3,
        "reviewed": True,
    }


def test_set_entity_business_metadata_merges_within_the_business_metadata(
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test a second set adds and changes attributes but keeps the ones it does not mention."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_business_metadata_def.name

    atlas_entity_client.set_entity_business_metadata(
        guid,
        name,
        {"owner_name": "alice", "rank": 1},
    )
    atlas_entity_client.set_entity_business_metadata(guid, name, {"rank": 2})

    assert _business_attributes(atlas_entity_client, guid, name) == {
        "owner_name": "alice",
        "rank": 2,
    }


def test_set_entity_business_metadata_keeps_other_business_metadata(
    atlas_entity_client,
    atlas_typedef_client,
    atlas_purge_typedef,
    atlas_entity_type,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test setting one business metadata leaves the others alone, because isOverwrite is false."""
    guid = str(atlas_deletable_entity.guid)
    first = atlas_entity_business_metadata_def.name
    second = atlas_purge_typedef(f"{first}_two", force=True)
    atlas_typedef_client.create_business_metadata_def(
        AtlasBusinessMetadataDef(
            name=second,
            attribute_defs=[
                AtlasAttributeDef(
                    name="owner_name",
                    type_name="string",
                    is_optional=True,
                    options={
                        "applicableEntityTypes": json.dumps([atlas_entity_type.name]),
                        "maxStrLength": "50",
                    },
                ),
            ],
        ),
    )

    atlas_entity_client.set_entity_business_metadata(
        guid,
        first,
        {"owner_name": "alice"},
    )
    atlas_entity_client.set_entity_business_metadata(
        guid,
        second,
        {"owner_name": "bob"},
    )

    assert _business_attributes(atlas_entity_client, guid, first) == {
        "owner_name": "alice",
    }
    assert _business_attributes(atlas_entity_client, guid, second) == {
        "owner_name": "bob",
    }


def test_set_entity_business_metadata_stores_strings_as_the_declared_type(
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test Atlas stores "5" for an int attribute as 5, which is why the module converts values before it compares."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_business_metadata_def.name

    atlas_entity_client.set_entity_business_metadata(guid, name, {"rank": "5"})

    stored = _business_attributes(atlas_entity_client, guid, name)
    assert stored is not None
    assert stored == {"rank": 5}
    assert type(stored["rank"]) is int


def test_set_entity_business_metadata_ignores_unknown_attributes(
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test Atlas silently accepts and drops an attribute the typedef lacks, which is why the module validates names."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_business_metadata_def.name

    atlas_entity_client.set_entity_business_metadata(
        guid,
        name,
        {"owner_name": "alice", "no_such_attribute": "x"},
    )

    assert _business_attributes(atlas_entity_client, guid, name) == {
        "owner_name": "alice",
    }


def test_set_entity_business_metadata_not_applicable_to_type_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_deletable_business_metadata_def,
    atlas_deletable_entity,
):
    """Test a business metadata that does not apply to the entity's type is an error (Atlas answers HTTP 404)."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.set_entity_business_metadata(
            str(atlas_deletable_entity.guid),
            atlas_deletable_business_metadata_def.name,
            {"owner": "alice"},
        )

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_set_entity_business_metadata_unknown_business_metadata_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_deletable_entity,
):
    """Test a business metadata name with no typedef is an error."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.set_entity_business_metadata(
            str(atlas_deletable_entity.guid),
            "ansible_test_no_such_business_metadata",
            {"owner_name": "alice"},
        )

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_set_entity_business_metadata_unknown_entity_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_entity_business_metadata_def,
):
    """Test setting business metadata on an unknown guid is an error."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.set_entity_business_metadata(
            UNKNOWN_GUID,
            atlas_entity_business_metadata_def.name,
            {"owner_name": "alice"},
        )

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_remove_entity_business_metadata(
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test removing business metadata deletes the whole business metadata with all its attributes."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_business_metadata_def.name

    atlas_entity_client.set_entity_business_metadata(
        guid,
        name,
        {"owner_name": "alice", "rank": 1},
    )
    result = atlas_entity_client.remove_entity_business_metadata(guid, name)

    assert result is None
    assert _business_attributes(atlas_entity_client, guid, name) is None
