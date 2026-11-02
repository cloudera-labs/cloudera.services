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
import uuid
from typing import Optional

import pytest

from ansible_collections.cloudera.services.plugins.modules import atlas_entity_label
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


def test_atlas_entity_label_module_add_labels(
    atlas_module_args,
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test labels are added to an entity, and a repeat run changes nothing."""
    guid = atlas_deletable_entity.guid

    atlas_module_args({"guid": guid, "labels": ["ansible-one", "two_2"]})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    assert isinstance(entity.labels, list)
    assert set(entity.labels) == {"ansible-one", "two_2"}

    atlas_module_args({"guid": guid, "labels": ["ansible-one", "two_2"]})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False


def test_atlas_entity_label_module_by_qualified_name(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_deletable_entity,
):
    """Test the entity can be identified by type and qualified name."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": atlas_deletable_entity.attributes["qualifiedName"],
            "labels": ["byname"],
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == atlas_deletable_entity.guid
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert entity.labels == ["byname"]


def test_atlas_entity_label_module_keeps_existing_labels(
    atlas_module_args,
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test a present run adds to the existing labels instead of replacing them."""
    guid = atlas_deletable_entity.guid

    atlas_module_args({"guid": guid, "labels": ["first"]})
    with pytest.raises(AnsibleExitJson):
        atlas_entity_label.main()

    atlas_module_args({"guid": guid, "labels": ["second"]})
    with pytest.raises(AnsibleExitJson):
        atlas_entity_label.main()

    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    assert isinstance(entity.labels, list)
    assert set(entity.labels) == {"first", "second"}


def test_atlas_entity_label_module_exclusive(
    atlas_module_args,
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test exclusive replaces the labels, and an empty list clears them."""
    guid = atlas_deletable_entity.guid

    atlas_module_args({"guid": guid, "labels": ["a", "b"]})
    with pytest.raises(AnsibleExitJson):
        atlas_entity_label.main()

    atlas_module_args({"guid": guid, "labels": ["c"], "exclusive": True})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    assert entity.labels == ["c"]

    atlas_module_args({"guid": guid, "labels": [], "exclusive": True})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    assert not entity.labels


def test_atlas_entity_label_module_remove_labels(
    atlas_module_args,
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test absent removes only the named labels, and a repeat run changes nothing."""
    guid = atlas_deletable_entity.guid

    atlas_module_args({"guid": guid, "labels": ["a", "b", "c"]})
    with pytest.raises(AnsibleExitJson):
        atlas_entity_label.main()

    atlas_module_args({"guid": guid, "labels": ["b"], "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    assert isinstance(entity.labels, list)
    assert set(entity.labels) == {"a", "c"}

    atlas_module_args({"guid": guid, "labels": ["b"], "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False


def test_atlas_entity_label_module_check_mode(
    atlas_module_args,
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test check mode reports a change but leaves the labels alone."""
    atlas_module_args(
        {
            "guid": atlas_deletable_entity.guid,
            "labels": ["checkonly"],
            "_ansible_check_mode": True,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is True
    entity = atlas_entity_client.get_entity_by_guid(atlas_deletable_entity.guid)
    assert entity is not None
    assert not entity.labels


def test_atlas_entity_label_module_missing_entity(atlas_module_args, atlas_entity_type):
    """Test present fails and absent succeeds for an entity that does not exist."""
    qualified_name = f"ansible_test_missing_{uuid.uuid4().hex}"

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": qualified_name,
            "labels": ["a"],
        },
    )
    with pytest.raises(AnsibleFailJson):
        atlas_entity_label.main()

    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": qualified_name,
            "labels": ["a"],
            "state": "absent",
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False


def test_atlas_entity_label_module_deleted_entity(
    atlas_module_args,
    atlas_entity_client,
    atlas_deletable_entity,
):
    """Test present refuses a deleted entity (still visible by guid) and absent leaves it."""
    guid = atlas_deletable_entity.guid
    atlas_entity_client.delete_entity_by_guid(guid)

    atlas_module_args({"guid": guid, "labels": ["a"]})
    with pytest.raises(AnsibleFailJson):
        atlas_entity_label.main()

    atlas_module_args({"guid": guid, "labels": ["a"], "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_label.main()

    assert e.value["changed"] is False


def test_atlas_entity_label_module_invalid_label_fails(
    atlas_module_args,
    atlas_deletable_entity,
):
    """Test a label with a character Atlas rejects fails the module."""
    atlas_module_args({"guid": atlas_deletable_entity.guid, "labels": ["not valid!"]})

    with pytest.raises(AnsibleFailJson):
        atlas_entity_label.main()
