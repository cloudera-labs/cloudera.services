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
from typing import Any, Dict, Optional

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_entity_business_metadata,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntity,
)

BASE_URL = "https://atlas.example"
MODULE = "ansible_collections.cloudera.services.plugins.modules.atlas_entity_business_metadata"
CLIENT = f"{MODULE}.AtlasEntityClient"
TYPEDEF_CLIENT = f"{MODULE}.AtlasTypeDefClient"
GUID = "fc0fd256-be16-4775-99ad-9e0b7e304ae5"
BM = "my_bm"


def _entity(
    business_attributes: Optional[Dict[str, Any]] = None,
    status: str = "ACTIVE",
) -> AtlasEntity:
    """Build an entity; with business_attributes=None the key is left unset, as Atlas omits it when an entity has none."""
    entity = AtlasEntity(type_name="test_entity_type", guid=GUID, status=status)
    if business_attributes is not None:
        entity.business_attributes = business_attributes
    return entity


def _typedef() -> AtlasBusinessMetadataDef:
    return AtlasBusinessMetadataDef(
        name=BM,
        attribute_defs=[
            AtlasAttributeDef(name="ownerName", type_name="string"),
            AtlasAttributeDef(name="rank", type_name="int"),
            AtlasAttributeDef(name="tags", type_name="array<string>"),
        ],
    )


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        "guid": GUID,
        "name": BM,
        **extra,
    }


@pytest.fixture
def typedef(mocker):
    """Patch the business metadata typedef lookup to return the test typedef."""
    return mocker.patch(
        f"{TYPEDEF_CLIENT}.get_business_metadata_def_by_name",
        return_value=_typedef(),
    )


def test_atlas_entity_business_metadata_module_present_adds_missing_attributes(
    module_args,
    mocker,
    typedef,
):
    """Test present keeps existing attributes and sends only the ones that differ."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"ownerName": "alice"}}),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"ownerName": "alice", "rank": 3}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == GUID
    assert e.value["business_metadata"] == {"ownerName": "alice", "rank": 3}
    mock_set.assert_called_once_with(GUID, BM, {"rank": 3})
    typedef.assert_called_once_with(BM)


def test_atlas_entity_business_metadata_module_present_changes_a_value(
    module_args,
    mocker,
    typedef,
):
    """Test a differing value is sent, and attributes not mentioned are left alone."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"ownerName": "alice", "rank": 1}}),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"ownerName": "bob"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {"ownerName": "bob", "rank": 1}
    mock_set.assert_called_once_with(GUID, BM, {"ownerName": "bob"})


def test_atlas_entity_business_metadata_module_present_on_entity_without_any(
    module_args,
    mocker,
    typedef,
):
    """Test an entity without a businessAttributes key (as Atlas omits it) counts as having none."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"ownerName": "alice"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {"ownerName": "alice"}
    mock_set.assert_called_once_with(GUID, BM, {"ownerName": "alice"})


def test_atlas_entity_business_metadata_module_present_leaves_other_business_metadata(
    module_args,
    mocker,
    typedef,
):
    """Test only the named business metadata is written and returned, never the others."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({"other_bm": {"x": 1}}),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"ownerName": "alice"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["business_metadata"] == {"ownerName": "alice"}
    mock_set.assert_called_once_with(GUID, BM, {"ownerName": "alice"})


def test_atlas_entity_business_metadata_module_present_is_idempotent(
    module_args,
    mocker,
    typedef,
):
    """Test present makes no change when every requested attribute already has its value."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity(
            {BM: {"ownerName": "alice", "rank": 3, "tags": ["a", "b"]}},
        ),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"ownerName": "alice", "tags": ["a", "b"]}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    assert e.value["business_metadata"] == {
        "ownerName": "alice",
        "rank": 3,
        "tags": ["a", "b"],
    }
    mock_set.assert_not_called()


def test_atlas_entity_business_metadata_module_string_for_int_is_idempotent(
    module_args,
    mocker,
    typedef,
):
    """Test "3" for an int attribute that Atlas stores as 3 is not a change."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"rank": 3}}),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"rank": "3"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    mock_set.assert_not_called()


