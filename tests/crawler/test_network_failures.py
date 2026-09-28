# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline regressions for outbound DNS and connection failure handling."""

import asyncio
import socket
from unittest.mock import AsyncMock

import httpcore
import pytest

from ritterradar.crawler.network import PublicNetworkBackend


def _answer(address: str) -> tuple[int, int, int, str, tuple[str, int]]:
    return (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))


async def test_dns_without_addresses_fails_closed(monkeypatch):
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", AsyncMock(return_value=[]))

    with pytest.raises(httpcore.ConnectError, match="not a public IP"):
        await PublicNetworkBackend().connect_tcp("example.test", 443)


async def test_backend_tries_each_checked_public_address(monkeypatch):
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(
        loop,
        "getaddrinfo",
        AsyncMock(return_value=[_answer("93.184.216.34"), _answer("1.1.1.1")]),
    )
    attempted: list[str] = []

    async def connect(self, address, port, timeout, local_address, socket_options):
        attempted.append(address)
        if len(attempted) == 1:
            raise httpcore.ConnectError("first address unavailable")
        return "connected stream"

    monkeypatch.setattr("ritterradar.crawler.network.AutoBackend.connect_tcp", connect)
    backend = PublicNetworkBackend()

    assert await backend.connect_tcp("example.test", 443) == "connected stream"
    assert attempted == ["93.184.216.34", "1.1.1.1"]


async def test_backend_reports_when_all_public_addresses_fail(monkeypatch):
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", AsyncMock(return_value=[_answer("93.184.216.34")]))
    monkeypatch.setattr(
        "ritterradar.crawler.network.AutoBackend.connect_tcp",
        AsyncMock(side_effect=httpcore.ConnectError("refused")),
    )

    with pytest.raises(httpcore.ConnectError, match="could not be reached"):
        await PublicNetworkBackend().connect_tcp("example.test", 443)
