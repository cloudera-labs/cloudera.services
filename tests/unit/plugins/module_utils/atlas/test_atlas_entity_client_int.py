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
    AtlasClassification,
    AtlasEntity,
    entity_attribute_defs,
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


def _labels(atlas_entity_client, guid):
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    # Atlas may omit labels for an entity that has none
    return entity.labels if isinstance(entity.labels, list) else []


def test_set_entity_labels(atlas_entity_client, atlas_deletable_entity):
    """Test setting labels returns nothing and Atlas stores them."""
    guid = str(atlas_deletable_entity.guid)

    result = atlas_entity_client.set_entity_labels(guid, ["ansible-one", "two_2"])

    assert result is None
    assert set(_labels(atlas_entity_client, guid)) == {"ansible-one", "two_2"}


def test_set_entity_labels_replaces_the_whole_list(
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test a second set replaces the labels instead of adding to them (POST sets the whole list)."""
    guid = str(atlas_deletable_entity.guid)

    atlas_entity_client.set_entity_labels(guid, ["first", "second"])
    atlas_entity_client.set_entity_labels(guid, ["third"])

    assert _labels(atlas_entity_client, guid) == ["third"]


def test_set_entity_labels_empty_list_clears(
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test setting an empty list removes every label, the only way to remove labels through Knox."""
    guid = str(atlas_deletable_entity.guid)

    atlas_entity_client.set_entity_labels(guid, ["first", "second"])
    atlas_entity_client.set_entity_labels(guid, [])

    assert _labels(atlas_entity_client, guid) == []


def test_set_entity_labels_invalid_label_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_deletable_entity,
):
    """Test a label Atlas rejects (HTTP 400, ATLAS-400-00-090) is an error and changes nothing."""
    guid = str(atlas_deletable_entity.guid)
    atlas_entity_client.set_entity_labels(guid, ["keep"])

    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.set_entity_labels(guid, ["has space"])

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]
    assert _labels(atlas_entity_client, guid) == ["keep"]


