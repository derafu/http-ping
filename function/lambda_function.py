"""
AWS Lambda handler: performs HTTP requests to the configured URL(s).

Environment variables:
  HTTP_PING_URL      One or more URLs to request (space-separated, required)
  HTTP_PING_METHOD   HTTP method (default: GET)
  HTTP_PING_AUTH     Full Authorization header value
  HTTP_PING_TOKEN    Token auth shortcut — sets Authorization: Token <value>
  HTTP_PING_BEARER   Bearer auth shortcut — sets Authorization: Bearer <value>
  HTTP_PING_BODY     JSON body for POST requests (as a JSON string)
  HTTP_PING_TIMEOUT  Request timeout in seconds (default: 30)
  HTTP_PING_RETRIES  Number of retries on failure (default: 3)
  HTTP_PING_BACKOFF  Base backoff in seconds between retries (default: 1.0)

Response body:
  Single URL    → dict
  Multiple URLs → list of dicts (one per URL, includes "url" key)
"""

import json
import os
from http import HTTPStatus

from http_ping import HttpAuth, HttpPing, HttpPingBatch, HttpRequest


def _auth_from_env() -> str | None:
    if auth := os.environ.get("HTTP_PING_AUTH"):
        return auth
    if token := os.environ.get("HTTP_PING_TOKEN"):
        return HttpAuth.token(token)
    if bearer := os.environ.get("HTTP_PING_BEARER"):
        return HttpAuth.bearer(bearer)
    return None


def lambda_handler(event, context):
    """Read environment variables, run HTTP ping, return Lambda response."""
    urls = os.environ.get("HTTP_PING_URL", "").split()
    if not urls:
        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "body": json.dumps({"error": "HTTP_PING_URL must be set"}),
        }

    method = os.environ.get("HTTP_PING_METHOD", "GET").upper()
    timeout = float(os.environ.get("HTTP_PING_TIMEOUT", "30"))
    retries = int(os.environ.get("HTTP_PING_RETRIES", "3"))
    backoff = float(os.environ.get("HTTP_PING_BACKOFF", "1.0"))

    body_raw = os.environ.get("HTTP_PING_BODY")
    body = json.loads(body_raw) if body_raw else None

    auth = _auth_from_env()
    http_requests = [
        HttpRequest(
            url=url,
            method=method,
            headers={"Accept": "application/json"},
            body=body,
            timeout=timeout,
            auth=auth,
        )
        for url in urls
    ]

    if len(http_requests) == 1:
        ping = HttpPing(http_requests[0], retries=retries, backoff=backoff)
        result = ping.run()
        status_code = result["status_code"]
    else:
        batch = HttpPingBatch(
            http_requests, retries=retries, backoff=backoff
        )
        result = batch.run()
        # Use the highest status code as the Lambda response status.
        status_code = max(
            (r.get("status_code", HTTPStatus.INTERNAL_SERVER_ERROR)
             for r in result),
            default=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    return {
        "statusCode": status_code,
        "body": json.dumps(result),
    }


if __name__ == "__main__":
    out = lambda_handler(None, None)
    print(json.dumps(out, indent=2))
