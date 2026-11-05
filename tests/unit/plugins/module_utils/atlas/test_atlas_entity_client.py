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
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasTypeDefClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasClassification,
    AtlasEntity,
    AtlasEntityClient,
    classification_attribute_defs,
    entity_attribute_defs,
    normalize_attributes,
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
    """Test delete issues a DELETE for the guid and returns the guids Atlas deleted."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = {
        "mutatedEntities": {"DELETE": [{"guid": GUID}, {"guid": "child-guid"}]},
    }

    result = AtlasEntityClient(api_client).delete_entity_by_guid(GUID)

    assert result == [GUID, "child-guid"]
    api_client.delete.assert_called_once_with(f"/api/atlas/v2/entity/guid/{GUID}")


@pytest.mark.parametrize(
    "response",
    [None, {}, {"mutatedEntities": {}}, {"mutatedEntities": {"DELETE": None}}, []],
    ids=["none", "empty", "no-delete", "null-delete", "list"],
)
def test_delete_entity_by_guid_without_deleted_entities(mocker, response):
    """Test the silent 200 Atlas gives for an unknown guid returns no guids."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = response

    assert AtlasEntityClient(api_client).delete_entity_by_guid(GUID) == []


def test_update_entity_by_unique_attributes(mocker):
    """Test a partial update PUTs only the given attributes, addressed by unique attribute."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"mutatedEntities": {"PARTIAL_UPDATE": []}}

    result = AtlasEntityClient(api_client).update_entity_by_unique_attributes(
        "test_entity_type",
        {"qualifiedName": "test_entity_1"},
        AtlasEntity(
            type_name="test_entity_type",
            attributes={"someCamel": 1},
            custom_attributes={"myKey": "myValue"},
        ),
    )

    assert result is None
    api_client.put.assert_called_once_with(
        "/api/atlas/v2/entity/uniqueAttribute/type/test_entity_type",
        params={"attr:qualifiedName": "test_entity_1"},
        data={
            "entity": {
                "typeName": "test_entity_type",
                "attributes": {"someCamel": 1},
                "customAttributes": {"myKey": "myValue"},
            },
        },
    )
    api_client.post.assert_not_called()


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


def test_add_entity_classifications(mocker):
    """Test classifications are POSTed as a list; attribute names keep their case."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = None

    result = AtlasEntityClient(api_client).add_entity_classifications(
        GUID,
        [
            AtlasClassification(
                type_name="my_tag",
                attributes={"levelOne": "high"},
                propagate=False,
                remove_propagations_on_entity_delete=True,
            ),
        ],
    )

    assert result is None
    api_client.post.assert_called_once_with(
        f"/api/atlas/v2/entity/guid/{GUID}/classifications",
        data=[
            {
                "typeName": "my_tag",
                "attributes": {"levelOne": "high"},
                "propagate": False,
                "removePropagationsOnEntityDelete": True,
            },
        ],
    )


def test_add_entity_classifications_sends_only_what_is_set(mocker):
    """Test unset fields are left out so Atlas applies its defaults."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasEntityClient(api_client).add_entity_classifications(
        GUID,
        [AtlasClassification(type_name="my_tag")],
    )

    assert api_client.post.call_args.kwargs["data"] == [{"typeName": "my_tag"}]


def test_add_entity_classifications_never_sends_read_only_fields(mocker):
    """Test the entity guid and status Atlas reports are not echoed back in a request."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasEntityClient(api_client).add_entity_classifications(
        GUID,
        [
            AtlasClassification(
                type_name="my_tag",
                entity_guid=GUID,
                entity_status="ACTIVE",
            ),
        ],
    )

    assert api_client.post.call_args.kwargs["data"] == [{"typeName": "my_tag"}]


def test_add_entity_classifications_converts_validity_periods(mocker):
    """Test validity period keys are camelCased, as Atlas expects."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasEntityClient(api_client).add_entity_classifications(
        GUID,
        [
            AtlasClassification(
                type_name="my_tag",
                validity_periods=[
                    {
                        "start_time": "2026/01/01 00:00:00",
                        "end_time": "2026/12/31 00:00:00",
                        "time_zone": "UTC",
                    },
                ],
            ),
        ],
    )

    assert api_client.post.call_args.kwargs["data"][0]["validityPeriods"] == [
        {
            "startTime": "2026/01/01 00:00:00",
            "endTime": "2026/12/31 00:00:00",
            "timeZone": "UTC",
        },
    ]


def test_update_entity_classifications(mocker):
    """Test classifications are updated with a PUT of a list to the same endpoint."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = None

    result = AtlasEntityClient(api_client).update_entity_classifications(
        GUID,
        [AtlasClassification(type_name="my_tag", attributes={"levelOne": "low"})],
    )

    assert result is None
    api_client.put.assert_called_once_with(
        f"/api/atlas/v2/entity/guid/{GUID}/classifications",
        data=[{"typeName": "my_tag", "attributes": {"levelOne": "low"}}],
    )
    api_client.post.assert_not_called()


def test_remove_entity_classification(mocker):
    """Test a classification is removed by name with a bodiless DELETE."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    result = AtlasEntityClient(api_client).remove_entity_classification(
        GUID,
        "my_tag",
    )

    assert result is None
    api_client.delete.assert_called_once_with(
        f"/api/atlas/v2/entity/guid/{GUID}/classification/my_tag",
    )


def test_entity_classification_requests_quote_path_segments(mocker):
    """Test the guid and name are quoted so they cannot alter the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    client = AtlasEntityClient(api_client)

    client.add_entity_classifications("a/b?c", [AtlasClassification(type_name="t")])
    client.update_entity_classifications("a/b?c", [AtlasClassification(type_name="t")])
    client.remove_entity_classification("a/b?c", "d/e")

    assert api_client.post.call_args.args[0] == (
        "/api/atlas/v2/entity/guid/a%2Fb%3Fc/classifications"
    )
    assert api_client.put.call_args.args[0] == (
        "/api/atlas/v2/entity/guid/a%2Fb%3Fc/classifications"
    )
    assert api_client.delete.call_args.args[0] == (
        "/api/atlas/v2/entity/guid/a%2Fb%3Fc/classification/d%2Fe"
    )


