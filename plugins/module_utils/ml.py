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

"""
Service-model layer for the Cloudera Machine Learning (CML) Workspace API v2.

See https://docs.cloudera.com/machine-learning/cloud/api/topics/ml-api-v2.html

This module uses typed dataclass models plus stateless ``*Client`` classes that
operate against a ``ServicesClient``. CML authenticates with a bearer token
(``api_key``), so this module also provides:

- ``CmlServicesClient`` - an ``AnsibleServicesClient`` subclass that injects the
  ``Authorization: Bearer <api_key>`` header on every request.
- ``CmlAuthMixin`` - a ``ParametersMixin`` declaring the shared ``url``/``api_key`` params.
- ``MlServicesModule`` - a thin ``ServicesModule`` base wiring the two together, reused by
  every ``ml_*`` module.
"""

import re

from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any, Dict, List, Optional, Union

from ansible.module_utils.basic import env_fallback

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    NULLABLE,
    ServicesClient,
    AnsibleServicesClient,
    ServicesModule,
    ParametersMixin,
    paginated,
)

__maintainer__ = [
    "wmudge@cloudera.com",
]

API_VERSION = "api/v2"


# CML v2 uses snake_case pagination tokens; bind the shared decorator once.
def _cml_paginated(func):
    return paginated(
        next_key="next_page_token",
        token_param="page_token",
        size_param="page_size",
    )(func)


class CmlServicesClient(AnsibleServicesClient):
    """``AnsibleServicesClient`` that authenticates CML requests with a bearer token.

    The token is read from the module's ``api_key`` parameter and attached as an
    ``Authorization`` header, which ``AnsibleServicesClient`` merges into every request.
    """

    def __init__(self, module, **kwargs):
        api_key = module.params.get("api_key")
        headers = dict(kwargs.pop("headers", {}))
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        super().__init__(module=module, headers=headers, **kwargs)


class CmlAuthMixin(ParametersMixin):
    """Declares the shared CML connection parameters (``url`` and ``api_key``)."""

    @staticmethod
    def get_argument_spec() -> Dict[str, Dict[str, Any]]:
        return dict(
            # Override the base ``url`` (merged from url_argument_spec just before mixin
            # specs) to add the CML endpoint alias and environment fallback.
            url=dict(
                type="str",
                required=True,
                aliases=["endpoint", "endpoint_url", "workspace_url"],
                fallback=(env_fallback, ["CML_ENDPOINT"]),
            ),
            api_key=dict(
                type="str",
                required=True,
                no_log=True,
                aliases=["token"],
                fallback=(env_fallback, ["CML_API_KEY"]),
            ),
        )

    def init_parameters(self) -> None:
        self.api_key: Optional[str] = self.get_param("api_key")  # type: ignore[attr-defined]


class MlServicesModule(ServicesModule, CmlAuthMixin):
    """Base class for CML (``ml_*``) modules using bearer-token authentication."""

    def build_api_client(self) -> ServicesClient:
        return CmlServicesClient(
            module=self.module,
            timeout=self.timeout,
            default_page_size=self.page_size,
            cookies=CookieJar(),
        )


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@dataclass
class MlProject:
    """A CML project."""

    name: str
    id: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    visibility: Union[str, None, NULLABLE] = NULLABLE
    environment: Union[Dict[str, Any], str, None, NULLABLE] = NULLABLE
    organization_permission: Union[str, None, NULLABLE] = NULLABLE
    parent_project: Union[str, None, NULLABLE] = NULLABLE
    shared_memory_limit: Union[int, None, NULLABLE] = NULLABLE
    default_project_engine_type: Union[str, None, NULLABLE] = NULLABLE
    default_engine_type: Union[str, None, NULLABLE] = NULLABLE
    template: Union[str, None, NULLABLE] = NULLABLE
    git_url: Union[str, None, NULLABLE] = NULLABLE
    git_ref: Union[str, None, NULLABLE] = NULLABLE
    creator: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    updated_at: Union[str, None, NULLABLE] = NULLABLE


