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

from ansible_collections.cloudera.services.plugins.modules import ml_project
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlProject

BASE_URL = "https://ml.cloudera.internal"
API_KEY = "SECRET"

CLIENT = (
    "ansible_collections.cloudera.services.plugins.modules.ml_project.MlProjectClient"
)

EXISTING = MlProject(
    id="aaaa-bbbb-cccc-dddd",
    name="test-project",
    description="Original",
    visibility="private",
)


def _creds(extra):
    return {"url": BASE_URL, "api_key": API_KEY, **extra}


def test_missing_required(module_args, monkeypatch):
    """Absent url/api_key (and no env fallback) fails."""
    monkeypatch.delenv("CML_ENDPOINT", raising=False)
    monkeypatch.delenv("CML_API_KEY", raising=False)
    module_args({"name": "x"})

    with pytest.raises(AnsibleFailJson) as e:
        ml_project.main()

    assert "api_key" in e.value.msg or "url" in e.value.msg


def test_create_by_name(module_args, mocker):
    mock_list = mocker.patch(f"{CLIENT}.list_projects", return_value=[])
    mock_create = mocker.patch(
        f"{CLIENT}.create_project",
        return_value=MlProject(id="new-1234-5678-9abc", name="brand-new"),
    )

    module_args(_creds({"name": "brand-new", "state": "present"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    result = e.value
    assert result["changed"] is True
    assert result["project"]["name"] == "brand-new"
    mock_list.assert_called_once()
    mock_create.assert_called_once()


def test_create_check_mode(module_args, mocker):
    mocker.patch(f"{CLIENT}.list_projects", return_value=[])
    mock_create = mocker.patch(f"{CLIENT}.create_project")

    module_args(_creds({"name": "brand-new", "_ansible_check_mode": True}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()


def test_present_noop(module_args, mocker):
    """An existing project with no changes reports changed=False."""
    mocker.patch(f"{CLIENT}.list_projects", return_value=[EXISTING])
    mock_update = mocker.patch(f"{CLIENT}.update_project")

    module_args(_creds({"name": "test-project", "desc": "Original"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_update_description(module_args, mocker):
    mocker.patch(f"{CLIENT}.list_projects", return_value=[EXISTING])
    mock_update = mocker.patch(
        f"{CLIENT}.update_project",
        return_value=MlProject(
            id=EXISTING.id,
            name="test-project",
            description="Updated",
        ),
    )

    module_args(_creds({"name": "test-project", "desc": "Updated"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    assert e.value["changed"] is True
    mock_update.assert_called_once()


def test_absent_by_id(module_args, mocker):
    mocker.patch(f"{CLIENT}.describe_project", return_value=EXISTING)
    mock_delete = mocker.patch(f"{CLIENT}.delete_project")

    module_args(_creds({"id": "aaaa-bbbb-cccc-dddd", "state": "absent"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    assert e.value["changed"] is True
    mock_delete.assert_called_once_with("aaaa-bbbb-cccc-dddd")


def test_absent_missing_noop(module_args, mocker):
    mocker.patch(f"{CLIENT}.describe_project", return_value=None)
    mock_delete = mocker.patch(f"{CLIENT}.delete_project")

    module_args(_creds({"id": "aaaa-bbbb-cccc-dddd", "state": "absent"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_template_git_requires_git(module_args, mocker):
    """template=git without a git URL fails the argument spec check."""
    mocker.patch(f"{CLIENT}.list_projects", return_value=[])

    module_args(_creds({"name": "git-project", "template": "git"}))

    with pytest.raises(AnsibleFailJson) as e:
        ml_project.main()

    assert "git" in e.value.msg


def test_template_git_with_git_ok(module_args, mocker):
    """template=git with a git URL passes the argument spec check."""
    mocker.patch(f"{CLIENT}.list_projects", return_value=[])
    mock_create = mocker.patch(
        f"{CLIENT}.create_project",
        return_value=MlProject(id="new-1234-5678-9abc", name="git-project"),
    )

    module_args(
        _creds(
            {
                "name": "git-project",
                "template": "git",
                "git": "https://github.com/example/repo.git",
            },
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project.main()

    assert e.value["changed"] is True
    mock_create.assert_called_once()


def test_invalid_project_id(module_args, mocker):
    mocker.patch(f"{CLIENT}.describe_project", return_value=None)

    module_args(_creds({"id": "not-a-valid-id", "state": "present"}))

    with pytest.raises(AnsibleFailJson) as e:
        ml_project.main()

    assert "Invalid Project ID" in e.value.msg
