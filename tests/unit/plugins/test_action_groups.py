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

from pathlib import Path

import pytest
import yaml

COLLECTION_ROOT = Path(__file__).resolve().parents[3]

# Action groups named after the module prefix, so every `<prefix>_*` module
# must be listed in the `<prefix>` group of meta/runtime.yml.
CHECKED_GROUPS = ["ranger", "atlas"]


@pytest.fixture(scope="module")
def action_groups():
    runtime = yaml.safe_load((COLLECTION_ROOT / "meta" / "runtime.yml").read_text())
    return runtime["action_groups"]


@pytest.mark.parametrize("prefix", CHECKED_GROUPS)
def test_action_group_lists_every_module(action_groups, prefix):
    """Test each module with the group's prefix is in its action group."""
    modules = {
        path.stem
        for path in (COLLECTION_ROOT / "plugins" / "modules").glob(f"{prefix}_*.py")
    }

    assert modules, f"no modules found for prefix '{prefix}'"
    assert sorted(modules - set(action_groups[prefix])) == []


@pytest.mark.parametrize("prefix", CHECKED_GROUPS)
def test_action_group_lists_only_existing_modules(action_groups, prefix):
    """Test each action group entry has a module behind it."""
    modules = {
        path.stem for path in (COLLECTION_ROOT / "plugins" / "modules").glob("*.py")
    }

    assert sorted(set(action_groups[prefix]) - modules) == []
