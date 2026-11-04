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

import pytest

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasClassification,
    AtlasEntity,
    AtlasEntityClient,
    normalize_business_attributes,
    validate_labels,
)

GUID = "fc0fd256-be16-4775-99ad-9e0b7e304ae5"

# Shaped after a real Atlas 2.4 response: attribute and business attribute names
# are camelCase user data and must come back untouched.
ENTITY_RESPONSE = {
    "referredEntities": {},
    "entity": {
        "typeName": "test_entity_type",
        "attributes": {
            "note": "n1",
            "replicatedTo": None,
            "qualifiedName": "test_entity_1",
            "count": 1,
            "someRef": {"guid": "other-guid", "typeName": "other_type"},
        },
        "guid": GUID,
        "isIncomplete": False,
        "status": "ACTIVE",
        "createdBy": "admin",
        "updatedBy": "admin",
        "createTime": 1793110013191,
        "updateTime": 1793110013192,
        "version": 0,
        "relationshipAttributes": {"meanings": []},
        "businessAttributes": {"my_bm": {"ownerName": "alice", "n": 6}},
        "customAttributes": {"myKey": "myValue"},
        "labels": ["a", "b"],
        "classifications": [
            {
                "typeName": "my_tag",
                "attributes": {"levelOne": "high"},
                "entityGuid": GUID,
                "entityStatus": "ACTIVE",
                "propagate": True,
                "removePropagationsOnEntityDelete": False,
                "validityPeriods": [
                    {
                        "startTime": "2026/01/01 00:00:00",
                        "endTime": "2026/12/31 00:00:00",
                        "timeZone": "UTC",
                    },
                ],
            },
        ],
    },
}

EXPECTED_ENTITY = AtlasEntity(
    type_name="test_entity_type",
    attributes={
        "note": "n1",
        "replicatedTo": None,
        "qualifiedName": "test_entity_1",
        "count": 1,
        "someRef": {"guid": "other-guid", "typeName": "other_type"},
    },
    relationship_attributes={"meanings": []},
    business_attributes={"my_bm": {"ownerName": "alice", "n": 6}},
    custom_attributes={"myKey": "myValue"},
    labels=["a", "b"],
    classifications=[
        AtlasClassification(
            type_name="my_tag",
            attributes={"levelOne": "high"},
            entity_guid=GUID,
            entity_status="ACTIVE",
            propagate=True,
            remove_propagations_on_entity_delete=False,
            validity_periods=[
                {
                    "start_time": "2026/01/01 00:00:00",
                    "end_time": "2026/12/31 00:00:00",
                    "time_zone": "UTC",
                },
            ],
        ),
    ],
    guid=GUID,
    status="ACTIVE",
    is_incomplete=False,
    created_by="admin",
    updated_by="admin",
    create_time=1793110013191,
    update_time=1793110013192,
    version=0,
)

MALFORMED_RESPONSES = [
    [],
    "not json",
    {},
    {"entity": None},
    {"entity": []},
    {"entity": {"guid": GUID}},
]
MALFORMED_IDS = ["list", "string", "empty", "null-entity", "list-entity", "no-type"]


def test_get_entity_by_guid(mocker):
    """Test an Atlas entity response maps onto AtlasEntity with user data left verbatim."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = ENTITY_RESPONSE

    client = AtlasEntityClient(api_client=api_client)

    assert client.get_entity_by_guid(GUID) == EXPECTED_ENTITY

    api_client.get.assert_called_once_with(
        f"/api/atlas/v2/entity/guid/{GUID}",
        params={"minExtInfo": "true"},
        squelch={404: None},
    )


def test_get_entity_by_guid_not_found(mocker):
    """Test a missing guid returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    assert AtlasEntityClient(api_client).get_entity_by_guid(GUID) is None


