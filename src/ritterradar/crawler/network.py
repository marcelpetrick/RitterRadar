# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve once, reject non-public destinations, connect to the checked IP.

HTTPcore retains the original hostname for TLS SNI/certificate verification.
This isolated adapter to its network interface is covered by regression tests.
Environment proxies are intentionally unsupported because they bypass this policy.
"""

import asyncio
import ipaddress
import socket
import ssl
from collections.abc import Iterable

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend
from httpcore._backends.base import SOCKET_OPTION, AsyncNetworkStream


class PublicNetworkBackend(AutoBackend):
    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SOCKET_OPTION] | None = None,
    ) -> AsyncNetworkStream:
        async with asyncio.timeout(timeout or 30):
            answers = await asyncio.get_running_loop().getaddrinfo(
                host, port, type=socket.SOCK_STREAM
            )
            addresses = list(dict.fromkeys(str(answer[4][0]) for answer in answers))
            if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
                raise httpcore.ConnectError("Destination is not a public IP address")
            # Connecting to the numeric result prevents a second DNS lookup from
            # changing the destination after validation (DNS rebinding).
            for address in addresses:
                try:
                    return await super().connect_tcp(
                        address, port, timeout, local_address, socket_options
                    )
                except httpcore.ConnectError:
                    continue
            raise httpcore.ConnectError("Public destination could not be reached")


class PublicTransport(httpx.AsyncHTTPTransport):
    def __init__(self) -> None:
        super().__init__(trust_env=False)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(),
            network_backend=PublicNetworkBackend(),
            max_connections=4,
            max_keepalive_connections=2,
        )
