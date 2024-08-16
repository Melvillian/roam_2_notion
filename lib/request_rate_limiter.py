import requests
import time
import functools
import os

# Check if DEBUG environment variable is set
DEBUG = os.getenv("DEBUG")

"""
A simple wrapper for the requests library, which waits 0.4 seconds between requests
So that we don't get rate limited by the Notion API:
https://developers.notion.com/reference/request-limits
"""


def rate_limit(func):
    """
    Decorator for all requests to prevent rate limiting.

    Waits at least 400ms between requests.

    https://developers.notion.com/reference/request-limits#rate-limits

    """
    REQUEST_INTERVAL_SECS = 0.4
    time_of_last_response = time.time()

    @functools.wraps(func)
    def rate_limited(*args, **kwargs):
        nonlocal time_of_last_response
        now = time.time()
        if now - time_of_last_response < REQUEST_INTERVAL_SECS:
            time.sleep(REQUEST_INTERVAL_SECS - (now - time_of_last_response))
        result = func(*args, **kwargs)
        time_of_last_response = time.time()
        # make sure we've success status code
        result.raise_for_status()
        return result

    return rate_limited


@rate_limit
def get(url, headers):
    debug_print(f"Get:\n{url}\nHEADERS:\n{headers}")
    return requests.get(url, headers=headers)


@rate_limit
def post(url, headers, json):
    debug_print(f"POST:\n{url}\nHEADERS:\n{headers}\nJSON:\n{json}")
    return requests.post(url, headers=headers, json=json)


@rate_limit
def patch(url, headers, json):
    debug_print(f"PATCH:\n{url}\nHEADERS:\n{headers}\nJSON:\n{json}")
    return requests.patch(url, headers=headers, json=json)


def debug_print(*args, **kwargs):
    """Print debug messages if DEBUG environment variable is set."""
    if DEBUG:
        print(*args, **kwargs)
