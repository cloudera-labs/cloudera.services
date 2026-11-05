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
from typing import Any, Dict, List, Optional

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_entity_classification,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasClassification,
    AtlasEntity,
)

BASE_URL = "https://atlas.example"
MODULE = (
    "ansible_collections.cloudera.services.plugins.modules.atlas_entity_classification"
)
CLIENT = f"{MODULE}.AtlasEntityClient"
ATTRIBUTE_DEFS = f"{MODULE}.classification_attribute_defs"
GUID = "fc0fd256-be16-4775-99ad-9e0b7e304ae5"
OTHER_GUID = "11111111-2222-3333-4444-555555555555"
TAG = "my_tag"


def _classification(
    attributes: Optional[Dict[str, Any]] = None,
    propagate: bool = True,
    remove: bool = False,
    entity_guid: Optional[str] = GUID,
    type_name: str = TAG,
    validity_periods: Optional[List[Dict[str, Any]]] = None,
) -> AtlasClassification:
    """Build a classification as Atlas returns it; with attributes=None the key is left unset."""
    classification = AtlasClassification(
        type_name=type_name,
        propagate=propagate,
        remove_propagations_on_entity_delete=remove,
        entity_status="ACTIVE",
    )
    if attributes is not None:
        classification.attributes = attributes
    if entity_guid is not None:
        classification.entity_guid = entity_guid
    if validity_periods is not None:
        classification.validity_periods = validity_periods
    return classification


def _entity(
    classifications: Optional[List[AtlasClassification]] = None,
    status: str = "ACTIVE",
) -> AtlasEntity:
    """Build an entity; with classifications=None the key is left unset, as Atlas omits it when there are none."""
    entity = AtlasEntity(type_name="test_entity_type", guid=GUID, status=status)
    if classifications is not None:
        entity.classifications = classifications
    return entity


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        "guid": GUID,
        "name": TAG,
        **extra,
    }


@pytest.fixture
def attribute_defs(mocker):
    """Patch the classification typedef lookup to return the test attributes."""
    return mocker.patch(
        ATTRIBUTE_DEFS,
        return_value=[
            AtlasAttributeDef(name="level", type_name="string"),
            AtlasAttributeDef(name="rank", type_name="int"),
        ],
    )


def test_atlas_entity_classification_module_present_attaches_classification(
    module_args,
    mocker,
    attribute_defs,
):
    """Test present attaches a missing classification with the requested values, then reports what Atlas stored."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[
            _entity(),
            _entity([_classification({"level": "high"}, propagate=False)]),
        ],
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args(attributes={"level": "high"}, propagate=False))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == GUID
    assert e.value["classification"]["type_name"] == TAG
    assert e.value["classification"]["attributes"] == {"level": "high"}
    assert e.value["classification"]["propagate"] is False
    mock_add.assert_called_once_with(
        GUID,
        [
            AtlasClassification(
                type_name=TAG,
                attributes={"level": "high"},
                propagate=False,
            ),
        ],
    )
    mock_update.assert_not_called()
    assert mock_get.call_count == 2
    attribute_defs.assert_called_once()


def test_atlas_entity_classification_module_present_with_only_a_name(
    module_args,
    mocker,
    attribute_defs,
):
    """Test present with no other option attaches the classification and leaves everything else to Atlas's defaults."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[_entity(), _entity([_classification()])],
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args())

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    mock_add.assert_called_once_with(GUID, [AtlasClassification(type_name=TAG)])


