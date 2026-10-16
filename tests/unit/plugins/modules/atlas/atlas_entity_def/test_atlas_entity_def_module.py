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

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import atlas_entity_def
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasEntityDef,
    AtlasRelationshipAttributeDef,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_entity_def.AtlasTypeDefClient"


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_entity_def_module_create(module_args, mocker):
    """Test the module creates an entity typedef that does not exist."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_def_by_name", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_entity_def",
        return_value=AtlasEntityDef(name="test_entity", guid="new"),
    )

    module_args(
        _args(
            name="test_entity",
            super_types=["DataSet"],
            attribute_defs=[{"name": "owner", "type_name": "string"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_def.main()

    result = e.value
    assert result["changed"] is True
    assert result["entity_def"]["guid"] == "new"
    assert "diff" not in result

    mock_get.assert_called_once_with("test_entity")
    created = mock_create.call_args[0][0]
    assert created.super_types == ["DataSet"]
    assert created.attribute_defs == [
        AtlasAttributeDef(name="owner", type_name="string"),
    ]


# Atlas fills attribute defaults and derives relationship/business attributes.
EXISTING = AtlasEntityDef(
    name="test_entity",
    description="An existing entity",
    type_version="1.0",
    category="ENTITY",
    guid="ent-guid-1",
    version=1,
    attribute_defs=[
        AtlasAttributeDef(
            name="owner",
            type_name="string",
            is_optional=True,
            cardinality="SINGLE",
            values_min_count=0,
            values_max_count=1,
            is_unique=False,
            is_indexable=True,
        ),
    ],
    super_types=["DataSet"],
    sub_types=[],
    relationship_attribute_defs=[
        AtlasRelationshipAttributeDef(
            name="columns",
            type_name="array<hive_column>",
            relationship_type_name="hive_table_columns",
        ),
    ],
    business_attribute_defs={"myMetadata": [{"name": "cost", "type_name": "int"}]},
)


def test_atlas_entity_def_module_present_no_changes(module_args, mocker):
    """Test unset attribute fields keep Atlas-filled defaults, so no change is reported."""
    mocker.patch(f"{CLIENT}.get_entity_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(f"{CLIENT}.update_entity_def")

    module_args(
        _args(
            name="test_entity",
            description="An existing entity",
            super_types=["DataSet"],
            attribute_defs=[{"name": "owner", "type_name": "string"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_def.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_atlas_entity_def_module_present_attribute_added(module_args, mocker):
    """Test adding an attribute updates and keeps existing and read-only fields intact."""
    mocker.patch(f"{CLIENT}.get_entity_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(
        f"{CLIENT}.update_entity_def",
        return_value=AtlasEntityDef(name="test_entity"),
    )

    module_args(
        _args(
            name="test_entity",
            attribute_defs=[
                {"name": "owner", "type_name": "string"},
                {"name": "steward", "type_name": "string", "is_optional": True},
            ],
            _ansible_diff=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_def.main()

    assert e.value["changed"] is True
    assert e.value["diff"]["before"] != e.value["diff"]["after"]
    sent = mock_update.call_args[0][0]
    assert sent.attribute_defs[0].cardinality == "SINGLE"
    assert [a.name for a in sent.attribute_defs] == ["owner", "steward"]
    assert sent.guid == "ent-guid-1"
    assert sent.relationship_attribute_defs == EXISTING.relationship_attribute_defs


def test_atlas_entity_def_module_check_mode(module_args, mocker):
    """Test create in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_entity_def_by_name", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_entity_def")

    module_args(_args(name="test_entity", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_def.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()


def test_atlas_entity_def_module_create_diff(module_args, mocker):
    """Test create in diff mode reports an empty before and the new definition after."""
    mocker.patch(f"{CLIENT}.get_entity_def_by_name", return_value=None)
    mocker.patch(
        f"{CLIENT}.create_entity_def",
        return_value=AtlasEntityDef(name="test_entity"),
    )

    module_args(_args(name="test_entity", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_def.main()

    assert e.value["diff"]["before"] == {}
    assert e.value["diff"]["after"]["name"] == "test_entity"


def test_atlas_entity_def_module_absent(module_args, mocker):
    """Test absent deletes an existing entity and is a no-op when missing."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_def_by_name", return_value=EXISTING)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_entity", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_def.main()
    assert e.value["changed"] is True
    mock_delete.assert_called_once_with("test_entity")

    mock_get.return_value = None
    mock_delete.reset_mock()
    module_args(_args(name="test_entity", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_def.main()
    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_atlas_entity_def_module_absent_check_mode(module_args, mocker):
    """Test absent in check mode reports a change without deleting."""
    mocker.patch(f"{CLIENT}.get_entity_def_by_name", return_value=EXISTING)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_entity", state="absent", _ansible_check_mode=True))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_def.main()

    assert e.value["changed"] is True
    mock_delete.assert_not_called()


def test_atlas_entity_def_module_present_requires_name(module_args):
    """Test present without a name fails."""
    module_args(_args())

    with pytest.raises(AnsibleFailJson):
        atlas_entity_def.main()


def test_atlas_entity_def_module_absent_requires_name(module_args, mocker):
    """Test absent without a name fails instead of silently doing nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_def_by_name")
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleFailJson):
        atlas_entity_def.main()

    mock_get.assert_not_called()
    mock_delete.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"attribute_defs": [{"name": "owner"}]},
        {
            "attribute_defs": [
                {"name": "owner", "type_name": "string", "cardinality": "MANY"},
            ],
        },
        {
            "attribute_defs": [
                {"name": "owner", "type_name": "string", "index_type": "FULLTEXT"},
            ],
        },
        {"state": "unknown"},
        {"entity_types": ["hive_table"]},
    ],
    ids=[
        "attribute-missing-type-name",
        "invalid-cardinality",
        "invalid-index-type",
        "invalid-state",
        "classification-only-parameter",
    ],
)
def test_atlas_entity_def_module_invalid_arguments_fail(module_args, mocker, extra):
    """Test invalid arguments fail before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_def_by_name")

    module_args(_args(name="test_entity", **extra))

    with pytest.raises(AnsibleFailJson):
        atlas_entity_def.main()

    mock_get.assert_not_called()


FETCH_URL = (
    "ansible_collections.cloudera.services.plugins.module_utils.common.fetch_url"
)

ENTITY_EXISTING_JSON = {
    "category": "ENTITY",
    "guid": "ent-guid-1",
    "name": "test_entity",
    "attributeDefs": [],
    "superTypes": [],
}


def _http(mocker, status, body=None):
    """Build a fetch_url (response, info) result for the given status and JSON body."""
    payload = json.dumps(body if body is not None else {})
    resp = mocker.Mock()
    resp.read.return_value = payload.encode("utf-8")
    return resp, {"status": status, "msg": f"HTTP {status}", "body": payload}


ATLAS_ERROR_MESSAGE = "ATLAS-400-00-0AB: type is referenced by other types"


def _atlas_error(mocker):
    return _http(
        mocker,
        400,
        {"errorCode": "ATLAS-400-00-0AB", "errorMessage": ATLAS_ERROR_MESSAGE},
    )


def test_atlas_entity_def_module_create_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on create fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 404)
        assert method == "POST"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_entity"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_entity_def_module_update_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on update fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 200, ENTITY_EXISTING_JSON)
        assert method == "PUT"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_entity", description="new"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_entity_def_module_delete_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on delete fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 200, ENTITY_EXISTING_JSON)
        assert method == "DELETE"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_entity", state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_entity_def_module_unexpected_response_fails(module_args, mocker):
    """Test a 200 response lacking the written entity def fails the module cleanly."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 404)
        return _http(mocker, 200, {"entityDefs": []})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_entity"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_def.main()

    assert "test_entity" in e.value["msg"]
