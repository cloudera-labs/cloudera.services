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
    ATLAS_ERROR_MESSAGE,
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    atlas_error_result,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import atlas_struct_def
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasConstraintDef,
    AtlasStructDef,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_struct_def.AtlasTypeDefClient"

# Atlas fills attribute defaults on the server; the existing def carries them.
EXISTING = AtlasStructDef(
    name="test_struct",
    description="An existing struct",
    type_version="1.0",
    category="STRUCT",
    guid="struct-guid-1",
    version=1,
    attribute_defs=[
        AtlasAttributeDef(
            name="street",
            type_name="string",
            is_optional=True,
            cardinality="SINGLE",
            values_min_count=0,
            values_max_count=1,
            is_unique=False,
            is_indexable=True,
        ),
    ],
)


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_struct_def_module_create(module_args, mocker):
    """Test the module creates a struct typedef that does not exist."""
    mock_get = mocker.patch(f"{CLIENT}.get_struct_def_by_name", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_struct_def",
        return_value=AtlasStructDef(name="test_struct", guid="new"),
    )

    module_args(
        _args(
            name="test_struct",
            attribute_defs=[{"name": "street", "type_name": "string"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()

    result = e.value
    assert result["changed"] is True
    assert result["struct_def"]["guid"] == "new"
    assert "diff" not in result

    mock_get.assert_called_once_with("test_struct")
    created = mock_create.call_args[0][0]
    assert created.attribute_defs == [
        AtlasAttributeDef(name="street", type_name="string"),
    ]


def test_atlas_struct_def_module_present_no_changes(module_args, mocker):
    """Test unset attribute fields keep Atlas-filled defaults, so no change is reported."""
    mocker.patch(f"{CLIENT}.get_struct_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(f"{CLIENT}.update_struct_def")

    module_args(
        _args(
            name="test_struct",
            description="An existing struct",
            attribute_defs=[{"name": "street", "type_name": "string"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()

    assert e.value["changed"] is False
    assert e.value["struct_def"]["guid"] == "struct-guid-1"
    mock_update.assert_not_called()


def test_atlas_struct_def_module_present_attribute_added(module_args, mocker):
    """Test adding an attribute updates and keeps the existing attribute intact."""
    mocker.patch(f"{CLIENT}.get_struct_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(
        f"{CLIENT}.update_struct_def",
        return_value=AtlasStructDef(name="test_struct"),
    )

    module_args(
        _args(
            name="test_struct",
            attribute_defs=[
                {"name": "street", "type_name": "string"},
                {
                    "name": "ref",
                    "type_name": "string",
                    "constraints": [{"type": "ownedRef", "params": {"a": "b"}}],
                },
            ],
            _ansible_diff=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()

    assert e.value["changed"] is True
    assert e.value["diff"]["before"] != e.value["diff"]["after"]
    sent = mock_update.call_args[0][0]
    assert sent.attribute_defs[0].cardinality == "SINGLE"
    assert sent.attribute_defs[1].constraints == [
        AtlasConstraintDef(type="ownedRef", params={"a": "b"}),
    ]
    assert sent.guid == "struct-guid-1"


def test_atlas_struct_def_module_check_mode(module_args, mocker):
    """Test create in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_struct_def_by_name", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_struct_def")

    module_args(_args(name="test_struct", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()


def test_atlas_struct_def_module_update_check_mode(module_args, mocker):
    """Test update in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_struct_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(f"{CLIENT}.update_struct_def")

    module_args(
        _args(name="test_struct", description="new", _ansible_check_mode=True),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()

    assert e.value["changed"] is True
    mock_update.assert_not_called()


def test_atlas_struct_def_module_create_diff(module_args, mocker):
    """Test create in diff mode reports an empty before and the new definition after."""
    mocker.patch(f"{CLIENT}.get_struct_def_by_name", return_value=None)
    mocker.patch(
        f"{CLIENT}.create_struct_def",
        return_value=AtlasStructDef(name="test_struct"),
    )

    module_args(_args(name="test_struct", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()

    assert e.value["diff"]["before"] == {}
    assert e.value["diff"]["after"]["name"] == "test_struct"


def test_atlas_struct_def_module_absent(module_args, mocker):
    """Test absent deletes an existing struct and is a no-op when missing."""
    mock_get = mocker.patch(f"{CLIENT}.get_struct_def_by_name", return_value=EXISTING)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_struct", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()
    assert e.value["changed"] is True
    mock_delete.assert_called_once_with("test_struct")

    mock_get.return_value = None
    mock_delete.reset_mock()
    module_args(_args(name="test_struct", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()
    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_atlas_struct_def_module_absent_check_mode(module_args, mocker):
    """Test absent in check mode reports a change without deleting."""
    mocker.patch(f"{CLIENT}.get_struct_def_by_name", return_value=EXISTING)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(
        _args(name="test_struct", state="absent", _ansible_check_mode=True),
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_struct_def.main()

    assert e.value["changed"] is True
    mock_delete.assert_not_called()


def test_atlas_struct_def_module_present_requires_name(module_args):
    """Test present without a name fails."""
    module_args(_args())

    with pytest.raises(AnsibleFailJson):
        atlas_struct_def.main()


def test_atlas_struct_def_module_absent_requires_name(module_args, mocker):
    """Test absent without a name fails instead of silently doing nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_struct_def_by_name")
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleFailJson):
        atlas_struct_def.main()

    mock_get.assert_not_called()
    mock_delete.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"attribute_defs": [{"name": "street"}]},
        {
            "attribute_defs": [
                {"name": "street", "type_name": "string", "cardinality": "MANY"},
            ],
        },
        {
            "attribute_defs": [
                {"name": "street", "type_name": "string", "index_type": "FULLTEXT"},
            ],
        },
        {"state": "unknown"},
        {"super_types": ["parent"]},
        {"entity_types": ["hive_table"]},
    ],
    ids=[
        "attribute-missing-type-name",
        "invalid-cardinality",
        "invalid-index-type",
        "invalid-state",
        "entity-only-parameter",
        "classification-only-parameter",
    ],
)
def test_atlas_struct_def_module_invalid_arguments_fail(module_args, mocker, extra):
    """Test invalid arguments fail before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_struct_def_by_name")

    module_args(_args(name="test_struct", **extra))

    with pytest.raises(AnsibleFailJson):
        atlas_struct_def.main()

    mock_get.assert_not_called()


STRUCT_EXISTING_JSON = {
    "category": "STRUCT",
    "guid": "struct-guid-1",
    "name": "test_struct",
    "attributeDefs": [],
}


def test_atlas_struct_def_module_create_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on create fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 404)
        assert method == "POST"
        return atlas_error_result(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_struct"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_struct_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_struct_def_module_update_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on update fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 200, STRUCT_EXISTING_JSON)
        assert method == "PUT"
        return atlas_error_result(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_struct", description="new"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_struct_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_struct_def_module_delete_atlas_error_fails(module_args, mocker):
    """Test an Atlas 400 on delete fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 200, STRUCT_EXISTING_JSON)
        assert method == "DELETE"
        return atlas_error_result(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_struct", state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_struct_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_struct_def_module_unexpected_response_fails(module_args, mocker):
    """Test a 200 response lacking the written struct def fails the module cleanly."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 404)
        return http_result(mocker, 200, {"structDefs": []})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_struct"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_struct_def.main()

    assert "test_struct" in e.value["msg"]
