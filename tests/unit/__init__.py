# -*- coding: utf-8 -*-
#
# Copyright 2026 Cloudera, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

from collections.abc import Mapping
from functools import wraps
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode
from urllib.error import HTTPError
from http.client import HTTPResponse

from ansible.module_utils.urls import Request

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesClient,
)


class AnsibleFailJson(Exception, Mapping):
    """Exception class to be raised by module.fail_json and caught by the test case"""

    def __init__(self, kwargs):
        super(AnsibleFailJson, self).__init__(
            kwargs.get("msg", "General module failure"),
        )
        self.__dict__.update(kwargs)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)


class AnsibleExitJson(Exception, Mapping):
    """Exception class to be raised by module.exit_json and caught by the test case"""

    def __init__(self, kwargs):
        super(AnsibleExitJson, self).__init__(
            kwargs.get("msg", "General module success"),
        )
        self.__dict__.update(kwargs)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)


def handle_response(func):
    """Decorator to handle HTTP response parsing and error squelching."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        squelch = kwargs.get("squelch", {})
        try:
            response: HTTPResponse = func(*args, **kwargs)
            if response:
                response_text = response.read().decode("utf-8")
                if response_text:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        return {"response": response_text}
                else:
                    return {}
            else:
                return {}
        except HTTPError as e:
            if e.code in squelch:
                return squelch[e.code]
            else:
                raise

    return wrapper


class TestServicesClient(ServicesClient):
    def __init__(
        self,
        endpoint: str,
        port: int,
        headers: Dict[str, str] = {},
    ):
        super().__init__(
            default_page_size=100,
        )
        self.request = Request(http_agent="TestServicesClient/1.0")
        self.endpoint = endpoint.rstrip("/")
        self.port = port

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.headers.update(headers)

    @handle_response
    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        # Prepare query parameters
        if params:
            path += "?" + urlencode(params)

        url = f"{self.endpoint}/{path.strip('/')}"

        return Request().get(
            url=url,
            headers=self.headers,
            **kwargs,
        )

    @handle_response
    def post(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        format: str = "json",
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        url = f"{self.endpoint}/{path.strip('/')}"

        return Request().post(
            url=url,
            data=data,
            **kwargs,
        )

    def put(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        url = f"{self.endpoint}/{path.strip('/')}"

        return Request().put(
            url=url,
            headers=self.headers,
            **kwargs,
        )

    def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        url = f"{self.endpoint}/{path.strip('/')}"

        return Request().delete(
            url=url,
            headers=self.headers,
            **kwargs,
        )


# Patch target for stubbing HTTP calls made through ServicesClient.
FETCH_URL = (
    "ansible_collections.cloudera.services.plugins.module_utils.common.fetch_url"
)

ATLAS_ERROR_MESSAGE = "ATLAS-400-00-0AB: type is referenced by other types"


def http_result(mocker, status, body=None):
    """Build a fetch_url (response, info) result for the given status and JSON body."""
    payload = json.dumps(body if body is not None else {})
    resp = mocker.Mock()
    resp.read.return_value = payload.encode("utf-8")
    return resp, {"status": status, "msg": f"HTTP {status}", "body": payload}


def atlas_error_result(mocker):
    """Build a fetch_url result for an Atlas HTTP 400 carrying ATLAS_ERROR_MESSAGE."""
    return http_result(
        mocker,
        400,
        {"errorCode": "ATLAS-400-00-0AB", "errorMessage": ATLAS_ERROR_MESSAGE},
    )
