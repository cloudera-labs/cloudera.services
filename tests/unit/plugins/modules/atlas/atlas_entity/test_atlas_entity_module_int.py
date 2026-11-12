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

from ansible_collections.cloudera.services.plugins.modules import atlas_entity
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntity,
)
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


@pytest.fixture
def new_qualified_name(atlas_entity_type):
    """A qualified name no entity of the test type has."""
    return f"{atlas_entity_type.name}_{uuid.uuid4().hex[:8]}"


def _qualified_name(entity) -> str:
    return entity.attributes["qualifiedName"]


def _set_with_client(client, entity_type, entity, **fields) -> None:
    """Set up state through the client, so the test only exercises the module."""
    client.update_entity_by_unique_attributes(
        entity_type.name,
        {"qualifiedName": _qualified_name(entity)},
        AtlasEntity(type_name=entity_type.name, **fields),
    )


def test_atlas_entity_module_create(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_purge_entity,
    new_qualified_name,
):
    """Test an entity that does not exist is created."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": new_qualified_name,
            "attributes": {"note": "first"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["entity"]["status"] == "ACTIVE"
    guid = atlas_purge_entity(e.value["entity"]["guid"])
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    assert entity.attributes["qualifiedName"] == new_qualified_name
    assert entity.attributes["note"] == "first"


def test_atlas_entity_module_create_is_idempotent(
    atlas_module_args,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test an entity that exists with the requested values is left alone."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"note": atlas_deletable_entity.attributes["note"]},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    assert e.value["entity"]["guid"] == atlas_deletable_entity.guid


def test_atlas_entity_module_update(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test a changed attribute is updated in place."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"note": "updated"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["entity"]["guid"] == atlas_deletable_entity.guid
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.attributes["note"] == "updated"
    assert entity.attributes["qualifiedName"] == _qualified_name(atlas_deletable_entity)


def test_atlas_entity_module_update_is_idempotent(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test an entity already holding the updated value is left alone."""
    _set_with_client(
        atlas_entity_client,
        atlas_entity_type,
        atlas_deletable_entity,
        attributes={"note": "updated"},
    )

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"note": "updated"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False


