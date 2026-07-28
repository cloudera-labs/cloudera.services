#!/usr/bin/python
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

DOCUMENTATION = r"""
module: ml_runtime
short_description: Register or set the status of a Cloudera Machine Learning (CML) runtime
description:
  - Register a custom Cloudera Machine Learning (CML) runtime from a container image, or
    set the status of existing runtimes.
  - There is no hard delete for runtimes; set O(status=DISABLED) to retire a runtime.
  - The module supports C(check_mode).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.0.0"
options:
  image_url:
    description:
      - The container registry URL of the custom runtime image to register.
      - Mutually exclusive with O(status).
    type: str
    required: false
    aliases:
      - registry_url
  docker_credential_id:
    description:
      - The identifier of the Docker credential to use when registering the image.
    type: str
    required: false
  validate:
    description:
      - Whether to validate the runtime image before registering it.
    type: bool
    required: false
    default: false
  image_identifier:
    description:
      - The image identifier of an existing runtime to target for a status change.
      - Used with O(status).
    type: str
    required: false
  runtime_id:
    description:
      - The numeric identifier of an existing runtime to target for a status change.
      - Used with O(status).
    type: int
    required: false
  status:
    description:
      - The status to set on the target runtime(s).
      - Requires O(image_identifier) or O(runtime_id).
      - Mutually exclusive with O(image_url).
    type: str
    required: false
    choices:
      - ENABLED
      - DISABLED
      - DEPRECATED
extends_documentation_fragment:
  - cloudera.services.ml_client
  - cloudera.services.services_client
"""

EXAMPLES = r"""
- name: Register a custom runtime
  cloudera.services.ml_runtime:
    url: "https://ml-workspace.example.com"
    api_key: "{{ cml_api_key }}"
    image_url: registry.example.com/custom-runtime:1.0
    validate: true

- name: Disable a runtime by image identifier
  cloudera.services.ml_runtime:
    image_identifier: registry.example.com/custom-runtime:1.0
    status: DISABLED
"""

RETURN = r"""
runtime:
  description:
    - The result of the operation.
    - For a registration, the validation/insert result and image details.
    - For a status change, the number of rows affected and the applied status.
  returned: always
  type: dict
sdk_out:
  description: Returns the captured REST API log.
  returned: when supported
  type: str
sdk_out_lines:
  description: Returns a list of each line of the captured REST API log.
  returned: when supported
  type: list
  elements: str
"""

from typing import Any, Dict, NoReturn

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlServicesModule,
    MlRuntimeClient,
)


class MlRuntimeModule(MlServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                image_url=dict(type="str", required=False, aliases=["registry_url"]),
                docker_credential_id=dict(type="str", required=False),
                validate=dict(type="bool", required=False, default=False),
                image_identifier=dict(type="str", required=False),
                runtime_id=dict(type="int", required=False),
                status=dict(
                    type="str",
                    required=False,
                    choices=["ENABLED", "DISABLED", "DEPRECATED"],
                ),
            ),
            mutually_exclusive=[["image_url", "status"]],
            required_one_of=[["image_url", "status"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.image_url = self.get_param("image_url")
        self.docker_credential_id = self.get_param("docker_credential_id")
        self.validate = self.get_param("validate")
        self.image_identifier = self.get_param("image_identifier")
        self.runtime_id = self.get_param("runtime_id")
        self.status = self.get_param("status")

        # TODO Add diff support for runtime registration and status change operations.
        # Initialize the return values
        self.changed = False
        self.diff = {"before": {}, "after": {}}
        self.runtime: Dict[str, Any] = {}

    def _fail(self, msg: str) -> NoReturn:
        # AnsibleModule.fail_json raises SystemExit at runtime; the trailing
        # raise is unreachable but marks this method as NoReturn so the type
        # checker can narrow values validated ahead of a failure.
        self.module.fail_json(msg=msg)
        raise SystemExit(msg)

    def _register(self, client: MlRuntimeClient) -> None:
        if self.validate:
            validation = client.validate_runtime(
                self.image_url,
                self.docker_credential_id,
            )
            if validation.success is False:
                self._fail("Runtime validation failed: %s" % validation.reason)

        if self.module.check_mode:
            self.changed = True
            self.runtime = {"image_url": self.image_url}
            return

        registration = client.register_runtime(
            self.image_url,
            self.docker_credential_id,
        )
        if registration.validation_success is False:
            self._fail("Runtime registration failed: %s" % registration.reason)
        # insert_success is False when the runtime is already registered.
        self.changed = bool(registration.insert_success)
        self.runtime = to_dict(registration)

    def _set_status(self, client: MlRuntimeClient) -> None:
        if self.image_identifier is None and self.runtime_id is None:
            self._fail(
                "One of 'image_identifier' or 'runtime_id' is required with 'status'.",
            )

        if self.module.check_mode:
            self.changed = True
            self.runtime = {"status": self.status}
            return

        rows = client.update_runtime_status(
            self.status,
            runtime_id=[self.runtime_id] if self.runtime_id is not None else None,
            image_identifier=(
                [self.image_identifier] if self.image_identifier is not None else None
            ),
        )
        self.changed = rows > 0
        self.runtime = {"rows_affected": rows, "status": self.status}

    def process(self) -> None:
        client = MlRuntimeClient(self.api_client)
        if self.image_url:
            self._register(client)
        else:
            self._set_status(client)


def main():
    result = MlRuntimeModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        runtime=result.runtime,
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