class MlProjectClient:
    """CML Project API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_projects(self, **params) -> Dict[str, Any]:
        return self.api_client.get(
            f"/{API_VERSION}/projects",
            params={"include_public_projects": True, **params},
        )

    def list_projects(self) -> List[MlProject]:
        """List all projects accessible to the current user."""
        resp = self._list_projects()
        return [from_dict(MlProject, p) for p in resp.get("projects", [])]

    def describe_project(self, project_id: str) -> Optional[MlProject]:
        """Return a project by ID, or None if it is not found or not accessible."""
        return from_dict(
            MlProject,
            self.api_client.get(
                f"/{API_VERSION}/projects/{project_id}",
                squelch={403: None, 404: None},
            ),
        )

    def create_project(self, project: MlProject) -> MlProject:
        """Create a project."""
        return from_dict(
            MlProject,
            self.api_client.post(f"/{API_VERSION}/projects", data=to_dict(project)),
        )

    def update_project(self, project: MlProject) -> MlProject:
        """Update a project (PATCH). ``project.id`` must be set."""
        return from_dict(
            MlProject,
            self.api_client.patch(
                f"/{API_VERSION}/projects/{project.id}",
                data=to_dict(project),
            ),
        )

    def delete_project(self, project_id: str) -> None:
        """Delete a project by ID."""
        self.api_client.delete(f"/{API_VERSION}/projects/{project_id}")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@dataclass
class MlJob:
    """A CML project job."""

    name: str
    id: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    script: Union[str, None, NULLABLE] = NULLABLE
    arguments: Union[str, None, NULLABLE] = NULLABLE
    kernel: Union[str, None, NULLABLE] = NULLABLE
    cpu: Union[float, None, NULLABLE] = NULLABLE
    memory: Union[float, None, NULLABLE] = NULLABLE
    nvidia_gpu: Union[int, None, NULLABLE] = NULLABLE
    runtime_identifier: Union[str, None, NULLABLE] = NULLABLE
    runtime_addon_identifiers: Union[List[str], None, NULLABLE] = NULLABLE
    attachments: Union[List[str], None, NULLABLE] = NULLABLE
    schedule: Union[str, None, NULLABLE] = NULLABLE
    parent_job_id: Union[str, None, NULLABLE] = NULLABLE
    timeout: Union[int, None, NULLABLE] = NULLABLE
    kill_on_timeout: Union[bool, None, NULLABLE] = NULLABLE
    paused: Union[bool, None, NULLABLE] = NULLABLE
    recipients: Union[List[Dict[str, Any]], None, NULLABLE] = NULLABLE
    environment: Union[Dict[str, Any], str, None, NULLABLE] = NULLABLE
    creator: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    updated_at: Union[str, None, NULLABLE] = NULLABLE


class MlJobClient:
    """CML Job API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_jobs(self, project_id: str, **params) -> Dict[str, Any]:
        return self.api_client.get(
            f"/{API_VERSION}/projects/{project_id}/jobs",
            params=params,
        )

    def list_jobs(self, project_id: str) -> List[MlJob]:
        resp = self._list_jobs(project_id)
        return [from_dict(MlJob, j) for j in resp.get("jobs", [])]

    def describe_job(self, project_id: str, job_id: str) -> Optional[MlJob]:
        return from_dict(
            MlJob,
            self.api_client.get(
                f"/{API_VERSION}/projects/{project_id}/jobs/{job_id}",
                squelch={403: None, 404: None},
            ),
        )

    def create_job(self, project_id: str, job: MlJob) -> MlJob:
        return from_dict(
            MlJob,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/jobs",
                data=to_dict(job),
            ),
        )

    def update_job(self, project_id: str, job: MlJob) -> MlJob:
        return from_dict(
            MlJob,
            self.api_client.patch(
                f"/{API_VERSION}/projects/{project_id}/jobs/{job.id}",
                data=to_dict(job),
            ),
        )

    def delete_job(self, project_id: str, job_id: str) -> None:
        self.api_client.delete(
            f"/{API_VERSION}/projects/{project_id}/jobs/{job_id}",
        )


