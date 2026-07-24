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

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    ServicesClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlRuntime,
    MlRuntimeClient,
    MlRuntimeRegistration,
    MlRuntimeValidation,
    MlRuntimeAddon,
    MlRuntimeAddonClient,
    MlRuntimeRepo,
    MlRuntimeRepoClient,
    API_VERSION,
)

RUNTIME = dict(
    image_identifier="docker.repository/runtime:1",
    edition="Standard",
    kernel="Python 3.10",
    editor="Workbench",
    status="ENABLED",
    register_user_id=7,
)

ADDON = dict(
    identifier="spark-3.2",
    component="Spark",
    display_name="Spark 3.2",
    status="AVAILABLE",
    manageable=True,
    id=3,
    created_at="2026-01-01T00:00:00Z",
)

REPO = dict(id=1, name="internal", url="https://repo.example.com/a")


# ---------------------------------------------------------------------------
# Dataclass round trips
# ---------------------------------------------------------------------------


def test_runtime_dataclass_roundtrip():
    runtime = from_dict(MlRuntime, RUNTIME)
    assert isinstance(runtime, MlRuntime)
    assert to_dict(runtime) == RUNTIME


def test_addon_dataclass_roundtrip():
    addon = from_dict(MlRuntimeAddon, ADDON)
    assert isinstance(addon, MlRuntimeAddon)
    assert to_dict(addon) == ADDON


def test_repo_dataclass_roundtrip():
    repo = from_dict(MlRuntimeRepo, REPO)
    assert isinstance(repo, MlRuntimeRepo)
    assert to_dict(repo) == REPO


def test_registration_dataclass_roundtrip():
    data = dict(
        validation_success=True,
        insert_success=True,
        reason="",
        reason_data="",
        details={"editor": "Workbench"},
    )
    reg = from_dict(MlRuntimeRegistration, data)
    assert isinstance(reg, MlRuntimeRegistration)
    assert to_dict(reg) == data


def test_validation_dataclass_roundtrip():
    data = dict(success=True, reason="", reason_data="", details={"kernel": "Python"})
    validation = from_dict(MlRuntimeValidation, data)
    assert isinstance(validation, MlRuntimeValidation)
    assert to_dict(validation) == data


# ---------------------------------------------------------------------------
# MlRuntimeClient
# ---------------------------------------------------------------------------


