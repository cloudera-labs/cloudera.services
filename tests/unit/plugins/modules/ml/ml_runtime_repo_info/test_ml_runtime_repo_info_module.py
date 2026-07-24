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
)

from ansible_collections.cloudera.services.plugins.modules import ml_runtime_repo_info
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlRuntimeRepo

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"

REPOS = "ansible_collections.cloudera.services.plugins.modules.ml_runtime_repo_info.MlRuntimeRepoClient"

REPO_ONE = MlRuntimeRepo(id=1, name="internal", url="https://repo.example.com/a")
REPO_TWO = MlRuntimeRepo(id=2, name="external", url="https://repo.example.com/b")


def _base_args(overrides=None):
    args = {"url": BASE_URL, "api_key": API_KEY}
    if overrides:
        args.update(overrides)
    return args


def test_list_all(module_args, mocker):
    """All repos are returned when no filter is given."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[REPO_ONE, REPO_TWO])

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo_info.main()

    assert e.value["changed"] is False
    assert len(e.value["runtime_repos"]) == 2


def test_filter_by_name(module_args, mocker):
    """Repos can be filtered by name."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[REPO_ONE, REPO_TWO])

    module_args(_base_args({"name": "external"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo_info.main()

    repos = e.value["runtime_repos"]
    assert len(repos) == 1
    assert repos[0]["id"] == 2


def test_filter_by_id(module_args, mocker):
    """Repos can be filtered by id."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[REPO_ONE, REPO_TWO])

    module_args(_base_args({"id": 1}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo_info.main()

    repos = e.value["runtime_repos"]
    assert len(repos) == 1
    assert repos[0]["name"] == "internal"


def test_filter_no_match(module_args, mocker):
    """A non-matching filter returns no repos."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[REPO_ONE, REPO_TWO])

    module_args(_base_args({"name": "ghost"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo_info.main()

    assert e.value["runtime_repos"] == []
