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

from ansible_collections.cloudera.services.plugins.modules import ml_project_application
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlApplication,
    MlProject,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"
PROJECT_ID = "aaaa-bbbb-cccc-dddd"

PROJECTS = "ansible_collections.cloudera.services.plugins.modules.ml_project_application.MlProjectClient"
APPS = "ansible_collections.cloudera.services.plugins.modules.ml_project_application.MlApplicationClient"


def _mock_project(mocker, project=MlProject(id=PROJECT_ID, name="proj")):
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[project] if project else [])
    mocker.patch(f"{PROJECTS}.describe_project", return_value=project)


def test_create_application(module_args, mocker):
    """A new application is created with the required fields."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    mock_create = mocker.patch(
        f"{APPS}.create_application",
        return_value=MlApplication(id="app-1", name="my-app", project_id=PROJECT_ID),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "subdomain": "my-app",
            "script": "app.py",
            "runtime": "rt-1",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    result = e.value
    assert result["changed"] is True
    assert result["application"]["id"] == "app-1"

    mock_create.assert_called_once()
    project_id_arg, app_arg = mock_create.call_args.args
    assert project_id_arg == PROJECT_ID
    assert app_arg.name == "my-app"
    assert app_arg.subdomain == "my-app"
    assert app_arg.script == "app.py"
    assert app_arg.runtime_identifier == "rt-1"


def test_create_auth_negated_and_addons(module_args, mocker):
    """auth maps to negated bypass_authentication; addons map to runtime addons."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    mock_create = mocker.patch(
        f"{APPS}.create_application",
        return_value=MlApplication(id="app-1", name="my-app"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "subdomain": "my-app",
            "script": "app.py",
            "runtime": "rt-1",
            "auth": False,
            "addons": ["addon-a", "addon-b"],
        },
    )

    with pytest.raises(AnsibleExitJson):
        ml_project_application.main()

    _, app_arg = mock_create.call_args.args
    assert app_arg.bypass_authentication is True
    assert app_arg.runtime_addon_identifiers == ["addon-a", "addon-b"]


def test_create_missing_required(module_args, mocker):
    """Creating without subdomain/script/runtime fails."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    mock_create = mocker.patch(f"{APPS}.create_application")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Missing required parameters"):
        ml_project_application.main()

    mock_create.assert_not_called()


def test_create_invalid_subdomain(module_args, mocker):
    """An invalid subdomain fails before any create call."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    mock_create = mocker.patch(f"{APPS}.create_application")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "subdomain": "Not_Valid",
            "script": "app.py",
            "runtime": "rt-1",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid subdomain"):
        ml_project_application.main()

    mock_create.assert_not_called()


