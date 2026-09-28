# SPDX-License-Identifier: GPL-3.0-or-later
"""Local-first HTTP boundary, bounded admission and privacy-safe logging."""

import asyncio
import base64
import binascii
import hmac
import ipaddress
import logging
import time
from collections import deque
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ritterradar.config import get_settings

REQUEST_HEADER = "x-ritterradar-request"
SECURITY_HEADERS = {
    "content-security-policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self'; "
        "font-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; "
        "form-action 'self'"
    ),
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "cache-control": "no-store",
}


def is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def safe_web_url(value: str) -> bool:
    """Validate display links; outbound crawling applies stricter host/IP rules."""
    try:
        url = urlsplit(value)
        return (
            len(value) <= 2048
            and not any(ord(c) <= 32 or ord(c) == 127 for c in value)
            and "\\" not in value
            and url.scheme in ("http", "https")
            and bool(url.hostname)
            and url.username is None
            and url.password is None
            and (url.port is None or 1 <= url.port <= 65535)
        )
    except ValueError:
        return False


class PrivateAccessLog(logging.Filter):
    """Never retain addresses/coordinates from HTTP query strings."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            args[2] = str(args[2]).partition("?")[0]
            record.args = tuple(args)
        return True


class SecurityMiddleware:
    """Reject untrusted requests before they reach stateful application code.

    A custom header plus exact Origin/Fetch-Metadata validation protects local
    browser mutations. Network clients additionally need the configured secret.
    No CORS policy is enabled. Bounds are process-wide for the single-user app.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.active = 0
        self.requests: deque[float] = deque()
        self.auth_failures: dict[str, deque[float]] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        settings = get_settings()
        headers = Headers(scope=scope)

        async def secured_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                additions = dict(SECURITY_HEADERS)
                if settings.offline:
                    additions["content-security-policy"] = additions[
                        "content-security-policy"
                    ].replace(" https://tile.openstreetmap.org", "")
                message["headers"] = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.decode().lower() not in additions
                ] + [(k.encode(), v.encode()) for k, v in additions.items()]
            await send(message)

        async def reject(code: int, detail: str) -> None:
            extra = {"WWW-Authenticate": 'Basic realm="RitterRadar", charset="UTF-8"'}
            await JSONResponse(
                {"detail": detail}, status_code=code, headers=extra if code == 401 else None
            )(scope, receive, secured_send)

        # Count rejected requests too: otherwise invalid credentials and Host
        # headers can evade the process-wide admission budget.
        now = time.monotonic()
        while self.requests and self.requests[0] < now - 10:
            self.requests.popleft()
        if len(self.requests) >= settings.request_limit:
            await reject(429, "Request budget exceeded; retry later")
            return
        self.requests.append(now)

        host_values = headers.getlist("host")
        try:
            authority = urlsplit("//" + headers.get("host", ""))
            host = authority.hostname
            valid_host = (
                len(host_values) == 1
                and host in settings.allowed_hosts
                and authority.username is None
                and authority.password is None
                and not authority.path
                and not authority.query
                and not authority.fragment
                and not any(c.isspace() or c == "\\" for c in headers.get("host", ""))
            )
            _ = authority.port
        except ValueError:
            valid_host = False
        if not valid_host:
            await reject(400, "Untrusted Host")
            return
        peer = scope.get("client") or ("", 0)
        secret = settings.auth_token.get_secret_value() if settings.auth_token else ""
        if scope["path"] != "/health":
            if secret:
                authorization = headers.get("authorization", "")
                supplied = ""
                if authorization.startswith("Bearer "):
                    supplied = authorization[7:]
                elif authorization.startswith("Basic "):
                    try:
                        user, _, password = (
                            base64.b64decode(authorization[6:], validate=True)
                            .decode()
                            .partition(":")
                        )
                        if user == "ritterradar":
                            supplied = password
                    except (ValueError, UnicodeError, binascii.Error):
                        pass
                if not hmac.compare_digest(supplied.encode(), secret.encode()):
                    peer_key = str(peer[0])
                    attempts = self.auth_failures.get(peer_key)
                    if attempts is None:
                        if len(self.auth_failures) >= 1024:
                            self.auth_failures.pop(next(iter(self.auth_failures)))
                        attempts = deque()
                        self.auth_failures[peer_key] = attempts
                    while attempts and attempts[0] < now - 60:
                        attempts.popleft()
                    limited = len(attempts) >= 10
                    attempts.append(now)
                    await reject(
                        429 if limited else 401,
                        (
                            "Too many authentication attempts"
                            if limited
                            else "Authentication required"
                        ),
                    )
                    return
                self.auth_failures.pop(str(peer[0]), None)
            elif not is_loopback(peer[0]):
                await reject(403, "Network access requires authentication")
                return
        unsafe = scope["method"] not in ("GET", "HEAD", "OPTIONS")
        if unsafe:
            origin = headers.get("origin")
            expected = f"{scope['scheme']}://{headers.get('host')}"
            if (
                headers.get(REQUEST_HEADER) != "1"
                or headers.get("sec-fetch-site") == "cross-site"
                or (origin is not None and origin != expected)
            ):
                await reject(403, "Untrusted mutation request")
                return
        if len(scope.get("query_string", b"")) > 4096:
            await reject(414, "Query too long")
            return
        if self.active >= settings.request_concurrency:
            await reject(503, "Server busy; retry later")
            return
        self.active += 1
        try:
            # Read bounded bodies before JSON parsing; also covers chunked requests.
            chunks = bytearray()
            deadline = time.monotonic() + 15
            while True:
                try:
                    message = await asyncio.wait_for(
                        receive(), max(0.001, deadline - time.monotonic())
                    )
                except TimeoutError:
                    await reject(408, "Request body deadline exceeded")
                    return
                if message["type"] == "http.disconnect":
                    return
                chunks.extend(message.get("body", b""))
                if len(chunks) > 16_384:
                    await reject(413, "Request body too large")
                    return
                if not message.get("more_body", False):
                    break
            delivered = False

            async def bounded_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(chunks), "more_body": False}
                return await receive()

            await self.app(scope, bounded_receive, secured_send)
        finally:
            self.active -= 1