def test_atlas_entity_module_update_keeps_unmanaged_attributes(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test an update leaves the attributes the task does not mention as they are."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"count": 7},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.attributes["count"] == 7
    assert entity.attributes["note"] == atlas_deletable_entity.attributes["note"]


def test_atlas_entity_module_string_for_int_is_stored_as_int(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test "5" for an int attribute is sent, and stored, as 5."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"count": "5"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.attributes["count"] == 5


def test_atlas_entity_module_string_for_int_is_idempotent(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test "5" for an int attribute that holds 5 reports no change."""
    _set_with_client(
        atlas_entity_client,
        atlas_entity_type,
        atlas_deletable_entity,
        attributes={"count": 5},
    )

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"count": "5"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False


def test_atlas_entity_module_array_attribute_is_set(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test an array attribute is set as a list."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"tags": ["a", "b"]},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.attributes["tags"] == ["a", "b"]


def test_atlas_entity_module_array_attribute_is_idempotent(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test an array attribute that holds the requested list reports no change."""
    _set_with_client(
        atlas_entity_client,
        atlas_entity_type,
        atlas_deletable_entity,
        attributes={"tags": ["a", "b"]},
    )

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"tags": ["a", "b"]},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False


def test_atlas_entity_module_array_attribute_is_changed(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test an array attribute whose items differ is updated."""
    _set_with_client(
        atlas_entity_client,
        atlas_entity_type,
        atlas_deletable_entity,
        attributes={"tags": ["a", "b"]},
    )

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"tags": ["a", "c"]},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.attributes["tags"] == ["a", "c"]


def test_atlas_entity_module_custom_attributes_are_set(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test custom attributes are set on an entity that has none."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "custom_attributes": {"first": "1"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.custom_attributes == {"first": "1"}


def test_atlas_entity_module_custom_attributes_are_merged(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test new custom attributes are added to the existing ones."""
    _set_with_client(
        atlas_entity_client,
        atlas_entity_type,
        atlas_deletable_entity,
        custom_attributes={"first": "1"},
    )

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "custom_attributes": {"second": "2"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.custom_attributes == {"first": "1", "second": "2"}


def test_atlas_entity_module_custom_attributes_are_idempotent(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test custom attributes that are already set report no change."""
    _set_with_client(
        atlas_entity_client,
        atlas_entity_type,
        atlas_deletable_entity,
        custom_attributes={"first": "1", "second": "2"},
    )

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "custom_attributes": {"second": "2"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False


def test_atlas_entity_module_check_mode_create(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    new_qualified_name,
):
    """Test check mode reports a create without creating the entity."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": new_qualified_name,
            "_ansible_check_mode": True,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert (
        atlas_entity_client.get_entity_by_unique_attributes(
            atlas_entity_type.name,
            {"qualifiedName": new_qualified_name},
        )
        is None
    )


def test_atlas_entity_module_check_mode_update(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test check mode reports an update without changing the entity."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "attributes": {"note": "changed"},
            "_ansible_check_mode": True,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.attributes["note"] == atlas_deletable_entity.attributes["note"]


def test_atlas_entity_module_check_mode_delete(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test check mode reports a delete without deleting the entity."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["deleted_guids"] == [atlas_deletable_entity.guid]
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.status == "ACTIVE"


def test_atlas_entity_module_delete_by_qualified_name(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test absent deletes the entity softly."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "state": "absent",
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["deleted_guids"] == [atlas_deletable_entity.guid]
    assert e.value["entity"]["status"] == "DELETED"
    deleted = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert deleted is not None
    assert deleted.status == "DELETED"


def test_atlas_entity_module_delete_by_qualified_name_is_idempotent(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test absent for an entity that is already deleted reports no change."""
    atlas_entity_client.delete_entity_by_guid(str(atlas_deletable_entity.guid))

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": _qualified_name(atlas_deletable_entity),
            "state": "absent",
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    assert e.value["deleted_guids"] == []


def test_atlas_entity_module_delete_by_guid(
    atlas_module_args,
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test absent can delete an entity identified by its guid."""
    atlas_module_args({"guid": atlas_deletable_entity.guid, "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    deleted = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert deleted is not None
    assert deleted.status == "DELETED"


def test_atlas_entity_module_delete_by_guid_is_idempotent(
    atlas_module_args,
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test absent for a guid that is already deleted reports no change."""
    atlas_entity_client.delete_entity_by_guid(str(atlas_deletable_entity.guid))

    atlas_module_args({"guid": atlas_deletable_entity.guid, "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False


def test_atlas_entity_module_create_again_after_delete_makes_a_new_entity(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_purge_entity,
    atlas_deletable_entity,
):
    """Test present after a delete creates a new entity with a new guid."""
    atlas_entity_client.delete_entity_by_guid(str(atlas_deletable_entity.guid))

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": atlas_deletable_entity.attributes["qualifiedName"],
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["entity"]["guid"] != atlas_deletable_entity.guid
    atlas_purge_entity(e.value["entity"]["guid"])


def test_atlas_entity_module_absent_of_missing_entity(
    atlas_module_args,
    atlas_entity_type,
    new_qualified_name,
):
    """Test absent succeeds without a change for an entity that never existed."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": new_qualified_name,
            "state": "absent",
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    assert e.value["entity"] == {}


def test_atlas_entity_module_unknown_attribute_fails(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    new_qualified_name,
):
    """Test an attribute the type does not define fails, and nothing is created."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": new_qualified_name,
            "attributes": {"noSuchAttribute": "x"},
        },
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "noSuchAttribute" in e.value["msg"]
    assert (
        atlas_entity_client.get_entity_by_unique_attributes(
            atlas_entity_type.name,
            {"qualifiedName": new_qualified_name},
        )
        is None
    )


def test_atlas_entity_module_unknown_type_fails(atlas_module_args):
    """Test an entity type without a typedef fails."""
    atlas_module_args(
        {
            "type_name": f"ansible_test_no_such_type_{uuid.uuid4().hex[:8]}",
            "qualified_name": "q",
        },
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "does not exist" in e.value["msg"]


def test_atlas_entity_module_service_type_is_refused(
    atlas_module_args,
    atlas_typedef_client,
):
    """Test a hook-owned type is refused before any entity is looked up or written."""
    entity_def = atlas_typedef_client.get_entity_def_by_name("hive_table")
    if entity_def is None or not entity_def.service_type:
        pytest.skip("This Atlas has no service-owned hive_table type")

    atlas_module_args(
        {
            "type_name": "hive_table",
            "qualified_name": f"ansible_test_never_created_{uuid.uuid4().hex[:8]}",
        },
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "allow_service_types" in e.value["msg"]
