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

from ansible_collections.cloudera.services.plugins.modules import ml_project_file_info

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


def test_list_root(ml_module_args, existing_ml_project, existing_ml_file):
    """List files at the project root includes the seeded file."""

    ml_module_args({"project_id": existing_ml_project.id})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file_info.main()

    result = e.value
    assert result["changed"] is False
    assert isinstance(result["files"], list)
    assert any(
        f["path"].rsplit("/", 1)[-1] == existing_ml_file.path for f in result["files"]
    )


def test_list_nonexistent_path(ml_module_args, existing_ml_project):
    """Listing a nonexistent path returns an empty list."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "path": "this-directory-does-not-exist",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["files"] == []


def test_check_mode(ml_module_args, existing_ml_project):
    """Check mode returns the listing without reporting change."""

    ml_module_args(
        {
            "project_id": existing_ml_project.id,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_file_info.main()

    result = e.value
    assert result["changed"] is False
    assert isinstance(result["files"], list)
