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

from ansible_collections.cloudera.services.plugins.modules import ml_project_file_info
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlFile,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_file_info.MlProjectClient"
FILES = "ansible_collections.cloudera.services.plugins.modules.ml_project_file_info.MlProjectFileClient"


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def test_list_root(module_args, mocker):
    """List files at the project root by default."""
    _mock_project(mocker)
    mock_list = mocker.patch(
        f"{FILES}.list_files",
        return_value=[
            MlFile(path="app.py", is_dir=False),
            MlFile(path="src", is_dir=True),
        ],
    )

    module_args({"url": BASE_URL, "api_key": API_KEY, "project_name": "proj"})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["files"]) == 2
    mock_list.assert_called_once_with(PROJECT_ID, "")


def test_list_subdir(module_args, mocker):
    """List files within a subdirectory."""
    _mock_project(mocker)
    mock_list = mocker.patch(
        f"{FILES}.list_files",
        return_value=[MlFile(path="src/run.py", is_dir=False)],
    )

    module_args(
        {"url": BASE_URL, "api_key": API_KEY, "project_name": "proj", "path": "src"},
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file_info.main()

    result = e.value
    assert len(result["files"]) == 1
    assert result["files"][0]["path"] == "src/run.py"
    mock_list.assert_called_once_with(PROJECT_ID, "src")


def test_leading_slash_normalized(module_args, mocker):
    """A leading slash on the path is stripped."""
    _mock_project(mocker)
    mock_list = mocker.patch(f"{FILES}.list_files", return_value=[])

    module_args(
        {"url": BASE_URL, "api_key": API_KEY, "project_name": "proj", "path": "/src"},
    )

    with pytest.raises(AnsibleExitJson):
        ml_project_file_info.main()

    mock_list.assert_called_once_with(PROJECT_ID, "src")


def test_empty(module_args, mocker):
    """An empty project path returns an empty list."""
    _mock_project(mocker)
    mocker.patch(f"{FILES}.list_files", return_value=[])

    module_args({"url": BASE_URL, "api_key": API_KEY, "project_name": "proj"})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file_info.main()

    assert len(e.value["files"]) == 0


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args({"url": BASE_URL, "api_key": API_KEY, "project_id": "not-valid"})

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_file_info.main()


def test_project_required(module_args):
    """Neither project_name nor project_id fails required_one_of."""
    module_args({"url": BASE_URL, "api_key": API_KEY})

    with pytest.raises(AnsibleFailJson, match="project_name|project_id"):
        ml_project_file_info.main()