def test_atlas_entity_classification_module_present_updates_changed_attribute(
    module_args,
    mocker,
    attribute_defs,
):
    """Test a differing attribute is updated, keeping the attributes and settings not mentioned."""
    period = [
        {
            "start_time": "2026/01/01 00:00:00",
            "end_time": "2026/12/31 00:00:00",
            "time_zone": "UTC",
        },
    ]
    existing = _classification(
        {"level": "low", "rank": 1},
        propagate=False,
        remove=True,
        validity_periods=period,
    )
    updated = _classification(
        {"level": "high", "rank": 1},
        propagate=False,
        remove=True,
    )
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[_entity([existing]), _entity([updated])],
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args(attributes={"level": "high"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"]["attributes"] == {"level": "high", "rank": 1}
    mock_add.assert_not_called()
    mock_update.assert_called_once_with(
        GUID,
        [
            AtlasClassification(
                type_name=TAG,
                attributes={"level": "high", "rank": 1},
                propagate=False,
                remove_propagations_on_entity_delete=True,
                validity_periods=period,
            ),
        ],
    )


def test_atlas_entity_classification_module_present_updates_propagation_only(
    module_args,
    mocker,
    attribute_defs,
):
    """Test a changed propagate flag is updated without touching the attributes."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[
            _entity([_classification({"level": "low"})]),
            _entity([_classification({"level": "low"}, propagate=False)]),
        ],
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args(propagate=False))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    mock_update.assert_called_once_with(
        GUID,
        [
            AtlasClassification(
                type_name=TAG,
                attributes={"level": "low"},
                propagate=False,
                remove_propagations_on_entity_delete=False,
            ),
        ],
    )


def test_atlas_entity_classification_module_present_changes_remove_propagations_flag(
    module_args,
    mocker,
    attribute_defs,
):
    """Test remove_propagations_on_entity_delete is managed like propagate."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[
            _entity([_classification({})]),
            _entity([_classification({}, remove=True)]),
        ],
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args(remove_propagations_on_entity_delete=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert mock_update.call_args.args[1][0].remove_propagations_on_entity_delete is True


def test_atlas_entity_classification_module_present_is_idempotent(
    module_args,
    mocker,
    attribute_defs,
):
    """Test present makes no change when every requested value is already set."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification({"level": "high", "rank": 1})]),
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args(attributes={"level": "high"}, propagate=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False
    assert e.value["classification"]["attributes"] == {"level": "high", "rank": 1}
    mock_add.assert_not_called()
    mock_update.assert_not_called()
    mock_get.assert_called_once()


def test_atlas_entity_classification_module_present_name_only_is_idempotent(
    module_args,
    mocker,
    attribute_defs,
):
    """Test present with just a name changes nothing for a classification that is already attached."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification({"level": "low"}, propagate=False)]),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args())

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_atlas_entity_classification_module_string_for_int_is_idempotent(
    module_args,
    mocker,
    attribute_defs,
):
    """Test "1" for an int attribute that Atlas stores as 1 is not a change."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification({"rank": 1})]),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args(attributes={"rank": "1"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_atlas_entity_classification_module_string_for_int_is_sent_as_int(
    module_args,
    mocker,
    attribute_defs,
):
    """Test a value is converted to the attribute's type before it is sent."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[_entity(), _entity([_classification({"rank": 1})])],
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args(attributes={"rank": "1"}))

    with pytest.raises(AnsibleExitJson):
        atlas_entity_classification.main()

    assert mock_add.call_args.args[1][0].attributes == {"rank": 1}


def test_atlas_entity_classification_module_ignores_null_attributes_atlas_returns(
    module_args,
    mocker,
    attribute_defs,
):
    """Test attributes Atlas reports as null are not sent back on an update."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[
            _entity([_classification({"level": "low", "rank": None})]),
            _entity([_classification({"level": "high"})]),
        ],
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args(attributes={"level": "high"}))

    with pytest.raises(AnsibleExitJson):
        atlas_entity_classification.main()

    assert mock_update.call_args.args[1][0].attributes == {"level": "high"}


def test_atlas_entity_classification_module_propagated_classification_is_not_attached(
    module_args,
    mocker,
    attribute_defs,
):
    """Test a classification propagated from another entity does not count as attached to this one."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[
            _entity([_classification({"level": "x"}, entity_guid=OTHER_GUID)]),
            _entity(
                [
                    _classification({"level": "x"}, entity_guid=OTHER_GUID),
                    _classification({"level": "high"}),
                ],
            ),
        ],
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(_args(attributes={"level": "high"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"]["attributes"] == {"level": "high"}
    mock_add.assert_called_once()
    mock_update.assert_not_called()


def test_atlas_entity_classification_module_classification_without_entity_guid_is_direct(
    module_args,
    mocker,
    attribute_defs,
):
    """Test a classification with no entityGuid is treated as attached to the entity itself."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification({"level": "high"}, entity_guid=None)]),
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args(attributes={"level": "high"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False
    mock_add.assert_not_called()


def test_atlas_entity_classification_module_other_classifications_are_untouched(
    module_args,
    mocker,
    attribute_defs,
):
    """Test only the named classification is read, written and returned."""
    other = _classification({"x": 1}, type_name="other_tag")
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[
            _entity([other]),
            _entity([other, _classification({"level": "high"})]),
        ],
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args(attributes={"level": "high"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["classification"]["type_name"] == TAG
    assert [c.type_name for c in mock_add.call_args.args[1]] == [TAG]


def test_atlas_entity_classification_module_absent_removes_classification(
    module_args,
    mocker,
):
    """Test absent removes the classification attached to the entity."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification({"level": "high"})]),
    )
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_classification")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == GUID
    assert e.value["classification"] == {}
    mock_remove.assert_called_once_with(GUID, TAG)


@pytest.mark.parametrize(
    "classifications",
    [
        None,
        [],
        [_classification({"x": 1}, type_name="other_tag")],
        [_classification({"level": "x"}, entity_guid=OTHER_GUID)],
    ],
    ids=["no-key", "empty", "other-classification", "only-propagated"],
)
def test_atlas_entity_classification_module_absent_is_idempotent(
    module_args,
    mocker,
    classifications,
):
    """Test absent makes no change when the classification is not attached to the entity itself."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity(classifications),
    )
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_classification")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False
    assert e.value["classification"] == {}
    mock_remove.assert_not_called()


@pytest.mark.parametrize(
    "entity",
    [None, _entity([_classification()], status="DELETED")],
    ids=["missing", "deleted"],
)
def test_atlas_entity_classification_module_absent_without_an_active_entity_is_a_no_op(
    module_args,
    mocker,
    entity,
):
    """Test absent on a missing or soft-deleted entity has nothing to remove."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=entity)
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_classification")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False
    assert e.value["guid"] is None
    assert e.value["classification"] == {}
    mock_remove.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"attributes": {"level": "x"}},
        {"propagate": True},
        {"remove_propagations_on_entity_delete": False},
    ],
    ids=["attributes", "propagate", "remove-propagations"],
)
def test_atlas_entity_classification_module_absent_with_values_fails(
    module_args,
    mocker,
    extra,
):
    """Test values with absent are refused, because absent removes the whole classification."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_classification")

    module_args(_args(state="absent", **extra))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "absent" in e.value["msg"]
    mock_get.assert_not_called()
    mock_remove.assert_not_called()


@pytest.mark.parametrize(
    "entity",
    [None, _entity(status="DELETED")],
    ids=["missing", "deleted"],
)
def test_atlas_entity_classification_module_present_fails_without_an_active_entity(
    module_args,
    mocker,
    attribute_defs,
    entity,
):
    """Test present fails, with no write, when the entity is missing or deleted."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=entity)
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "active entity" in e.value["msg"]
    mock_add.assert_not_called()


