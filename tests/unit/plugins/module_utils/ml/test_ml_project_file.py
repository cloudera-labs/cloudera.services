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
    MlFile,
    MlProjectFileClient,
    API_VERSION,
)

PROJECT_ID = "aaaa-bbbb-cccc-dddd"

FILE = dict(path="app.py", is_dir=False, file_size="12")


def test_file_dataclass_roundtrip():
    f = from_dict(MlFile, FILE)
    assert isinstance(f, MlFile)
    assert to_dict(f) == FILE


def test_list_files(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = dict(files=[FILE])

    client = MlProjectFileClient(api_client=api_client)
    response = client.list_files(PROJECT_ID, "src")

    assert response == [from_dict(MlFile, FILE)]
    api_client.get.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/files/src",
        squelch={403: None, 404: None},
    )


def test_list_files_none_squelched(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = MlProjectFileClient(api_client=api_client)
    assert client.list_files(PROJECT_ID, "missing") == []


def test_upload_file_content(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlProjectFileClient(api_client=api_client)
    client.upload_file(PROJECT_ID, "app.py", content="print(1)")

    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/files",
        data={"app.py": {"content": "print(1)", "filename": "app.py"}},
        format="multipart",
    )


def test_upload_file_src(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlProjectFileClient(api_client=api_client)
    client.upload_file(PROJECT_ID, "sub/dir/run.py", src="/tmp/run.py")

    api_client.post.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/files",
        data={"sub/dir/run.py": {"filename": "/tmp/run.py"}},
        format="multipart",
    )


def test_delete_file(mocker):
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = MlProjectFileClient(api_client=api_client)
    client.delete_file(PROJECT_ID, "app.py")

    api_client.delete.assert_called_once_with(
        f"/{API_VERSION}/projects/{PROJECT_ID}/files/app.py",
    )