@dataclass
class MlJobRun:
    """A CML job run."""

    id: Union[str, None, NULLABLE] = NULLABLE
    job_id: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    status: Union[str, None, NULLABLE] = NULLABLE
    arguments: Union[str, None, NULLABLE] = NULLABLE
    environment: Union[Dict[str, Any], str, None, NULLABLE] = NULLABLE
    creator: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    scheduling_at: Union[str, None, NULLABLE] = NULLABLE
    starting_at: Union[str, None, NULLABLE] = NULLABLE
    finished_at: Union[str, None, NULLABLE] = NULLABLE


class MlJobRunClient:
    """CML Job Run API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_job_runs(self, project_id: str, job_id: str, **params) -> Dict[str, Any]:
        return self.api_client.get(
            f"/{API_VERSION}/projects/{project_id}/jobs/{job_id}/runs",
            params=params,
        )

    def list_job_runs(self, project_id: str, job_id: str) -> List[MlJobRun]:
        resp = self._list_job_runs(project_id, job_id)
        return [from_dict(MlJobRun, r) for r in resp.get("job_runs", [])]

    def describe_job_run(
        self,
        project_id: str,
        job_id: str,
        run_id: str,
    ) -> Optional[MlJobRun]:
        return from_dict(
            MlJobRun,
            self.api_client.get(
                f"/{API_VERSION}/projects/{project_id}/jobs/{job_id}/runs/{run_id}",
                squelch={403: None, 404: None},
            ),
        )

    def create_job_run(self, project_id: str, job_id: str, run: MlJobRun) -> MlJobRun:
        return from_dict(
            MlJobRun,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/jobs/{job_id}/runs",
                data=to_dict(run),
            ),
        )

    def stop_job_run(
        self,
        project_id: str,
        job_id: str,
        run_id: str,
    ) -> MlJobRun:
        return from_dict(
            MlJobRun,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/jobs/{job_id}/runs/{run_id}:stop",
            ),
        )


# ---------------------------------------------------------------------------
# Models, builds, and deployments
# ---------------------------------------------------------------------------


@dataclass
class MlModel:
    """A CML model."""

    name: str
    id: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    access_key: Union[str, None, NULLABLE] = NULLABLE
    auth_enabled: Union[bool, None, NULLABLE] = NULLABLE
    creator: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    updated_at: Union[str, None, NULLABLE] = NULLABLE


class MlModelClient:
    """CML Model API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_models(self, project_id: str, **params) -> Dict[str, Any]:
        return self.api_client.get(
            f"/{API_VERSION}/projects/{project_id}/models",
            params=params,
        )

    def list_models(self, project_id: str) -> List[MlModel]:
        resp = self._list_models(project_id)
        return [from_dict(MlModel, m) for m in resp.get("models", [])]

    def describe_model(self, project_id: str, model_id: str) -> Optional[MlModel]:
        return from_dict(
            MlModel,
            self.api_client.get(
                f"/{API_VERSION}/projects/{project_id}/models/{model_id}",
                squelch={403: None, 404: None},
            ),
        )

    def create_model(self, project_id: str, model: MlModel) -> MlModel:
        return from_dict(
            MlModel,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/models",
                data=to_dict(model),
            ),
        )

    def update_model(self, project_id: str, model: MlModel) -> MlModel:
        return from_dict(
            MlModel,
            self.api_client.patch(
                f"/{API_VERSION}/projects/{project_id}/models/{model.id}",
                data=to_dict(model),
            ),
        )

    def delete_model(self, project_id: str, model_id: str) -> None:
        self.api_client.delete(
            f"/{API_VERSION}/projects/{project_id}/models/{model_id}",
        )


@dataclass
class MlModelBuild:
    """A CML model build."""

    id: Union[str, None, NULLABLE] = NULLABLE
    model_id: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    status: Union[str, None, NULLABLE] = NULLABLE
    file_path: Union[str, None, NULLABLE] = NULLABLE
    function_name: Union[str, None, NULLABLE] = NULLABLE
    kernel: Union[str, None, NULLABLE] = NULLABLE
    runtime_identifier: Union[str, None, NULLABLE] = NULLABLE
    runtime_addon_identifiers: Union[List[str], None, NULLABLE] = NULLABLE
    comment: Union[str, None, NULLABLE] = NULLABLE
    crn: Union[str, None, NULLABLE] = NULLABLE
    creator: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    updated_at: Union[str, None, NULLABLE] = NULLABLE


