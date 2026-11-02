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
from typing import List, Optional

from ansible_collections.cloudera.services.tests.unit import (
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import atlas_entity_label
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntity,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_entity_label.AtlasEntityClient"
GUID = "fc0fd256-be16-4775-99ad-9e0b7e304ae5"


def _entity(labels: Optional[List[str]] = None, status: str = "ACTIVE") -> AtlasEntity:
    """Build an entity; with labels=None the key is left unset, as Atlas omits it when an entity has none."""
    entity = AtlasEntity(type_name="test_entity_type", guid=GUID, status=status)
    if labels is not None:
        entity.labels = labels
    return entity


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        "guid": GUID,
        **extra,
    }


def test_atlas_entity_label_module_present_adds_missing_labels(module_args, mocker):
    """Test present keeps the existing labels and adds the requested ones."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a"]))
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["b", "c"]))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == GUID
    assert e.value["labels"] == ["a", "b", "c"]
    mock_set.assert_called_once_with(GUID, ["a", "b", "c"])


def test_atlas_entity_label_module_present_on_unlabelled_entity(module_args, mocker):
    """Test an entity without a labels key (as Atlas returns it) counts as having none."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity())
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["a"]))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    assert e.value["labels"] == ["a"]
    mock_set.assert_called_once_with(GUID, ["a"])


def test_atlas_entity_label_module_present_is_idempotent(module_args, mocker):
    """Test present makes no change when every requested label is already there."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity(["b", "a", "c"]),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["a", "b"]))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False
    assert e.value["labels"] == ["b", "a", "c"]
    mock_set.assert_not_called()


def test_atlas_entity_label_module_duplicate_requested_labels_are_collapsed(
    module_args,
    mocker,
):
    """Test a label requested twice is only sent once."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a"]))
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["b", "b"]))

    with pytest.raises(AnsibleExitJson):
        atlas_entity_label.main()

    mock_set.assert_called_once_with(GUID, ["a", "b"])


def test_atlas_entity_label_module_exclusive_replaces_labels(module_args, mocker):
    """Test exclusive makes the requested labels the entity's only labels."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a", "b"]))
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["c"], exclusive=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    assert e.value["labels"] == ["c"]
    mock_set.assert_called_once_with(GUID, ["c"])


def test_atlas_entity_label_module_exclusive_is_idempotent_regardless_of_order(
    module_args,
    mocker,
):
    """Test exclusive compares labels as a set."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["b", "a"]))
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["a", "b"], exclusive=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False
    mock_set.assert_not_called()


def test_atlas_entity_label_module_exclusive_with_no_labels_clears_them(
    module_args,
    mocker,
):
    """Test exclusive with an empty list removes every label (POSTing [] clears)."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a"]))
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=[], exclusive=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    assert e.value["labels"] == []
    mock_set.assert_called_once_with(GUID, [])


def test_atlas_entity_label_module_absent_removes_labels(module_args, mocker):
    """Test absent removes only the requested labels, since DELETE bodies are not honoured."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity(["a", "b", "c"]),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["b", "missing"], state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    assert e.value["labels"] == ["a", "c"]
    mock_set.assert_called_once_with(GUID, ["a", "c"])


def test_atlas_entity_label_module_absent_removing_every_label(module_args, mocker):
    """Test removing the last labels sends an empty list."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a"]))
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["a"], state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["labels"] == []
    mock_set.assert_called_once_with(GUID, [])


def test_atlas_entity_label_module_absent_is_idempotent(module_args, mocker):
    """Test absent makes no change when none of the labels are attached."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a"]))
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["b"], state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False
    assert e.value["labels"] == ["a"]
    mock_set.assert_not_called()


def test_atlas_entity_label_module_absent_on_missing_entity_is_a_no_op(
    module_args,
    mocker,
):
    """Test absent succeeds without a change when the entity does not exist."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=None)
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["a"], state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False
    assert e.value["labels"] == []
    assert e.value["guid"] is None
    mock_set.assert_not_called()


def test_atlas_entity_label_module_absent_on_deleted_entity_is_a_no_op(
    module_args,
    mocker,
):
    """Test absent leaves a deleted entity alone, since Atlas keeps its labels as history."""
    mocker.patch(
        f"{CLIENT}.get_entity_by_guid",
        return_value=_entity(["a"], status="DELETED"),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["a"], state="absent"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False
    mock_set.assert_not_called()


@pytest.mark.parametrize(
    "entity",
    [None, _entity(["a"], status="DELETED")],
    ids=["missing", "deleted"],
)
def test_atlas_entity_label_module_present_fails_without_an_active_entity(
    module_args,
    mocker,
    entity,
):
    """Test present fails, and writes nothing, for an entity that is missing or deleted."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=entity)
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels")

    module_args(_args(labels=["a"]))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_label.main()

    assert "active entity" in e.value["msg"]
    mock_set.assert_not_called()


def test_atlas_entity_label_module_by_qualified_name(module_args, mocker):
    """Test the entity is looked up by type and qualified name, then labelled by guid."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(["a"]),
    )
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels")

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "type_name": "test_entity_type",
            "qualified_name": "test_entity_1",
            "labels": ["b"],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["guid"] == GUID
    mock_get.assert_called_once_with(
        "test_entity_type",
        {"qualifiedName": "test_entity_1"},
    )
    mock_set.assert_called_once_with(GUID, ["a", "b"])


def test_atlas_entity_label_module_by_unique_attributes(module_args, mocker):
    """Test unique_attributes are passed through unchanged."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_entity_by_unique_attributes",
        return_value=_entity(["a"]),
    )
    mocker.patch(f"{CLIENT}.set_entity_labels")

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "type_name": "test_entity_type",
            "unique_attributes": {"qualifiedName": "q", "other": "x"},
            "labels": ["a"],
        },
    )

    with pytest.raises(AnsibleExitJson):
        atlas_entity_label.main()

    mock_get.assert_called_once_with(
        "test_entity_type",
        {"qualifiedName": "q", "other": "x"},
    )