def test_set_entity_labels_unknown_entity_fails(
    atlas_entity_client,
    atlas_rest_client,
):
    """Test setting labels on an unknown guid is an error."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.set_entity_labels(UNKNOWN_GUID, ["a"])

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


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


def _classification(atlas_entity_client, guid, name):
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    # Atlas omits classifications once the last one is removed
    classifications = (
        entity.classifications if isinstance(entity.classifications, list) else []
    )
    return next((c for c in classifications if c.type_name == name), None)


def test_add_entity_classifications(
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test attaching a classification returns nothing, and Atlas stores it with its defaults."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_classification_def.name

    result = atlas_entity_client.add_entity_classifications(
        guid,
        [AtlasClassification(type_name=name, attributes={"level": "high", "rank": 2})],
    )

    assert result is None
    attached = _classification(atlas_entity_client, guid, name)
    assert attached is not None
    assert attached.entity_guid == guid
    assert attached.propagate is True
    assert attached.remove_propagations_on_entity_delete is False
    assert isinstance(attached.attributes, dict)
    assert attached.attributes["level"] == "high"
    assert attached.attributes["rank"] == 2


def test_add_entity_classifications_with_flags(
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test the propagation flags are stored as given."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_classification_def.name

    atlas_entity_client.add_entity_classifications(
        guid,
        [
            AtlasClassification(
                type_name=name,
                propagate=False,
                remove_propagations_on_entity_delete=True,
            ),
        ],
    )

    attached = _classification(atlas_entity_client, guid, name)
    assert attached is not None
    assert attached.propagate is False
    assert attached.remove_propagations_on_entity_delete is True


def test_add_entity_classifications_drops_unknown_attributes(
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test Atlas silently drops an attribute the typedef lacks, which is why the module validates names."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_classification_def.name

    atlas_entity_client.add_entity_classifications(
        guid,
        [
            AtlasClassification(
                type_name=name,
                attributes={"level": "high", "no_such_attribute": "x"},
            ),
        ],
    )

    attached = _classification(atlas_entity_client, guid, name)
    assert attached is not None
    assert isinstance(attached.attributes, dict)
    assert attached.attributes["level"] == "high"
    assert "no_such_attribute" not in attached.attributes


def test_add_entity_classifications_twice_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test attaching a classification that is already attached is an error (Atlas answers HTTP 400)."""
    guid = str(atlas_deletable_entity.guid)
    classification = AtlasClassification(type_name=atlas_entity_classification_def.name)
    atlas_entity_client.add_entity_classifications(guid, [classification])

    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.add_entity_classifications(guid, [classification])

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_add_entity_classifications_unknown_classification_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_deletable_entity,
):
    """Test attaching a classification that has no typedef is an error."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.add_entity_classifications(
            str(atlas_deletable_entity.guid),
            [AtlasClassification(type_name="ansible_test_no_such_classification")],
        )

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_add_entity_classifications_unknown_entity_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_entity_classification_def,
):
    """Test attaching a classification to an unknown guid is an error."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.add_entity_classifications(
            UNKNOWN_GUID,
            [AtlasClassification(type_name=atlas_entity_classification_def.name)],
        )

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_update_entity_classifications(
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test updating a classification returns nothing and changes the attribute and the flags."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_classification_def.name
    atlas_entity_client.add_entity_classifications(
        guid,
        [AtlasClassification(type_name=name, attributes={"level": "low"})],
    )

    result = atlas_entity_client.update_entity_classifications(
        guid,
        [
            AtlasClassification(
                type_name=name,
                attributes={"level": "high"},
                propagate=False,
                remove_propagations_on_entity_delete=True,
            ),
        ],
    )

    assert result is None
    attached = _classification(atlas_entity_client, guid, name)
    assert attached is not None
    assert isinstance(attached.attributes, dict)
    assert attached.attributes["level"] == "high"
    assert attached.propagate is False
    assert attached.remove_propagations_on_entity_delete is True


def test_update_entity_classifications_merges_attributes(
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test an update keeps the attributes it does not mention, so one cannot be cleared by leaving it out."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_classification_def.name
    atlas_entity_client.add_entity_classifications(
        guid,
        [AtlasClassification(type_name=name, attributes={"level": "low", "rank": 1})],
    )

    atlas_entity_client.update_entity_classifications(
        guid,
        [AtlasClassification(type_name=name, attributes={"rank": 2})],
    )

    attached = _classification(atlas_entity_client, guid, name)
    assert attached is not None
    assert isinstance(attached.attributes, dict)
    assert attached.attributes["level"] == "low"
    assert attached.attributes["rank"] == 2


def test_update_entity_classifications_not_attached_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test updating a classification that is not attached is an error (Atlas answers HTTP 400)."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.update_entity_classifications(
            str(atlas_deletable_entity.guid),
            [AtlasClassification(type_name=atlas_entity_classification_def.name)],
        )

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_remove_entity_classification(
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test removing a classification returns nothing and detaches it."""
    guid = str(atlas_deletable_entity.guid)
    name = atlas_entity_classification_def.name
    atlas_entity_client.add_entity_classifications(
        guid,
        [AtlasClassification(type_name=name)],
    )

    result = atlas_entity_client.remove_entity_classification(guid, name)

    assert result is None
    assert _classification(atlas_entity_client, guid, name) is None


def test_remove_entity_classification_not_attached_fails(
    atlas_entity_client,
    atlas_rest_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test removing a classification that is not attached is an error (Atlas answers HTTP 400)."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.remove_entity_classification(
            str(atlas_deletable_entity.guid),
            atlas_entity_classification_def.name,
        )

    assert atlas_rest_client.module.fail_json.call_args.kwargs["msg"]


def test_update_entity_by_unique_attributes_is_partial(
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test a partial update changes only the attributes given."""
    qualified_name = atlas_deletable_entity.attributes["qualifiedName"]

    atlas_entity_client.update_entity_by_unique_attributes(
        atlas_entity_type.name,
        {"qualifiedName": qualified_name},
        AtlasEntity(type_name=atlas_entity_type.name, attributes={"count": 3}),
    )

    entity = atlas_entity_client.get_entity_by_guid(str(atlas_deletable_entity.guid))
    assert entity is not None
    assert entity.status == "ACTIVE"
    assert entity.attributes["count"] == 3
    assert entity.attributes["note"] == atlas_deletable_entity.attributes["note"]
    assert entity.attributes["qualifiedName"] == qualified_name


def test_update_entity_by_unique_attributes_sets_custom_attributes(
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test custom attributes are set by a partial update, and the attributes are left alone."""
    qualified_name = atlas_deletable_entity.attributes["qualifiedName"]

    atlas_entity_client.update_entity_by_unique_attributes(
        atlas_entity_type.name,
        {"qualifiedName": qualified_name},
        AtlasEntity(
            type_name=atlas_entity_type.name,
            custom_attributes={"first": "1", "second": "2"},
        ),
    )

    entity = atlas_entity_client.get_entity_by_guid(str(atlas_deletable_entity.guid))
    assert entity is not None
    assert entity.custom_attributes == {"first": "1", "second": "2"}
    assert entity.attributes["note"] == atlas_deletable_entity.attributes["note"]


def test_update_entity_by_unique_attributes_unknown_entity_fails(
    atlas_rest_client,
    atlas_entity_client,
    atlas_entity_type,
):
    """Test updating an entity that does not exist fails."""
    with pytest.raises(AnsibleFailJson):
        atlas_entity_client.update_entity_by_unique_attributes(
            atlas_entity_type.name,
            {"qualifiedName": f"ansible_test_missing_{uuid.uuid4().hex}"},
            AtlasEntity(type_name=atlas_entity_type.name, attributes={"count": 1}),
        )


def test_delete_entity_by_guid_returns_the_deleted_guids(
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test a delete reports the guid it deleted, and a repeat delete reports none."""
    guid = str(atlas_deletable_entity.guid)

    assert atlas_entity_client.delete_entity_by_guid(guid) == [guid]
    assert atlas_entity_client.delete_entity_by_guid(guid) == []


def test_delete_entity_by_guid_unknown_guid_returns_no_guids(atlas_entity_client):
    """Test the silent HTTP 200 Atlas gives for an unknown guid returns an empty list."""
    assert atlas_entity_client.delete_entity_by_guid(UNKNOWN_GUID) == []


def test_entity_attribute_defs(atlas_typedef_client, atlas_entity_type):
    """Test the attributes of the type include the ones inherited from Referenceable."""
    attribute_defs = entity_attribute_defs(atlas_typedef_client, atlas_entity_type.name)

    assert attribute_defs is not None
    names = {attribute_def.name for attribute_def in attribute_defs}
    assert {"note", "count", "tags", "qualifiedName"} <= names


def test_entity_attribute_defs_unknown_type(atlas_typedef_client):
    """Test a type without a typedef returns None."""
    assert (
        entity_attribute_defs(atlas_typedef_client, "ansible_test_no_such_type") is None
    )