def test_atlas_entity_classification_module_unknown_classification_fails(
    module_args,
    mocker,
    attribute_defs,
):
    """Test a classification that has no typedef fails without a write."""
    attribute_defs.return_value = None
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert TAG in e.value["msg"]
    assert "does not exist" in e.value["msg"]
    mock_add.assert_not_called()


def test_atlas_entity_classification_module_unknown_attribute_fails(
    module_args,
    mocker,
    attribute_defs,
):
    """Test an attribute the typedef lacks fails, because Atlas would silently ignore it."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args(attributes={"levl": "high"}))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "levl" in e.value["msg"]
    mock_add.assert_not_called()


@pytest.mark.parametrize(
    "attributes",
    [{"level": None}, {"rank": "high"}],
    ids=["null", "bad-int"],
)
def test_atlas_entity_classification_module_invalid_value_fails(
    module_args,
    mocker,
    attribute_defs,
    attributes,
):
    """Test a null or ill-typed value fails without a write."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args(attributes=attributes))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert next(iter(attributes)) in e.value["msg"]
    mock_add.assert_not_called()


def test_atlas_entity_classification_module_write_not_visible_afterwards_fails(
    module_args,
    mocker,
    attribute_defs,
):
    """Test the module fails if Atlas does not report the classification it just wrote."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[_entity(), _entity([])],
    )
    mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert TAG in e.value["msg"]


def test_atlas_entity_classification_module_by_qualified_name(
    module_args,
    mocker,
    attribute_defs,
):
    """Test the entity is looked up by type and qualified name, then written by guid."""
    mock_unique = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(),
    )
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification()]),
    )
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    args = _args(type_name="test_entity_type", qualified_name="test_entity_1")
    del args["guid"]
    module_args(args)

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["guid"] == GUID
    mock_unique.assert_called_once_with(
        "test_entity_type",
        {"qualifiedName": "test_entity_1"},
    )
    mock_add.assert_called_once_with(GUID, [AtlasClassification(type_name=TAG)])


def test_atlas_entity_classification_module_by_unique_attributes(
    module_args,
    mocker,
    attribute_defs,
):
    """Test unique_attributes are passed through unchanged."""
    mock_unique = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity([_classification()]),
    )

    args = _args(
        type_name="test_entity_type",
        unique_attributes={"qualifiedName": "q", "other": "x"},
    )
    del args["guid"]
    module_args(args)

    with pytest.raises(AnsibleExitJson):
        atlas_entity_classification.main()

    mock_unique.assert_called_once_with(
        "test_entity_type",
        {"qualifiedName": "q", "other": "x"},
    )


def test_atlas_entity_classification_module_check_mode_attach(
    module_args,
    mocker,
    attribute_defs,
):
    """Test check mode reports the classification that would be attached, with Atlas's defaults, and writes nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(_args(attributes={"level": "high"}, _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"]["type_name"] == TAG
    assert e.value["classification"]["attributes"] == {"level": "high"}
    assert e.value["classification"]["propagate"] is True
    assert e.value["classification"]["remove_propagations_on_entity_delete"] is False
    mock_add.assert_not_called()
    mock_get.assert_called_once()


