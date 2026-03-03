"""HTTP ping: perform HTTP requests and return status, body and timing."""

import base64
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

import requests


@dataclass
class HttpRequest:

    """Configuration for an HTTP request."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    timeout: float = 30.0
    auth: str | None = None


class HttpAuth:

    """Helpers to build common Authorization header values."""

    @staticmethod
    def token(value: str) -> str:
        """Return an Authorization header value using the Token scheme."""
        return f"Token {value}"

    @staticmethod
    def bearer(value: str) -> str:
        """Return an Authorization header value using the Bearer scheme."""
        return f"Bearer {value}"

    @staticmethod
    def basic(username: str, password: str) -> str:
        """Return an Authorization header value using the Basic scheme."""
        encoded = base64.b64encode(
            f"{username}:{password}".encode()
        ).decode()
        return f"Basic {encoded}"


class HttpPingBatch:

    """
    Executes a list of HttpRequests sequentially and returns a result per URL.

    Uses the same retries and backoff for every request. If a request fails
    after all retries, its result includes an "error" key instead of
    "status_code"/"body"/"elapsed_seconds". Execution continues with the
    remaining URLs regardless of individual failures.
    """

    def __init__(
        self,
        http_requests: list[HttpRequest],
        *,
        retries: int = 3,
        backoff: float = 1.0,
    ) -> None:
        self.http_requests = http_requests
        self.retries = retries
        self.backoff = backoff

    def run(self) -> list[dict[str, Any]]:
        """Execute all requests and return one result dict per URL."""
        results = []
        for req in self.http_requests:
            try:
                ping = HttpPing(
                    req, retries=self.retries, backoff=self.backoff
                )
                result = ping.run()
                result["url"] = req.url
                results.append(result)
            except requests.RequestException as exc:
                results.append({
                    "url": req.url,
                    "error": str(exc),
                    "attempts": self.retries + 1,
                })
        return results


class HttpPing:

    """
    Executes an HttpRequest and returns status code, body and elapsed time.

    Retries automatically on network errors and 5xx responses.
    Backoff between retries doubles each time: backoff, backoff*2, backoff*4, …
    """

    def __init__(
        self,
        request: HttpRequest,
        *,
        retries: int = 3,
        backoff: float = 1.0,
    ) -> None:
        self.request = request
        self.retries = retries
        self.backoff = backoff

    def run(self) -> dict[str, Any]:
        """
        Execute the request with retry logic.

        Returns a dict with:
          - status_code:     int
          - body:            parsed JSON if possible, else str
          - elapsed_seconds: float (last attempt only)
          - attempts:        int
        """
        req = self.request
        headers = dict(req.headers)
        if req.auth:
            headers["Authorization"] = req.auth

        last_exc: Exception | None = None
        last_result: dict[str, Any] | None = None

        for attempt in range(self.retries + 1):
            if attempt > 0:
                time.sleep(self.backoff * (2 ** (attempt - 1)))

            last_exc = None
            try:
                start = time.perf_counter()
                kwargs: dict[str, Any] = {
                    "headers": headers,
                    "timeout": req.timeout,
                }
                if req.body is not None:
                    kwargs["json"] = req.body

                response = requests.request(req.method, req.url, **kwargs)
                elapsed = time.perf_counter() - start

                try:
                    body = response.json()
                except ValueError:
                    body = response.text

                last_result = {
                    "status_code": response.status_code,
                    "body": body,
                    "elapsed_seconds": round(elapsed, 3),
                    "attempts": attempt + 1,
                }

                if response.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
                    return last_result

            except requests.RequestException as exc:
                last_exc = exc
                last_result = None

        if last_exc is not None:
            raise last_exc

        assert last_result is not None
        return last_result
