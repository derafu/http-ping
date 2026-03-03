"""
Tests for http_ping.

Unit tests cover HttpAuth (pure functions, no I/O).
Integration tests cover HttpPing and HttpPingBatch against derafu.dev
"""

import base64
from http import HTTPStatus

from http_ping import HttpAuth, HttpPing, HttpPingBatch, HttpRequest

TEST_URL = "https://www.derafu.dev"


class TestHttpAuth:

    """Unit tests for HttpAuth header helpers."""

    def test_token(self):
        assert HttpAuth.token("abc") == "Token abc"

    def test_bearer(self):
        assert HttpAuth.bearer("abc") == "Bearer abc"

    def test_basic(self):
        expected = "Basic " + base64.b64encode(b"user:pass").decode()
        assert HttpAuth.basic("user", "pass") == expected


class TestHttpPing:

    """Integration tests: single URL."""

    def test_get(self):
        result = HttpPing(HttpRequest(url=TEST_URL)).run()
        assert result["status_code"] == HTTPStatus.OK
        assert result["elapsed_seconds"] > 0
        assert result["attempts"] == 1


class TestHttpPingBatch:

    """Integration tests: multiple URLs."""

    def test_two_urls(self):
        http_requests = [
            HttpRequest(url=TEST_URL),
            HttpRequest(url=TEST_URL),
        ]
        results = HttpPingBatch(http_requests).run()
        assert len(results) == len(http_requests)
        for result in results:
            assert result["status_code"] == HTTPStatus.OK
            assert result["url"] == TEST_URL