def test_get_entity_by_guid_quotes_the_path_segment(mocker):
    """Test a guid with reserved characters cannot change the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    AtlasEntityClient(api_client).get_entity_by_guid("a/b c")

    assert api_client.get.call_args.args[0] == "/api/atlas/v2/entity/guid/a%2Fb%20c"


def test_get_entity_by_unique_attributes(mocker):
    """Test the lookup sends each unique attribute as an attr:<name> query parameter."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = ENTITY_RESPONSE

    client = AtlasEntityClient(api_client=api_client)

    result = client.get_entity_by_unique_attributes(
        "test_entity_type",
        {"qualifiedName": "test_entity_1"},
    )

    assert result == EXPECTED_ENTITY
    api_client.get.assert_called_once_with(
        "/api/atlas/v2/entity/uniqueAttribute/type/test_entity_type",
        params={"minExtInfo": "true", "attr:qualifiedName": "test_entity_1"},
        squelch={404: None},
    )


def test_get_entity_by_unique_attributes_not_found(mocker):
    """Test a missing (or deleted) entity returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = AtlasEntityClient(api_client)

    assert client.get_entity_by_unique_attributes("t", {"qualifiedName": "q"}) is None


def test_get_entity_by_unique_attributes_quotes_the_type_name(mocker):
    """Test a type name with reserved characters cannot change the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    AtlasEntityClient(api_client).get_entity_by_unique_attributes(
        "a/b",
        {"qualifiedName": "q"},
    )

    assert api_client.get.call_args.args[0].endswith("/type/a%2Fb")


@pytest.mark.parametrize("response", MALFORMED_RESPONSES, ids=MALFORMED_IDS)
def test_get_entity_malformed_response_raises(mocker, response):
    """Test an unexpected body raises a ServicesError instead of a TypeError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = response

    client = AtlasEntityClient(api_client)

    with pytest.raises(ServicesError, match="unexpected"):
        client.get_entity_by_guid(GUID)
    with pytest.raises(ServicesError, match="unexpected"):
        client.get_entity_by_unique_attributes("t", {"qualifiedName": "q"})


def test_create_entity(mocker):
    """Test create POSTs the entity, then reads back the entity Atlas created."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {
        "mutatedEntities": {
            "CREATE": [
                {"typeName": "test_entity_type", "guid": GUID, "status": "ACTIVE"},
            ],
        },
        "guidAssignments": {"-1": GUID},
    }
    api_client.get.return_value = ENTITY_RESPONSE

    client = AtlasEntityClient(api_client)

    result = client.create_entity(
        AtlasEntity(
            type_name="test_entity_type",
            attributes={"qualifiedName": "test_entity_1", "someCamel": {"innerKey": 1}},
            custom_attributes={"myKey": "myValue"},
        ),
    )

    assert result == EXPECTED_ENTITY
    api_client.post.assert_called_once_with(
        "/api/atlas/v2/entity",
        data={
            "entity": {
                "typeName": "test_entity_type",
                "attributes": {
                    "qualifiedName": "test_entity_1",
                    "someCamel": {"innerKey": 1},
                },
                "customAttributes": {"myKey": "myValue"},
            },
        },
    )
    assert api_client.get.call_args.args[0] == f"/api/atlas/v2/entity/guid/{GUID}"


@pytest.mark.parametrize(
    "response",
    [None, {}, {"mutatedEntities": {}}, {"mutatedEntities": {"CREATE": []}}, []],
    ids=["none", "empty", "no-create", "empty-create", "list"],
)
def test_create_entity_without_created_entity_raises(mocker, response):
    """Test a response that reports no created entity raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = response

    with pytest.raises(ServicesError, match="did not report"):
        AtlasEntityClient(api_client).create_entity(
            AtlasEntity(type_name="t", attributes={"qualifiedName": "q"}),
        )

    api_client.get.assert_not_called()


def test_create_entity_that_cannot_be_read_back_raises(mocker):
    """Test an entity Atlas reports as created but cannot return raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"mutatedEntities": {"CREATE": [{"guid": GUID}]}}
    api_client.get.return_value = None

    with pytest.raises(ServicesError, match=GUID):
        AtlasEntityClient(api_client).create_entity(
            AtlasEntity(type_name="t", attributes={"qualifiedName": "q"}),
        )