class MlModelBuildClient:
    """CML Model Build API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_builds(self, project_id: str, model_id: str, **params) -> Dict[str, Any]:
        return self.api_client.get(
            f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds",
            params=params,
        )

    def list_builds(self, project_id: str, model_id: str) -> List[MlModelBuild]:
        resp = self._list_builds(project_id, model_id)
        return [from_dict(MlModelBuild, b) for b in resp.get("model_builds", [])]

    def find_latest_build(
        self,
        project_id: str,
        model_id: str,
    ) -> Optional[MlModelBuild]:
        """Return the most recently created build with a ``built`` status."""
        resp = self.api_client.get(
            f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds",
            params={"sort": "-created_at", "search_filter": '{"status":"built"}'},
        )
        builds = resp.get("model_builds", []) if isinstance(resp, dict) else []
        return from_dict(MlModelBuild, builds[0]) if builds else None

    def describe_build(
        self,
        project_id: str,
        model_id: str,
        build_id: str,
    ) -> Optional[MlModelBuild]:
        return from_dict(
            MlModelBuild,
            self.api_client.get(
                f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds/{build_id}",
                squelch={403: None, 404: None},
            ),
        )

    def create_build(
        self,
        project_id: str,
        model_id: str,
        build: MlModelBuild,
    ) -> MlModelBuild:
        return from_dict(
            MlModelBuild,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds",
                data=to_dict(build),
            ),
        )

    def delete_build(self, project_id: str, model_id: str, build_id: str) -> None:
        self.api_client.delete(
            f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds/{build_id}",
        )


@dataclass
class MlModelDeployment:
    """A CML model deployment."""

    id: Union[str, None, NULLABLE] = NULLABLE
    build_id: Union[str, None, NULLABLE] = NULLABLE
    model_id: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    status: Union[str, None, NULLABLE] = NULLABLE
    cpu: Union[float, None, NULLABLE] = NULLABLE
    memory: Union[float, None, NULLABLE] = NULLABLE
    nvidia_gpus: Union[int, None, NULLABLE] = NULLABLE
    replicas: Union[int, None, NULLABLE] = NULLABLE
    environment: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    deployer: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    updated_at: Union[str, None, NULLABLE] = NULLABLE


class MlModelDeploymentClient:
    """CML Model Deployment API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_deployments(
        self,
        project_id: str,
        model_id: str,
        build_id: str,
        **params,
    ) -> Dict[str, Any]:
        return self.api_client.get(
            f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds/{build_id}/deployments",
            params=params,
        )

    def list_deployments(
        self,
        project_id: str,
        model_id: str,
        build_id: str,
    ) -> List[MlModelDeployment]:
        resp = self._list_deployments(project_id, model_id, build_id)
        return [
            from_dict(MlModelDeployment, d) for d in resp.get("model_deployments", [])
        ]

    def describe_deployment(
        self,
        project_id: str,
        model_id: str,
        build_id: str,
        deployment_id: str,
    ) -> Optional[MlModelDeployment]:
        return from_dict(
            MlModelDeployment,
            self.api_client.get(
                f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds/{build_id}/deployments/{deployment_id}",
                squelch={403: None, 404: None},
            ),
        )

    def create_deployment(
        self,
        project_id: str,
        model_id: str,
        build_id: str,
        deployment: MlModelDeployment,
    ) -> MlModelDeployment:
        return from_dict(
            MlModelDeployment,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds/{build_id}/deployments",
                data=to_dict(deployment),
            ),
        )

    def delete_deployment(
        self,
        project_id: str,
        model_id: str,
        build_id: str,
        deployment_id: str,
    ) -> None:
        self.api_client.delete(
            f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds/{build_id}/deployments/{deployment_id}",
        )

    def stop_deployment(
        self,
        project_id: str,
        model_id: str,
        build_id: str,
        deployment_id: str,
    ) -> MlModelDeployment:
        return from_dict(
            MlModelDeployment,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/models/{model_id}/builds/{build_id}/deployments/{deployment_id}:stop",
            ),
        )


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------


