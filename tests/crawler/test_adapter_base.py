# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for base adapter, registry, and a simple generic adapter stub."""

from datetime import date

import pytest

from ritterradar.crawler.base_adapter import MarketData
from ritterradar.crawler.registry import get_adapter, list_adapters


def test_market_data_defaults():
    m = MarketData(
        name="Test",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 3),
    )
    assert m.market_type == "medieval"
    assert m.country == "DE"
    assert m.confidence_score == 1.0
    assert m.tags == []


def test_registry_lists_all_adapters():
    adapters = list_adapters()
    assert "mittelalterfeste" in adapters
    assert "generic_table" in adapters
    assert "spectaculum" in adapters
    assert "schwerttanz" in adapters
    assert "ritterschaft" in adapters
    assert "mittelaltermarkt" in adapters


def test_registry_get_adapter_unknown():
    with pytest.raises(KeyError):
        get_adapter("nonexistent_adapter_xyz")


def test_registry_get_adapter_returns_instance():
    adapter = get_adapter("generic_table")
    assert hasattr(adapter, "crawl")
