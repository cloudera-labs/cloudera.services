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
from typing import Any, Dict, List, Optional

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import atlas_entity
from ansible_collections.cloudera.services.plugins.module_utils.common import NULLABLE
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasEntityDef,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntity,
)

BASE_URL = "https://atlas.example"
MODULE = "ansible_collections.cloudera.services.plugins.modules.atlas_entity"
CLIENT = f"{MODULE}.AtlasEntityClient"
TYPEDEF = f"{MODULE}.AtlasTypeDefClient.get_entity_def_by_name"
GUID = "fc0fd256-be16-4775-99ad-9e0b7e304ae5"
TYPE = "test_entity_type"
QN = "test_entity_1"


def _entity(
    attributes: Optional[Dict[str, Any]] = None,
    custom_attributes: Optional[Dict[str, str]] = None,
    status: str = "ACTIVE",
    type_name: str = TYPE,
) -> AtlasEntity:
    """Build an entity as Atlas returns it; custom attributes are left unset when None."""
    entity = AtlasEntity(
        type_name=type_name,
        guid=GUID,
        status=status,
        attributes={"qualifiedName": QN, **(attributes or {})},
    )
    if custom_attributes is not None:
        entity.custom_attributes = custom_attributes
    return entity


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        "type_name": TYPE,
        "qualified_name": QN,
        **extra,
    }


@pytest.fixture
def typedefs(mocker):
    """Patch the entity typedef lookup with the test type, its parent and a hook-owned type."""
    defs = {
        TYPE: AtlasEntityDef(
            name=TYPE,
            super_types=["Referenceable"],
            attribute_defs=[
                AtlasAttributeDef(name="note", type_name="string"),
                AtlasAttributeDef(name="count", type_name="int"),
                AtlasAttributeDef(name="tags", type_name="array<string>"),
            ],
        ),
        "Referenceable": AtlasEntityDef(
            name="Referenceable",
            attribute_defs=[
                AtlasAttributeDef(name="qualifiedName", type_name="string"),
            ],
        ),
        "hive_table": AtlasEntityDef(
            name="hive_table",
            service_type="hive",
            super_types=["Referenceable"],
            attribute_defs=[AtlasAttributeDef(name="owner", type_name="string")],
        ),
    }
    return mocker.patch(TYPEDEF, side_effect=defs.get)