@dataclass
class MlApplication:
    """A CML application."""

    name: str
    id: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    subdomain: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    script: Union[str, None, NULLABLE] = NULLABLE
    kernel: Union[str, None, NULLABLE] = NULLABLE
    cpu: Union[float, None, NULLABLE] = NULLABLE
    memory: Union[float, None, NULLABLE] = NULLABLE
    nvidia_gpu: Union[int, None, NULLABLE] = NULLABLE
    runtime_identifier: Union[str, None, NULLABLE] = NULLABLE
    runtime_addon_identifiers: Union[List[str], None, NULLABLE] = NULLABLE
    bypass_authentication: Union[bool, None, NULLABLE] = NULLABLE
    environment: Union[Dict[str, Any], str, None, NULLABLE] = NULLABLE
    status: Union[str, None, NULLABLE] = NULLABLE
    creator: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    updated_at: Union[str, None, NULLABLE] = NULLABLE


class MlApplicationClient:
    """CML Application API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_applications(self, project_id: str, **params) -> Dict[str, Any]:
        return self.api_client.get(
            f"/{API_VERSION}/projects/{project_id}/applications",
            params=params,
        )

    def list_applications(self, project_id: str) -> List[MlApplication]:
        resp = self._list_applications(project_id)
        return [from_dict(MlApplication, a) for a in resp.get("applications", [])]

    def describe_application(
        self,
        project_id: str,
        application_id: str,
    ) -> Optional[MlApplication]:
        return from_dict(
            MlApplication,
            self.api_client.get(
                f"/{API_VERSION}/projects/{project_id}/applications/{application_id}",
                squelch={403: None, 404: None},
            ),
        )

    def create_application(
        self,
        project_id: str,
        application: MlApplication,
    ) -> MlApplication:
        return from_dict(
            MlApplication,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/applications",
                data=to_dict(application),
            ),
        )

    def update_application(
        self,
        project_id: str,
        application: MlApplication,
    ) -> MlApplication:
        return from_dict(
            MlApplication,
            self.api_client.patch(
                f"/{API_VERSION}/projects/{project_id}/applications/{application.id}",
                data=to_dict(application),
            ),
        )

    def delete_application(self, project_id: str, application_id: str) -> None:
        self.api_client.delete(
            f"/{API_VERSION}/projects/{project_id}/applications/{application_id}",
        )

    def restart_application(
        self,
        project_id: str,
        application_id: str,
    ) -> MlApplication:
        """Restart an application."""
        return from_dict(
            MlApplication,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/applications/{application_id}:restart",
            ),
        )

    def stop_application(
        self,
        project_id: str,
        application_id: str,
    ) -> MlApplication:
        """Stop an application."""
        return from_dict(
            MlApplication,
            self.api_client.post(
                f"/{API_VERSION}/projects/{project_id}/applications/{application_id}:stop",
            ),
        )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@dataclass
class MlFile:
    """A file or directory within a CML project."""

    path: str
    is_dir: Union[bool, None, NULLABLE] = NULLABLE
    file_size: Union[str, None, NULLABLE] = NULLABLE


class MlProjectFileClient:
    """CML Project Files API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    def list_files(self, project_id: str, path: str = "") -> List[MlFile]:
        """List the files/directories within a project path."""
        resp = self.api_client.get(
            f"/{API_VERSION}/projects/{project_id}/files/{path}",
            squelch={403: None, 404: None},
        )
        return [from_dict(MlFile, f) for f in (resp or {}).get("files", [])]

    def upload_file(
        self,
        project_id: str,
        path: str,
        content: Optional[str] = None,
        src: Optional[str] = None,
    ) -> None:
        """Upload a file to a project.

        The multipart form field name is the destination path (relative to the
        project root), matching the CML API's ``UploadFile`` contract.
        """
        if src is not None:
            part: Dict[str, Any] = {"filename": src}
        else:
            part = {"content": content or "", "filename": path.rsplit("/", 1)[-1]}

        self.api_client.post(
            f"/{API_VERSION}/projects/{project_id}/files",
            data={path: part},
            format="multipart",
        )

    def delete_file(self, project_id: str, path: str) -> None:
        """Delete a file from a project."""
        self.api_client.delete(
            f"/{API_VERSION}/projects/{project_id}/files/{path}",
        )