def test_list_runtimes(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(runtimes=[RUNTIME])

    client = MlRuntimeClient(api_client=api_client)
    response = client.list_runtimes()

    assert response == [from_dict(MlRuntime, RUNTIME)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/runtimes",
        params={"page_size": 100},
    )


def test_list_runtimes_empty(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {}

    client = MlRuntimeClient(api_client=api_client)
    assert client.list_runtimes() == []


def test_validate_runtime(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(success=True, reason="")

    client = MlRuntimeClient(api_client=api_client)
    result = client.validate_runtime("registry/img:1")

    assert isinstance(result, MlRuntimeValidation)
    assert result.success is True
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/runtimes:validate",
        params={"url": "registry/img:1"},
    )


def test_validate_runtime_with_credential(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(success=False, reason="no auth")

    client = MlRuntimeClient(api_client=api_client)
    result = client.validate_runtime("registry/img:1", docker_credential_id="cred-1")

    assert result.success is False
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/runtimes:validate",
        params={"url": "registry/img:1", "docker_credential_id": "cred-1"},
    )


def test_register_runtime(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = dict(validation_success=True, insert_success=True)

    client = MlRuntimeClient(api_client=api_client)
    result = client.register_runtime("registry/img:1")

    assert isinstance(result, MlRuntimeRegistration)
    assert result.insert_success is True
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/runtimes",
        data={"url": "registry/img:1"},
    )


def test_register_runtime_with_credential(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = dict(validation_success=True, insert_success=True)

    client = MlRuntimeClient(api_client=api_client)
    client.register_runtime("registry/img:1", docker_credential_id="cred-1")

    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/runtimes",
        data={"url": "registry/img:1", "docker_credential_id": "cred-1"},
    )


def test_update_runtime_status_by_image(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = dict(rows_affected=2)

    client = MlRuntimeClient(api_client=api_client)
    rows = client.update_runtime_status("DISABLED", image_identifier=["registry/img:1"])

    assert rows == 2
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/runtimes:update",
        data={"status": "DISABLED", "image_identifier": ["registry/img:1"]},
    )


def test_update_runtime_status_by_id(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = dict(rows_affected=1)

    client = MlRuntimeClient(api_client=api_client)
    rows = client.update_runtime_status("ENABLED", runtime_id=[5])

    assert rows == 1
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/runtimes:update",
        data={"status": "ENABLED", "runtime_id": [5]},
    )


def test_update_runtime_status_missing_rows(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {}

    client = MlRuntimeClient(api_client=api_client)
    assert client.update_runtime_status("ENABLED", runtime_id=[5]) == 0


def test_set_docker_credential(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {}

    client = MlRuntimeClient(api_client=api_client)
    client.set_docker_credential("cred-1", "registry/img:1")

    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/runtimes/credential:set",
        data={
            "docker_credential_id": "cred-1",
            "runtime_identifier": "registry/img:1",
        },
    )


# ---------------------------------------------------------------------------
# MlRuntimeAddonClient
# ---------------------------------------------------------------------------


def test_list_runtime_addons(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(runtime_addons=[ADDON])

    client = MlRuntimeAddonClient(api_client=api_client)
    response = client.list_runtime_addons()

    assert response == [from_dict(MlRuntimeAddon, ADDON)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/runtimeaddons",
        params={"page_size": 100},
    )


def test_update_addon_status_by_identifiers(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = dict(rows_affected=1)

    client = MlRuntimeAddonClient(api_client=api_client)
    rows = client.update_addon_status("DISABLED", identifiers=["spark-3.2"])

    assert rows == 1
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/runtimeaddons:updatestatus",
        data={"status": "DISABLED", "identifiers": ["spark-3.2"]},
    )


def test_update_addon_status_by_ids(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = dict(rows_affected=2)

    client = MlRuntimeAddonClient(api_client=api_client)
    rows = client.update_addon_status("AVAILABLE", ids=[1, 2])

    assert rows == 2
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/runtimeaddons:updatestatus",
        data={"status": "AVAILABLE", "ids": [1, 2]},
    )


def test_update_addon_status_missing_rows(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {}

    client = MlRuntimeAddonClient(api_client=api_client)
    assert client.update_addon_status("DISABLED", ids=[1]) == 0


# ---------------------------------------------------------------------------
# MlRuntimeRepoClient
# ---------------------------------------------------------------------------


def test_list_runtime_repos(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(runtimerepos=[REPO])

    client = MlRuntimeRepoClient(api_client=api_client)
    response = client.list_runtime_repos()

    assert response == [from_dict(MlRuntimeRepo, REPO)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/runtimerepos",
        params={"page_size": 100},
    )


def test_create_runtime_repo(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = REPO

    client = MlRuntimeRepoClient(api_client=api_client)
    result = client.create_runtime_repo(
        MlRuntimeRepo(name="internal", url="https://repo.example.com/a"),
    )

    assert result == from_dict(MlRuntimeRepo, REPO)
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/runtimerepos",
        data={"name": "internal", "url": "https://repo.example.com/a"},
    )


def test_update_runtime_repo(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.patch.return_value = REPO

    client = MlRuntimeRepoClient(api_client=api_client)
    repo = MlRuntimeRepo(id=1, name="internal", url="https://repo.example.com/a")
    result = client.update_runtime_repo(repo)

    assert result == from_dict(MlRuntimeRepo, REPO)
    api_client.patch.assert_called_once_with(
        f"/{API_VERSION}/runtimerepos/1",
        data=to_dict(repo),
    )


def test_delete_runtime_repo(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlRuntimeRepoClient(api_client=api_client)
    client.delete_runtime_repo(1)

    api_client.delete.assert_called_once_with(f"/{API_VERSION}/runtimerepos/1")
