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

from dataclasses import replace

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_runtime_repo
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlRuntimeRepo

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"

REPOS = "ansible_collections.cloudera.services.plugins.modules.ml_runtime_repo.MlRuntimeRepoClient"

EXISTING = MlRuntimeRepo(id=1, name="internal", url="https://repo.example.com/a")


def _base_args(overrides=None):
    args = {"url": BASE_URL, "api_key": API_KEY}
    if overrides:
        args.update(overrides)
    return args


def test_create(module_args, mocker):
    """A new repo is created."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[])
    mock_create = mocker.patch(
        f"{REPOS}.create_runtime_repo",
        return_value=MlRuntimeRepo(id=2, name="new", url="https://repo.example.com/b"),
    )

    module_args(_base_args({"name": "new", "repo_url": "https://repo.example.com/b"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    assert e.value["changed"] is True
    assert e.value["runtime_repo"]["id"] == 2
    _, repo_arg = (mock_create.call_args.args, mock_create.call_args.args[0])
    assert repo_arg.name == "new"
    assert repo_arg.url == "https://repo.example.com/b"


def test_create_missing_url(module_args, mocker):
    """Creating without a url fails."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[])
    mock_create = mocker.patch(f"{REPOS}.create_runtime_repo")

    module_args(_base_args({"name": "new"}))

    with pytest.raises(AnsibleFailJson, match="Missing required parameters"):
        ml_runtime_repo.main()

    mock_create.assert_not_called()


def test_present_idempotent(module_args, mocker):
    """No change means no update."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[EXISTING])
    mock_update = mocker.patch(f"{REPOS}.update_runtime_repo")

    module_args(
        _base_args({"name": "internal", "repo_url": "https://repo.example.com/a"}),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_update_url(module_args, mocker):
    """A changed url triggers an update."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[EXISTING])
    mock_update = mocker.patch(
        f"{REPOS}.update_runtime_repo",
        return_value=replace(EXISTING, url="https://repo.example.com/c"),
    )

    module_args(
        _base_args({"name": "internal", "repo_url": "https://repo.example.com/c"}),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    assert e.value["changed"] is True
    repo_arg = mock_update.call_args.args[0]
    assert repo_arg.url == "https://repo.example.com/c"
    assert repo_arg.id == 1


def test_absent_existing(module_args, mocker):
    """Deleting an existing repo removes it."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[EXISTING])
    mock_delete = mocker.patch(f"{REPOS}.delete_runtime_repo")

    module_args(_base_args({"id": 1, "state": "absent"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    assert e.value["changed"] is True
    assert e.value["runtime_repo"] == {}
    mock_delete.assert_called_once_with(1)


def test_absent_missing(module_args, mocker):
    """Deleting a non-existent repo is a no-op."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[])
    mock_delete = mocker.patch(f"{REPOS}.delete_runtime_repo")

    module_args(_base_args({"id": 99, "state": "absent"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_by_id_lookup(module_args, mocker):
    """A repo can be addressed by id."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[EXISTING])
    mock_update = mocker.patch(f"{REPOS}.update_runtime_repo")

    module_args(_base_args({"id": 1, "repo_url": "https://repo.example.com/a"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    # url unchanged -> idempotent
    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_check_mode_create(module_args, mocker):
    """Check mode reports change but does not create."""
    mocker.patch(f"{REPOS}.list_runtime_repos", return_value=[])
    mock_create = mocker.patch(f"{REPOS}.create_runtime_repo")

    module_args(
        _base_args(
            {
                "name": "new",
                "repo_url": "https://repo.example.com/b",
                "_ansible_check_mode": True,
            },
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()
