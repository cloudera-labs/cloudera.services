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
    MlRuntime,
    MlRuntimeAddon,
    MlRuntimeRepo,
    MlRuntimeRegistration,
    MlRuntimeValidation,
)

REQUIRED_ENV_VARS = [
    "CML_ENDPOINT",
    "CML_API_KEY",
]


# ---------------------------------------------------------------------------
# Runtimes (read + non-destructive validate/status)
# ---------------------------------------------------------------------------


def test_list_runtimes(ml_runtime_client):
    """List runtimes and confirm pagination assembles a list of dataclasses."""
    response = ml_runtime_client.list_runtimes()

    assert isinstance(response, list)
    assert len(response) > 0
    assert all(isinstance(r, MlRuntime) for r in response)
    # Real runtimes expose an image identifier.
    assert all(isinstance(r.image_identifier, str) for r in response)


def test_validate_runtime_invalid(ml_runtime_client):
    """Validating a bogus image URL returns an unsuccessful result (non-destructive)."""
    result = ml_runtime_client.validate_runtime(
        "registry.invalid.example.com/does-not-exist:0",
    )

    assert isinstance(result, MlRuntimeValidation)
    assert result.success is not True


def test_update_runtime_status_no_match(ml_runtime_client):
    """Updating status for a non-existent image affects no rows (non-destructive)."""
    rows = ml_runtime_client.update_runtime_status(
        "DISABLED",
        image_identifier=["registry.invalid.example.com/does-not-exist:0"],
    )

    assert rows == 0


# ---------------------------------------------------------------------------
# Runtime addons (read + non-destructive status)
# ---------------------------------------------------------------------------


def test_list_runtime_addons(ml_runtime_addon_client):
    """List runtime addons and confirm dataclass typing."""
    response = ml_runtime_addon_client.list_runtime_addons()

    assert isinstance(response, list)
    assert all(isinstance(a, MlRuntimeAddon) for a in response)


def test_update_addon_status_no_match(ml_runtime_addon_client):
    """Updating status for a non-existent addon affects no rows (non-destructive)."""
    rows = ml_runtime_addon_client.update_addon_status(
        "DISABLED",
        identifiers=["does-not-exist-runtime-addon-12345"],
    )

    assert rows == 0


# ---------------------------------------------------------------------------
# Runtime repositories (full CRUD lifecycle)
# ---------------------------------------------------------------------------


def test_list_runtime_repos(ml_runtime_repo_client):
    """List runtime repositories."""
    response = ml_runtime_repo_client.list_runtime_repos()

    assert isinstance(response, list)
    assert all(isinstance(r, MlRuntimeRepo) for r in response)


def test_runtime_repo_lifecycle(request, ml_runtime_repo_client, purge_ml_runtime_repo):
    """Create, update, then delete a runtime repository."""
    name = request.node.name.lower()[:100]

    created = ml_runtime_repo_client.create_runtime_repo(
        MlRuntimeRepo(
            name=name,
            url="https://raw.githubusercontent.com/example/repo/main/runtimes.json",
        ),
    )
    purge_ml_runtime_repo(created)

    assert isinstance(created, MlRuntimeRepo)
    assert created.name == name
    assert isinstance(created.id, int)

    # It now appears in the listing.
    assert any(r.id == created.id for r in ml_runtime_repo_client.list_runtime_repos())

    # Update the URL.
    updated = ml_runtime_repo_client.update_runtime_repo(
        MlRuntimeRepo(
            id=created.id,
            name=name,
            url="https://raw.githubusercontent.com/example/repo/main/other.json",
        ),
    )
    assert isinstance(updated, MlRuntimeRepo)

    # Delete it and confirm removal.
    ml_runtime_repo_client.delete_runtime_repo(created.id)
    assert not any(
        r.id == created.id for r in ml_runtime_repo_client.list_runtime_repos()
    )
