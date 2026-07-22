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


class ModuleDocFragment(object):
    # Shared connection options for Cloudera Machine Learning (CML) modules.
    #
    # This fragment fully restates ``url`` (rather than only the CML-specific delta) so that,
    # when a module lists it *before* ``cloudera.services.services_client``, Ansible's fragment
    # merge (a shallow per-key update where the earlier-listed fragment wins) keeps the CML
    # aliases and environment fallback.
    DOCUMENTATION = r"""
options:
    url:
        description:
            - The base URL of the CML Workspace API endpoint, including the port if necessary.
            - If not set, the value of the E(CML_ENDPOINT) environment variable is used.
        type: str
        required: true
        aliases:
            - endpoint
            - endpoint_url
            - workspace_url
    api_key:
        description:
            - The CML API key (bearer token) used to authenticate to the Workspace API.
            - If not set, the value of the E(CML_API_KEY) environment variable is used.
        type: str
        required: true
        aliases:
            - token
"""
