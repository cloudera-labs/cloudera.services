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
    MlProject,
    MlProjectClient,
    API_VERSION,
)

PROJECT = dict(
    id="aaaa-bbbb-cccc-dddd",
    name="test-project",
    description="Test project",
    visibility="private",
)

PROJECTS_PAGE = dict(projects=[PROJECT])


def test_project_dataclass_roundtrip():
    """from_dict/to_dict preserve the set fields and skip NULLABLE defaults."""
    project = from_dict(MlProject, PROJECT)

    assert isinstance(project, MlProject)
    assert project.name == "test-project"
    assert to_dict(project) == PROJECT


def test_project_to_dict_minimal():
    """Unset fields are omitted from to_dict output."""
    assert to_dict(MlProject(name="only-name")) == {"name": "only-name"}


def test_list_projects(mocker):
    """Listing projects maps each entry to an MlProject."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = PROJECTS_PAGE

    client = MlProjectClient(api_client=api_client)
    response = client.list_projects()

    assert response == [from_dict(MlProject, PROJECT)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects",
        params={"include_public_projects": True, "page_size": 100},
    )


def test_list_projects_paginates(mocker):
    """Listing projects follows next_page_token across pages."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [
        dict(projects=[PROJECT], next_page_token="t1"),
        dict(projects=[{**PROJECT, "id": "eeee-ffff-0000-1111"}]),
    ]

    client = MlProjectClient(api_client=api_client)
    response = client.list_projects()

    assert len(response) == 2
    assert api_client.get.call_count == 2


def test_list_projects_empty(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(projects=[])

    client = MlProjectClient(api_client=api_client)
    assert client.list_projects() == []


def test_describe_project(mocker):
    """Describing a project squelches 403/404 to None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = PROJECT

    client = MlProjectClient(api_client=api_client)
    response = client.describe_project("aaaa-bbbb-cccc-dddd")

    assert response == from_dict(MlProject, PROJECT)
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/aaaa-bbbb-cccc-dddd",
        squelch={403: None, 404: None},
    )


def test_describe_project_missing(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = MlProjectClient(api_client=api_client)
    assert client.describe_project("aaaa-bbbb-cccc-dddd") is None


def test_create_project(mocker):
    """Creating a project posts only the set fields."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = PROJECT

    client = MlProjectClient(api_client=api_client)
    response = client.create_project(
        MlProject(name="test-project", description="Test project"),
    )

    assert response == from_dict(MlProject, PROJECT)
    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects",
        data={"name": "test-project", "description": "Test project"},
    )


def test_update_project(mocker):
    """Updating a project patches at the project id."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.patch.return_value = PROJECT

    client = MlProjectClient(api_client=api_client)
    client.update_project(
        MlProject(name="test-project", id="aaaa-bbbb-cccc-dddd", description="New"),
    )

    api_client.patch.assert_called_once_with(
        f"/{API_VERSION}/projects/aaaa-bbbb-cccc-dddd",
        data={
            "name": "test-project",
            "id": "aaaa-bbbb-cccc-dddd",
            "description": "New",
        },
    )


def test_delete_project(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlProjectClient(api_client=api_client)
    client.delete_project("aaaa-bbbb-cccc-dddd")

    api_client.delete.assert_called_once_with(
        f"/{API_VERSION}/projects/aaaa-bbbb-cccc-dddd",
    )
