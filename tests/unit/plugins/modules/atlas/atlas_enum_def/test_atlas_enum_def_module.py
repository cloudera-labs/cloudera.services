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

from ansible_collections.cloudera.services.plugins.modules import atlas_enum_def
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasEnumDef,
    AtlasEnumElementDef,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_enum_def.AtlasTypeDefClient"

# AtlasEnumElementDef (not a raw dict) matches what the real client returns
# (via from_dict()), so "no changes" detection compares like with like.
EXISTING_ENUM = AtlasEnumDef(
    name="test_enum",
    description="An existing enum",
    type_version="1.0",
    category="ENUM",
    guid="enum-guid-1",
    version=1,
    element_defs=[
        AtlasEnumElementDef(value="RED", ordinal=1),
        AtlasEnumElementDef(value="GREEN", ordinal=2),
    ],
)


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_enum_def_module_create(module_args, mocker):
    """Test the module creates an enum typedef that does not exist."""
    mock_get = mocker.patch(f"{CLIENT}.get_enum_def_by_name", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_enum_def",
        return_value=AtlasEnumDef(
            name="test_enum",
            guid="new-guid",
            element_defs=[AtlasEnumElementDef(value="RED", ordinal=1)],
        ),
    )

    module_args(
        _args(
            name="test_enum",
            element_defs=[{"value": "RED"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    result = e.value
    assert result["changed"] is True
    assert result["enum_def"]["name"] == "test_enum"
    assert result["enum_def"]["guid"] == "new-guid"
    assert "diff" not in result

    mock_get.assert_called_once_with("test_enum")
    created = mock_create.call_args[0][0]
    assert created.name == "test_enum"
    assert created.element_defs == [AtlasEnumElementDef(value="RED")]


def test_atlas_enum_def_module_create_check_mode(module_args, mocker):
    """Test create in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_enum_def_by_name", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_enum_def")

    module_args(_args(name="test_enum", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["changed"] is True
    assert e.value["enum_def"]["name"] == "test_enum"
    mock_create.assert_not_called()


def test_atlas_enum_def_module_create_diff(module_args, mocker):
    """Test create in diff mode reports an empty before and the new definition after."""
    mocker.patch(f"{CLIENT}.get_enum_def_by_name", return_value=None)
    mocker.patch(
        f"{CLIENT}.create_enum_def",
        return_value=AtlasEnumDef(name="test_enum"),
    )

    module_args(_args(name="test_enum", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["diff"]["before"] == {}
    assert e.value["diff"]["after"]["name"] == "test_enum"


def test_atlas_enum_def_module_present_no_changes(module_args, mocker):
    """Test an identical definition is idempotent, including unset ordinals."""
    mocker.patch(f"{CLIENT}.get_enum_def_by_name", return_value=EXISTING_ENUM)
    mock_update = mocker.patch(f"{CLIENT}.update_enum_def")

    module_args(
        _args(
            name="test_enum",
            description="An existing enum",
            element_defs=[{"value": "RED"}, {"value": "GREEN"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["changed"] is False
    assert e.value["enum_def"]["guid"] == "enum-guid-1"
    mock_update.assert_not_called()


def test_atlas_enum_def_module_update_add_element(module_args, mocker):
    """Test adding an element updates the definition and keeps read-only fields."""
    mocker.patch(f"{CLIENT}.get_enum_def_by_name", return_value=EXISTING_ENUM)
    mock_update = mocker.patch(
        f"{CLIENT}.update_enum_def",
        side_effect=lambda enum_def: enum_def,
    )

    module_args(
        _args(
            name="test_enum",
            element_defs=[{"value": "RED"}, {"value": "GREEN"}, {"value": "BLUE"}],
            _ansible_diff=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["changed"] is True
    assert e.value["diff"]["after"]["element_defs"][2]["value"] == "BLUE"

    updated = mock_update.call_args[0][0]
    assert updated.guid == "enum-guid-1"
    assert [el.value for el in updated.element_defs] == ["RED", "GREEN", "BLUE"]
    assert updated.element_defs[0].ordinal == 1


def test_atlas_enum_def_module_absent_existing(module_args, mocker):
    """Test absent deletes an existing definition."""
    mocker.patch(f"{CLIENT}.get_enum_def_by_name", return_value=EXISTING_ENUM)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_enum", state="absent", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["changed"] is True
    assert e.value["diff"]["after"] == {}
    mock_delete.assert_called_once_with("test_enum")


def test_atlas_enum_def_module_absent_check_mode(module_args, mocker):
    """Test absent in check mode reports a change without deleting."""
    mocker.patch(f"{CLIENT}.get_enum_def_by_name", return_value=EXISTING_ENUM)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_enum", state="absent", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["changed"] is True
    mock_delete.assert_not_called()


def test_atlas_enum_def_module_absent_missing(module_args, mocker):
    """Test absent on a missing definition is a no-op."""
    mocker.patch(f"{CLIENT}.get_enum_def_by_name", return_value=None)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_enum", state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_enum_def.main()

    assert e.value["changed"] is False
    assert e.value["enum_def"] == {}
    mock_delete.assert_not_called()


def test_atlas_enum_def_module_present_requires_name(module_args):
    """Test present without a name fails."""
    module_args(_args(description="no name"))

    with pytest.raises(AnsibleFailJson):
        atlas_enum_def.main()


FETCH_URL = (
    "ansible_collections.cloudera.services.plugins.module_utils.common.fetch_url"
)

ATLAS_ERROR_MESSAGE = "ATLAS-400-00-0AB: type is referenced by other types"


def _http(mocker, status, body=None):
    """Build a fetch_url (response, info) result for the given status and JSON body."""
    payload = json.dumps(body if body is not None else {})
    resp = mocker.Mock()
    resp.read.return_value = payload.encode("utf-8")
    return resp, {"status": status, "msg": f"HTTP {status}", "body": payload}


def _atlas_error(mocker):
    return _http(
        mocker,
        400,
        {"errorCode": "ATLAS-400-00-0AB", "errorMessage": ATLAS_ERROR_MESSAGE},
    )


EXISTING_JSON = {
    "category": "ENUM",
    "guid": "enum-guid-1",
    "name": "test_enum",
    "elementDefs": [{"value": "RED", "ordinal": 1}],
}


def test_atlas_enum_def_module_absent_requires_name(module_args, mocker):
    """Test absent without a name fails instead of silently doing nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_enum_def_by_name")
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleFailJson):
        atlas_enum_def.main()

    mock_get.assert_not_called()
    mock_delete.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"element_defs": [{"ordinal": 1}]},
        {"element_defs": [{"value": "RED", "ordinal": "first"}]},
        {"super_types": ["parent"]},
        {"state": "unknown"},
        {"propagate_tags": "NONE"},
    ],
    ids=[
        "element-missing-value",
        "element-non-integer-ordinal",
        "entity-only-parameter",
        "invalid-state",
        "relationship-only-parameter",
    ],
)
def test_atlas_enum_def_module_invalid_arguments_fail(module_args, mocker, extra):
    """Test invalid arguments fail before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_enum_def_by_name")

    module_args(_args(name="test_enum", **extra))

    with pytest.raises(AnsibleFailJson):
        atlas_enum_def.main()

    mock_get.assert_not_called()


def test_atlas_enum_def_module_create_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on create fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 404)
        assert method == "POST"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_enum"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_enum_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_enum_def_module_update_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on update fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 200, EXISTING_JSON)
        assert method == "PUT"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_enum", description="new"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_enum_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_enum_def_module_delete_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on delete fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 200, EXISTING_JSON)
        assert method == "DELETE"
        return _atlas_error(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_enum", state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_enum_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_enum_def_module_unexpected_response_fails(module_args, mocker):
    """Test a 200 response lacking the written def fails the module cleanly."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return _http(mocker, 404)
        return _http(mocker, 200, {"enumDefs": []})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_enum"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_enum_def.main()

    assert "test_enum" in e.value["msg"]
