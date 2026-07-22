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

from ansible_collections.cloudera.services.plugins.module_utils.common import paginated


class _CamelPager:
    """Uses the default (camelCase) pagination convention."""

    page_size = 50

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    @paginated()
    def list(self, **params):
        self.calls.append(params)
        return self.pages[len(self.calls) - 1]


class _SnakePager:
    """Uses the CML (snake_case) pagination convention."""

    page_size = 100

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    @paginated(
        next_key="next_page_token",
        token_param="page_token",
        size_param="page_size",
    )
    def list(self, **params):
        self.calls.append(params)
        return self.pages[len(self.calls) - 1]


def test_camel_case_default_unchanged():
    pager = _CamelPager(
        [
            {"items": [1], "nextPageToken": "a"},
            {"items": [2]},
        ],
    )
    result = pager.list()

    assert result["items"] == [1, 2]
    assert pager.calls == [
        {"pageSize": 50},
        {"pageToken": "a", "pageSize": 50},
    ]


def test_camel_case_single_page():
    pager = _CamelPager([{"items": [1, 2]}])
    result = pager.list()

    assert result == {"items": [1, 2]}
    assert len(pager.calls) == 1


def test_empty_token_on_first_page_single_call():
    """A present-but-empty token on the first page does not trigger another call."""
    pager = _SnakePager([{"projects": [1, 2], "next_page_token": ""}])
    result = pager.list()

    assert result["projects"] == [1, 2]
    # Single-page response is passed through unchanged; the empty token is inert.
    assert not result.get("next_page_token")
    assert len(pager.calls) == 1


def test_empty_token_on_last_page_terminates():
    """A present-but-empty token on a later page terminates pagination (no infinite loop)."""
    pager = _SnakePager(
        [
            {"projects": [1], "next_page_token": "t1"},
            {"projects": [2], "next_page_token": ""},
        ],
    )
    result = pager.list()

    assert result["projects"] == [1, 2]
    assert "next_page_token" not in result
    assert len(pager.calls) == 2


def test_none_token_on_last_page_terminates():
    """A None token on a later page terminates pagination."""
    pager = _SnakePager(
        [
            {"projects": [1], "next_page_token": "t1"},
            {"projects": [2], "next_page_token": None},
        ],
    )
    result = pager.list()

    assert result["projects"] == [1, 2]
    assert len(pager.calls) == 2


def test_snake_case_next_page_token():
    pager = _SnakePager(
        [
            {"projects": [1, 2], "next_page_token": "t1"},
            {"projects": [3], "next_page_token": "t2"},
            {"projects": [4]},
        ],
    )
    result = pager.list()

    assert result["projects"] == [1, 2, 3, 4]
    assert "next_page_token" not in result
    assert pager.calls == [
        {"page_size": 100},
        {"page_token": "t1", "page_size": 100},
        {"page_token": "t2", "page_size": 100},
    ]
