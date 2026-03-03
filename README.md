# Derafu: http-ping ("A tank for a fly")

Perform HTTP requests (GET, POST, …) and get status code, response body and timing. Includes automatic retry with exponential backoff. Useful for scheduled triggers, health checks, and smoke tests.

## Basic use case: scheduled trigger (e.g. Celery beat)

On AWS Elastic Beanstalk, Celery's built-in **beat** only runs on the leader instance. With auto-scaling, the leader can change and beat may not run, so scheduled tasks never fire.

**Approach:** Expose an HTTP endpoint that triggers your tasks. Call that endpoint on a schedule from **AWS Lambda** (e.g. via EventBridge). This project provides the Lambda code and a small **http-ping** module that performs the request and returns the result.

You keep responsibility for ensuring each logical task runs only once in your own code when handling the request.

## Classes

### `HttpRequest`

Value object holding the request configuration:

```python
from http_ping import HttpRequest

request = HttpRequest(
    url="https://example.com/api/beat",
    method="POST",                    # default: "GET"
    headers={"Accept": "application/json"},
    body={"task": "run"},             # serialized as JSON; default: None
    timeout=30.0,                     # seconds; default: 30.0
    auth="Token abc123",              # full Authorization header value; default: None
)
```

### `HttpAuth`

Helpers to build common `Authorization` header values:

```python
from http_ping import HttpAuth

HttpAuth.token("abc123")             # → "Token abc123"
HttpAuth.bearer("abc123")            # → "Bearer abc123"
HttpAuth.basic("user", "pass")       # → "Basic dXNlcjpwYXNz"
```

Pass the result to `HttpRequest(auth=...)`.

### `HttpPing`

Executes an `HttpRequest` with optional retry and exponential backoff:

```python
from http_ping import HttpAuth, HttpPing, HttpRequest

request = HttpRequest(
    url="https://example.com/api/beat",
    auth=HttpAuth.token("abc123"),
)
result = HttpPing(request, retries=3, backoff=1.0).run()
```

`run()` retries on network errors and 5xx responses. Backoff between retries: `backoff`, `backoff*2`, `backoff*4`, …

Returns a dict:

```json
{
  "status_code": 200,
  "body": { "…": "…" },
  "elapsed_seconds": 0.234,
  "attempts": 1
}
```

`body` is parsed JSON if possible, otherwise a string.

### `HttpPingBatch`

Executes a list of `HttpRequest` objects sequentially, sharing the same retry config. Individual failures are captured per URL without aborting the rest:

```python
from http_ping import HttpAuth, HttpPingBatch, HttpRequest

requests = [
    HttpRequest(url="https://example.com/api/health", auth=HttpAuth.token("abc123")),
    HttpRequest(url="https://example.com/api/beat",   auth=HttpAuth.token("abc123")),
]
results = HttpPingBatch(requests, retries=3, backoff=1.0).run()
```

Returns a list of dicts, one per URL. Each dict includes a `"url"` key. On failure, `"error"` replaces `"status_code"`/`"body"`/`"elapsed_seconds"`:

```json
[
  {"url": "https://…/health", "status_code": 200, "body": {}, "elapsed_seconds": 0.1, "attempts": 1},
  {"url": "https://…/beat",   "error": "Connection timeout", "attempts": 3}
]
```

## Console usage

Install the project first (e.g. `python3 -m venv .venv && .venv/bin/pip install .`), then:

```bash
# GET, no auth.
python -m http_ping "https://example.com/health"

# Multiple URLs (output is a list).
python -m http_ping "https://example.com/health" "https://example.com/api/beat"

# POST with bearer token.
HTTP_PING_METHOD=POST HTTP_PING_BEARER=abc123 python -m http_ping "https://example.com/api/run"

# Token auth via env var.
HTTP_PING_TOKEN=abc123 python -m http_ping "https://example.com/api/beat"

# Full Authorization header value (any scheme).
HTTP_PING_AUTH="Token abc123" python -m http_ping "https://example.com/api/beat"

# All options via env vars (space-separated URLs for multiple).
export HTTP_PING_URL="https://example.com/api/health https://example.com/api/beat"
export HTTP_PING_TOKEN="abc123"
export HTTP_PING_RETRIES=5
export HTTP_PING_BACKOFF=2.0
python -m http_ping
```

CLI arguments override env vars:

```
python -m http_ping --help
python -m http_ping "https://example.com/api/beat" --method POST --timeout 10 --retries 2 --backoff 0.5
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `HTTP_PING_URL` | yes | — | Target URL |
| `HTTP_PING_METHOD` | no | `GET` | HTTP method |
| `HTTP_PING_AUTH` | no | — | Full `Authorization` header value |
| `HTTP_PING_TOKEN` | no | — | Shortcut: sets `Authorization: Token <value>` |
| `HTTP_PING_BEARER` | no | — | Shortcut: sets `Authorization: Bearer <value>` |
| `HTTP_PING_BODY` | no | — | JSON body for POST requests (as JSON string) |
| `HTTP_PING_TIMEOUT` | no | `30` | Request timeout in seconds |
| `HTTP_PING_RETRIES` | no | `3` | Number of retries on failure |
| `HTTP_PING_BACKOFF` | no | `1.0` | Base backoff in seconds (doubles each retry) |

`HTTP_PING_AUTH` takes precedence over `HTTP_PING_TOKEN` and `HTTP_PING_BEARER`.

## Makefile

- **`make all`** – install the project into `function/` and build `http-ping-function.zip` (for Lambda).
- **`make clean`** – remove the zip and everything in `function/` except `lambda_function.py`.
- **`make dist`** – build sdist and wheel (`python -m build`).
- **`make upload`** – upload with twine (run after `make dist`).

## Note on project structure

This project is intentionally over-structured for what it does ("a tank for a fly"). Its real purpose is to serve as a reference for real Python projects, following modern standards and conventions end to end:

- **Package** (`http_ping/`) — proper Python package with `__init__.py` exposing the public API, `__main__.py` as CLI entry point, and internal modules with clear separation of concerns: data (`HttpRequest`), helpers (`HttpAuth`), and logic (`HttpPing`, `HttpPingBatch`).
- **Adapters** (`function/lambda_function.py`, `http_ping/__main__.py`) — thin layers that read environment variables and wire up the core classes. The business logic knows nothing about env vars or deployment targets.
- **Linting** (`pyproject.toml` → `[tool.ruff]`) — ruff configured with an explicit rule set, enforcing style, correctness, complexity and docstring conventions.
- **Tests** (`tests/`) — pytest with coverage, showing both unit tests (pure functions, no I/O) and integration tests (real HTTP calls).
- **CI** (`.github/workflows/ci.yml`) — runs lint and tests on every push across multiple Python versions.
- **Docs** (`docs/`, `.github/workflows/docs.yml`, `.readthedocs.yaml`) — Sphinx with autodoc, deployed automatically to GitHub Pages and Read the Docs.
- **Packaging** (`pyproject.toml`, `Makefile`) — `make lambda` builds the deployable AWS Lambda zip; `make dist` / `make upload` build and publish to PyPI. These targets are kept as reference even though this project is not published.
