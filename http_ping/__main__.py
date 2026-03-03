"""
Console entry point: run HTTP ping from the command line.

Environment variables:
  HTTP_PING_URL      One or more URLs to request (space-separated)
  HTTP_PING_METHOD   HTTP method (default: GET)
  HTTP_PING_AUTH     Full Authorization header value
  HTTP_PING_TOKEN    Token auth shortcut — sets Authorization: Token <value>
  HTTP_PING_BEARER   Bearer auth shortcut — sets Authorization: Bearer <value>
  HTTP_PING_BODY     JSON body for POST requests (as a JSON string)
  HTTP_PING_TIMEOUT  Request timeout in seconds (default: 30)
  HTTP_PING_RETRIES  Number of retries on failure (default: 3)
  HTTP_PING_BACKOFF  Base backoff in seconds between retries (default: 1.0)

Output:
  Single URL    → dict
  Multiple URLs → list of dicts (one per URL, includes "url" key)
"""

import argparse
import json
import os
import sys

from http_ping import HttpAuth, HttpPing, HttpPingBatch, HttpRequest


def _auth_from_env() -> str | None:
    if auth := os.environ.get("HTTP_PING_AUTH"):
        return auth
    if token := os.environ.get("HTTP_PING_TOKEN"):
        return HttpAuth.token(token)
    if bearer := os.environ.get("HTTP_PING_BEARER"):
        return HttpAuth.bearer(bearer)
    return None


def main() -> None:
    """Parse arguments and environment, then run HTTP ping."""
    parser = argparse.ArgumentParser(
        description=(
            "HTTP ping: request one or more URLs"
            " and print status, body and timing."
        )
    )
    parser.add_argument(
        "url", nargs="*",
        help="URLs to request (overrides HTTP_PING_URL)",
    )
    parser.add_argument(
        "--method", default=None,
        help="HTTP method (default: GET)",
    )
    parser.add_argument(
        "--timeout", type=float, default=None,
        help="Timeout in seconds",
    )
    parser.add_argument(
        "--retries", type=int, default=None,
        help="Number of retries on failure",
    )
    parser.add_argument(
        "--backoff", type=float, default=None,
        help="Base backoff in seconds",
    )
    args = parser.parse_args()

    urls = args.url or os.environ.get("HTTP_PING_URL", "").split()
    if not urls:
        print(
            "Error: provide at least one URL as argument or set HTTP_PING_URL",
            file=sys.stderr,
        )
        sys.exit(1)

    method = (
        args.method or os.environ.get("HTTP_PING_METHOD", "GET")
    ).upper()
    timeout = (
        args.timeout if args.timeout is not None
        else float(os.environ.get("HTTP_PING_TIMEOUT", "30"))
    )
    retries = (
        args.retries if args.retries is not None
        else int(os.environ.get("HTTP_PING_RETRIES", "3"))
    )
    backoff = (
        args.backoff if args.backoff is not None
        else float(os.environ.get("HTTP_PING_BACKOFF", "1.0"))
    )

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
    else:
        batch = HttpPingBatch(
            http_requests, retries=retries, backoff=backoff
        )
        result = batch.run()

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