def test_atlas_entity_classification_module_check_mode_update(
    module_args,
    mocker,
    attribute_defs,
):
    """Test check mode reports the merged classification and writes nothing."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification({"level": "low", "rank": 1})]),
    )
    mock_update = mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(
        _args(attributes={"level": "high"}, propagate=False, _ansible_check_mode=True),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"]["attributes"] == {"level": "high", "rank": 1}
    assert e.value["classification"]["propagate"] is False
    mock_update.assert_not_called()


def test_atlas_entity_classification_module_check_mode_absent(module_args, mocker):
    """Test check mode reports the removal and writes nothing."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification()]),
    )
    mock_remove = mocker.patch(f"{CLIENT}.remove_entity_classification")

    module_args(_args(state="absent", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"] == {}
    mock_remove.assert_not_called()


def test_atlas_entity_classification_module_diff_mode_attach(
    module_args,
    mocker,
    attribute_defs,
):
    """Test diff mode shows the classification being attached."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[
            _entity(),
            _entity([_classification({"level": "high"}, propagate=False)]),
        ],
    )
    mocker.patch(f"{CLIENT}.add_entity_classifications")

    module_args(
        _args(attributes={"level": "high"}, propagate=False, _ansible_diff=True),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["diff"] == {
        "before": {"classification": {}},
        "after": {
            "classification": {
                TAG: {"attributes": {"level": "high"}, "propagate": False},
            },
        },
    }


def test_atlas_entity_classification_module_diff_mode_update(
    module_args,
    mocker,
    attribute_defs,
):
    """Test diff mode shows only the values that change."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        side_effect=[
            _entity([_classification({"level": "low", "rank": 1})]),
            _entity([_classification({"level": "high", "rank": 1})]),
        ],
    )
    mocker.patch(f"{CLIENT}.update_entity_classifications")

    module_args(
        _args(
            attributes={"level": "high", "rank": 1},
            propagate=True,
            _ansible_diff=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["diff"] == {
        "before": {"classification": {TAG: {"attributes": {"level": "low"}}}},
        "after": {"classification": {TAG: {"attributes": {"level": "high"}}}},
    }


def test_atlas_entity_classification_module_diff_mode_absent(module_args, mocker):
    """Test diff mode shows the classification being removed."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification({"level": "high"})]),
    )
    mocker.patch(f"{CLIENT}.remove_entity_classification")

    module_args(_args(state="absent", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["diff"] == {
        "before": {
            "classification": {
                TAG: {
                    "attributes": {"level": "high"},
                    "propagate": True,
                    "remove_propagations_on_entity_delete": False,
                },
            },
        },
        "after": {"classification": {}},
    }


def test_atlas_entity_classification_module_diff_mode_without_change(
    module_args,
    mocker,
    attribute_defs,
):
    """Test diff mode reports an empty diff when nothing changes."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity([_classification({"level": "high"})]),
    )

    module_args(_args(attributes={"level": "high"}, _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

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
    ],
    ids=[
        "nothing",
        "guid-and-type",
        "guid-and-qualified-name",
        "qualified-name-and-unique-attributes",
        "guid-and-type-and-qualified-name",
        "no-name",
    ],
)
def test_atlas_entity_classification_module_invalid_arguments_fail(
    module_args,
    mocker,
    extra,
):
    """Test an ambiguous identity or missing name fails before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_unique = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")
    mock_defs = mocker.patch(ATTRIBUTE_DEFS)
    mock_add = mocker.patch(f"{CLIENT}.add_entity_classifications")

    args = _args()
    args.update(extra)
    module_args({k: v for k, v in args.items() if v is not None})

    with pytest.raises(AnsibleFailJson):
        atlas_entity_classification.main()

    mock_get.assert_not_called()
    mock_unique.assert_not_called()
    mock_defs.assert_not_called()
    mock_add.assert_not_called()


def _entity_json(classifications):
    return {
        "referredEntities": {},
        "entity": {
            "typeName": "test_entity_type",
            "attributes": {"qualifiedName": "test_entity_1"},
            "guid": GUID,
            "status": "ACTIVE",
            "classifications": classifications,
        },
    }


ATTACHED = {
    "typeName": TAG,
    "attributes": {"level": "low"},
    "entityGuid": GUID,
    "entityStatus": "ACTIVE",
    "propagate": True,
    "removePropagationsOnEntityDelete": False,
}

TYPEDEF_JSON = {
    "category": "CLASSIFICATION",
    "name": TAG,
    "superTypes": ["parent_tag"],
    "attributeDefs": [{"name": "level", "typeName": "string"}],
}

PARENT_TYPEDEF_JSON = {
    "category": "CLASSIFICATION",
    "name": "parent_tag",
    "attributeDefs": [{"name": "rank", "typeName": "int"}],
}


def _typedef_response(mocker, url):
    if url.split("?")[0].endswith("/parent_tag"):
        return http_result(mocker, 200, PARENT_TYPEDEF_JSON)
    return http_result(mocker, 200, TYPEDEF_JSON)


def test_atlas_entity_classification_module_update_requests(module_args, mocker):
    """Test the real requests: read the entity and the typedefs, then PUT the merged classification, then read back."""
    calls = []
    reads = iter(
        [
            _entity_json([ATTACHED]),
            _entity_json([{**ATTACHED, "attributes": {"level": "high", "rank": 2}}]),
        ],
    )

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if method == "GET" and "/types/classificationdef/" in url:
            return _typedef_response(mocker, url)
        if method == "GET":
            return http_result(mocker, 200, next(reads))
        return http_result(mocker, 204)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"level": "high", "rank": "2"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"]["attributes"] == {"level": "high", "rank": 2}
    assert [c[0] for c in calls] == ["GET", "GET", "GET", "PUT", "GET"]
    put = calls[3]
    assert put[1].endswith(f"/api/atlas/v2/entity/guid/{GUID}/classifications")
    assert json.loads(put[2]) == [
        {
            "typeName": TAG,
            "attributes": {"level": "high", "rank": 2},
            "propagate": True,
            "removePropagationsOnEntityDelete": False,
        },
    ]


def test_atlas_entity_classification_module_attach_requests(module_args, mocker):
    """Test the real requests: a POST of the classification list, then a read back."""
    calls = []
    reads = iter([_entity_json([]), _entity_json([ATTACHED])])

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if method == "GET" and "/types/classificationdef/" in url:
            return _typedef_response(mocker, url)
        if method == "GET":
            return http_result(mocker, 200, next(reads))
        return http_result(mocker, 204)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"level": "low"}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    post = [c for c in calls if c[0] == "POST"]
    assert len(post) == 1
    assert post[0][1].endswith(f"/api/atlas/v2/entity/guid/{GUID}/classifications")
    assert json.loads(post[0][2]) == [{"typeName": TAG, "attributes": {"level": "low"}}]


def test_atlas_entity_classification_module_absent_requests(module_args, mocker):
    """Test the real requests: read the entity, then DELETE the classification by name with no body."""
    calls = []

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if method == "GET":
            return http_result(mocker, 200, _entity_json([ATTACHED]))
        return http_result(mocker, 204)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert [c[0] for c in calls] == ["GET", "DELETE"]
    assert calls[1][1].endswith(
        f"/api/atlas/v2/entity/guid/{GUID}/classification/{TAG}",
    )
    assert not calls[1][2]


def test_atlas_entity_classification_module_inherited_attribute_is_accepted(
    module_args,
    mocker,
):
    """Test an attribute defined by a super type is accepted, because the typedefs are followed."""
    reads = iter([_entity_json([ATTACHED]), _entity_json([ATTACHED])])

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        if method == "GET" and "/types/classificationdef/" in url:
            return _typedef_response(mocker, url)
        if method == "GET":
            return http_result(mocker, 200, next(reads))
        return http_result(mocker, 204)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(attributes={"rank": 2}))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True


def test_atlas_entity_classification_module_typedef_not_found_fails(
    module_args,
    mocker,
):
    """Test a 404 for the classification typedef reads as a missing typedef, not an Atlas error."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if "/types/classificationdef/" in url:
            return http_result(
                mocker,
                404,
                {"errorCode": "ATLAS-404-00-00B", "errorMessage": "not found"},
            )
        return http_result(mocker, 200, _entity_json([]))

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "does not exist" in e.value["msg"]


def test_atlas_entity_classification_module_atlas_rejects_attach(module_args, mocker):
    """Test an Atlas HTTP 400 (already associated) on the write fails the module with Atlas's message."""
    message = "Given entity is already associated with the classification"

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET" and "/types/classificationdef/" in url:
            return _typedef_response(mocker, url)
        if method == "GET":
            return http_result(mocker, 200, _entity_json([]))
        return http_result(
            mocker,
            400,
            {"errorCode": "ATLAS-400-00-01A", "errorMessage": message},
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert message in e.value["msg"]


def test_atlas_entity_classification_module_atlas_rejects_remove(module_args, mocker):
    """Test an Atlas HTTP 400 on the delete fails the module with Atlas's message."""
    message = "not associated with the classification"

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 200, _entity_json([ATTACHED]))
        return http_result(
            mocker,
            400,
            {"errorCode": "ATLAS-400-00-06D", "errorMessage": message},
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert message in e.value["msg"]


def test_atlas_entity_classification_module_unknown_type_fails(module_args, mocker):
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

    args = _args(type_name="no_such_type", qualified_name="q")
    del args["guid"]
    module_args(args)

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "does not exist" in e.value["msg"]


@pytest.mark.parametrize("body", [[], {}, {"entity": {"guid": GUID}}])
def test_atlas_entity_classification_module_malformed_entity_response_fails(
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

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "unexpected" in e.value["msg"]
    assert calls == ["GET"]


def test_atlas_entity_classification_module_forbidden_fails(module_args, mocker):
    """Test an authorization failure fails the module."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 403, {"errorMessage": "denied"})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "Forbidden" in e.value["msg"]
