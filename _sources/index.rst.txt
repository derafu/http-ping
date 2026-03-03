http-ping
=========

Perform HTTP requests and get status code, response body and timing.
Supports authentication, retry with exponential backoff, and multiple URLs.
Designed as a deployable AWS Lambda + CLI utility and as a pedagogical example
of a minimal Python project structure.

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   api

Installation
------------

.. code-block:: bash

   pip install .

Quick start
-----------

.. code-block:: python

   from http_ping import HttpAuth, HttpPing, HttpRequest

   request = HttpRequest(
       url="https://example.com/api/beat",
       auth=HttpAuth.token("your-token"),
   )
   result = HttpPing(request).run()
   print(result)
   # {
   #   "status_code": 200,
   #   "body": {...},
   #   "elapsed_seconds": 0.123,
   #   "attempts": 1,
   # }