# ---------------------------------------------------------------------------
# Runtimes (read-only)
# ---------------------------------------------------------------------------


@dataclass
class MlRuntime:
    """A CML runtime."""

    image_identifier: Union[str, None, NULLABLE] = NULLABLE
    edition: Union[str, None, NULLABLE] = NULLABLE
    kernel: Union[str, None, NULLABLE] = NULLABLE
    editor: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    full_version: Union[str, None, NULLABLE] = NULLABLE
    status: Union[str, None, NULLABLE] = NULLABLE
    register_user_id: Union[int, None, NULLABLE] = NULLABLE
    runtime_metadata_version: Union[int, None, NULLABLE] = NULLABLE


@dataclass
class MlRuntimeRegistration:
    """The result of registering a custom CML runtime."""

    validation_success: Union[bool, None, NULLABLE] = NULLABLE
    insert_success: Union[bool, None, NULLABLE] = NULLABLE
    reason: Union[str, None, NULLABLE] = NULLABLE
    reason_data: Union[str, None, NULLABLE] = NULLABLE
    details: Union[Dict[str, Any], None, NULLABLE] = NULLABLE


@dataclass
class MlRuntimeValidation:
    """The result of validating a custom CML runtime image."""

    success: Union[bool, None, NULLABLE] = NULLABLE
    reason: Union[str, None, NULLABLE] = NULLABLE
    reason_data: Union[str, None, NULLABLE] = NULLABLE
    details: Union[Dict[str, Any], None, NULLABLE] = NULLABLE


class MlRuntimeClient:
    """CML Runtime API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_runtimes(self, **params) -> Dict[str, Any]:
        return self.api_client.get(f"/{API_VERSION}/runtimes", params=params)

    def list_runtimes(self) -> List[MlRuntime]:
        resp = self._list_runtimes()
        return [from_dict(MlRuntime, r) for r in resp.get("runtimes", [])]

    def validate_runtime(
        self,
        url: str,
        docker_credential_id: Optional[str] = None,
    ) -> MlRuntimeValidation:
        """Validate a custom runtime image by registry URL."""
        params: Dict[str, Any] = {"url": url}
        if docker_credential_id is not None:
            params["docker_credential_id"] = docker_credential_id
        return from_dict(
            MlRuntimeValidation,
            self.api_client.get(f"/{API_VERSION}/runtimes:validate", params=params),
        )

    def register_runtime(
        self,
        url: str,
        docker_credential_id: Optional[str] = None,
    ) -> MlRuntimeRegistration:
        """Register a custom runtime by registry URL."""
        body: Dict[str, Any] = {"url": url}
        if docker_credential_id is not None:
            body["docker_credential_id"] = docker_credential_id
        return from_dict(
            MlRuntimeRegistration,
            self.api_client.post(f"/{API_VERSION}/runtimes", data=body),
        )

    def update_runtime_status(
        self,
        status: str,
        runtime_id: Optional[List[int]] = None,
        image_identifier: Optional[List[str]] = None,
    ) -> int:
        """Update the status of selected runtimes; returns rows affected."""
        body: Dict[str, Any] = {"status": status}
        if runtime_id is not None:
            body["runtime_id"] = runtime_id
        if image_identifier is not None:
            body["image_identifier"] = image_identifier
        resp = self.api_client.post(f"/{API_VERSION}/runtimes:update", data=body)
        return resp.get("rows_affected", 0) if isinstance(resp, dict) else 0

    def set_docker_credential(
        self,
        docker_credential_id: str,
        runtime_identifier: str,
    ) -> None:
        """Set a Docker credential for a runtime."""
        self.api_client.post(
            f"/{API_VERSION}/runtimes/credential:set",
            data={
                "docker_credential_id": docker_credential_id,
                "runtime_identifier": runtime_identifier,
            },
        )


@dataclass
class MlRuntimeAddon:
    """A CML runtime addon."""

    identifier: Union[str, None, NULLABLE] = NULLABLE
    component: Union[str, None, NULLABLE] = NULLABLE
    display_name: Union[str, None, NULLABLE] = NULLABLE
    status: Union[str, None, NULLABLE] = NULLABLE
    manageable: Union[bool, None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    id: Union[int, None, NULLABLE] = NULLABLE
    reason: Union[str, None, NULLABLE] = NULLABLE


class MlRuntimeAddonClient:
    """CML Runtime Addon API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_runtime_addons(self, **params) -> Dict[str, Any]:
        return self.api_client.get(f"/{API_VERSION}/runtimeaddons", params=params)

    def list_runtime_addons(self) -> List[MlRuntimeAddon]:
        resp = self._list_runtime_addons()
        return [from_dict(MlRuntimeAddon, a) for a in resp.get("runtime_addons", [])]

    def update_addon_status(
        self,
        status: str,
        ids: Optional[List[int]] = None,
        identifiers: Optional[List[str]] = None,
    ) -> int:
        """Update the status of selected runtime addons; returns rows affected."""
        body: Dict[str, Any] = {"status": status}
        if ids is not None:
            body["ids"] = ids
        if identifiers is not None:
            body["identifiers"] = identifiers
        resp = self.api_client.post(
            f"/{API_VERSION}/runtimeaddons:updatestatus",
            data=body,
        )
        return resp.get("rows_affected", 0) if isinstance(resp, dict) else 0


