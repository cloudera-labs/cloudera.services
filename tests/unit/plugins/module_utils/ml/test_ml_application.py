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
    MlApplication,
    MlApplicationClient,
    API_VERSION,
)

PROJECT_ID = "aaaa-bbbb-cccc-dddd"

APPLICATION = dict(
    id="app-1",
    name="test-app",
    project_id=PROJECT_ID,
    subdomain="test-app",
    script="app.py",
)


def test_application_dataclass_roundtrip():
    app = from_dict(MlApplication, APPLICATION)
    assert isinstance(app, MlApplication)
    assert to_dict(app) == APPLICATION


def test_list_applications(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(applications=[APPLICATION])

    client = MlApplicationClient(api_client=api_client)
    response = client.list_applications(PROJECT_ID)

    assert response == [from_dict(MlApplication, APPLICATION)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/applications",
        params={"page_size": 100},
    )


def test_describe_application(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = APPLICATION

    client = MlApplicationClient(api_client=api_client)
    response = client.describe_application(PROJECT_ID, "app-1")

    assert response == from_dict(MlApplication, APPLICATION)
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/applications/app-1",
        squelch={403: None, 404: None},
    )


def test_create_application(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = APPLICATION

    client = MlApplicationClient(api_client=api_client)
    client.create_application(
        PROJECT_ID,
        MlApplication(name="test-app", subdomain="test-app", script="app.py"),
    )

    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/applications",
        data={"name": "test-app", "subdomain": "test-app", "script": "app.py"},
    )


def test_update_application(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.patch.return_value = APPLICATION

    client = MlApplicationClient(api_client=api_client)
    client.update_application(
        PROJECT_ID,
        MlApplication(name="test-app", id="app-1", description="updated"),
    )

    api_client.patch.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/applications/app-1",
        data={"name": "test-app", "id": "app-1", "description": "updated"},
    )


def test_delete_application(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlApplicationClient(api_client=api_client)
    client.delete_application(PROJECT_ID, "app-1")

    api_client.delete.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/applications/app-1",
    )


def test_restart_application(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = APPLICATION

    client = MlApplicationClient(api_client=api_client)
    response = client.restart_application(PROJECT_ID, "app-1")

    assert response == from_dict(MlApplication, APPLICATION)
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/applications/app-1:restart",
    )


def test_stop_application(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = APPLICATION

    client = MlApplicationClient(api_client=api_client)
    response = client.stop_application(PROJECT_ID, "app-1")

    assert response == from_dict(MlApplication, APPLICATION)
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/applications/app-1:stop",
    )
