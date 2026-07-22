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

from ansible_collections.cloudera.services.plugins.modules import ml_project_info
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlProject

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
VALID_ID = "d5tv-auiv-yl59-ncmc"

LIST_PROJECTS = (
    "ansible_collections.cloudera.services.plugins.modules."
    "ml_project_info.MlProjectClient.list_projects"
)
DESCRIBE_PROJECT = (
    "ansible_collections.cloudera.services.plugins.modules."
    "ml_project_info.MlProjectClient.describe_project"
)


def test_ml_project_info_module_list_all(module_args, mocker):
    """List all projects."""
    mock_list = mocker.patch(
        LIST_PROJECTS,
        return_value=[
            MlProject(id="0000-0000-0000-0001", name="project-one"),
            MlProject(id="0000-0000-0000-0002", name="project-two"),
        ],
    )

    module_args({"url": BASE_URL, "api_key": API_KEY})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 2
    assert result["projects"][0]["name"] == "project-one"
    assert result["projects"][1]["name"] == "project-two"

    mock_list.assert_called_once()


def test_ml_project_info_module_filter_by_name(module_args, mocker):
    """Filter the listing by name."""
    mock_list = mocker.patch(
        LIST_PROJECTS,
        return_value=[
            MlProject(id="0000-0000-0000-0001", name="project-one"),
            MlProject(id="0000-0000-0000-0002", name="project-two"),
        ],
    )

    module_args({"url": BASE_URL, "api_key": API_KEY, "name": "project-one"})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 1
    assert result["projects"][0]["name"] == "project-one"

    mock_list.assert_called_once()


def test_ml_project_info_module_filter_by_name_not_found(module_args, mocker):
    """Filter by a name that does not exist."""
    mock_list = mocker.patch(
        LIST_PROJECTS,
        return_value=[MlProject(id="0000-0000-0000-0001", name="project-one")],
    )

    module_args({"url": BASE_URL, "api_key": API_KEY, "name": "nonexistent"})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 0

    mock_list.assert_called_once()


def test_ml_project_info_module_by_id(module_args, mocker):
    """Retrieve a project by ID."""
    mock_describe = mocker.patch(
        DESCRIBE_PROJECT,
        return_value=MlProject(
            id=VALID_ID,
            name="project-one",
            description="First project",
        ),
    )

    module_args({"url": BASE_URL, "api_key": API_KEY, "id": VALID_ID})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 1
    assert result["projects"][0]["id"] == VALID_ID
    assert result["projects"][0]["description"] == "First project"

    mock_describe.assert_called_once_with(VALID_ID)


def test_ml_project_info_module_by_id_not_found(module_args, mocker):
    """Retrieve by ID when the project is not found or not accessible."""
    mock_describe = mocker.patch(DESCRIBE_PROJECT, return_value=None)

    module_args({"url": BASE_URL, "api_key": API_KEY, "id": VALID_ID})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 0

    mock_describe.assert_called_once_with(VALID_ID)


def test_ml_project_info_module_invalid_id(module_args, mocker):
    """An id that does not match the CML format fails before any API call."""
    mock_describe = mocker.patch(DESCRIBE_PROJECT)

    module_args({"url": BASE_URL, "api_key": API_KEY, "id": "not-a-valid-id"})

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_info.main()

    mock_describe.assert_not_called()


def test_ml_project_info_module_empty_list(module_args, mocker):
    """No projects exist."""
    mock_list = mocker.patch(LIST_PROJECTS, return_value=[])

    module_args({"url": BASE_URL, "api_key": API_KEY})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 0

    mock_list.assert_called_once()


def test_ml_project_info_module_mutually_exclusive(module_args):
    """name and id cannot be supplied together."""
    module_args(
        {"url": BASE_URL, "api_key": API_KEY, "name": "project-one", "id": VALID_ID},
    )

    with pytest.raises(
        AnsibleFailJson,
        match="parameters are mutually exclusive: name|id",
    ):
        ml_project_info.main()


def test_ml_project_info_module_check_mode(module_args, mocker):
    """Check mode still returns the listing without reporting change."""
    mock_list = mocker.patch(
        LIST_PROJECTS,
        return_value=[MlProject(id="0000-0000-0000-0001", name="project-one")],
    )

    module_args({"url": BASE_URL, "api_key": API_KEY, "_ansible_check_mode": True})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 1

    mock_list.assert_called_once()
