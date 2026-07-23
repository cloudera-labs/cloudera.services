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

from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlFile,
)

REQUIRED_ENV_VARS = [
    "CML_ENDPOINT",
    "CML_API_KEY",
]


def _basename(path):
    return path.rsplit("/", 1)[-1]


def test_list_files(ml_project_file_client, existing_ml_project, existing_ml_file):
    """List files at the project root (includes the seeded file)."""
    response = ml_project_file_client.list_files(existing_ml_project.id, "")

    assert isinstance(response, list)
    assert all(isinstance(f, MlFile) for f in response)
    assert any(_basename(f.path) == existing_ml_file.path for f in response)


def test_list_missing_path_squelched(ml_project_file_client, existing_ml_project):
    """Listing a nonexistent path is squelched to an empty list."""
    response = ml_project_file_client.list_files(
        existing_ml_project.id,
        "this-directory-does-not-exist",
    )

    assert response == []


def test_upload_and_delete(
    request,
    ml_project_file_client,
    existing_ml_project,
):
    """Upload a file, confirm it exists, then delete it."""
    path = f"{request.node.name}.py"

    ml_project_file_client.upload_file(
        existing_ml_project.id,
        path,
        content="print('int')\n",
    )

    listed = ml_project_file_client.list_files(existing_ml_project.id, "")
    assert any(_basename(f.path) == path for f in listed)

    ml_project_file_client.delete_file(existing_ml_project.id, path)

    listed_after = ml_project_file_client.list_files(existing_ml_project.id, "")
    assert not any(_basename(f.path) == path for f in listed_after)
