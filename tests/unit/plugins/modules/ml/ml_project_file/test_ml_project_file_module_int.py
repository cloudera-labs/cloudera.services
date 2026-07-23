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

from typing import Callable

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
)

from ansible_collections.cloudera.services.plugins.modules import ml_project_file

REQUIRED_ENV_VARS = [
    "CML_ENDPOINT",
    "CML_API_KEY",
]


@pytest.fixture
def ml_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args (endpoint + bearer token) for CML tests."""

    def _ml_module_args(overrides: dict = {}) -> None:
        args = {
            "url": env_context["CML_ENDPOINT"],
            "api_key": env_context["CML_API_KEY"],
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _ml_module_args


def test_create_file(
    request,
    ml_module_args,
    existing_ml_project,
    ml_project_file_client,
    purge_ml_file,
):
    """Upload a file from literal content."""
    path = f"{request.node.name}.py"

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "path": path,
            "content": "print('created')\n",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    purge_ml_file(existing_ml_project.id, path)

    result = e.value
    assert result["changed"] is True
    assert result["file"]["path"] == path
    # Confirm the file is present in the project root listing
    assert any(
        f.path.rsplit("/", 1)[-1] == path
        for f in ml_project_file_client.list_files(existing_ml_project.id, "")
    )


def test_idempotent_when_exists(ml_module_args, existing_ml_project, existing_ml_file):
    """Re-applying an existing file without force is idempotent."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "path": existing_ml_file.path,
            "content": "print('changed')\n",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is False


def test_force_reupload(ml_module_args, existing_ml_project, existing_ml_file):
    """force re-uploads an existing file."""

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "path": existing_ml_file.path,
            "content": "print('forced')\n",
            "force": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is True


def test_delete_file(
    request,
    ml_module_args,
    existing_ml_project,
    ml_project_file_client,
):
    """Delete an existing file."""
    path = f"{request.node.name}.py"
    ml_project_file_client.upload_file(
        existing_ml_project.id,
        path,
        content="print('to delete')\n",
    )

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "path": path,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is True
    assert not any(
        f.path.rsplit("/", 1)[-1] == path
        for f in ml_project_file_client.list_files(existing_ml_project.id, "")
    )


def test_delete_nonexistent(ml_module_args, existing_ml_project):
    """Deleting a non-existent file is a no-op."""

    ml_module_args(
        {
            "state": "absent",
            "project_id": existing_ml_project.id,
            "path": "nonexistent-file-12345.py",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is False


def test_check_mode_create(
    request,
    ml_module_args,
    existing_ml_project,
    ml_project_file_client,
):
    """Check mode reports change but does not upload."""
    path = f"{request.node.name}.py"

    ml_module_args(
        {
            "state": "present",
            "project_id": existing_ml_project.id,
            "path": path,
            "content": "print('nope')\n",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file.main()

    assert e.value["changed"] is True
    assert not any(
        f.path.rsplit("/", 1)[-1] == path
        for f in ml_project_file_client.list_files(existing_ml_project.id, "")
    )
