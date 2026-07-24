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

from ansible_collections.cloudera.services.plugins.modules import ml_runtime_repo
from ansible_collections.cloudera.services.plugins.module_utils.common import from_dict
from ansible_collections.cloudera.services.plugins.module_utils.ml import MlRuntimeRepo

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


def test_create_and_delete(request, ml_module_args, purge_ml_runtime_repo):
    """Create then delete a runtime repository."""
    name = request.node.name.lower()[:100]

    ml_module_args(
        {
            "state": "present",
            "name": name,
            "repo_url": "https://raw.githubusercontent.com/example/repo/main/runtimes.json",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    result = e.value
    repo = from_dict(MlRuntimeRepo, result["runtime_repo"])
    purge_ml_runtime_repo(repo)

    assert result["changed"] is True
    assert result["runtime_repo"]["name"] == name
    assert "id" in result["runtime_repo"]

    # Delete by id.
    ml_module_args({"state": "absent", "id": repo.id})

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    assert e.value["changed"] is True


def test_delete_nonexistent(ml_module_args):
    """Deleting a non-existent repo is a no-op."""
    ml_module_args({"state": "absent", "name": "nonexistent-repo-name-12345"})

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime_repo.main()

    assert e.value["changed"] is False
