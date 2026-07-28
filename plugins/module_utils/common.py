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
Shared functions for Cloudera Data Services Ansible modules
"""

import abc
import binascii
import functools
import http.client
import io
import json
import logging
import os
import sys
import time

from dataclasses import asdict, is_dataclass
from http.cookiejar import CookieJar
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)
from urllib.parse import urlencode

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url, url_argument_spec

LOG_FORMAT = "%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s"


T = TypeVar("T")


def from_dict(cls: Type[T], data: Any) -> T:
    """
    Recursively loads a dict into a dataclass
    """

    def _from_dict_recursive(current_cls: Type[Any], current_data: Any) -> Any:
        if current_data is None:
            return None

        origin = get_origin(current_cls)

        if origin is Union:
            # If a Union, check each type in the Union
            for union_arg in get_args(current_cls):
                # Ignore NoneType
                if union_arg is type(None):
                    continue

                # Process only dataclasses (not instances) and Lists
                if isinstance(union_arg, type) and (
                    is_dataclass(union_arg) or get_origin(union_arg) in (list, List)
                ):
                    # If Union contains a dataclass or List, parse accordingly
                    return _from_dict_recursive(union_arg, current_data)
            # If a Union of primitives, return data as-is
            return current_data

        if origin is list or origin is List:
            # If a list, get the item type and parse each item
            item_type = get_args(current_cls)[0]
            if isinstance(current_data, list):
                return [_from_dict_recursive(item_type, item) for item in current_data]
            return []  # or raise error if data isn't a list

        if is_dataclass(current_cls) and isinstance(current_data, dict):
            # Get type hints for all fields in this specific dataclass
            type_hints = get_type_hints(current_cls)

            return current_cls(
                **{
                    field: _from_dict_recursive(
                        type_hints[field],
                        current_data.get(field),
                    )
                    for field in current_data
                    if field in type_hints
                },
            )

        if isinstance(current_data, dict):
            # If a dict, parse each value, assuming keys are strings
            value_cls = get_args(current_cls)[1]
            return {
                k: _from_dict_recursive(value_cls, v) for k, v in current_data.items()
            }

        # Return primitives (int, str, bool)
        return current_data

    return _from_dict_recursive(cls, data)


NULLABLE = object  # Sentinel value to allow explicit None values in to_dict()


def to_dict(instance: Any) -> Dict[str, Any]:
    """
    Recursively convert a dataclass instance to a dictionary, skipping default NULLABLE values.
    NoneType values are included in the dictionary.

    Args:
        instance: The dataclass instance to convert.
    """

    def _skip_none_factory(data):
        return {k: v for k, v in data if v is not NULLABLE}

    if is_dataclass(instance) and not isinstance(instance, type):
        return asdict(instance, dict_factory=_skip_none_factory)

    raise TypeError(f"Expected dataclass type, got {type(instance)}")


def diff_dict(
    prev: Any,
    next: Any,
    filter_nullable: bool = True,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Compare two dataclass instances and return their differences.

    Recursively compares two dataclass instances field by field and returns
    a tuple of dictionaries containing the old and new values for fields that differ.
    Supports nested dataclasses, lists, and primitive types.

    Args:
        prev: The previous dataclass instance to compare from.
        next: The next dataclass instance to compare to.
        filter_nullable: If True, exclude fields with NULLABLE sentinel values from comparison.
            Defaults to True.

    Returns:
        A tuple of two dictionaries (old_values, new_values) containing only the fields
        that differ between the instances. Nested differences are represented as nested
        dictionaries. Empty dictionaries are returned if instances are identical.

    Raises:
        TypeError: If instances are not dataclasses or are of different types.

    Example:
        >>> @dataclass
        ... class Person:
        ...     name: str
        ...     age: int
        >>> old = Person(name="Alice", age=30)
        >>> new = Person(name="Alice", age=31)
        >>> old_diff, new_diff = diff_dict(old, new)
        >>> print(old_diff)
        {'age': 30}
        >>> print(new_diff)
        {'age': 31}
    """

    def _diff_recursive(prev_val: Any, new_val: Any) -> Tuple[Any, Any, bool]:
        """
        Recursively compare values and return (prev_val, new_val, has_diff).

        Returns:
            Tuple of (prev_value, new_value, has_difference)
        """
        # Handle NULLABLE filtering
        if filter_nullable:
            if prev_val is NULLABLE and new_val is NULLABLE:
                return None, None, False
            if prev_val is NULLABLE:
                prev_val = None
            if new_val is NULLABLE:
                new_val = None

        # If both are None, no difference
        if prev_val is None and new_val is None:
            return None, None, False

        # If one is None and the other isn't, there's a difference
        if prev_val is None or new_val is None:
            # Convert dataclass instances to dicts for consistency
            prev_result = (
                to_dict(prev_val)
                if is_dataclass(prev_val) and not isinstance(prev_val, type)
                else prev_val
            )
            new_result = (
                to_dict(new_val)
                if is_dataclass(new_val) and not isinstance(new_val, type)
                else new_val
            )
            return prev_result, new_result, True

        # If both are dataclasses, recursively compare fields
        if is_dataclass(prev_val) and is_dataclass(new_val):
            if type(prev_val) != type(new_val):
                # Different types, convert both to dicts
                prev_result = (
                    to_dict(prev_val) if not isinstance(prev_val, type) else prev_val
                )
                new_result = (
                    to_dict(new_val) if not isinstance(new_val, type) else new_val
                )
                return prev_result, new_result, True

            old_dict = {}
            new_dict = {}
            has_diff = False

            type_hints = get_type_hints(type(prev_val))
            for field_name in type_hints:
                old_field = getattr(prev_val, field_name, NULLABLE)
                new_field = getattr(new_val, field_name, NULLABLE)

                old_result, new_result, field_diff = _diff_recursive(
                    old_field,
                    new_field,
                )

                if field_diff:
                    old_dict[field_name] = old_result
                    new_dict[field_name] = new_result
                    has_diff = True

            if has_diff:
                return old_dict, new_dict, True
            return {}, {}, False

        # If both are lists, compare element by element
        if isinstance(prev_val, list) and isinstance(new_val, list):
            if len(prev_val) != len(new_val):
                # Convert any dataclass instances in the lists to dicts
                prev_result = [
                    (
                        to_dict(item)
                        if is_dataclass(item) and not isinstance(item, type)
                        else item
                    )
                    for item in prev_val
                ]
                new_result = [
                    (
                        to_dict(item)
                        if is_dataclass(item) and not isinstance(item, type)
                        else item
                    )
                    for item in new_val
                ]
                return prev_result, new_result, True

            old_list = []
            new_list = []
            has_diff = False

            for old_item, new_item in zip(prev_val, new_val):
                old_result, new_result, item_diff = _diff_recursive(
                    old_item,
                    new_item,
                )
                if item_diff:
                    old_list.append(old_result)
                    new_list.append(new_result)
                    has_diff = True
                else:
                    # Include unchanged items to maintain list structure
                    # Convert dataclass instances to dicts for consistency
                    old_item_result = (
                        to_dict(old_item)
                        if is_dataclass(old_item) and not isinstance(old_item, type)
                        else old_item
                    )
                    new_item_result = (
                        to_dict(new_item)
                        if is_dataclass(new_item) and not isinstance(new_item, type)
                        else new_item
                    )
                    old_list.append(old_item_result)
                    new_list.append(new_item_result)

            if has_diff:
                return old_list, new_list, True
            return [], [], False

        # If both are dicts, compare key by key
        if isinstance(prev_val, dict) and isinstance(new_val, dict):
            old_dict = {}
            new_dict = {}
            has_diff = False

            all_keys = set(prev_val.keys()) | set(new_val.keys())
            for key in all_keys:
                old_item = prev_val.get(key, None)
                new_item = new_val.get(key, None)

                old_result, new_result, item_diff = _diff_recursive(
                    old_item,
                    new_item,
                )

                if item_diff:
                    old_dict[key] = old_result
                    new_dict[key] = new_result
                    has_diff = True

            if has_diff:
                return old_dict, new_dict, True
            return {}, {}, False

        # For primitives and other types, direct comparison
        if prev_val != new_val:
            return prev_val, new_val, True

        return prev_val, new_val, False

    # Validate inputs
    if not is_dataclass(prev) or isinstance(prev, type):
        raise TypeError(
            f"Expected dataclass instance for prev, got {type(prev)}",
        )

    if not is_dataclass(next) or isinstance(next, type):
        raise TypeError(
            f"Expected dataclass instance for next, got {type(next)}",
        )

    if type(prev) != type(next):
        raise TypeError(
            f"Cannot compare different dataclass types: {type(prev)} vs {type(next)}",
        )

    prev_diff, next_diff, _ = _diff_recursive(prev, next)

    return prev_diff if isinstance(prev_diff, dict) else {}, (
        next_diff
        if isinstance(
            next_diff,
            dict,
        )
        else {}
    )