def test_atlas_entity_label_module_check_mode_reports_without_writing(
    module_args,
    mocker,
):
    """Test check mode reports the change and the intended labels but makes no write."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a"]))
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["b"], _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    assert e.value["labels"] == ["a", "b"]
    mock_set.assert_not_called()


def test_atlas_entity_label_module_diff_mode(module_args, mocker):
    """Test diff mode reports the labels before and after."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a"]))
    mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["b"], _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["diff"] == {
        "before": {"labels": ["a"]},
        "after": {"labels": ["a", "b"]},
    }


def test_atlas_entity_label_module_diff_mode_without_change(module_args, mocker):
    """Test diff mode reports no difference when nothing changes."""
    mocker.patch(f"{CLIENT}.get_entity_by_guid", return_value=_entity(["a"]))
    mocker.patch(f"{CLIENT}.set_entity_labels", return_value=None)

    module_args(_args(labels=["a"], _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["diff"] == {}


@pytest.mark.parametrize(
    "label",
    ["has space", "dot.ted", "", "semi;colon"],
)
def test_atlas_entity_label_module_invalid_label_fails_before_any_call(
    module_args,
    mocker,
    label,
):
    """Test a label Atlas would reject fails up front, even in check mode."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels")

    module_args(_args(labels=["ok", label], _ansible_check_mode=True))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_label.main()

    assert "label" in e.value["msg"].lower()
    mock_get.assert_not_called()
    mock_set.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"guid": None},
        {"type_name": "t"},
        {"qualified_name": "q"},
        {"type_name": "t", "qualified_name": "q", "unique_attributes": {"a": "b"}},
        {"type_name": "t", "qualified_name": "q"},
        {"labels": None},
    ],
    ids=[
        "nothing",
        "guid-and-type",
        "guid-and-qualified-name",
        "qualified-name-and-unique-attributes",
        "guid-and-type-and-qualified-name",
        "no-labels",
    ],
)
def test_atlas_entity_label_module_invalid_arguments_fail(module_args, mocker, extra):
    """Test an ambiguous identity or missing labels fails before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")
    mock_unique = mocker.patch(f"{CLIENT}.get_entity_by_unique_attributes")
    mock_set = mocker.patch(f"{CLIENT}.set_entity_labels")

    args = _args(labels=["a"])
    args.update(extra)
    module_args({k: v for k, v in args.items() if v is not None})

    with pytest.raises(AnsibleFailJson):
        atlas_entity_label.main()

    mock_get.assert_not_called()
    mock_unique.assert_not_called()
    mock_set.assert_not_called()


def test_atlas_entity_label_module_exclusive_with_absent_fails(module_args, mocker):
    """Test exclusive makes no sense when removing labels, so it is refused."""
    mock_get = mocker.patch(f"{CLIENT}.get_entity_by_guid")

    module_args(_args(labels=["a"], state="absent", exclusive=True))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_label.main()

    assert "exclusive" in e.value["msg"]
    mock_get.assert_not_called()


ENTITY_JSON = {
    "referredEntities": {},
    "entity": {
        "typeName": "test_entity_type",
        "attributes": {"qualifiedName": "test_entity_1"},
        "guid": GUID,
        "status": "ACTIVE",
        "labels": ["a"],
    },
}


def test_atlas_entity_label_module_requests(module_args, mocker):
    """Test the real requests: a GET of the entity, then a POST of the whole label list."""
    calls = []

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        calls.append((method, url, data))
        if method == "GET":
            return http_result(mocker, 200, ENTITY_JSON)
        return http_result(mocker, 204)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(labels=["b"]))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    assert [c[0] for c in calls] == ["GET", "POST"]
    assert calls[1][1].endswith(f"/api/atlas/v2/entity/guid/{GUID}/labels")
    assert calls[1][2] == b'["a", "b"]'


def test_atlas_entity_label_module_atlas_rejects_labels(module_args, mocker):
    """Test an Atlas HTTP 400 on the write fails the module with Atlas's message."""
    message = "Invalid label: a b"

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 200, ENTITY_JSON)
        return http_result(
            mocker,
            400,
            {"errorCode": "ATLAS-400-00-090", "errorMessage": message},
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(labels=["b"]))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_label.main()

    assert message in e.value["msg"]


def test_atlas_entity_label_module_unknown_type_fails(module_args, mocker):
    """Test a mistyped type name fails instead of reading as a missing entity."""

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

    args = _args(type_name="no_such_type", qualified_name="q", labels=["a"])
    del args["guid"]
    module_args(args)

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_label.main()

    assert "does not exist" in e.value["msg"]


@pytest.mark.parametrize("body", [[], {}, {"entity": {"guid": GUID}}])
def test_atlas_entity_label_module_malformed_entity_response_fails(
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

    module_args(_args(labels=["a"]))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_label.main()

    assert "unexpected" in e.value["msg"]
    assert calls == ["GET"]


def test_atlas_entity_label_module_forbidden_fails(module_args, mocker):
    """Test an authorization failure fails the module."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 403, {"errorMessage": "denied"})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(labels=["a"]))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_label.main()

    assert "Forbidden" in e.value["msg"]
