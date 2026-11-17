"""Ask public registries when a specific version was published."""

from __future__ import annotations

import gzip
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable

from . import __version__

UA = f"too-fresh/{__version__} (+https://github.com/TanbirRamim/too-fresh)"

Fetch = Callable[[str, dict], object]  # (url, headers) -> parsed JSON, or None on 404


def http_json(url: str, headers: dict | None = None, timeout: float = 20.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            return json.loads(body)
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return None
        raise


def parse_time(s: str) -> datetime:
    s = s.strip().replace("Z", "+00:00")
    # crates.io and go have nanoseconds sometimes; fromisoformat in 3.11 handles up to 6 digits
    if "." in s:
        head, _, rest = s.partition(".")
        frac = "".join(c for c in rest if c.isdigit())
        tz = rest[len(frac):]
        s = f"{head}.{frac[:6]}{tz}"
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class Registry:
    def __init__(self, fetch: Fetch = http_json):
        self.fetch = fetch
        self._npm_cache: dict[str, object] = {}
        self.npm_base = os.environ.get("TOO_FRESH_NPM_REGISTRY", "https://registry.npmjs.org").rstrip("/")

    def published(self, ecosystem: str, name: str, version: str) -> datetime | None:
        return getattr(self, f"_{ecosystem}")(name, version)

    def _npm(self, name: str, version: str):
        if name not in self._npm_cache:
            self._npm_cache[name] = self.fetch(f"{self.npm_base}/{urllib.parse.quote(name, safe='@')}", {})
        doc = self._npm_cache[name]
        t = (doc or {}).get("time", {}).get(version)
        return parse_time(t) if t else None

    def _pypi(self, name: str, version: str):
        doc = self.fetch(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/{urllib.parse.quote(version)}/json", {})
        times = [u["upload_time_iso_8601"] for u in (doc or {}).get("urls", []) if u.get("upload_time_iso_8601")]
        return min(parse_time(t) for t in times) if times else None

    def _crates(self, name: str, version: str):
        doc = self.fetch(f"https://crates.io/api/v1/crates/{urllib.parse.quote(name)}/{urllib.parse.quote(version)}", {})
        t = ((doc or {}).get("version") or {}).get("created_at")
        return parse_time(t) if t else None

    def _go(self, module: str, version: str):
        esc = "".join("!" + c.lower() if c.isupper() else c for c in module)
        doc = self.fetch(f"https://proxy.golang.org/{esc}/@v/{version}.info", {})
        t = (doc or {}).get("Time")
        return parse_time(t) if t else None
