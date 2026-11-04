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
import os
from typing import Optional

import pytest

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_entity_business_metadata,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
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


def _business_attributes(atlas_entity_client, guid, name):
    entity = atlas_entity_client.get_entity_by_guid(guid)
    assert entity is not None
    # Atlas omits businessAttributes once the last business metadata is removed
    business = entity.business_attributes
    return business.get(name) if isinstance(business, dict) else None


def test_atlas_entity_business_metadata_module_set_attributes(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test attributes are set on an entity, and a repeat run changes nothing."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_business_metadata_def.name
    args = {
        "guid": guid,
        "name": name,
        "attributes": {"owner_name": "alice", "rank": 3, "reviewed": True},
    }

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == guid
    assert e.value["business_metadata"] == {
        "owner_name": "alice",
        "rank": 3,
        "reviewed": True,
    }
    assert _business_attributes(atlas_entity_client, guid, name) == {
        "owner_name": "alice",
        "rank": 3,
        "reviewed": True,
    }

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False


def test_atlas_entity_business_metadata_module_string_values_are_idempotent(
    atlas_module_args,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test "3" for an int attribute, which Atlas stores as 3, is not reported as a change on a repeat run."""
    args = {
        "guid": atlas_deletable_entity.guid,
        "name": atlas_entity_business_metadata_def.name,
        "attributes": {"rank": "3", "reviewed": "true"},
    }

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {"rank": 3, "reviewed": True}

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False


def test_atlas_entity_business_metadata_module_by_qualified_name(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_type,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test the entity can be identified by type and qualified name."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": atlas_deletable_entity.attributes["qualifiedName"],
            "name": atlas_entity_business_metadata_def.name,
            "attributes": {"owner_name": "byname"},
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["guid"] == atlas_deletable_entity.guid
    assert _business_attributes(
        atlas_entity_client,
        atlas_deletable_entity.guid,
        atlas_entity_business_metadata_def.name,
    ) == {"owner_name": "byname"}


def test_atlas_entity_business_metadata_module_keeps_other_attributes(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test a present run changes only the listed attributes and keeps the rest."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_business_metadata_def.name

    atlas_module_args(
        {"guid": guid, "name": name, "attributes": {"owner_name": "alice", "rank": 1}},
    )
    with pytest.raises(AnsibleExitJson):
        atlas_entity_business_metadata.main()

    atlas_module_args({"guid": guid, "name": name, "attributes": {"rank": 2}})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {"owner_name": "alice", "rank": 2}
    assert _business_attributes(atlas_entity_client, guid, name) == {
        "owner_name": "alice",
        "rank": 2,
    }


def test_atlas_entity_business_metadata_module_keeps_other_business_metadata(
    atlas_module_args,
    atlas_entity_client,
    atlas_typedef_client,
    atlas_purge_typedef,
    atlas_entity_type,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test setting one business metadata leaves the entity's other business metadata alone (isOverwrite is never sent)."""
    guid = atlas_deletable_entity.guid
    first = atlas_entity_business_metadata_def.name
    second = atlas_purge_typedef(f"{first}_two", force=True)
    atlas_typedef_client.create_business_metadata_def(
        AtlasBusinessMetadataDef(
            name=second,
            attribute_defs=[
                AtlasAttributeDef(
                    name="owner_name",
                    type_name="string",
                    is_optional=True,
                    options={
                        "applicableEntityTypes": json.dumps([atlas_entity_type.name]),
                        "maxStrLength": "50",
                    },
                ),
            ],
        ),
    )

    for name, owner in ((first, "alice"), (second, "bob")):
        atlas_module_args(
            {"guid": guid, "name": name, "attributes": {"owner_name": owner}},
        )
        with pytest.raises(AnsibleExitJson):
            atlas_entity_business_metadata.main()

    assert _business_attributes(atlas_entity_client, guid, first) == {
        "owner_name": "alice",
    }
    assert _business_attributes(atlas_entity_client, guid, second) == {
        "owner_name": "bob",
    }


def test_atlas_entity_business_metadata_module_absent_removes_business_metadata(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test absent removes the whole business metadata, and a repeat run changes nothing."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_business_metadata_def.name

    atlas_module_args(
        {"guid": guid, "name": name, "attributes": {"owner_name": "alice", "rank": 1}},
    )
    with pytest.raises(AnsibleExitJson):
        atlas_entity_business_metadata.main()

    atlas_module_args({"guid": guid, "name": name, "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {}
    assert _business_attributes(atlas_entity_client, guid, name) is None

    atlas_module_args({"guid": guid, "name": name, "state": "absent"})
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False


def test_atlas_entity_business_metadata_module_check_mode_makes_no_change(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test check mode reports the change without writing it."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_business_metadata_def.name

    atlas_module_args(
        {
            "guid": guid,
            "name": name,
            "attributes": {"owner_name": "alice"},
            "_ansible_check_mode": True,
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is True
    assert e.value["business_metadata"] == {"owner_name": "alice"}
    assert _business_attributes(atlas_entity_client, guid, name) is None


def test_atlas_entity_business_metadata_module_unknown_attribute_fails(
    atlas_module_args,
    atlas_entity_client,
    atlas_entity_business_metadata_def,
    atlas_deletable_entity,
):
    """Test an attribute the typedef lacks fails, where Atlas alone would silently ignore it."""
    guid = atlas_deletable_entity.guid
    name = atlas_entity_business_metadata_def.name

    atlas_module_args(
        {"guid": guid, "name": name, "attributes": {"no_such_attribute": "x"}},
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "no_such_attribute" in e.value["msg"]
    assert _business_attributes(atlas_entity_client, guid, name) is None


def test_atlas_entity_business_metadata_module_unknown_business_metadata_fails(
    atlas_module_args,
    atlas_deletable_entity,
):
    """Test a business metadata with no typedef fails."""
    atlas_module_args(
        {
            "guid": atlas_deletable_entity.guid,
            "name": "ansible_test_no_such_business_metadata",
            "attributes": {"owner_name": "alice"},
        },
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "does not exist" in e.value["msg"]


def test_atlas_entity_business_metadata_module_not_applicable_to_type_fails(
    atlas_module_args,
    atlas_deletable_entity,
    atlas_deletable_business_metadata_def,
):
    """Test Atlas's refusal of a business metadata that does not apply to the entity's type fails the module."""
    atlas_module_args(
        {
            "guid": atlas_deletable_entity.guid,
            "name": atlas_deletable_business_metadata_def.name,
            "attributes": {"owner": "alice"},
        },
    )
    with pytest.raises(AnsibleFailJson):
        atlas_entity_business_metadata.main()


def test_atlas_entity_business_metadata_module_present_fails_for_missing_entity(
    atlas_module_args,
    atlas_entity_type,
    atlas_entity_business_metadata_def,
):
    """Test present fails when no such entity exists."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": "ansible_test_no_such_entity",
            "name": atlas_entity_business_metadata_def.name,
            "attributes": {"owner_name": "alice"},
        },
    )
    with pytest.raises(AnsibleFailJson) as e:
        atlas_entity_business_metadata.main()

    assert "active entity" in e.value["msg"]


def test_atlas_entity_business_metadata_module_absent_on_missing_entity_is_a_no_op(
    atlas_module_args,
    atlas_entity_type,
    atlas_entity_business_metadata_def,
):
    """Test absent makes no change when no such entity exists."""
    atlas_module_args(
        {
            "type_name": atlas_entity_type.name,
            "qualified_name": "ansible_test_no_such_entity",
            "name": atlas_entity_business_metadata_def.name,
            "state": "absent",
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_entity_business_metadata.main()

    assert e.value["changed"] is False
    assert e.value["guid"] is None