def test_normalize_attributes_names_the_owner_in_errors():
    """Test the owner label and name appear in the errors, so each module's messages read naturally."""
    with pytest.raises(ServicesError) as e:
        normalize_attributes(
            "Classification",
            "my_tag",
            [AtlasAttributeDef(name="levelOne", type_name="string")],
            {"levelTwo": "x"},
        )

    assert "Classification 'my_tag'" in str(e.value)
    assert "levelTwo" in str(e.value)
    assert "levelOne" in str(e.value)


def test_normalize_attributes_passes_complex_types_through():
    """Test enum, map and struct values are not touched, because only Atlas can check them."""
    defs = [
        AtlasAttributeDef(name="kind", type_name="some_enum"),
        AtlasAttributeDef(name="labels", type_name="map<string,string>"),
        AtlasAttributeDef(name="detail", type_name="some_struct"),
    ]
    attributes = {
        "kind": "HIGH",
        "labels": {"a": "b"},
        "detail": {"x": 1, "y": [1, 2]},
    }

    assert normalize_attributes("Classification", "my_tag", defs, attributes) == (
        attributes
    )


def _typedef_client(mocker, defs):
    typedef_client = mocker.create_autospec(AtlasTypeDefClient, instance=True)
    typedef_client.get_classification_def_by_name.side_effect = defs.get
    return typedef_client


def test_classification_attribute_defs(mocker):
    """Test the attributes of a classification and of all its super types are returned."""
    typedef_client = _typedef_client(
        mocker,
        {
            "child": AtlasClassificationDef(
                name="child",
                super_types=["parent"],
                attribute_defs=[AtlasAttributeDef(name="own", type_name="string")],
            ),
            "parent": AtlasClassificationDef(
                name="parent",
                super_types=["grandparent"],
                attribute_defs=[AtlasAttributeDef(name="inherited", type_name="int")],
            ),
            "grandparent": AtlasClassificationDef(
                name="grandparent",
                attribute_defs=[AtlasAttributeDef(name="deep", type_name="boolean")],
            ),
        },
    )

    result = classification_attribute_defs(typedef_client, "child")

    assert result is not None
    assert [d.name for d in result] == ["own", "inherited", "deep"]


def test_classification_attribute_defs_without_attributes_or_super_types(mocker):
    """Test a classification Atlas returns without attributeDefs or superTypes has none."""
    typedef_client = _typedef_client(
        mocker,
        {"plain": AtlasClassificationDef(name="plain")},
    )

    assert classification_attribute_defs(typedef_client, "plain") == []


def test_classification_attribute_defs_unknown_classification(mocker):
    """Test a classification without a typedef returns None."""
    assert classification_attribute_defs(_typedef_client(mocker, {}), "nope") is None


def test_classification_attribute_defs_visits_each_type_once(mocker):
    """Test a shared or circular super type does not repeat attributes or loop."""
    typedef_client = _typedef_client(
        mocker,
        {
            "a": AtlasClassificationDef(
                name="a",
                super_types=["b", "c"],
                attribute_defs=[AtlasAttributeDef(name="x", type_name="string")],
            ),
            "b": AtlasClassificationDef(name="b", super_types=["c"]),
            "c": AtlasClassificationDef(
                name="c",
                super_types=["a"],
                attribute_defs=[AtlasAttributeDef(name="y", type_name="string")],
            ),
        },
    )

    result = classification_attribute_defs(typedef_client, "a")

    assert result is not None
    assert [d.name for d in result] == ["x", "y"]


def test_classification_attribute_defs_ignores_missing_super_type(mocker):
    """Test a super type Atlas cannot return does not hide the attributes found so far."""
    typedef_client = _typedef_client(
        mocker,
        {
            "child": AtlasClassificationDef(
                name="child",
                super_types=["gone"],
                attribute_defs=[AtlasAttributeDef(name="own", type_name="string")],
            ),
        },
    )

    result = classification_attribute_defs(typedef_client, "child")

    assert result is not None
    assert [d.name for d in result] == ["own"]


def test_entity_attribute_defs(mocker):
    """Test the attributes of an entity type and of all its super types are returned."""
    typedef_client = mocker.create_autospec(AtlasTypeDefClient, instance=True)
    defs = {
        "child": AtlasEntityDef(
            name="child",
            super_types=["parent", "other"],
            attribute_defs=[AtlasAttributeDef(name="own", type_name="string")],
        ),
        "parent": AtlasEntityDef(
            name="parent",
            super_types=["other"],
            attribute_defs=[
                AtlasAttributeDef(name="qualifiedName", type_name="string"),
            ],
        ),
        "other": AtlasEntityDef(
            name="other",
            attribute_defs=[AtlasAttributeDef(name="count", type_name="int")],
        ),
    }
    typedef_client.get_entity_def_by_name.side_effect = defs.get

    result = entity_attribute_defs(typedef_client, "child")

    assert result is not None
    assert [d.name for d in result] == ["own", "qualifiedName", "count"]


def test_entity_attribute_defs_unknown_type(mocker):
    """Test an entity type without a typedef returns None."""
    typedef_client = mocker.create_autospec(AtlasTypeDefClient, instance=True)
    typedef_client.get_entity_def_by_name.return_value = None

    assert entity_attribute_defs(typedef_client, "nope") is None