def test_check_mode_create(module_args, mocker):
    """Check mode reports change but does not create."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    mock_create = mocker.patch(f"{APPS}.create_application")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "subdomain": "my-app",
            "script": "app.py",
            "runtime": "rt-1",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    assert e.value["application"]["name"] == "my-app"
    mock_create.assert_not_called()


def test_project_not_found(module_args, mocker):
    """A missing project fails."""
    mocker.patch(f"{PROJECTS}.list_projects", return_value=[])

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "nope",
            "name": "my-app",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Project not found"):
        ml_project_application.main()


def test_invalid_project_id(module_args, mocker):
    """A malformed project id fails."""
    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": "not-valid",
            "name": "my-app",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Invalid Project ID"):
        ml_project_application.main()


def test_update_application(module_args, mocker):
    """A changed field triggers an update."""
    _mock_project(mocker)
    existing = MlApplication(
        id="app-1",
        name="my-app",
        project_id=PROJECT_ID,
        description="old",
        subdomain="my-app",
        script="app.py",
    )
    mocker.patch(f"{APPS}.list_applications", return_value=[existing])
    mock_update = mocker.patch(
        f"{APPS}.update_application",
        return_value=replace(existing, description="new"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "desc": "new",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    _, app_arg = mock_update.call_args.args
    assert app_arg.description == "new"


def test_present_idempotent(module_args, mocker):
    """No field changes means no update and no change."""
    _mock_project(mocker)
    existing = MlApplication(
        id="app-1",
        name="my-app",
        project_id=PROJECT_ID,
        subdomain="my-app",
        script="app.py",
    )
    mocker.patch(f"{APPS}.list_applications", return_value=[existing])
    mock_update = mocker.patch(f"{APPS}.update_application")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is False
    assert e.value["application"]["id"] == "app-1"
    mock_update.assert_not_called()


def test_restarted(module_args, mocker):
    """state=restarted restarts the application."""
    _mock_project(mocker)
    existing = MlApplication(id="app-1", name="my-app", project_id=PROJECT_ID)
    mocker.patch(f"{APPS}.list_applications", return_value=[existing])
    mocker.patch(f"{APPS}.update_application")
    mock_restart = mocker.patch(
        f"{APPS}.restart_application",
        return_value=replace(existing, status="starting"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "state": "restarted",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    mock_restart.assert_called_once_with(PROJECT_ID, "app-1")


def test_stopped(module_args, mocker):
    """state=stopped stops the application."""
    _mock_project(mocker)
    existing = MlApplication(id="app-1", name="my-app", project_id=PROJECT_ID)
    mocker.patch(f"{APPS}.list_applications", return_value=[existing])
    mocker.patch(f"{APPS}.update_application")
    mock_stop = mocker.patch(
        f"{APPS}.stop_application",
        return_value=replace(existing, status="stopped"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "state": "stopped",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    mock_stop.assert_called_once_with(PROJECT_ID, "app-1")


def test_restarted_creates_when_missing(module_args, mocker):
    """state=restarted implies present: a missing application is created then restarted."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    created = MlApplication(id="app-9", name="my-app", project_id=PROJECT_ID)
    mock_create = mocker.patch(f"{APPS}.create_application", return_value=created)
    mock_restart = mocker.patch(
        f"{APPS}.restart_application",
        return_value=replace(created, status="starting"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "subdomain": "my-app",
            "script": "app.py",
            "runtime": "rt-1",
            "state": "restarted",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    mock_create.assert_called_once()
    mock_restart.assert_called_once_with(PROJECT_ID, "app-9")


def test_stopped_creates_when_missing(module_args, mocker):
    """state=stopped implies present: a missing application is created then stopped."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    created = MlApplication(id="app-9", name="my-app", project_id=PROJECT_ID)
    mock_create = mocker.patch(f"{APPS}.create_application", return_value=created)
    mock_stop = mocker.patch(
        f"{APPS}.stop_application",
        return_value=replace(created, status="stopped"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "subdomain": "my-app",
            "script": "app.py",
            "runtime": "rt-1",
            "state": "stopped",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    mock_create.assert_called_once()
    mock_stop.assert_called_once_with(PROJECT_ID, "app-9")


def test_restarted_missing_requires_create_params(module_args, mocker):
    """Restarting a missing application still requires the create parameters."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    mock_create = mocker.patch(f"{APPS}.create_application")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "ghost",
            "state": "restarted",
        },
    )

    with pytest.raises(AnsibleFailJson, match="Missing required parameters"):
        ml_project_application.main()

    mock_create.assert_not_called()


def test_absent_existing(module_args, mocker):
    """Deleting an existing application removes it."""
    _mock_project(mocker)
    existing = MlApplication(id="app-1", name="my-app", project_id=PROJECT_ID)
    mocker.patch(f"{APPS}.list_applications", return_value=[existing])
    mock_delete = mocker.patch(f"{APPS}.delete_application")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "my-app",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    mock_delete.assert_called_once_with(PROJECT_ID, "app-1")


def test_absent_missing(module_args, mocker):
    """Deleting a non-existent application is a no-op."""
    _mock_project(mocker)
    mocker.patch(f"{APPS}.list_applications", return_value=[])
    mock_delete = mocker.patch(f"{APPS}.delete_application")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "ghost",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_present_matches_existing_by_subdomain(module_args, mocker):
    """When name misses, an existing app with the same subdomain is matched (no create)."""
    _mock_project(mocker)
    existing = MlApplication(
        id="app-1",
        name="old-name",
        project_id=PROJECT_ID,
        subdomain="my-app",
        script="app.py",
    )
    mocker.patch(f"{APPS}.list_applications", return_value=[existing])
    mock_create = mocker.patch(f"{APPS}.create_application")
    mock_update = mocker.patch(
        f"{APPS}.update_application",
        return_value=replace(existing, name="new-name"),
    )

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_name": "proj",
            "name": "new-name",
            "subdomain": "my-app",
            "script": "app.py",
            "runtime": "rt-1",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    # The existing app (by subdomain) is used; no duplicate create is attempted.
    mock_create.assert_not_called()
    assert e.value["application"]["id"] == "app-1"
    # A name change is a real update.
    mock_update.assert_called_once()


def test_by_id(module_args, mocker):
    """An application can be addressed by id via describe_application."""
    _mock_project(mocker)
    existing = MlApplication(id="app-1", name="my-app", project_id=PROJECT_ID)
    mock_describe = mocker.patch(
        f"{APPS}.describe_application",
        return_value=existing,
    )
    mock_delete = mocker.patch(f"{APPS}.delete_application")

    module_args(
        {
            "url": BASE_URL,
            "api_key": API_KEY,
            "project_id": PROJECT_ID,
            "id": "app-1",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_application.main()

    assert e.value["changed"] is True
    mock_describe.assert_called_once_with(PROJECT_ID, "app-1")
    mock_delete.assert_called_once_with(PROJECT_ID, "app-1")