def test_delete_entity_by_guid(mocker):
    """Test delete issues a DELETE for the guid and returns nothing."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = {}

    assert AtlasEntityClient(api_client).delete_entity_by_guid(GUID) is None

    api_client.delete.assert_called_once_with(f"/api/atlas/v2/entity/guid/{GUID}")


def test_purge_entities(mocker):
    """Test purge PUTs the guids to the admin purge endpoint."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {}

    assert AtlasEntityClient(api_client).purge_entities(["g1", "g2"]) is None

    api_client.put.assert_called_once_with("/api/atlas/admin/purge", data=["g1", "g2"])


def test_purge_entities_without_guids_makes_no_request(mocker):
    """Test an empty purge does nothing."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasEntityClient(api_client).purge_entities([])

    api_client.put.assert_not_called()


def test_set_entity_labels(mocker):
    """Test labels are set by POSTing the whole list to the entity's labels endpoint."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = None

    assert AtlasEntityClient(api_client).set_entity_labels(GUID, ["a", "b"]) is None

    api_client.post.assert_called_once_with(
        f"/api/atlas/v2/entity/guid/{GUID}/labels",
        data=["a", "b"],
    )


def test_set_entity_labels_empty_list_clears(mocker):
    """Test an empty list is sent as is, because POSTing [] clears every label."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = None

    AtlasEntityClient(api_client).set_entity_labels(GUID, [])

    api_client.post.assert_called_once_with(
        f"/api/atlas/v2/entity/guid/{GUID}/labels",
        data=[],
    )


def test_set_entity_labels_quotes_guid(mocker):
    """Test the guid is quoted so it cannot alter the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasEntityClient(api_client).set_entity_labels("a/b?c", ["a"])

    assert api_client.post.call_args.args[0] == (
        "/api/atlas/v2/entity/guid/a%2Fb%3Fc/labels"
    )


@pytest.mark.parametrize("label", ["a", "A1", "with_underscore", "with-dash", "9"])
def test_validate_labels_accepts_atlas_labels(label):
    """Test alphanumeric labels with underscores and dashes pass."""
    validate_labels([label])


@pytest.mark.parametrize(
    "label",
    ["", "has space", "dot.ted", "slash/ed", "colon:ed", "naïve", "tab\t"],
)
def test_validate_labels_rejects_invalid_labels(label):
    """Test a label Atlas would reject (ATLAS-400-00-090) is refused with its name."""
    with pytest.raises(ServicesError) as e:
        validate_labels(["ok", label])

    assert repr(label) in str(e.value) or label in str(e.value)


def test_set_entity_business_metadata(mocker):
    """Test attributes are POSTed to the named business metadata without overwriting the others."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = None

    result = AtlasEntityClient(api_client).set_entity_business_metadata(
        GUID,
        "my_bm",
        {"ownerName": "alice", "n": 6},
    )

    assert result is None
    api_client.post.assert_called_once_with(
        f"/api/atlas/v2/entity/guid/{GUID}/businessmetadata/my_bm",
        params={"isOverwrite": "false"},
        data={"ownerName": "alice", "n": 6},
    )


def test_set_entity_business_metadata_never_overwrites(mocker):
    """Test isOverwrite=true, which wipes every other business metadata, is never sent."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasEntityClient(api_client).set_entity_business_metadata(GUID, "my_bm", {"a": 1})

    assert api_client.post.call_args.kwargs["params"] == {"isOverwrite": "false"}


def test_set_entity_business_metadata_quotes_path_segments(mocker):
    """Test the guid and name are quoted so they cannot alter the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasEntityClient(api_client).set_entity_business_metadata("a/b?c", "d/e", {"a": 1})

    assert api_client.post.call_args.args[0] == (
        "/api/atlas/v2/entity/guid/a%2Fb%3Fc/businessmetadata/d%2Fe"
    )


def test_remove_entity_business_metadata(mocker):
    """Test the whole business metadata is deleted, with no body (Atlas ignores one)."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    result = AtlasEntityClient(api_client).remove_entity_business_metadata(
        GUID,
        "my_bm",
    )

    assert result is None
    api_client.delete.assert_called_once_with(
        f"/api/atlas/v2/entity/guid/{GUID}/businessmetadata/my_bm",
    )


