"""Talk to the Svenska Spel Stryktipset API.

Only the two endpoints we need:

    .../draw/1/stryktipset/draws            -> open/upcoming draws
    .../draw/1/stryktipset/draws/<n>/result -> the result of one draw

Everything network-related lives in this file. The rest of the code
never sees a URL or an HTTP status code, it only sees Python dicts
(on success) or one of the two exceptions below (on failure).
"""

from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset"
USER_AGENT = "stryktipset-results/1.0 (github.com/andreyhgl)"
TIMEOUT = 30  # seconds; never let a request hang forever
RETRIES = 3
BACKOFF = 2.0  # wait 2s, then 4s, then 8s between retries

# One Session reuses the TCP connection between requests, which is
# both faster and politer than opening a new one per draw.
session = requests.Session()
session.headers["User-Agent"] = USER_AGENT


class ApiError(Exception):
    """The API could not be reached, or answered with something unusable."""


class DrawNotFound(ApiError):
    """The requested draw number does not exist (HTTP 404)."""


def get_json(url, timeout=TIMEOUT, retries=RETRIES, backoff=BACKOFF):
    """GET a URL and decode the JSON body.

    Transient failures (HTTP 5xx, timeouts, connection errors) are
    retried with an exponential backoff. A 404 raises DrawNotFound at
    once, and any other 4xx raises ApiError at once: those mean the
    request itself is wrong, so retrying would not help.
    """
    last_error = "no attempt was made"

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout)

            if response.status_code == 404:
                raise DrawNotFound(f"404 for {url}")
            if 400 <= response.status_code < 500:
                raise ApiError(f"HTTP {response.status_code} for {url}")

            response.raise_for_status()  # turns 5xx into an exception
            return response.json()
        except requests.RequestException as err:
            last_error = str(err)
        except ValueError as err:  # body was not valid JSON
            last_error = f"invalid JSON: {err}"

        if attempt < retries:
            delay = backoff ** attempt
            log.warning(
                "%s (attempt %d/%d), retrying in %.0fs",
                last_error,
                attempt,
                retries,
                delay,
            )
            time.sleep(delay)

    raise ApiError(f"Gave up on {url} after {retries} attempts: {last_error}")


def fetch_result(drawnumber, **kwargs):
    """Return the `result` object for one draw, or None if it is missing."""
    url = f"{BASE_URL}/draws/{drawnumber}/result"
    log.debug("GET %s", url)
    try:
        payload = get_json(url, **kwargs)
    except DrawNotFound:
        log.info("Draw %s does not exist", drawnumber)
        return None

    result = payload.get("result")
    if not result:
        log.info("Draw %s has no result section", drawnumber)
        return None
    return result


def latest_drawnumber(**kwargs):
    """Highest draw number the API knows about (normally the open one)."""
    payload = get_json(f"{BASE_URL}/draws", **kwargs)
    draws = payload.get("draws") or []
    numbers = [d["drawNumber"] for d in draws if "drawNumber" in d]
    if not numbers:
        raise ApiError("No draws returned by the draws endpoint")
    return max(numbers)
