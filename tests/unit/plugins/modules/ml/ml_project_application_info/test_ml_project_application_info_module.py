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

from ansible_collections.cloudera.services.plugins.modules import (
    ml_project_application_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlApplication,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_application_info.MlProjectClient"
APPS = "ansible_collections.cloudera.services.plugins.modules.ml_project_application_info.MlApplicationClient"

APP_ONE = MlApplication(
    id="app-1",
    name="alpha",
    project_id=PROJECT_ID,
    kernel="python3",
    status="running",
    subdomain="alpha",
    script="alpha.py",
    description="first",
    bypass_authentication=False,
    creator={"username": "jdoe", "name": "Jane", "email": "jane@example.com"},
)
APP_TWO = MlApplication(
    id="app-2",
    name="beta",
    project_id=PROJECT_ID,
    kernel="scala",
    status="stopped",
    subdomain="beta",
    script="beta.py",
    description="second",
    bypass_authentication=True,
    creator={"username": "asmith", "name": "Al", "email": "al@example.com"},
)


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def _base_args(overrides=None):
    args = {
        "url": BASE_URL,
        "api_key": API_KEY,
        "project_name": "proj",
    }
    if overrides:
        args.update(overrides)
    return args


def test_list_all(module_args, mocker):
    """List every application in the project."""
    _mock_project(mocker)
    mock_list = mocker.patch(
        f"{APPS}.list_applications",
        return_value=[APP_ONE, APP_TWO],
    )

    module_args(_base_args())

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["applications"]) == 2
    mock_list.assert_called_once_with(PROJECT_ID)


def test_filter_by_name(module_args, mocker):
    """Filter applications by name."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[APP_ONE, APP_TWO])

    module_args(_base_args({"name": "beta"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    apps = e.value["applications"]
    assert len(apps) == 1
    assert apps[0]["id"] == "app-2"


def test_filter_by_status(module_args, mocker):
    """Filter applications by runtime status."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[APP_ONE, APP_TWO])

    module_args(_base_args({"status": "running"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    apps = e.value["applications"]
    assert len(apps) == 1
    assert apps[0]["id"] == "app-1"


def test_filter_by_kernel(module_args, mocker):
    """Filter applications by kernel."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[APP_ONE, APP_TWO])

    module_args(_base_args({"kernel": "scala"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    apps = e.value["applications"]
    assert len(apps) == 1
    assert apps[0]["id"] == "app-2"


def test_filter_by_creator_username(module_args, mocker):
    """Filter applications by creator username."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[APP_ONE, APP_TWO])

    module_args(_base_args({"creator": {"username": "jdoe"}}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    apps = e.value["applications"]
    assert len(apps) == 1
    assert apps[0]["id"] == "app-1"


def test_filter_by_auth(module_args, mocker):
    """auth=false returns only publicly accessible applications."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[APP_ONE, APP_TWO])

    module_args(_base_args({"auth": False}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    apps = e.value["applications"]
    # APP_TWO has bypass_authentication=True (public)
    assert len(apps) == 1
    assert apps[0]["id"] == "app-2"


def test_filter_combined_no_match(module_args, mocker):
    """Multiple filters are ANDed together."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[APP_ONE, APP_TWO])

    module_args(_base_args({"name": "alpha", "status": "stopped"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    assert len(e.value["applications"]) == 0


def test_by_id(module_args, mocker):
    """Retrieve a single application by id."""
    _mock_project(mocker)
    mock_describe = mocker.patch(
        f"{APPS}.describe_application",
        return_value=APP_ONE,
    )
    mock_list = mocker.patch(f"{APPS}.list_applications")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": PROJECT_ID,
            "id": "app-1",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    apps = e.value["applications"]
    assert len(apps) == 1
    assert apps[0]["id"] == "app-1"
    mock_describe.assert_called_once_with(PROJECT_ID, "app-1")
    mock_list.assert_not_called()


def test_by_id_not_found(module_args, mocker):
    """A missing application id yields an empty list."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.describe_application", return_value=None)

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": PROJECT_ID,
            "id": "ghost",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application_info.main()

    assert len(e.value["applications"]) == 0


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(_base_args({"project_name": "nope"}))

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_application_info.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": "not-valid",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_application_info.main()


def test_project_required(module_args):
    """Neither project_name nor project_id fails required_one_of."""
    module_args({"url": BASE_URL, "api_key": API_KEY})

    with pytest.raises(AnsibleFailJson, match="project_name|project_id"):
        ml_project_application_info.main()
