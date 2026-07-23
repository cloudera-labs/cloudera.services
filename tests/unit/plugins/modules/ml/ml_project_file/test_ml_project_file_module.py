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

from ansible_collections.cloudera.services.plugins.modules import ml_project_file
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlFile,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_file.MlProjectClient"
FILES = "ansible_collections.cloudera.services.plugins.modules.ml_project_file.MlProjectFileClient"


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def test_create_file(module_args, mocker):
    """A missing file is uploaded."""
    _mock_project(mocker)
    mocker.patch(f"{FILES}.list_files", return_value=[])
    mock_upload = mocker.patch(f"{FILES}.upload_file")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "app.py",
            "content": "print(1)",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    result = e.value
    assert result["changed"] is True
    assert result["file"]["path"] == "app.py"
    mock_upload.assert_called_once_with(
        PROJECT_ID,
        "app.py",
        content="print(1)",
        src=None,
    )


def test_create_nested_checks_parent(module_args, mocker):
    """Existence for a nested path is checked against its parent directory."""
    _mock_project(mocker)
    mock_list = mocker.patch(f"{FILES}.list_files", return_value=[])
    mocker.patch(f"{FILES}.upload_file")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "src/run.py",
            "content": "x",
        },
    )

    with pytest.raises(AnsibleExitJson):
        ml_project_file.main()

    mock_list.assert_called_once_with(PROJECT_ID, "src")


def test_idempotent_when_exists(module_args, mocker):
    """An existing file is not re-uploaded without force."""
    _mock_project(mocker)
    mocker.patch(f"{FILES}.list_files", return_value=[MlFile(path="app.py")])
    mock_upload = mocker.patch(f"{FILES}.upload_file")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "app.py",
            "content": "print(1)",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is False
    mock_upload.assert_not_called()


def test_force_reupload(module_args, mocker):
    """force re-uploads an existing file."""
    _mock_project(mocker)
    mocker.patch(f"{FILES}.list_files", return_value=[MlFile(path="app.py")])
    mock_upload = mocker.patch(f"{FILES}.upload_file")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "app.py",
            "content": "print(1)",
            "force": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is True
    mock_upload.assert_called_once()


def test_present_requires_content_or_src(module_args, mocker):
    """Uploading a missing file without src/content fails."""
    _mock_project(mocker)
    mocker.patch(f"{FILES}.list_files", return_value=[])
    mock_upload = mocker.patch(f"{FILES}.upload_file")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "app.py",
        },
    )

    with pytest.raises(AnsibleFailJson, match="src' or 'content"):
        ml_project_file.main()

    mock_upload.assert_not_called()


def test_check_mode_create(module_args, mocker):
    """Check mode reports change but does not upload."""
    _mock_project(mocker)
    mocker.patch(f"{FILES}.list_files", return_value=[])
    mock_upload = mocker.patch(f"{FILES}.upload_file")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "app.py",
            "content": "x",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is True
    mock_upload.assert_not_called()


def test_absent_existing(module_args, mocker):
    """Deleting an existing file removes it."""
    _mock_project(mocker)
    mocker.patch(f"{FILES}.list_files", return_value=[MlFile(path="app.py")])
    mock_delete = mocker.patch(f"{FILES}.delete_file")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "app.py",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is True
    mock_delete.assert_called_once_with(PROJECT_ID, "app.py")


def test_absent_missing(module_args, mocker):
    """Deleting a non-existent file is a no-op."""
    _mock_project(mocker)
    mocker.patch(f"{FILES}.list_files", return_value=[])
    mock_delete = mocker.patch(f"{FILES}.delete_file")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "ghost.py",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": "not-valid",
            "path": "app.py",
            "content": "x",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_file.main()


def test_src_and_content_mutually_exclusive(module_args, mocker):
    """src and content cannot both be supplied."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "path": "app.py",
            "src": "/tmp/x",
            "content": "x",
        },
    )

    with pytest.raises(AnsibleFailJson, match="mutually exclusive"):
        ml_project_file.main()
