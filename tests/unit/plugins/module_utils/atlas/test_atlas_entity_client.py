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
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasClassification,
    AtlasEntity,
    AtlasEntityClient,
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