def test_atlas_entity_business_metadata_module_string_for_int_is_sent_as_int(
    module_args,
    mocker,
    typedef,
):
    """Test a value is converted to the attribute's type before it is sent."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"rank": "3"}))

    with pytest.raises(AnsibleExitJson):
        atlas_entity_business_metadata.main()

    mock_set.assert_called_once_with(GUID, BM, {"rank": 3})


def test_atlas_entity_business_metadata_module_empty_attributes_is_a_no_op(
    module_args,
    mocker,
    typedef,
):
    """Test present with no attributes changes nothing."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    mock_set.assert_not_called()


def test_atlas_entity_business_metadata_module_absent_removes_whole_business_metadata(
    module_args,
    mocker,
):
    """Test absent removes the named business metadata and leaves the others."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"ownerName": "alice"}, "other_bm": {"x": 1}}),
    )
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_business_metadata")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == GUID
    assert e.value["business_metadata"] == {}
    mock_remove.assert_called_once_with(GUID, BM)


def test_atlas_entity_business_metadata_module_absent_is_idempotent(
    module_args,
    mocker,
):
    """Test absent makes no change when the business metadata is not on the entity."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({"other_bm": {"x": 1}}),
    )
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_business_metadata")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    mock_remove.assert_not_called()


def test_atlas_entity_business_metadata_module_absent_without_any_is_idempotent(
    module_args,
    mocker,
):
    """Test absent on an entity with no business attributes key makes no change."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_business_metadata")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    mock_remove.assert_not_called()


def test_atlas_entity_business_metadata_module_absent_on_missing_entity_is_a_no_op(
    module_args,
    mocker,
):
    """Test absent on an entity that does not exist has nothing to remove."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=None)
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_business_metadata")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    assert e.value["guid"] is None
    assert e.value["business_metadata"] == {}
    mock_remove.assert_not_called()


