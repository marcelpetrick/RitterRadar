#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local CLI uses configuration as data and never puts credentials in argv."""
import json
import sys
import urllib.request

from ritterradar.config import get_settings

s = get_settings()
endpoint = "/api/crawl/trigger" if "--trigger" in sys.argv else "/api/crawl/status"
headers = {"X-RitterRadar-Request": "1"}
if s.auth_token:
    headers["Authorization"] = "Bearer " + s.auth_token.get_secret_value()
request = urllib.request.Request(
    f"http://127.0.0.1:{s.port}{endpoint}",
    method="POST" if "--trigger" in sys.argv else "GET", headers=headers,
)
with urllib.request.urlopen(request, timeout=15) as response:
    print(json.dumps(json.load(response), indent=2))