def paginated(
    default_page_size=100,
    next_key=None,
    token_param="pageToken",
    size_param="pageSize",
):
    """
    Decorator to handle automatic pagination for Cloudera Data Services API methods.

    Usage:
        @paginated()
        def some_api_method(self, param1, param2, startingToken=None, pageSize=None):
            # Method implementation
            pass

        # For snake_case tokens:
        @paginated(next_key="next_page_token", token_param="page_token", size_param="page_size")
        def list_projects(self, page_size=None, page_token=None):
            ...

    Args:
        default_page_size: Default page size to use if not provided.
        next_key: The response field holding the continuation token. If None (default),
            auto-detect "nextPageToken" then "nextToken" (the camelCase convention).
        token_param: The request keyword used to send the continuation token.
        size_param: The request keyword used to send the page size.

    Returns:
        Decorator function
    """

    candidate_keys = (
        [next_key] if next_key is not None else ["nextPageToken", "nextToken"]
    )

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Add default page size if not specified
            paginated_kwargs = kwargs.copy()
            if size_param not in paginated_kwargs:
                # Use instance page size if available, otherwise use decorator default
                page_size = getattr(
                    self,
                    "page_size",
                    default_page_size,
                )
                paginated_kwargs[size_param] = page_size

            # Get the initial response
            response = func(self, *args, **paginated_kwargs)

            if not isinstance(response, dict):
                return response

            # Determine which pagination token is used. A token key that is present
            # but empty (blank string, None, etc.) signals no further pages, so it is
            # treated as absent to avoid looping indefinitely.
            next_token_key = None
            for candidate in candidate_keys:
                if response.get(candidate):
                    next_token_key = candidate
                    break
            else:
                # No populated pagination token found, return as-is
                return response

            # Collect all items from paginated responses
            all_items = {}
            list_keys = []

            # Identify which keys contain lists that need to be combined
            for key, value in response.items():
                if isinstance(value, list):
                    list_keys.append(key)
                    all_items[key] = value.copy()
                else:
                    all_items[key] = value

            # Continue pagination only while the continuation token is present AND
            # populated. An empty/None token ends pagination.
            while all_items.get(next_token_key):
                token = all_items.pop(next_token_key)

                # Add pagination parameters
                paginated_kwargs = kwargs.copy()
                paginated_kwargs[token_param] = token

                # Add default page size if not specified
                if size_param not in paginated_kwargs:
                    # Use instance page size if available, otherwise use decorator default
                    page_size = getattr(
                        self,
                        "page_size",
                        default_page_size,
                    )
                    paginated_kwargs[size_param] = page_size

                # Get next page
                next_page = func(self, *args, **paginated_kwargs)

                if not isinstance(next_page, dict):
                    break

                # Combine list data from this page
                for key in list_keys:
                    if key in next_page and isinstance(next_page[key], list):
                        all_items[key].extend(next_page[key])

                # Update other fields from latest response (including potential token).
                # Skip request-echo keys (pageToken/pageSize or page_token/page_size).
                for key, value in next_page.items():
                    if key not in list_keys and not key.startswith("page"):
                        all_items[key] = value

            # Drop a trailing empty continuation token if the last page carried one.
            if next_token_key in all_items and not all_items[next_token_key]:
                del all_items[next_token_key]

            return all_items

        return wrapper

    return decorator