def test_atlas_entity_module_present_creates_missing_entity(
    module_args,
    mocker,
    typedefs,
):
    """Test present creates an entity that does not exist, with the identity merged into its attributes."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_entity",
        return_value=_entity({"note": "hello"}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")

    module_args(_args(attributes={"note": "hello"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["deleted_guids"] == []
    assert e.value["entity"]["guid"] == GUID
    assert e.value["entity"]["attributes"] == {"qualifiedName": QN, "note": "hello"}
    mock_create.assert_called_once_with(
        AtlasEntity(
            type_name=TYPE,
            attributes={"qualifiedName": QN, "note": "hello"},
        ),
    )
    mock_update.assert_not_called()


def test_atlas_entity_module_present_creates_entity_with_custom_attributes(
    module_args,
    mocker,
    typedefs,
):
    """Test custom attributes are sent on create."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_entity",
        return_value=_entity(custom_attributes={"owner": "me"}),
    )

    module_args(_args(custom_attributes={"owner": "me"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["entity"]["custom_attributes"] == {"owner": "me"}
    mock_create.assert_called_once_with(
        AtlasEntity(
            type_name=TYPE,
            attributes={"qualifiedName": QN},
            custom_attributes={"owner": "me"},
        ),
    )


def test_atlas_entity_module_present_by_unique_attributes(
    module_args,
    mocker,
    typedefs,
):
    """Test unique_attributes identify the entity and are used as given."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(),
    )

    args = _args(unique_attributes={"qualifiedName": QN})
    del args["qualified_name"]
    module_args(args)

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    mock_get.assert_called_once_with(TYPE, {"qualifiedName": QN})


def test_atlas_entity_module_present_updates_changed_attribute(
    module_args,
    mocker,
    typedefs,
):
    """Test present sends only the attribute that differs, as a partial update by unique attribute."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "old", "count": 1}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")
    mock_read = mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({"note": "new", "count": 1}),
    )
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    module_args(_args(attributes={"note": "new", "count": 1}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["entity"]["attributes"]["note"] == "new"
    mock_update.assert_called_once_with(
        TYPE,
        {"qualifiedName": QN},
        AtlasEntity(type_name=TYPE, attributes={"note": "new"}),
    )
    mock_read.assert_called_once_with(GUID)
    mock_create.assert_not_called()


def test_atlas_entity_module_present_is_idempotent(module_args, mocker, typedefs):
    """Test present makes no change when the managed attributes already match."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "same"}, custom_attributes={"a": "1"}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    module_args(_args(attributes={"note": "same"}, custom_attributes={"a": "1"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    assert e.value["entity"]["guid"] == GUID
    mock_update.assert_not_called()
    mock_create.assert_not_called()


def test_atlas_entity_module_present_only_compares_managed_attributes(
    module_args,
    mocker,
    typedefs,
):
    """Test attributes the task does not mention, including server defaults, are not a change."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "same", "count": 0, "replicatedTo": None}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")

    module_args(_args(attributes={"note": "same"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_atlas_entity_module_present_with_only_the_identity(
    module_args,
    mocker,
    typedefs,
):
    """Test an existing entity needs nothing when only the identity is given."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "x"}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")

    module_args(_args())

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_atlas_entity_module_string_for_int_is_idempotent(
    module_args,
    mocker,
    typedefs,
):
    """Test "5" for an int attribute matches the 5 Atlas stores, so a repeated run reports no change."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"count": 5}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")

    module_args(_args(attributes={"count": "5"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_atlas_entity_module_string_for_int_is_sent_as_int(
    module_args,
    mocker,
    typedefs,
):
    """Test the value is converted to the declared type before it is sent."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_entity",
        return_value=_entity({"count": 5}),
    )

    module_args(_args(attributes={"count": "5"}))

    with pytest.raises(AnsibleExitJson):
        atlas_entity.main()

    assert mock_create.call_args.args[0].attributes["count"] == 5


def test_atlas_entity_module_array_attribute_is_compared_as_a_list(
    module_args,
    mocker,
    typedefs,
):
    """Test an array attribute changes when its items differ and not when they match."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"tags": ["a", "b"]}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({"tags": ["a", "c"]}),
    )

    module_args(_args(attributes={"tags": ["a", "c"]}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert mock_update.call_args.args[2].attributes == {"tags": ["a", "c"]}


def test_atlas_entity_module_custom_attributes_are_merged_with_existing(
    module_args,
    mocker,
    typedefs,
):
    """Test the update sends the existing custom attributes along with the new ones, since Atlas may replace the whole map."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(custom_attributes={"a": "1", "b": "2"}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity(custom_attributes={"a": "1", "b": "3", "c": "4"}),
    )

    module_args(_args(custom_attributes={"b": "3", "c": "4"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    sent = mock_update.call_args.args[2]
    assert sent.custom_attributes == {"a": "1", "b": "3", "c": "4"}
    assert sent.attributes is NULLABLE


def test_atlas_entity_module_custom_attributes_on_entity_without_any(
    module_args,
    mocker,
    typedefs,
):
    """Test an entity without a customAttributes key counts as having none."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity(custom_attributes={"a": "1"}),
    )

    module_args(_args(custom_attributes={"a": "1"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert mock_update.call_args.args[2].custom_attributes == {"a": "1"}


def test_atlas_entity_module_attribute_conflicting_with_identity_fails(
    module_args,
    mocker,
    typedefs,
):
    """Test an attribute that names the unique attribute with another value fails before any lookup."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")

    module_args(_args(attributes={"qualifiedName": "other"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "qualifiedName" in e.value["msg"]
    mock_get.assert_not_called()


def test_atlas_entity_module_attribute_repeating_identity_is_accepted(
    module_args,
    mocker,
    typedefs,
):
    """Test repeating the unique attribute with the same value is harmless."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(),
    )

    module_args(_args(attributes={"qualifiedName": QN}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False


def test_atlas_entity_module_unknown_attribute_fails(module_args, mocker, typedefs):
    """Test an attribute the type lacks fails, because Atlas would ignore it."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    module_args(_args(attributes={"nope": "x"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "nope" in e.value["msg"]
    mock_create.assert_not_called()


@pytest.mark.parametrize(
    "attributes",
    [{"note": None}, {"count": "many"}, {"tags": "a"}],
    ids=["null", "bad-int", "not-a-list"],
)
def test_atlas_entity_module_invalid_value_fails(
    module_args,
    mocker,
    typedefs,
    attributes,
):
    """Test a null or ill-typed value fails without a write."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    module_args(_args(attributes=attributes))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert next(iter(attributes)) in e.value["msg"]
    mock_create.assert_not_called()


def test_atlas_entity_module_custom_attribute_must_be_a_string(
    module_args,
    mocker,
    typedefs,
):
    """Test a custom attribute value that is not a string fails."""
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    module_args(_args(custom_attributes={"a": 1}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "a" in e.value["msg"]
    mock_create.assert_not_called()


def test_atlas_entity_module_unknown_entity_type_fails(module_args, mocker, typedefs):
    """Test a type that has no typedef fails without a write."""
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    module_args(_args(type_name="nope_type"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "nope_type" in e.value["msg"]
    assert "does not exist" in e.value["msg"]
    mock_create.assert_not_called()


def test_atlas_entity_module_service_type_is_refused(module_args, mocker, typedefs):
    """Test a type owned by a service hook is refused unless allowed."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    module_args(_args(type_name="hive_table"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "hive_table" in e.value["msg"]
    assert "allow_service_types" in e.value["msg"]
    mock_get.assert_not_called()
    mock_create.assert_not_called()


def test_atlas_entity_module_service_type_is_allowed_when_opted_in(
    module_args,
    mocker,
    typedefs,
):
    """Test allow_service_types lets the module manage a hook-owned type."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_entity",
        return_value=_entity(type_name="hive_table"),
    )

    module_args(_args(type_name="hive_table", allow_service_types=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    mock_create.assert_called_once()


def test_atlas_entity_module_created_entity_not_active_fails(
    module_args,
    mocker,
    typedefs,
):
    """Test an entity that Atlas reports as not ACTIVE after creation fails."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mocker.patch(f"{CLIENT}.create_entity", return_value=_entity(status="DELETED"))

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "ACTIVE" in e.value["msg"]


@pytest.mark.parametrize(
    "read_back",
    [None, _entity(status="DELETED")],
    ids=["gone", "deleted"],
)
def test_atlas_entity_module_update_not_visible_afterwards_fails(
    module_args,
    mocker,
    typedefs,
    read_back,
):
    """Test an entity that is missing or not ACTIVE after an update fails."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "old"}),
    )
    mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=read_back)

    module_args(_args(attributes={"note": "new"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "ACTIVE" in e.value["msg"]


def test_atlas_entity_module_absent_deletes_entity(module_args, mocker, typedefs):
    """Test absent deletes an entity that exists and reports the guids Atlas deleted."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "x"}),
    )
    mock_delete = mocker.patch(
        f"{CLIENT}.delete_entity_by_guid",
        return_value=[GUID, "owned-guid"],
    )
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({"note": "x"}, status="DELETED"),
    )

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["deleted_guids"] == [GUID, "owned-guid"]
    assert e.value["entity"]["status"] == "DELETED"
    mock_delete.assert_called_once_with(GUID)


def test_atlas_entity_module_absent_by_guid(module_args, mocker, typedefs):
    """Test absent can identify the entity by guid alone."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_get.side_effect = [_entity(), _entity(status="DELETED")]
    mock_unique = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")
    mocker.patch(f"{CLIENT}.delete_entity_by_guid", return_value=[GUID])

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "guid": GUID,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    mock_unique.assert_not_called()


def test_atlas_entity_module_absent_is_idempotent(module_args, mocker, typedefs):
    """Test absent makes no change when there is no such entity."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mock_delete = mocker.patch(f"{CLIENT}.delete_entity_by_guid")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    assert e.value["entity"] == {}
    assert e.value["deleted_guids"] == []
    mock_delete.assert_not_called()


@pytest.mark.parametrize(
    "entity",
    [None, _entity(status="DELETED")],
    ids=["unknown", "deleted"],
)
def test_atlas_entity_module_absent_by_guid_without_an_active_entity_is_a_no_op(
    module_args,
    mocker,
    typedefs,
    entity,
):
    """Test an unknown or already deleted guid has nothing to delete."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=entity)
    mock_delete = mocker.patch(f"{CLIENT}.delete_entity_by_guid")

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "guid": GUID,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_atlas_entity_module_absent_service_type_is_refused(
    module_args,
    mocker,
    typedefs,
):
    """Test deleting an entity of a hook-owned type is refused, because the delete can cascade."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(type_name="hive_table"),
    )
    mock_delete = mocker.patch(f"{CLIENT}.delete_entity_by_guid")

    module_args(_args(type_name="hive_table", state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "allow_service_types" in e.value["msg"]
    mock_delete.assert_not_called()


def test_atlas_entity_module_absent_of_a_missing_service_entity_is_not_refused(
    module_args,
    mocker,
    typedefs,
):
    """Test the guard only matters when there is something to delete."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)

    module_args(_args(type_name="hive_table", state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False


def test_atlas_entity_module_absent_entity_still_active_fails(
    module_args,
    mocker,
    typedefs,
):
    """Test an entity that is still ACTIVE after the delete fails."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(),
    )
    mocker.patch(f"{CLIENT}.delete_entity_by_guid", return_value=[])
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "DELETED" in e.value["msg"]


def test_atlas_entity_module_absent_with_values_fails(module_args, mocker, typedefs):
    """Test attributes with absent fail before any Atlas call."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")

    module_args(_args(state="absent", attributes={"note": "x"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "absent" in e.value["msg"]
    mock_get.assert_not_called()


def test_atlas_entity_module_present_by_guid_fails(module_args, mocker, typedefs):
    """Test guid is only for absent, because creating needs the type and unique attributes."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "guid": GUID,
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "guid" in e.value["msg"]
    mock_get.assert_not_called()


def test_atlas_entity_module_present_without_unique_attributes_fails(
    module_args,
    mocker,
    typedefs,
):
    """Test present needs qualified_name or unique_attributes with the type."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")

    args = _args()
    del args["qualified_name"]
    module_args(args)

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "qualified_name" in e.value["msg"]
    mock_get.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"guid": GUID},
        {"guid": GUID, "qualified_name": None, "unique_attributes": {"a": "b"}},
        {"qualified_name": None},
        {"unique_attributes": {"qualifiedName": QN}},
        {"type_name": None, "qualified_name": QN},
    ],
    ids=[
        "guid-and-type",
        "guid-and-unique-attributes",
        "type-without-identity",
        "qualified-name-and-unique-attributes",
        "qualified-name-without-type",
    ],
)
def test_atlas_entity_module_invalid_arguments_fail(module_args, mocker, extra):
    """Test an ambiguous or incomplete identity fails before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")
    mock_by_guid = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    args = _args()
    args.update(extra)
    module_args({k: v for k, v in args.items() if v is not None})

    with pytest.raises(AnsibleFailJson):
        atlas_entity.main()

    mock_get.assert_not_called()
    mock_by_guid.assert_not_called()
    mock_create.assert_not_called()


def test_atlas_entity_module_check_mode_create(module_args, mocker, typedefs):
    """Test check mode reports the entity it would create, with no write."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_entity")

    module_args(
        _args(
            attributes={"count": "2"},
            custom_attributes={"a": "1"},
            _ansible_check_mode=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["entity"]["type_name"] == TYPE
    assert e.value["entity"]["attributes"] == {"qualifiedName": QN, "count": 2}
    assert e.value["entity"]["custom_attributes"] == {"a": "1"}
    mock_create.assert_not_called()


def test_atlas_entity_module_check_mode_update(module_args, mocker, typedefs):
    """Test check mode reports the merged entity it would leave, with no write."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "old", "count": 1}),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")

    module_args(_args(attributes={"note": "new"}, _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["entity"]["guid"] == GUID
    assert e.value["entity"]["attributes"] == {
        "qualifiedName": QN,
        "note": "new",
        "count": 1,
    }
    mock_update.assert_not_called()


def test_atlas_entity_module_check_mode_absent(module_args, mocker, typedefs):
    """Test check mode reports the delete it would do, with no write."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(),
    )
    mock_delete = mocker.patch(f"{CLIENT}.delete_entity_by_guid")

    module_args(_args(state="absent", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["deleted_guids"] == [GUID]
    assert e.value["entity"]["status"] == "DELETED"
    mock_delete.assert_not_called()


def test_atlas_entity_module_diff_mode_create(module_args, mocker, typedefs):
    """Test diff mode shows the attributes of a new entity."""
    mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes", return_value=None)
    mocker.patch(f"{CLIENT}.create_entity", return_value=_entity({"note": "n"}))

    module_args(_args(attributes={"note": "n"}, _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["diff"] == {
        "before": {"entity": {}},
        "after": {
            "entity": {"attributes": {"qualifiedName": QN, "note": "n"}},
        },
    }


def test_atlas_entity_module_diff_mode_update(module_args, mocker, typedefs):
    """Test diff mode shows only the managed values that change."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "old"}, custom_attributes={"a": "1"}),
    )
    mocker.patch(f"{CLIENT}.update_entity_by_unique_attributes")
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({"note": "new"}, custom_attributes={"a": "2"}),
    )

    module_args(
        _args(
            attributes={"note": "new"},
            custom_attributes={"a": "2"},
            _ansible_diff=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["diff"] == {
        "before": {
            "entity": {"attributes": {"note": "old"}, "custom_attributes": {"a": "1"}},
        },
        "after": {
            "entity": {"attributes": {"note": "new"}, "custom_attributes": {"a": "2"}},
        },
    }


def test_atlas_entity_module_diff_mode_absent(module_args, mocker, typedefs):
    """Test diff mode shows the entity that is removed."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "x"}),
    )
    mocker.patch(f"{CLIENT}.delete_entity_by_guid", return_value=[GUID])
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity(status="DELETED"),
    )

    module_args(_args(state="absent", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["diff"] == {
        "before": {
            "entity": {
                "guid": GUID,
                "type_name": TYPE,
                "attributes": {"qualifiedName": QN, "note": "x"},
            },
        },
        "after": {"entity": {}},
    }


def test_atlas_entity_module_diff_mode_without_change(module_args, mocker, typedefs):
    """Test diff mode has no diff when nothing changes."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity({"note": "same"}),
    )

    module_args(_args(attributes={"note": "same"}, _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is False
    assert not e.value["diff"]


def _entity_json(attributes=None, status="ACTIVE"):
    return {
        "referredEntities": {},
        "entity": {
            "typeName": TYPE,
            "attributes": {"qualifiedName": QN, **(attributes or {})},
            "guid": GUID,
            "status": status,
        },
    }


TYPEDEF_JSON = {
    "category": "ENTITY",
    "name": TYPE,
    "superTypes": ["Referenceable"],
    "attributeDefs": [{"name": "note", "typeName": "string"}],
}

PARENT_TYPEDEF_JSON = {
    "category": "ENTITY",
    "name": "Referenceable",
    "attributeDefs": [{"name": "qualifiedName", "typeName": "string"}],
}


def _typedef_response(mocker, url):
    if url.split("?")[0].endswith("/Referenceable"):
        return http_result(mocker, 200, PARENT_TYPEDEF_JSON)
    return http_result(mocker, 200, TYPEDEF_JSON)


def test_atlas_entity_module_create_requests(module_args, mocker):
    """Test the real requests: look the entity up (404), POST it, then read it back by guid."""
    calls: List[Any] = []

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if "/types/entitydef/" in url:
            return _typedef_response(mocker, url)
        if "/uniqueAttribute/" in url:
            return http_result(
                mocker,
                404,
                {"errorCode": "ATLAS-404-00-009", "errorMessage": "not found"},
            )
        if method == "POST":
            return http_result(
                mocker,
                200,
                {"mutatedEntities": {"CREATE": [{"guid": GUID}]}},
            )
        return http_result(mocker, 200, _entity_json({"note": "n"}))

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"note": "n"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["entity"]["guid"] == GUID
    post = [c for c in calls if c[0] == "POST"]
    assert len(post) == 1
    assert post[0][1].endswith("/api/atlas/v2/entity")
    assert json.loads(post[0][2]) == {
        "entity": {
            "typeName": TYPE,
            "attributes": {"qualifiedName": QN, "note": "n"},
        },
    }


def test_atlas_entity_module_update_requests(module_args, mocker):
    """Test the real requests: a partial PUT by unique attribute carrying only the changed attribute."""
    calls: List[Any] = []
    reads = iter([_entity_json({"note": "old"}), _entity_json({"note": "new"})])

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if "/types/entitydef/" in url:
            return _typedef_response(mocker, url)
        if method == "PUT":
            return http_result(mocker, 200, {"mutatedEntities": {}})
        return http_result(mocker, 200, next(reads))

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"note": "new"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["entity"]["attributes"]["note"] == "new"
    put = [c for c in calls if c[0] == "PUT"]
    assert len(put) == 1
    assert f"/api/atlas/v2/entity/uniqueAttribute/type/{TYPE}" in put[0][1]
    assert "attr%3AqualifiedName=test_entity_1" in put[0][1]
    assert json.loads(put[0][2]) == {
        "entity": {"typeName": TYPE, "attributes": {"note": "new"}},
    }
    assert not [c for c in calls if c[0] == "POST"]


def test_atlas_entity_module_delete_requests(module_args, mocker):
    """Test the real requests: look the entity up, DELETE by guid with no body, then read it back."""
    calls: List[Any] = []
    reads = iter([_entity_json(), _entity_json(status="DELETED")])

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if "/types/entitydef/" in url:
            return _typedef_response(mocker, url)
        if method == "DELETE":
            return http_result(
                mocker,
                200,
                {"mutatedEntities": {"DELETE": [{"guid": GUID}]}},
            )
        return http_result(mocker, 200, next(reads))

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity.main()

    assert e.value["changed"] is True
    assert e.value["deleted_guids"] == [GUID]
    delete = [c for c in calls if c[0] == "DELETE"]
    assert len(delete) == 1
    assert delete[0][1].endswith(f"/api/atlas/v2/entity/guid/{GUID}")
    assert not delete[0][2]


def test_atlas_entity_module_atlas_rejects_create(module_args, mocker):
    """Test an Atlas HTTP 404 validation error (missing mandatory attribute) fails the module with Atlas's message."""
    message = "invalid attribute: mandatory attribute 'note' is missing"

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if "/types/entitydef/" in url:
            return _typedef_response(mocker, url)
        if method == "GET":
            return http_result(
                mocker,
                404,
                {"errorCode": "ATLAS-404-00-009", "errorMessage": "not found"},
            )
        return http_result(
            mocker,
            404,
            {"errorCode": "ATLAS-404-00-007", "errorMessage": message},
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert message in e.value["msg"]


def test_atlas_entity_module_atlas_rejects_update(module_args, mocker):
    """Test an Atlas HTTP error on the update fails the module with Atlas's message."""
    message = "invalid attribute value"

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if "/types/entitydef/" in url:
            return _typedef_response(mocker, url)
        if method == "GET":
            return http_result(mocker, 200, _entity_json({"note": "old"}))
        return http_result(
            mocker,
            400,
            {"errorCode": "ATLAS-400-00-001", "errorMessage": message},
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"note": "new"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert message in e.value["msg"]


def test_atlas_entity_module_forbidden_fails(module_args, mocker):
    """Test an HTTP 403 fails the module."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 403, {"errorMessage": "denied"})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "Forbidden" in e.value["msg"]


def test_atlas_entity_module_malformed_entity_response_fails(module_args, mocker):
    """Test a body that lacks the entity fails instead of crashing."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if "/types/entitydef/" in url:
            return _typedef_response(mocker, url)
        return http_result(mocker, 200, {"unexpected": True})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity.main()

    assert "unexpected response" in e.value["msg"]
