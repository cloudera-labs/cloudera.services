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
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_classification_def,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasClassificationDef,
    AtlasConstraintDef,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_classification_def.AtlasTypeDefClient"

# Atlas fills attribute defaults on the server; the existing def carries them.
EXISTING = AtlasClassificationDef(
    name="test_classification",
    description="An existing classification",
    type_version="1.0",
    category="CLASSIFICATION",
    guid="cls-guid-1",
    version=1,
    attribute_defs=[
        AtlasAttributeDef(
            name="level",
            type_name="string",
            is_optional=True,
            cardinality="SINGLE",
            values_min_count=0,
            values_max_count=1,
            is_unique=False,
            is_indexable=True,
        ),
    ],
    super_types=["parent"],
    entity_types=[],
    sub_types=[],
)


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_classification_def_module_create(module_args, mocker):
    """Test the module creates a classification typedef that does not exist."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_classification_def_by_name",
        return_value=None,
    )
    mock_create = mocker.patch(
        f"{CLIENT}.create_classification_def",
        return_value=AtlasClassificationDef(name="test_classification", guid="new"),
    )

    module_args(
        _args(
            name="test_classification",
            super_types=["parent"],
            attribute_defs=[{"name": "level", "type_name": "string"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_classification_def.main()

    result = e.value
    assert result["changed"] is True
    assert result["classification_def"]["guid"] == "new"
    assert "diff" not in result

    mock_get.assert_called_once_with("test_classification")
    created = mock_create.call_args[0][0]
    assert created.super_types == ["parent"]
    assert created.attribute_defs == [
        AtlasAttributeDef(name="level", type_name="string"),
    ]


def test_atlas_classification_def_module_present_no_changes(module_args, mocker):
    """Test unset attribute fields keep Atlas-filled defaults, so no change is reported."""
    mocker.patch(
        f"{CLIENT}.get_classification_def_by_name",
        return_value=EXISTING,
    )
    mock_update = mocker.patch(f"{CLIENT}.update_classification_def")

    module_args(
        _args(
            name="test_classification",
            description="An existing classification",
            super_types=["parent"],
            attribute_defs=[{"name": "level", "type_name": "string"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_classification_def.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_atlas_classification_def_module_present_attribute_added(module_args, mocker):
    """Test adding an attribute updates and keeps the existing attribute intact."""
    mocker.patch(
        f"{CLIENT}.get_classification_def_by_name",
        return_value=EXISTING,
    )
    mock_update = mocker.patch(
        f"{CLIENT}.update_classification_def",
        return_value=AtlasClassificationDef(name="test_classification"),
    )

    module_args(
        _args(
            name="test_classification",
            attribute_defs=[
                {"name": "level", "type_name": "string"},
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
        atlas_classification_def.main()

    assert e.value["changed"] is True
    assert e.value["diff"]["before"] != e.value["diff"]["after"]
    sent = mock_update.call_args[0][0]
    assert sent.attribute_defs[0].cardinality == "SINGLE"
    assert sent.attribute_defs[1].constraints == [
        AtlasConstraintDef(type="ownedRef", params={"a": "b"}),
    ]
    assert sent.guid == "cls-guid-1"


def test_atlas_classification_def_module_check_mode(module_args, mocker):
    """Test create in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_classification_def_by_name", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_classification_def")

    module_args(_args(name="test_classification", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_classification_def.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()


def test_atlas_classification_def_module_create_diff(module_args, mocker):
    """Test create in diff mode reports an empty before and the new definition after."""
    mocker.patch(f"{CLIENT}.get_classification_def_by_name", return_value=None)
    mocker.patch(
        f"{CLIENT}.create_classification_def",
        return_value=AtlasClassificationDef(name="test_classification"),
    )

    module_args(_args(name="test_classification", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_classification_def.main()

    assert e.value["diff"]["before"] == {}
    assert e.value["diff"]["after"]["name"] == "test_classification"


def test_atlas_classification_def_module_absent(module_args, mocker):
    """Test absent deletes an existing classification and is a no-op when missing."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_classification_def_by_name",
        return_value=EXISTING,
    )
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_classification", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_classification_def.main()
    assert e.value["changed"] is True
    mock_delete.assert_called_once_with("test_classification")

    mock_get.return_value = None
    mock_delete.reset_mock()
    module_args(_args(name="test_classification", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_classification_def.main()
    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_atlas_classification_def_module_absent_check_mode(module_args, mocker):
    """Test absent in check mode reports a change without deleting."""
    mocker.patch(f"{CLIENT}.get_classification_def_by_name", return_value=EXISTING)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(
        _args(name="test_classification", state="absent", _ansible_check_mode=True),
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_classification_def.main()

    assert e.value["changed"] is True
    mock_delete.assert_not_called()


def test_atlas_classification_def_module_present_requires_name(module_args):
    """Test present without a name fails."""
    module_args(_args())

    with pytest.raises(AnsibleFailJson):
        atlas_classification_def.main()
