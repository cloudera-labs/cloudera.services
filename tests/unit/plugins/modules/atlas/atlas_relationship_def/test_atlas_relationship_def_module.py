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

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_relationship_def,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_relationship_def.AtlasTypeDefClient"

# Atlas fills end and label defaults on the server; the existing def carries them.
EXISTING = AtlasRelationshipDef(
    name="test_relationship",
    description="An existing relationship",
    type_version="1.0",
    category="RELATIONSHIP",
    guid="rel-guid-1",
    version=1,
    relationship_category="ASSOCIATION",
    relationship_label="r:test_relationship",
    propagate_tags="NONE",
    end_def1=AtlasRelationshipEndDef(
        type="test_parent",
        name="children",
        is_container=True,
        cardinality="SET",
        is_legacy_attribute=False,
    ),
    end_def2=AtlasRelationshipEndDef(
        type="test_child",
        name="parent",
        is_container=False,
        cardinality="SINGLE",
        is_legacy_attribute=False,
    ),
    attribute_defs=[
        AtlasAttributeDef(
            name="weight",
            type_name="int",
            is_optional=True,
            cardinality="SINGLE",
        ),
    ],
)

ENDS = {
    "end_def1": {"type": "test_parent", "name": "children"},
    "end_def2": {"type": "test_child", "name": "parent"},
}


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_relationship_def_module_create(module_args, mocker):
    """Test the module creates a relationship typedef that does not exist."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_relationship_def_by_name",
        return_value=None,
    )
    mock_create = mocker.patch(
        f"{CLIENT}.create_relationship_def",
        return_value=AtlasRelationshipDef(name="test_relationship", guid="new"),
    )

    module_args(
        _args(
            name="test_relationship",
            relationship_category="ASSOCIATION",
            propagate_tags="ONE_TO_TWO",
            **ENDS,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    result = e.value
    assert result["changed"] is True
    assert result["relationship_def"]["guid"] == "new"
    assert "diff" not in result

    mock_get.assert_called_once_with("test_relationship")
    created = mock_create.call_args[0][0]
    assert created.propagate_tags == "ONE_TO_TWO"
    assert created.end_def1 == AtlasRelationshipEndDef(
        type="test_parent",
        name="children",
    )
    assert created.end_def2 == AtlasRelationshipEndDef(
        type="test_child",
        name="parent",
    )


def test_atlas_relationship_def_module_present_no_changes(module_args, mocker):
    """Test unset end fields keep Atlas-filled defaults, so no change is reported."""
    mocker.patch(f"{CLIENT}.get_relationship_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(f"{CLIENT}.update_relationship_def")

    module_args(
        _args(
            name="test_relationship",
            description="An existing relationship",
            propagate_tags="NONE",
            attribute_defs=[{"name": "weight", "type_name": "int"}],
            **ENDS,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    assert e.value["changed"] is False
    assert e.value["relationship_def"]["guid"] == "rel-guid-1"
    mock_update.assert_not_called()


def test_atlas_relationship_def_module_present_ends_omitted(module_args, mocker):
    """Test omitting the ends entirely keeps the existing ends and reports no change."""
    mocker.patch(f"{CLIENT}.get_relationship_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(f"{CLIENT}.update_relationship_def")

    module_args(_args(name="test_relationship"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_atlas_relationship_def_module_present_end_changed(module_args, mocker):
    """Test changing one end field updates and keeps the other end fields intact."""
    mocker.patch(f"{CLIENT}.get_relationship_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(
        f"{CLIENT}.update_relationship_def",
        return_value=AtlasRelationshipDef(name="test_relationship"),
    )

    module_args(
        _args(
            name="test_relationship",
            end_def1={"type": "test_parent", "name": "children", "cardinality": "LIST"},
            end_def2=ENDS["end_def2"],
            _ansible_diff=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    assert e.value["changed"] is True
    assert e.value["diff"]["before"] != e.value["diff"]["after"]
    sent = mock_update.call_args[0][0]
    assert sent.end_def1.cardinality == "LIST"
    assert sent.end_def1.is_container is True
    assert sent.end_def2 == EXISTING.end_def2
    assert sent.guid == "rel-guid-1"


def test_atlas_relationship_def_module_check_mode(module_args, mocker):
    """Test create in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_relationship_def_by_name", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_relationship_def")

    module_args(_args(name="test_relationship", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()


def test_atlas_relationship_def_module_update_check_mode(module_args, mocker):
    """Test update in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_relationship_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(f"{CLIENT}.update_relationship_def")

    module_args(
        _args(name="test_relationship", description="new", _ansible_check_mode=True),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    assert e.value["changed"] is True
    mock_update.assert_not_called()


def test_atlas_relationship_def_module_create_diff(module_args, mocker):
    """Test create in diff mode reports an empty before and the new definition after."""
    mocker.patch(f"{CLIENT}.get_relationship_def_by_name", return_value=None)
    mocker.patch(
        f"{CLIENT}.create_relationship_def",
        return_value=AtlasRelationshipDef(name="test_relationship"),
    )

    module_args(_args(name="test_relationship", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    assert e.value["diff"]["before"] == {}
    assert e.value["diff"]["after"]["name"] == "test_relationship"


def test_atlas_relationship_def_module_absent(module_args, mocker):
    """Test absent deletes an existing relationship and is a no-op when missing."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_relationship_def_by_name",
        return_value=EXISTING,
    )
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_relationship", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()
    assert e.value["changed"] is True
    mock_delete.assert_called_once_with("test_relationship")

    mock_get.return_value = None
    mock_delete.reset_mock()
    module_args(_args(name="test_relationship", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()
    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_atlas_relationship_def_module_absent_check_mode(module_args, mocker):
    """Test absent in check mode reports a change without deleting."""
    mocker.patch(f"{CLIENT}.get_relationship_def_by_name", return_value=EXISTING)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(
        _args(name="test_relationship", state="absent", _ansible_check_mode=True),
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    assert e.value["changed"] is True
    mock_delete.assert_not_called()


def test_atlas_relationship_def_module_present_requires_name(module_args):
    """Test present without a name fails."""
    module_args(_args())

    with pytest.raises(AnsibleFailJson):
        atlas_relationship_def.main()


def test_atlas_relationship_def_module_absent_requires_name(module_args, mocker):
    """Test absent without a name fails instead of silently doing nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_relationship_def_by_name")
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleFailJson):
        atlas_relationship_def.main()

    mock_get.assert_not_called()
    mock_delete.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"end_def1": {"name": "children"}},
        {"end_def1": {"type": "test_parent"}},
        {"end_def2": {"type": "t", "name": "n", "cardinality": "MANY"}},
        {"relationship_category": "INHERITANCE"},
        {"propagate_tags": "SIDEWAYS"},
        {"attribute_defs": [{"name": "weight"}]},
        {"state": "unknown"},
        {"super_types": ["parent"]},
    ],
    ids=[
        "end-missing-type",
        "end-missing-name",
        "invalid-end-cardinality",
        "invalid-relationship-category",
        "invalid-propagate-tags",
        "attribute-missing-type-name",
        "invalid-state",
        "entity-only-parameter",
    ],
)
def test_atlas_relationship_def_module_invalid_arguments_fail(
    module_args,
    mocker,
    extra,
):
    """Test invalid arguments fail before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_relationship_def_by_name")

    module_args(_args(name="test_relationship", **extra))

    with pytest.raises(AnsibleFailJson):
        atlas_relationship_def.main()

    mock_get.assert_not_called()


FETCH_URL = (
    "ansible_collections.cloudera.services.plugins.module_utils.common.fetch_url"
)

RELATIONSHIP_EXISTING_JSON = {
    "category": "RELATIONSHIP",
    "guid": "rel-guid-1",
    "name": "test_relationship",
    "attributeDefs": [],
    "endDef1": {"type": "test_parent", "name": "children"},
    "endDef2": {"type": "test_child", "name": "parent"},
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


def test_atlas_relationship_def_module_create_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on create fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 404)
        assert method == "POST"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_relationship", **ENDS))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_relationship_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_relationship_def_module_update_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on update fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 200, RELATIONSHIP_EXISTING_JSON)
        assert method == "PUT"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_relationship", description="new"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_relationship_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_relationship_def_module_delete_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on delete fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 200, RELATIONSHIP_EXISTING_JSON)
        assert method == "DELETE"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_relationship", state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_relationship_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_relationship_def_module_unexpected_response_fails(module_args, mocker):
    """Test a 200 response lacking the written relationship def fails the module cleanly."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 404)
        return _http(mocker, 200, {"relationshipDefs": []})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_relationship", **ENDS))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_relationship_def.main()

    assert "test_relationship" in e.value["msg"]