def test_atlas_entity_business_metadata_module_absent_on_deleted_entity_is_a_no_op(
    module_args,
    mocker,
):
    """Test absent on a soft-deleted entity (a lookup by guid still returns it) does nothing."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"ownerName": "alice"}}, status="DELETED"),
    )
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_business_metadata")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    mock_remove.assert_not_called()


def test_atlas_entity_business_metadata_module_absent_with_attributes_fails(
    module_args,
    mocker,
):
    """Test attributes with absent are refused, because Atlas can only remove the whole business metadata."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_business_metadata")

    module_args(_args(state="absent", attributes={"ownerName": "alice"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "attributes" in e.value["msg"]
    mock_get.assert_not_called()
    mock_remove.assert_not_called()


@pytest.mark.parametrize(
    "entity",
    [None, _entity(status="DELETED")],
    ids=["missing", "deleted"],
)
def test_atlas_entity_business_metadata_module_present_fails_without_an_active_entity(
    module_args,
    mocker,
    typedef,
    entity,
):
    """Test present fails, with no write, when the entity is missing or deleted."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=entity)
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"ownerName": "alice"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "active entity" in e.value["msg"]
    mock_set.assert_not_called()


def test_atlas_entity_business_metadata_module_unknown_business_metadata_fails(
    module_args,
    mocker,
    typedef,
):
    """Test a business metadata that has no typedef fails without a write."""
    typedef.return_value = None
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"ownerName": "alice"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert BM in e.value["msg"]
    assert "does not exist" in e.value["msg"]
    mock_set.assert_not_called()


def test_atlas_entity_business_metadata_module_unknown_attribute_fails(
    module_args,
    mocker,
    typedef,
):
    """Test an attribute the typedef lacks fails, because Atlas would silently ignore it."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"ownerNmae": "alice"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "ownerNmae" in e.value["msg"]
    mock_set.assert_not_called()


@pytest.mark.parametrize(
    "attributes",
    [{"ownerName": None}, {"rank": "high"}, {"tags": "a"}],
    ids=["null", "bad-int", "not-a-list"],
)
def test_atlas_entity_business_metadata_module_invalid_value_fails(
    module_args,
    mocker,
    typedef,
    attributes,
):
    """Test a null or ill-typed value fails without a write."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes=attributes))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert next(iter(attributes)) in e.value["msg"]
    mock_set.assert_not_called()


def test_atlas_entity_business_metadata_module_by_qualified_name(
    module_args,
    mocker,
    typedef,
):
    """Test the entity is looked up by type and qualified name, then written by guid."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    args = _args(
        type_name="test_entity_type",
        qualified_name="test_entity_1",
        attributes={"ownerName": "alice"},
    )
    del args["guid"]
    module_args(args)

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["guid"] == GUID
    mock_get.assert_called_once_with(
        "test_entity_type",
        {"qualifiedName": "test_entity_1"},
    )
    mock_set.assert_called_once_with(GUID, BM, {"ownerName": "alice"})


def test_atlas_entity_business_metadata_module_by_unique_attributes(
    module_args,
    mocker,
    typedef,
):
    """Test unique_attributes are passed through unchanged."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(),
    )
    mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    args = _args(
        type_name="test_entity_type",
        unique_attributes={"qualifiedName": "q", "other": "x"},
        attributes={"ownerName": "alice"},
    )
    del args["guid"]
    module_args(args)

    with pytest.raises(AnsibleExitJson):
        atlas_entity_business_metadata.main()

    mock_get.assert_called_once_with(
        "test_entity_type",
        {"qualifiedName": "q", "other": "x"},
    )


def test_atlas_entity_business_metadata_module_check_mode_present(
    module_args,
    mocker,
    typedef,
):
    """Test check mode reports the change and the intended attributes but makes no write."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"ownerName": "alice"}}),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"rank": 2}, _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {"ownerName": "alice", "rank": 2}
    mock_set.assert_not_called()


def test_atlas_entity_business_metadata_module_check_mode_absent(module_args, mocker):
    """Test check mode reports the removal but makes no write."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"ownerName": "alice"}}),
    )
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_business_metadata")

    module_args(_args(state="absent", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {}
    mock_remove.assert_not_called()


def test_atlas_entity_business_metadata_module_diff_mode_present(
    module_args,
    mocker,
    typedef,
):
    """Test diff mode shows only the attributes that change."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"ownerName": "alice", "rank": 1}}),
    )
    mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(
        _args(attributes={"ownerName": "alice", "rank": 2}, _ansible_diff=True),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["diff"] == {
        "before": {"business_metadata": {BM: {"rank": 1}}},
        "after": {"business_metadata": {BM: {"rank": 2}}},
    }


def test_atlas_entity_business_metadata_module_diff_mode_new_attribute(
    module_args,
    mocker,
    typedef,
):
    """Test diff mode shows a newly set attribute as absent before."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    module_args(_args(attributes={"rank": 2}, _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["diff"] == {
        "before": {"business_metadata": {BM: {}}},
        "after": {"business_metadata": {BM: {"rank": 2}}},
    }


def test_atlas_entity_business_metadata_module_diff_mode_absent(module_args, mocker):
    """Test diff mode shows the whole business metadata being removed."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"ownerName": "alice"}}),
    )
    mocker.patch(f"{CLIENT}.remove_entity_business_metadata")

    module_args(_args(state="absent", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["diff"] == {
        "before": {"business_metadata": {BM: {"ownerName": "alice"}}},
        "after": {"business_metadata": {}},
    }


def test_atlas_entity_business_metadata_module_diff_mode_without_change(
    module_args,
    mocker,
    typedef,
):
    """Test diff mode reports an empty diff when nothing changes."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity({BM: {"rank": 1}}),
    )

    module_args(_args(attributes={"rank": 1}, _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    assert e.value["diff"] == {}


@pytest.mark.parametrize(
    "extra",
    [
        {"guid": None},
        {"type_name": "t"},
        {"qualified_name": "q"},
        {"type_name": "t", "qualified_name": "q", "unique_attributes": {"a": "b"}},
        {"type_name": "t", "qualified_name": "q"},
        {"name": None},
        {"attributes": None},
    ],
    ids=[
        "nothing",
        "guid-and-type",
        "guid-and-qualified-name",
        "qualified-name-and-unique-attributes",
        "guid-and-type-and-qualified-name",
        "no-name",
        "present-without-attributes",
    ],
)
def test_atlas_entity_business_metadata_module_invalid_arguments_fail(
    module_args,
    mocker,
    extra,
):
    """Test an ambiguous identity or missing arguments fails before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_unique = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")
    mock_typedef = mocker.patch(f"{TYPEDEF_CLIENT}.get_business_metadata_def_by_name")
    mock_set = mocker.patch(f"{CLIENT}.set_entity_business_metadata")

    args = _args(attributes={"ownerName": "alice"})
    args.update(extra)
    module_args({k: v for k, v in args.items() if v is not None})

    with pytest.raises(AnsibleFailJson):
        atlas_entity_business_metadata.main()

    mock_get.assert_not_called()
    mock_unique.assert_not_called()
    mock_typedef.assert_not_called()
    mock_set.assert_not_called()


ENTITY_JSON = {
    "referredEntities": {},
    "entity": {
        "typeName": "test_entity_type",
        "attributes": {"qualifiedName": "test_entity_1"},
        "guid": GUID,
        "status": "ACTIVE",
        "businessAttributes": {BM: {"ownerName": "alice"}},
    },
}

TYPEDEF_JSON = {
    "category": "BUSINESS_METADATA",
    "name": BM,
    "attributeDefs": [
        {"name": "ownerName", "typeName": "string"},
        {"name": "rank", "typeName": "int"},
    ],
}


def test_atlas_entity_business_metadata_module_requests(module_args, mocker):
    """Test the real requests: read the entity and typedef, then POST only the delta without overwrite."""
    calls = []

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if method == "GET" and "/types/businessmetadatadef/" in url:
            return http_result(mocker, 200, TYPEDEF_JSON)
        if method == "GET":
            return http_result(mocker, 200, ENTITY_JSON)
        return http_result(mocker, 204)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"ownerName": "alice", "rank": "4"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {"ownerName": "alice", "rank": 4}
    assert [c[0] for c in calls] == ["GET", "GET", "POST"]
    assert calls[2][1].endswith(
        f"/api/atlas/v2/entity/guid/{GUID}/businessmetadata/{BM}?isOverwrite=false",
    )
    assert json.loads(calls[2][2]) == {"rank": 4}


def test_atlas_entity_business_metadata_module_absent_requests(module_args, mocker):
    """Test the real requests: read the entity, then DELETE the business metadata with no body."""
    calls = []

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if method == "GET":
            return http_result(mocker, 200, ENTITY_JSON)
        return http_result(mocker, 204)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert [c[0] for c in calls] == ["GET", "DELETE"]
    assert calls[1][1].endswith(
        f"/api/atlas/v2/entity/guid/{GUID}/businessmetadata/{BM}"
    )
    assert not calls[1][2]


def test_atlas_entity_business_metadata_module_typedef_not_found_fails(
    module_args,
    mocker,
):
    """Test a 404 for the business metadata typedef reads as a missing typedef, not an Atlas error."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if "/types/businessmetadatadef/" in url:
            return http_result(
                mocker,
                404,
                {"errorCode": "ATLAS-404-00-00B", "errorMessage": "not found"},
            )
        return http_result(mocker, 200, ENTITY_JSON)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"ownerName": "bob"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "does not exist" in e.value["msg"]


def test_atlas_entity_business_metadata_module_not_applicable_to_type_fails(
    module_args,
    mocker,
):
    """Test Atlas's HTTP 404 for a business metadata not applicable to the entity type fails the write."""
    message = "Business metadata my_bm is not applicable for the entity type"

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET" and "/types/businessmetadatadef/" in url:
            return http_result(mocker, 200, TYPEDEF_JSON)
        if method == "GET":
            return http_result(mocker, 200, ENTITY_JSON)
        return http_result(
            mocker,
            404,
            {"errorCode": "ATLAS-404-00-007", "errorMessage": message},
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"ownerName": "bob"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert message in e.value["msg"]


def test_atlas_entity_business_metadata_module_unknown_type_fails(module_args, mocker):
    """Test a mistyped entity type name fails instead of reading as a missing entity."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(
            mocker,
            400,
            {
                "errorCode": "ATLAS-400-00-014",
                "errorMessage": "Type ENTITY with name no_such_type does not exist",
            },
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    args = _args(
        type_name="no_such_type",
        qualified_name="q",
        attributes={"ownerName": "bob"},
    )
    del args["guid"]
    module_args(args)

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "does not exist" in e.value["msg"]


@pytest.mark.parametrize("body", [[], {}, {"entity": {"guid": GUID}}])
def test_atlas_entity_business_metadata_module_malformed_entity_response_fails(
    module_args,
    mocker,
    body,
):
    """Test a 200 response that is not an entity fails the module without a write."""
    calls = []

    def fake_fetch_url(module, url, method="GET", **kwargs):
        calls.append(method)
        return http_result(mocker, 200, body)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"ownerName": "bob"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "unexpected" in e.value["msg"]
    assert calls == ["GET"]


def test_atlas_entity_business_metadata_module_forbidden_fails(module_args, mocker):
    """Test an authorization failure fails the module."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 403, {"errorMessage": "denied"})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"ownerName": "bob"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "Forbidden" in e.value["msg"]