class ServicesError(Exception):
    """Cloudera Data Services REST API error."""

    def __init__(self, msg: str, status: Optional[int] = None):
        """
        Initialize Cloudera Data Services REST API error.

        Args:
            msg: Error message
            status: HTTP status code (if applicable)
        """
        super().__init__(msg)
        self.msg = msg
        self.status = status

    def __str__(self) -> str:
        return f"[{self.status}] {self.msg}" if self.status else self.msg


class ServicesClient:
    """
    Abstract base class for Cloudera Data Services REST API clients.
    """

    def __init__(self, default_page_size: int = 100):
        """
        Initialize Cloudera Data Services REST client.

        Args:
            default_page_size: Default page size for paginated requests
        """
        self.default_page_size = default_page_size

    # Abstract HTTP methods that must be implemented by subclasses
    @abc.abstractmethod
    def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute HTTP DELETE request.

        Args:
            path: The URL path for the DELETE request
            params: Optional query parameters
            data: Optional JSON body
            squelch: Dictionary to suppress specific HTTP status codes
            passthru: List of HTTP status codes to passthru as-is without handling
            **kwargs: Additional keyword arguments passed directly to the REST client
        """
        pass

    @abc.abstractmethod
    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute HTTP GET request.

        Args:
            path: The URL path for the GET request
            params: Optional query parameters
            squelch: Dictionary to suppress specific HTTP status codes
            passthru: List of HTTP status codes to passthru as-is without handling
            **kwargs: Additional keyword arguments passed directly to the REST client
        """
        pass

    @abc.abstractmethod
    def head(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute HTTP HEAD request.

        Args:
            path: The URL path for the HEAD request
            params: Optional query parameters
            squelch: Dictionary to suppress specific HTTP status codes
            passthru: List of HTTP status codes to passthru as-is without handling
            **kwargs: Additional keyword arguments passed directly to the REST client
        """
        pass

    @abc.abstractmethod
    def options(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute HTTP OPTIONS request.

        Args:
            path: The URL path for the OPTIONS request
            params: Optional query parameters
            data: Optional JSON body
            squelch: Dictionary to suppress specific HTTP status codes
            passthru: List of HTTP status codes to passthru as-is without handling
            **kwargs: Additional keyword arguments passed directly to the REST client
        """
        pass

    @abc.abstractmethod
    def patch(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute HTTP PATCH request.

        Args:
            path: The URL path for the PATCH request
            params: Optional query parameters
            data: Optional JSON body
            squelch: Dictionary to suppress specific HTTP status codes
            passthru: List of HTTP status codes to passthru as-is without handling
            **kwargs: Additional keyword arguments passed directly to the REST client
        """
        pass

    @abc.abstractmethod
    def post(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        format: str = "json",
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute HTTP POST request.

        Args:
            path: The URL path for the POST request
            params: Optional query parameters
            data: Optional body data
            format: Optional format of the body data, e.g., 'json', 'urlencoded', 'multipart'. Defaults to 'json'.
            squelch: Dictionary to suppress specific HTTP status codes
            **kwargs: Additional keyword arguments passed directly to the REST client
        """
        pass

    @abc.abstractmethod
    def put(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute HTTP PUT request.

        Args:
            path: The URL path for the PUT request
            params: Optional query parameters
            data: Optional JSON body
            squelch: Dictionary to suppress specific HTTP status codes
            passthru: List of HTTP status codes to passthru as-is without handling
            **kwargs: Additional keyword arguments passed directly to the REST client
        """
        pass


def format_query_params(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    empty_value: bool = True,
) -> str:
    """
    Format query parameters into a URL-encoded string.
    Handles None values as empty (test=&foo=...) or bare (test?foo...) keys.
    Nested lists are flattened and the key repeated (foo=101&foo=102&...).
    """

    if not params:
        return url

    # Flatten nested lists and prepare for urlencode
    query_params = []
    for key, value in params.items():
        if isinstance(value, list):
            # Flatten nested lists recursively
            def flatten_list(lst):
                flattened = []
                for item in lst:
                    if isinstance(item, list):
                        flattened.extend(flatten_list(item))
                    else:
                        flattened.append(item)
                return flattened

            flattened_values = flatten_list(value)
            for item in flattened_values:
                if item is not None:
                    query_params.append((key, str(item)))
                elif empty_value:
                    query_params.append((key, ""))
                else:
                    query_params.append((key, None))
        else:
            if value is not None:
                query_params.append((key, str(value)))
            elif empty_value:
                query_params.append((key, ""))
            else:
                query_params.append((key, None))

    if query_params:
        # Handle bare keys (None values) manually when empty_value is False
        if not empty_value and any(value is None for key, value in query_params):
            param_strings = []
            for key, value in query_params:
                if value is None:
                    param_strings.append(key)
                else:
                    param_strings.append(f"{key}={value}")
            encoded_params = "&".join(param_strings)
        else:
            encoded_params = urlencode(query_params, doseq=True)
        return f"{url}?{encoded_params}"

    return url


def prepare_urlencoded(form_data: Union[Dict[str, Any], List[Any], str]) -> str:
    """Prepare URL-encoded form data."""

    # If form_data is already a string, return as-is
    if isinstance(form_data, str):
        return form_data

    # If form_data is a list or dictionary, encode it
    output = []
    for key, value in (
        form_data.items() if isinstance(form_data, dict) else enumerate(form_data)
    ):
        output.append((key, value))

    return urlencode(output, doseq=True)


def prepare_multipart_binary(
    form_data: Union[str, Dict[str, Any], List[Any]],
) -> Tuple[str, bytes]:
    """
    Prepare raw binary, multipart form data. Mimics the behavior of Ansible's prepare_multipart().

    Example form data:
        {
            "file1": {
                "filename": "/bin/true",
                "mime_type": "application/octet-stream"
            },
            "file2": {
                "content": "text based file content",
                "filename": "fake.txt",
                "mime_type": "text/plain",
            },
            "text_form_field": "value"
        }

    Args:
        form_data: Dict of form fields. Values can be
            - str/int/etc: Simple text field
            - dict with "content": File content already in memory (str or bytes)
            - dict with "filename": Path to file to read from disk

    Returns:
        Tuple of (content_type, body_bytes) where content_type is the Content-Type header
        value and body_bytes is the raw binary payload.
    """

    if not isinstance(form_data, dict):
        raise TypeError(
            f"Dict is required for multipart format, got {type(form_data).__name__}",
        )

    boundary = binascii.hexlify(os.urandom(16)).decode("ascii")
    boundary_bytes = boundary.encode("utf-8")

    payload = []

    for key, value in form_data.items():
        if isinstance(value, dict):
            # File upload - either from content or from file path
            if "content" in value:
                # File content provided directly
                content = value["content"]
                if isinstance(content, str):
                    content = content.encode("utf-8")
                filename = value.get("filename", key)
                mime_type = value.get("mime_type", "application/octet-stream")

                payload.append(b"--" + boundary_bytes)
                payload.append(
                    f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode(
                        "utf-8",
                    ),
                )
                payload.append(f"Content-Type: {mime_type}".encode("utf-8"))
                payload.append(b"")  # Blank line
                payload.append(content)
            elif "filename" in value:
                # Read file from disk
                filepath = value["filename"]
                filename = os.path.basename(filepath)
                mime_type = value.get("mime_type", "application/octet-stream")
                try:
                    with open(filepath, "rb") as f:
                        content = f.read()
                except IOError as e:
                    raise Exception(f"Could not read file {filepath}: {e}")

                payload.append(b"--" + boundary_bytes)
                payload.append(
                    f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode(
                        "utf-8",
                    ),
                )
                payload.append(f"Content-Type: {mime_type}".encode("utf-8"))
                payload.append(b"")  # Blank line
                payload.append(content)
            else:
                # Dict but no content or filename - treat as text field
                payload.append(b"--" + boundary_bytes)
                payload.append(
                    f'Content-Disposition: form-data; name="{key}"'.encode("utf-8"),
                )
                payload.append(b"")  # Blank line
                payload.append(str(value).encode("utf-8"))
        else:
            # Standard text field
            payload.append(b"--" + boundary_bytes)
            payload.append(
                f'Content-Disposition: form-data; name="{key}"'.encode("utf-8"),
            )
            payload.append(b"")  # Blank line
            payload.append(str(value).encode("utf-8"))

    payload.append(b"--" + boundary_bytes + b"--")
    payload.append(b"")  # Trailing newline

    body = b"\r\n".join(payload)
    content_type = f"multipart/form-data; boundary={boundary}"

    return content_type, body


def format_body(
    data: Optional[Union[Dict[str, Any], List[Any], str]] = None,
    format: Optional[str] = "json",
    headers: Dict[str, str] = {},
) -> Tuple[Dict[str, str], Optional[bytes]]:
    """
    Format the request body based on the specified format and set appropriate headers.

    Args:
        data: Optional request body (dictionary, list, or pre-formatted string) to send in the request body.
        format: Optional format of the request body ('json', 'urlencoded', 'multipart'). Defaults to 'json'.
        headers: Optional dictionary of HTTP headers to set or modify.

    Returns:
        Formatted request body as a string or None if no body is provided.
    """
    body = None

    if format == "json":
        # Encode JSON data if not a string (pre-formmated JSON)
        if data is not None and not isinstance(data, str):
            body = bytes(json.dumps(data), "utf-8")
        elif data is not None:
            body = bytes(data, "utf-8")

        # Set headers for JSON data
        if "content-type" not in (k.lower() for k in headers):
            headers["Content-Type"] = "application/json"
    elif data is not None:
        if format == "urlencoded":
            # Encode form data as URL-encoded TODO Check for parsing errors in prepare_urlencoded() call
            body = bytes(prepare_urlencoded(data), "utf-8")

            # Set headers for URL-encoded data
            if "content-type" not in (k.lower() for k in headers):
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif format == "multipart":
            # Encode form data as multipart binary payload (not base64-encoded)
            try:
                content_type, body = prepare_multipart_binary(data)
            except Exception as e:
                raise ServicesError(f"Failed to prepare multipart form data: {str(e)}")

            # Set headers for multipart data
            if "content-type" not in (k.lower() for k in headers):
                headers["Content-Type"] = str(content_type)
    else:
        raise ServicesError(f"Unsupported form format: {format}")

    # Set Content-Length header if body is present
    if body is not None:
        headers["Content-Length"] = str(len(body))

    return headers, body


class AnsibleServicesClient(ServicesClient):
    """Ansible-based Cloudera Data Services client using native Ansible HTTP methods."""

    def __init__(
        self,
        module: AnsibleModule,
        # endpoint_url: str,
        proxy_context_path: Optional[str] = None,
        default_page_size: int = 100,
        headers: Dict[str, str] = {},
        force: bool = False,  # Set cache-control to no-cache
        timeout: int = 60,
        cookies: Optional[CookieJar] = None,
        ca_path: Optional[str] = None,
        ciphers: Optional[str] = None,
    ):
        """
        Initialize Cloudera Data Services client with Ansible module.

        Args:
            module: AnsibleModule instance
            endpoint_url: Base URL for the Cloudera Data Services API endpoint
            timeout_seconds: Request timeout in seconds
            proxy_context_path: Optional Cloudera Data Services proxy context path
            default_page_size: Default page size for paginated requests
        """
        super().__init__(default_page_size=default_page_size)

        # Endpoint
        self.module = module
        self.endpoint_url = self.module.params[
            "url"
        ].rstrip(  # pyright: ignore[reportArgumentType]
            "/",
        )

        # Cache and timeout
        self.force = force
        self.timeout = timeout

        # Proxy settings
        self.proxy_context_path = proxy_context_path

        # Cookies
        self.cookies = cookies

        # TLS/SSL settings
        self.ca_path = ca_path
        self.ciphers = ciphers

        # Headers
        self.headers = headers

    def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        format: str = "json",
        headers: Dict[str, str] = {},
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        max_retries: int = 5,
        **kwargs,
    ) -> Any:
        """
        Make HTTP request with retry logic and minimal return code handling using Ansible's fetch_url().

        Args:
            method: HTTP method (DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT)
            path: Path appended to the Cloudera Data Services API endpoint
            params: Optional URL query parameters
            data: Optional form data (dictionary or list) to send in the request body. Formatted per 'format'
                parameter.
            format: Optional format of the form data ('json', 'urlencoded', 'multipart'). Defaults to 'json'.
                Headers will be set accordingly.
            max_retries: Maximum number of retry attempts
            headers: Additional HTTP headers to merge with constructed headers
            squelch: Dictionary of HTTP status codes to squelch with default return values
            passthru: List of HTTP status codes to passthru as-is without handling
            **kwargs: Additional keyword arguments passed directly to fetch_url(), e.g. use_gssapi
        Returns:
            Response data as dictionary or None for HTTP 204 responses

        Raises:
            AnsibleModule.fail_json: On HTTP errors or connection failures
        """

        try:
            # Construct the URL
            url = f"{self.endpoint_url}/{path.strip('/')}"

            # Add query parameters to URL if provided
            url = format_query_params(url, params)

            # Prepare headers and the request body if provided
            request_headers = dict(self.headers)
            request_headers.update(headers)

            headers, body = format_body(
                data=data,
                format=format,
                headers=request_headers,
            )

            # Set fallback headers for content
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            if "Accept" not in headers:
                headers["Accept"] = "application/json"

            # Execute request with retry logic and minimal return code handling
            last_error = None
            for attempt in range(max_retries):
                try:
                    resp, info = fetch_url(
                        self.module,
                        url,
                        method=method,
                        headers=headers,
                        data=body,
                        timeout=self.timeout,
                        **kwargs,  # Pass through additional fetch_url() args
                    )

                    status_code = info["status"]

                    # Handle passthru status codes, returning a dictionary of status and body
                    if status_code in passthru:
                        self.module.debug(
                            f"Passthru HTTP {status_code}; {url}",
                        )

                        # fetch_url returns body as bytes in info["body"] for HTTP errors (>=400)
                        if status_code >= 400:
                            return dict(status=status_code, body=info["body"])
                        else:
                            if resp:
                                response_text = resp.read().decode("utf-8")
                                if response_text:
                                    try:
                                        return dict(
                                            status=status_code,
                                            body=json.loads(response_text),
                                        )
                                    except json.JSONDecodeError:
                                        return dict(
                                            status=status_code,
                                            body={"response": response_text},
                                        )
                                else:
                                    return dict(status=status_code, body={})
                            else:
                                return dict(status=status_code, body={})

                    # Handle squelched status codes
                    if status_code in squelch:
                        self.module.debug(
                            f"Squelched HTTP {status_code}; {url}",
                        )
                        return squelch[status_code]

                    # Handle authentication errors
                    if status_code == 401:
                        raise ServicesError(
                            f"Unauthorized Access; {url}",
                            status=401,
                        )

                    if status_code == 403:
                        raise ServicesError(f"Forbidden Access; {url}", status=403)

                    # Handle success responses
                    if 200 <= status_code < 300:
                        # HTTP 204 No Content - return None
                        if status_code == 204:
                            return None

                        if resp:
                            response_text = resp.read().decode("utf-8")
                            if response_text:
                                try:
                                    return json.loads(response_text)
                                except json.JSONDecodeError:
                                    return {"response": response_text}
                            else:
                                return {}
                        else:
                            return {}

                    # Handle error responses
                    error_message = f"HTTP {status_code} Error"
                    if resp:
                        try:
                            error_data = json.loads(info.get("body"))
                            for k in [
                                "error",
                                "error_message",
                                "errorMessage",
                                "message",
                                "msg",
                            ]:
                                if k in error_data:
                                    error_message = error_data[k]
                                    break
                        except:
                            error_message = f"{info.get('msg', 'Unknown error; unparseable response')}"
                    else:
                        try:
                            error_message = info.get(
                                "msg",
                                "Unknown error; no response body",
                            )
                        except:
                            pass

                    # Retry on connection-level failures (fetch_url reports a
                    # dropped/failed connection as a negative status with no
                    # exception), server errors (5xx), or specific client errors.
                    if (
                        status_code < 0
                        or status_code >= 500
                        or status_code in [408, 429]
                    ):
                        if attempt < max_retries - 1:
                            # Exponential backoff: 0.5s, 1s, 2s, 4s, 5s (max)
                            wait_time = min(0.5 * (2**attempt), 5)
                            time.sleep(wait_time)
                            last_error = ServicesError(
                                f"{error_message} for {url}",
                                status=status_code,
                            )
                            continue

                    raise ServicesError(f"{error_message}; {url}", status=status_code)

                except ServicesError:
                    raise
                except Exception as e:
                    # Retry on connection errors
                    if attempt < max_retries - 1:
                        wait_time = min(0.5 * (2**attempt), 5)
                        time.sleep(wait_time)
                        last_error = ServicesError(
                            f"Connection error for {url}: {str(e)}",
                        )
                        continue
                    else:
                        raise ServicesError(
                            f"{str(e)}, request failed after {max_retries} attempts; {url}",
                        )

            # If we exhausted all retries
            if last_error:
                raise last_error
            raise ServicesError(f"Request failed; {url}")
        except Exception as e:
            self.module.fail_json(msg=str(e))

    def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute HTTP DELETE request."""
        return self._make_request(
            "DELETE",
            path,
            params=params,
            data=data,
            squelch=squelch,
            passthru=passthru,
            **kwargs,
        )

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute HTTP GET request."""
        return self._make_request(
            "GET",
            path,
            params=params,
            squelch=squelch,
            passthru=passthru,
            **kwargs,
        )

    def head(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        return self._make_request(
            "HEAD",
            path,
            params=params,
            squelch=squelch,
            passthru=passthru,
            **kwargs,
        )

    def options(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        return self._make_request(
            "OPTIONS",
            path,
            params=params,
            data=data,
            squelch=squelch,
            passthru=passthru,
            **kwargs,
        )

    def patch(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        return self._make_request(
            "PATCH",
            path,
            params=params,
            data=data,
            squelch=squelch,
            passthru=passthru,
            **kwargs,
        )

    def post(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        format: str = "json",
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute HTTP POST request."""
        return self._make_request(
            "POST",
            path,
            params=params,
            data=data,
            format=format,
            squelch=squelch,
            passthru=passthru,
            **kwargs,
        )

    def put(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        squelch: Dict[int, Any] = {},
        passthru: List[int] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute HTTP PUT request."""
        return self._make_request(
            "PUT",
            path,
            params=params,
            data=data,
            squelch=squelch,
            passthru=passthru,
            **kwargs,
        )


class ParametersMixin(abc.ABC):
    """Abstract base class for parameter mixins."""

    @staticmethod
    @abc.abstractmethod
    def get_argument_spec() -> Dict[str, Dict[str, Any]]:
        """Returns the argument spec for the parameter(s)."""
        pass

    @abc.abstractmethod
    def init_parameters(self) -> None:
        """Initialize the parameter value(s)."""
        pass


class MessageParameter(ParametersMixin):
    """Mixin class to add a 'message' parameter to the argument_spec."""

    @staticmethod
    def get_argument_spec() -> Dict[str, Dict[str, Any]]:
        """Returns the argument spec for the message parameter."""
        return {
            "message": dict(required=False, type="str", default=None),
        }

    def init_parameters(self) -> None:
        """Initialize the message parameter value."""
        self.message: Optional[str] = self.get_param("message")  # type: ignore[attr-defined]


class AutoExecuteMeta(abc.ABCMeta):
    """Metaclass that automatically calls execute() after all __init__ methods complete."""

    def __call__(cls, *args, **kwargs):
        # Create the instance normally
        instance = super().__call__(*args, **kwargs)

        # After all __init__ methods have completed, call execute()
        if hasattr(instance, "execute") and callable(instance.execute):
            instance.execute()

        return instance


def get_param(module, param, default=None):
    """Fetches an Ansible input parameter if it exists, else returns optional default or None"""
    if module is not None and module.params is not None:
        return module.params.get(param, default)
    return default


class ServicesModule(abc.ABC, metaclass=AutoExecuteMeta):
    """Base class for Cloudera Data Services Ansible modules."""

    def __init__(
        self,
        argument_spec: Dict[str, Dict[str, Any]] = {},
        bypass_checks: bool = False,
        no_log: bool = False,
        mutually_exclusive: Union[List[str], List[List[str]]] = [],
        required_together: List[List[str]] = [],
        required_one_of: List[List[str]] = [],
        add_file_common_args: bool = False,
        supports_check_mode: bool = False,
        required_if: List[List[Any]] = [],
        required_by: Dict[str, List[str]] = {},
    ):
        """Initializes the base Cloudera Data Services module"""
        super().__init__()

        # Merge in the base url_argument_spec
        merged_argument_spec = dict(argument_spec)
        merged_argument_spec.update(url_argument_spec())

        # Update url parameter with aliases
        merged_argument_spec["url"].update(
            required=True,
            aliases=["endpoint", "endpoint_url"],
        )

        # Update http_agent parameter with default value and aliases
        merged_argument_spec["http_agent"].update(
            default="cloudera-services-module",
            aliases=["user_agent"],
        )

        # Merge in mixin argument specs
        for base in self.__class__.__mro__:
            if hasattr(base, "get_argument_spec") and base != ServicesModule:
                mixin_spec = base.get_argument_spec()
                if mixin_spec:
                    merged_argument_spec.update(mixin_spec)

        # Initialize the Ansible module
        self.module = AnsibleModule(
            argument_spec=dict(
                **merged_argument_spec,
                timeout=dict(
                    required=False,
                    type="int",
                    default=60,
                    aliases=["timeout_seconds"],
                ),
                page_size=dict(
                    required=False,
                    type="int",
                    default=100,
                    aliases=["default_page_size"],
                ),
                debug=dict(
                    required=False,
                    type="bool",
                    default=False,
                    aliases=["debug_endpoints"],
                ),
            ),
            required_together=required_together,
            bypass_checks=bypass_checks,
            no_log=no_log,
            mutually_exclusive=mutually_exclusive,
            required_one_of=required_one_of,
            add_file_common_args=add_file_common_args,
            supports_check_mode=supports_check_mode,
            required_if=required_if,
            required_by=required_by,
        )

        # Initialize common parameters
        self.timeout: int = self.get_param("timeout")
        self.page_size: int = self.get_param("page_size")
        self.debug_log: bool = self.get_param("debug")

        # Initialize mixins parameters
        for base in self.__class__.__mro__:
            if (
                isinstance(base, type)
                and issubclass(base, ParametersMixin)
                and base != ParametersMixin
            ):
                base.init_parameters(self)  # type: ignore[misc]

        # Configure the urllib3 logger
        self.logger = logging.getLogger("cloudera.services")

        # Initialize logging properties
        self.log_out: str = ""
        self.log_lines: List[str] = []
        self.log_capture = None
        self.original_stdout = None
        self.original_stderr = None

        # If debug is enabled, set up logging capture to return in the module output
        if self.debug_log:
            http.client.HTTPConnection.debuglevel = 1
            # http.client.HTTPSConnection.debuglevel = 1

            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)
            root_logger.propagate = True

            self.log_capture = io.StringIO()
            handler = logging.StreamHandler(self.log_capture)

            formatter = logging.Formatter(LOG_FORMAT)
            handler.setFormatter(formatter)

            root_logger.addHandler(handler)

            # Redirect stdout and stderr to capture all output
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr

            sys.stdout = self.log_capture
            sys.stderr = self.log_capture

        self.logger.debug(
            "cloudera.services API agent: %s",
            self.get_param("http_agent"),
        )

        # Create the Ansible REST client with its own cookies and settings
        self.api_client = self.build_api_client()

    def build_api_client(self) -> ServicesClient:
        """Construct the REST client for this module.

        Override to supply an authenticated ``AnsibleServicesClient`` subclass (e.g. one
        that injects a bearer token header). The default returns an unauthenticated
        ``AnsibleServicesClient`` relying on cookie/URL-based authentication.
        """
        return AnsibleServicesClient(
            module=self.module,
            timeout=self.timeout,
            default_page_size=self.page_size,
            cookies=CookieJar(),
        )

    def get_param(self, param, default=None) -> Any:
        if self.module.params is not None and isinstance(self.module.params, dict):
            return self.module.params.get(param, default)
        return default

    @abc.abstractmethod
    def process(self) -> None:
        """Abstract method that Service modules must implement to perform their logic."""
        pass

    def execute(self) -> None:
        """Execute the process method and capture logging output."""
        try:
            # Call the abstract process method
            self.process()
        finally:
            # Restore stdout and stderr if they were redirected
            if self.debug_log and self.original_stdout:
                sys.stdout = self.original_stdout
                sys.stderr = self.original_stderr

            # Capture logging output if debug is enabled and the capture is not empty
            if self.debug_log and self.log_capture:
                captured = self.log_capture.getvalue()
                self.log_out = captured if captured else ""
                self.log_lines = self.log_out.splitlines() if self.log_out else []