def test_remove_entity_business_metadata_quotes_path_segments(mocker):
    """Test the guid and name are quoted so they cannot alter the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasEntityClient(api_client).remove_entity_business_metadata("a/b?c", "d/e")

    assert api_client.delete.call_args.args[0] == (
        "/api/atlas/v2/entity/guid/a%2Fb%3Fc/businessmetadata/d%2Fe"
    )


BM_ATTRIBUTE_DEFS = [
    AtlasAttributeDef(name="ownerName", type_name="string"),
    AtlasAttributeDef(name="rank", type_name="int"),
    AtlasAttributeDef(name="score", type_name="double"),
    AtlasAttributeDef(name="active", type_name="boolean"),
    AtlasAttributeDef(name="since", type_name="date"),
    AtlasAttributeDef(name="tags", type_name="array<string>"),
    AtlasAttributeDef(name="levels", type_name="array<int>"),
    AtlasAttributeDef(name="kind", type_name="some_enum"),
]


def test_normalize_business_attributes_keeps_typed_values():
    """Test values already of the declared type pass through unchanged."""
    attributes = {
        "ownerName": "alice",
        "rank": 5,
        "score": 1.5,
        "active": True,
        "since": 1793110013191,
        "tags": ["a", "b"],
        "levels": [1, 2],
        "kind": "HIGH",
    }

    assert normalize_business_attributes("my_bm", BM_ATTRIBUTE_DEFS, attributes) == (
        attributes
    )


def test_normalize_business_attributes_coerces_strings_like_atlas():
    """Test strings become the declared type, as Atlas stores "5" as 5, so a repeat run is idempotent."""
    result = normalize_business_attributes(
        "my_bm",
        BM_ATTRIBUTE_DEFS,
        {
            "rank": "5",
            "score": "2.5",
            "active": "True",
            "since": "1793110013191",
            "ownerName": 42,
            "levels": ["1", 2],
        },
    )

    assert result == {
        "rank": 5,
        "score": 2.5,
        "active": True,
        "since": 1793110013191,
        "ownerName": "42",
        "levels": [1, 2],
    }
    assert type(result["rank"]) is int
    assert type(result["active"]) is bool


@pytest.mark.parametrize("name", ["rank", "score", "since", "tags"])
def test_normalize_business_attributes_rejects_null(name):
    """Test null is refused, because Atlas cannot clear one attribute and would store nothing useful."""
    with pytest.raises(ServicesError) as e:
        normalize_business_attributes("my_bm", BM_ATTRIBUTE_DEFS, {name: None})

    assert name in str(e.value)
    assert "null" in str(e.value)


def test_normalize_business_attributes_rejects_unknown_attributes():
    """Test an attribute missing from the typedef fails, because Atlas silently ignores it."""
    with pytest.raises(ServicesError) as e:
        normalize_business_attributes(
            "my_bm",
            BM_ATTRIBUTE_DEFS,
            {"rank": 1, "ownerNmae": "typo", "other": "x"},
        )

    message = str(e.value)
    assert "my_bm" in message
    assert "ownerNmae" in message
    assert "other" in message
    assert "ownerName" in message  # lists what is defined


def test_normalize_business_attributes_with_no_attribute_defs_rejects_all():
    """Test a typedef without attributes (as Atlas may return it) accepts nothing."""
    with pytest.raises(ServicesError):
        normalize_business_attributes("my_bm", None, {"rank": 1})


@pytest.mark.parametrize(
    "name, value",
    [
        ("rank", "five"),
        ("rank", 1.5),
        ("rank", True),
        ("rank", [1]),
        ("score", "high"),
        ("active", "yes"),
        ("active", 1),
        ("since", "yesterday"),
        ("ownerName", {"a": 1}),
        ("ownerName", ["a"]),
        ("tags", "a"),
        ("tags", [["a"]]),
        ("levels", ["x"]),
    ],
)
def test_normalize_business_attributes_rejects_wrong_types(name, value):
    """Test a value that cannot be the declared type fails and names the attribute and type."""
    with pytest.raises(ServicesError) as e:
        normalize_business_attributes("my_bm", BM_ATTRIBUTE_DEFS, {name: value})

    assert name in str(e.value)
