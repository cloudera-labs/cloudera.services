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

from ansible_collections.cloudera.services.plugins.modules import ml_project_info

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


def test_ml_project_info_module_list_all(ml_module_args, existing_ml_project):
    """List all projects (includes the established project)."""

    ml_module_args({})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert isinstance(result["projects"], list)
    assert any(p["id"] == existing_ml_project.id for p in result["projects"])


def test_ml_project_info_module_by_name(ml_module_args, existing_ml_project):
    """Retrieve a single project by name."""

    ml_module_args({"name": existing_ml_project.name})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 1
    assert result["projects"][0]["id"] == existing_ml_project.id


def test_ml_project_info_module_by_id(ml_module_args, existing_ml_project):
    """Retrieve a single project by id."""

    ml_module_args({"id": existing_ml_project.id})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 1
    assert result["projects"][0]["id"] == existing_ml_project.id
    assert result["projects"][0]["name"] == existing_ml_project.name


def test_ml_project_info_module_nonexistent_name(ml_module_args):
    """A name that does not exist returns an empty list."""

    ml_module_args({"name": "nonexistent-project-name-12345"})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["projects"]) == 0


def test_ml_project_info_module_check_mode(ml_module_args):
    """Check mode returns the listing without reporting change."""

    ml_module_args({"_ansible_check_mode": True})

    with pytest.raises(AnsibleExitJson) as e:
        ml_project_info.main()

    result = e.value
    assert result["changed"] is False
    assert isinstance(result["projects"], list)
