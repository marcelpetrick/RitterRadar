# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter registry — maps adapter_name strings to concrete adapter classes."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter

_REGISTRY: dict[str, type["AbstractCrawlerAdapter"]] = {}


def register(name: str):  # type: ignore[return]
    """Class decorator: register an adapter under *name*."""
    def decorator(cls: type["AbstractCrawlerAdapter"]) -> type["AbstractCrawlerAdapter"]:
        _REGISTRY[name] = cls
        return cls
    return decorator


def get_adapter(name: str) -> "AbstractCrawlerAdapter":
    """Instantiate the adapter registered under *name*.

    Raises ``KeyError`` if the name is unknown.  Adapters are imported lazily
    the first time ``get_adapter`` is called to avoid circular imports.
    """
    _ensure_adapters_loaded()
    cls = _REGISTRY[name]
    return cls()


def list_adapters() -> list[str]:
    """Return the names of all registered adapters."""
    _ensure_adapters_loaded()
    return sorted(_REGISTRY.keys())


_adapters_loaded = False


def _ensure_adapters_loaded() -> None:
    global _adapters_loaded
    if not _adapters_loaded:
        import ritterradar.crawler.adapters  # noqa: F401
        _adapters_loaded = True