@dataclass
class MlRuntimeRepo:
    """A CML runtime repository."""

    id: Union[int, None, NULLABLE] = NULLABLE
    name: Union[str, None, NULLABLE] = NULLABLE
    url: Union[str, None, NULLABLE] = NULLABLE


class MlRuntimeRepoClient:
    """CML Runtime Repository API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    @_cml_paginated
    def _list_runtime_repos(self, **params) -> Dict[str, Any]:
        return self.api_client.get(f"/{API_VERSION}/runtimerepos", params=params)

    def list_runtime_repos(self) -> List[MlRuntimeRepo]:
        resp = self._list_runtime_repos()
        return [from_dict(MlRuntimeRepo, r) for r in resp.get("runtimerepos", [])]

    def create_runtime_repo(self, repo: MlRuntimeRepo) -> MlRuntimeRepo:
        return from_dict(
            MlRuntimeRepo,
            self.api_client.post(
                f"/{API_VERSION}/runtimerepos",
                data={"name": repo.name, "url": repo.url},
            ),
        )

    def update_runtime_repo(self, repo: MlRuntimeRepo) -> MlRuntimeRepo:
        """Update a runtime repo (PATCH). ``repo.id`` must be set."""
        return from_dict(
            MlRuntimeRepo,
            self.api_client.patch(
                f"/{API_VERSION}/runtimerepos/{repo.id}",
                data=to_dict(repo),
            ),
        )

    def delete_runtime_repo(self, repo_id: int) -> None:
        self.api_client.delete(f"/{API_VERSION}/runtimerepos/{repo_id}")


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_project_id(id: str) -> bool:
    """Validate a CML project ID of the form ``xxxx-xxxx-xxxx-xxxx``."""
    pattern = re.compile("^(?:[a-z0-9]{4}-){3}[a-z0-9]{4}$")
    return True if pattern.fullmatch(id) else False


def validate_subdomain(subdomain: str) -> bool:
    """Validate an application subdomain (lowercase alphanumerics with internal hyphens)."""
    pattern = re.compile("^[a-z0-9]+(-[a-z0-9]+)*$")
    return True if pattern.fullmatch(subdomain) else False
