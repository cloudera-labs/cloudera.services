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

from ansible_collections.cloudera.services.tests.unit import (
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import atlas_entity_info
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasClassification,
    AtlasEntity,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_entity_info.AtlasEntityClient"
GUID = "fc0fd256-be16-4775-99ad-9e0b7e304ae5"

ENTITY = AtlasEntity(
    type_name="test_entity_type",
    attributes={"qualifiedName": "test_entity_1", "someCamel": {"innerKey": 1}},
    business_attributes={"my_bm": {"ownerName": "alice"}},
    labels=["a"],
    classifications=[
        AtlasClassification(type_name="my_tag", attributes={"levelOne": "high"}),
    ],
    guid=GUID,
    status="ACTIVE",
)

ENTITY_JSON = {
    "referredEntities": {},
    "entity": {
        "typeName": "test_entity_type",
        "attributes": {"qualifiedName": "test_entity_1"},
        "guid": GUID,
        "status": "ACTIVE",
    },
}


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_entity_info_module_by_guid(module_args, mocker):
    """Test a guid lookup returns the entity with its user data left as Atlas names it."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=ENTITY)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["entities"]) == 1
    entity = result["entities"][0]
    assert entity["type_name"] == "test_entity_type"
    assert entity["guid"] == GUID
    assert entity["attributes"] == {
        "qualifiedName": "test_entity_1",
        "someCamel": {"innerKey": 1},
    }
    assert entity["business_attributes"] == {"my_bm": {"ownerName": "alice"}}
    assert entity["classifications"][0]["attributes"] == {"levelOne": "high"}
    mock_get.assert_called_once_with(GUID)


def test_atlas_entity_info_module_by_guid_returns_deleted_entity_as_is(
    module_args,
    mocker,
):
    """Test a deleted entity is reported with its DELETED status, not hidden."""
    deleted = AtlasEntity(type_name="t", guid=GUID, status="DELETED")
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=deleted)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert e.value["entities"][0]["status"] == "DELETED"


def test_atlas_entity_info_module_by_guid_not_found(module_args, mocker):
    """Test an unknown guid returns no entities rather than failing."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=None)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert e.value["entities"] == []
    assert e.value["changed"] is False


def test_atlas_entity_info_module_by_qualified_name(module_args, mocker):
    """Test qualified_name is shorthand for the qualifiedName unique attribute."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=ENTITY,
    )

    module_args(_args(type_name="test_entity_type", qualified_name="test_entity_1"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert len(e.value["entities"]) == 1
    mock_get.assert_called_once_with(
        "test_entity_type",
        {"qualifiedName": "test_entity_1"},
    )


def test_atlas_entity_info_module_by_unique_attributes(module_args, mocker):
    """Test unique_attributes are passed through unchanged."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=None,
    )

    module_args(
        _args(
            type_name="test_entity_type",
            unique_attributes={"qualifiedName": "q", "otherUnique": "x"},
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert e.value["entities"] == []
    mock_get.assert_called_once_with(
        "test_entity_type",
        {"qualifiedName": "q", "otherUnique": "x"},
    )


def test_atlas_entity_info_module_check_mode(module_args, mocker):
    """Test the lookup also runs in check mode, since it changes nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=ENTITY)

    module_args(_args(guid=GUID, _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert len(e.value["entities"]) == 1
    mock_get.assert_called_once_with(GUID)


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"guid": GUID, "type_name": "t"},
        {"guid": GUID, "qualified_name": "q"},
        {"guid": GUID, "unique_attributes": {"qualifiedName": "q"}},
        {"type_name": "t", "qualified_name": "q", "unique_attributes": {"a": "b"}},
        {"qualified_name": "q"},
        {"unique_attributes": {"qualifiedName": "q"}},
        {"type_name": "t"},
    ],
    ids=[
        "nothing",
        "guid-and-type",
        "guid-and-qualified-name",
        "guid-and-unique-attributes",
        "qualified-name-and-unique-attributes",
        "qualified-name-without-type",
        "unique-attributes-without-type",
        "type-without-attribute",
    ],
)
def test_atlas_entity_info_module_invalid_identity_fails(module_args, mocker, extra):
    """Test an ambiguous or incomplete identity fails before any Atlas call is made."""
    mock_guid = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_unique = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")

    module_args(_args(**extra))

    with pytest.raises(AnsibleFailJson):
        atlas_entity_info.main()

    mock_guid.assert_not_called()
    mock_unique.assert_not_called()


# The Atlas messages below are the real ones recorded from an Atlas 2.4 server.
UNKNOWN_TYPE_MESSAGE = "Type ENTITY with name no_such_type does not exist"


def test_atlas_entity_info_module_unknown_type_fails(module_args, mocker):
    """Test a mistyped type name fails with Atlas's message instead of reporting no entity."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(
            mocker,
            400,
            {"errorCode": "ATLAS-400-00-014", "errorMessage": UNKNOWN_TYPE_MESSAGE},
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(type_name="no_such_type", qualified_name="q"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_info.main()

    assert UNKNOWN_TYPE_MESSAGE in e.value["msg"]


def test_atlas_entity_info_module_missing_entity_returns_no_entities(
    module_args,
    mocker,
):
    """Test Atlas's 404 for an entity that does not exist (or was deleted) is not an error."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(
            mocker,
            404,
            {
                "errorCode": "ATLAS-404-00-009",
                "errorMessage": "Instance t with unique attribute {qualifiedName=q} does not exist",
            },
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(type_name="t", qualified_name="q"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert e.value["entities"] == []


def test_atlas_entity_info_module_requests_use_unique_attribute_query(
    module_args,
    mocker,
):
    """Test the real request carries the unique attribute as an attr: query parameter."""
    urls = []

    def fake_fetch_url(module, url, method="GET", **kwargs):
        urls.append((method, url))
        return http_result(mocker, 200, ENTITY_JSON)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(type_name="test_entity_type", qualified_name="test_entity_1"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_info.main()

    assert len(e.value["entities"]) == 1
    method, url = urls[0]
    assert method == "GET"
    assert "/api/atlas/v2/entity/uniqueAttribute/type/test_entity_type?" in url
    assert "attr%3AqualifiedName=test_entity_1" in url


@pytest.mark.parametrize(
    "body",
    [[], {}, {"entity": None}, {"entity": {"guid": GUID}}],
    ids=["list", "empty", "null-entity", "no-type-name"],
)
def test_atlas_entity_info_module_malformed_response_fails(module_args, mocker, body):
    """Test a 200 response that is not an entity fails the module cleanly."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 200, body)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_info.main()

    assert "unexpected" in e.value["msg"]


def test_atlas_entity_info_module_forbidden_fails(module_args, mocker):
    """Test an authorization failure fails the module."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 403, {"errorMessage": "denied"})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_info.main()

    assert "Forbidden" in e.value["msg"]
