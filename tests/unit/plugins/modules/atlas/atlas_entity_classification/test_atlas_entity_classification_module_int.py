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

import os
from typing import Optional

import pytest

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_entity_classification,
)
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]


@pytest.fixture
def atlas_module_args(module_args, env_context):
    """Fixture to set common module args for Atlas tests."""

    def _atlas_module_args(overrides: Optional[dict] = None) -> None:
        overrides = overrides or {}
        args = {
            "url": env_context["ATLAS_API_URL"],
            "url_username": env_context["ATLAS_API_USERNAME"],
            "url_password": env_context["ATLAS_API_PASSWORD"],
            "force_basic_auth": True,
            "validate_certs": os.environ.get("ATLAS_VALIDATE_CERTS", "false").lower()
            == "true",
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _atlas_module_args


def _attached(atlas_entity_client, guid, name):
    """The named classification attached directly to the entity, or None."""
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    # Atlas omits classifications once the last one is removed
    classifications = (
        entity.classifications if isinstance(entity.classifications, list) else []
    )
    for classification in classifications:
        origin = classification.entity_guid
        if classification.type_name == name and (
            not isinstance(origin, str) or origin in ("", guid)
        ):
            return classification
    return None


def test_atlas_entity_classification_module_attach(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test a classification is attached with its attributes, and a repeat run changes nothing."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_classification_def.name
    args = {"guid": guid, "name": name, "attributes": {"level": "high", "rank": 2}}

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == guid
    assert e.value["classification"]["type_name"] == name
    assert e.value["classification"]["attributes"]["level"] == "high"
    assert e.value["classification"]["attributes"]["rank"] == 2
    attached = _attached(atlas_entity_client, guid, name)
    assert attached is not None
    assert isinstance(attached.attributes, dict)
    assert attached.attributes["level"] == "high"
    assert attached.attributes["rank"] == 2

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False


def test_atlas_entity_classification_module_attach_with_only_a_name(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test a classification with no other option gets Atlas's defaults (propagate true, no removal on delete)."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_classification_def.name

    atlas_module_args({"guid": guid, "name": name})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"]["propagate"] is True
    assert e.value["classification"]["remove_propagations_on_entity_delete"] is False
    assert _attached(atlas_entity_client, guid, name) is not None

    atlas_module_args({"guid": guid, "name": name})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False


def test_atlas_entity_classification_module_string_values_are_idempotent(
    atlas_module_args,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test "2" for an int attribute, which Atlas stores as 2, is not reported as a change on a repeat run."""
    args = {
        "guid": atlas_deletable_entity.guid,
        "name": atlas_entity_classification_def.name,
        "attributes": {"rank": "2"},
    }

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"]["attributes"]["rank"] == 2

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False


def test_atlas_entity_classification_module_by_qualified_name(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test the entity can be identified by type and qualified name."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": atlas_deletable_entity.attributes["qualifiedName"],
            "name": atlas_entity_classification_def.name,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == atlas_deletable_entity.guid
    assert (
        _attached(
            atlas_entity_client,
            atlas_deletable_entity.guid,
            atlas_entity_classification_def.name,
        )
        is not None
    )


def test_atlas_entity_classification_module_inherited_attribute(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test an attribute inherited from a super type is accepted, and kept when the classification is updated."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_classification_def.name

    atlas_module_args(
        {"guid": guid, "name": name, "attributes": {"inherited": "from-parent"}},
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True

    atlas_module_args({"guid": guid, "name": name, "attributes": {"level": "low"}})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    attached = _attached(atlas_entity_client, guid, name)
    assert attached is not None
    assert isinstance(attached.attributes, dict)
    assert attached.attributes["inherited"] == "from-parent"
    assert attached.attributes["level"] == "low"


def test_atlas_entity_classification_module_update_keeps_other_attributes(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test an update changes only the listed attributes and keeps the rest."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_classification_def.name

    atlas_module_args(
        {"guid": guid, "name": name, "attributes": {"level": "low", "rank": 1}},
    )
    with pytest.raises(AnsibleExitJson):
        atlas_entity_classification.main()

    atlas_module_args({"guid": guid, "name": name, "attributes": {"rank": 2}})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    attached = _attached(atlas_entity_client, guid, name)
    assert attached is not None
    assert isinstance(attached.attributes, dict)
    assert attached.attributes["level"] == "low"
    assert attached.attributes["rank"] == 2


def test_atlas_entity_classification_module_update_propagation(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test the propagation flags are changed without touching the attributes."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_classification_def.name

    atlas_module_args({"guid": guid, "name": name, "attributes": {"level": "low"}})
    with pytest.raises(AnsibleExitJson):
        atlas_entity_classification.main()

    atlas_module_args(
        {
            "guid": guid,
            "name": name,
            "propagate": False,
            "remove_propagations_on_entity_delete": True,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    attached = _attached(atlas_entity_client, guid, name)
    assert attached is not None
    assert attached.propagate is False
    assert attached.remove_propagations_on_entity_delete is True
    assert isinstance(attached.attributes, dict)
    assert attached.attributes["level"] == "low"

    atlas_module_args(
        {
            "guid": guid,
            "name": name,
            "propagate": False,
            "remove_propagations_on_entity_delete": True,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False


def test_atlas_entity_classification_module_absent_removes_classification(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test absent removes the classification, and a repeat run changes nothing."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_classification_def.name

    atlas_module_args({"guid": guid, "name": name, "attributes": {"level": "low"}})
    with pytest.raises(AnsibleExitJson):
        atlas_entity_classification.main()

    atlas_module_args({"guid": guid, "name": name, "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"] == {}
    assert _attached(atlas_entity_client, guid, name) is None

    atlas_module_args({"guid": guid, "name": name, "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False


def test_atlas_entity_classification_module_check_mode_makes_no_change(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test check mode reports the change without writing it."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_classification_def.name

    atlas_module_args(
        {
            "guid": guid,
            "name": name,
            "attributes": {"level": "high"},
            "_ansible_check_mode": True,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is True
    assert e.value["classification"]["attributes"] == {"level": "high"}
    assert _attached(atlas_entity_client, guid, name) is None


def test_atlas_entity_classification_module_unknown_attribute_fails(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_classification_def,
    atlas_deletable_entity,
):
    """Test an attribute the typedef lacks fails, where Atlas alone would silently ignore it."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_classification_def.name

    atlas_module_args(
        {"guid": guid, "name": name, "attributes": {"no_such_attribute": "x"}},
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "no_such_attribute" in e.value["msg"]
    assert _attached(atlas_entity_client, guid, name) is None


def test_atlas_entity_classification_module_unknown_classification_fails(
    atlas_module_args,
    atlas_deletable_entity,
):
    """Test a classification with no typedef fails."""
    atlas_module_args(
        {
            "guid": atlas_deletable_entity.guid,
            "name": "ansible_test_no_such_classification",
        },
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "does not exist" in e.value["msg"]


def test_atlas_entity_classification_module_present_fails_for_missing_entity(
    atlas_module_args,
    atlas_entity_type,
    atlas_entity_classification_def,
):
    """Test present fails when no such entity exists."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": "ansible_test_no_such_entity",
            "name": atlas_entity_classification_def.name,
        },
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_classification.main()

    assert "active entity" in e.value["msg"]


def test_atlas_entity_classification_module_absent_on_missing_entity_is_a_no_op(
    atlas_module_args,
    atlas_entity_type,
    atlas_entity_classification_def,
):
    """Test absent makes no change when no such entity exists."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": "ansible_test_no_such_entity",
            "name": atlas_entity_classification_def.name,
            "state": "absent",
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_classification.main()

    assert e.value["changed"] is False
    assert e.value["guid"] is None
