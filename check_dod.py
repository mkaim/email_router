#!/usr/bin/env python3
"""End-to-end Definition of Done check against a running stack.

Start the stack with ``docker compose up -d`` first, then run this script.

Verifies the Definition of Done:

* the API serves Swagger docs under ``/api/v1/docs``;
* posting an issue produces a captured mail in MailHog;
* the captured mail is addressed to the correct department;
* the captured mail carries the client address as ``Reply-To``.

Usage::

    docker compose up -d
    python check_dod.py

Only the standard library is used, so no dependencies are required.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("API_BASE", "http://localhost:8000") + "/api/v1"
MAILHOG = os.environ.get("MAILHOG_BASE", "http://localhost:8025")
POLL_TIMEOUT = 120.0  # seconds; first LLM call can be slow to warm up

# Deliberately unambiguous messages so a small local model routes them reliably.
CASES = [
    {
        "email": "jane.doe@example.com",
        "message": (
            "My work laptop will not connect to the company VPN since this "
            "morning and I cannot reach any internal systems or my email."
        ),
        "expect": "it@example.com",
    },
    {
        "email": "jan.kowalski@example.com",
        "message": (
            "Nie otrzymalem paska wynagrodzen za poprzedni miesiac i moje "
            "wynagrodzenie nie wplynelo na konto."
        ),
        "expect": "kadry@example.com",
    },
]


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=POLL_TIMEOUT) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _get_json(url: str) -> dict:
    _status, body = _request("GET", url)
    return json.loads(body)


def _clear_mailhog() -> None:
    _request("DELETE", f"{MAILHOG}/api/v1/messages")


def _headers_of_latest() -> dict[str, list[str]] | None:
    messages = _get_json(f"{MAILHOG}/api/v2/messages")
    if not messages.get("items"):
        return None
    return messages["items"][0]["Content"]["Headers"]


def _wait_for_mail() -> dict[str, list[str]]:
    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        headers = _headers_of_latest()
        if headers is not None:
            return headers
        time.sleep(1.0)
    raise AssertionError("no message captured by MailHog within timeout")


def _wait_for_api() -> None:
    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        try:
            _request("GET", f"{API}/docs")
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(1.0)
    raise AssertionError(f"API at {API} did not come up within timeout")


def _check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {label}" + (f" -- {detail}" if detail else ""))
    return ok


def main() -> int:
    passed = True

    _wait_for_api()
    status, _ = _request("GET", f"{API}/docs")
    passed &= _check("Swagger docs at /api/v1/docs", status == 200, f"HTTP {status}")

    for case in CASES:
        _clear_mailhog()
        status, body = _request("POST", f"{API}/issues", case)
        passed &= _check(
            f"POST /issues accepted ({case['expect']})",
            status == 200,
            f"HTTP {status} {body[:200]!r}",
        )
        if status != 200:
            continue

        headers = _wait_for_mail()
        to = headers.get("To", [])
        reply_to = headers.get("Reply-To", [])

        passed &= _check(
            f"mail captured and routed to {case['expect']}",
            to == [case["expect"]],
            f"To={to}",
        )
        passed &= _check(
            "Reply-To set to client address",
            reply_to == [case["email"]],
            f"Reply-To={reply_to}",
        )
        print(f"       Subject: {headers.get('Subject', ['?'])[0]}")

    print()
    print("ALL CHECKS PASSED" if passed else "SOME CHECKS FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
