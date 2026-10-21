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
    atlas_relationship_def,
)
from ansible_collections.cloudera.services.tests.unit import AnsibleExitJson

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


def test_atlas_relationship_def_module_create_idempotent(
    request,
    atlas_module_args,
    atlas_relationship_end_types,
    atlas_purge_typedef,
):
    """Test create, then an identical re-run reports no change (end defaults)."""
    parent, child = atlas_relationship_end_types
    name = f"ansible_test_module_{request.node.name.lower()}"

    atlas_purge_typedef(name)

    args = {
        "name": name,
        "relationship_category": "ASSOCIATION",
        "propagate_tags": "NONE",
        "end_def1": {"type": parent, "name": "ansible_test_children"},
        "end_def2": {"type": child, "name": "ansible_test_parent"},
    }

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()
    assert e.value["changed"] is True
    assert e.value["relationship_def"]["guid"] is not None

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()
    assert e.value["changed"] is False


def test_atlas_relationship_def_module_change_propagate_tags(
    atlas_module_args,
    atlas_deletable_relationship_def,
):
    """Test changing tag propagation updates the relationship."""
    atlas_module_args(
        {
            "name": atlas_deletable_relationship_def.name,
            "propagate_tags": "ONE_TO_TWO",
        },
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()

    assert e.value["changed"] is True
    assert e.value["relationship_def"]["propagate_tags"] == "ONE_TO_TWO"


def test_atlas_relationship_def_module_absent(
    atlas_module_args,
    atlas_typedef_client,
    atlas_deletable_relationship_def,
):
    """Test absent deletes the relationship, then is a no-op."""
    args = {"name": atlas_deletable_relationship_def.name, "state": "absent"}

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()
    assert e.value["changed"] is True
    assert (
        atlas_typedef_client.get_relationship_def_by_name(
            atlas_deletable_relationship_def.name,
        )
        is None
    )

    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_relationship_def.main()
    assert e.value["changed"] is False
