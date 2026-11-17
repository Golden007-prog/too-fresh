"""too-fresh: fail when a lockfile pins something published in the last N days."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import __version__
from .lockfiles import Dep, collect, find_lockfiles
from .registries import Registry


def human_age(delta: timedelta) -> str:
    secs = max(0, int(delta.total_seconds()))
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400 * 2:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


def check(deps: list[Dep], registry: Registry, now: datetime, max_age: timedelta, ignore: list[str], jobs: int = 32):
    unique = sorted({(d.ecosystem, d.name, d.version): d for d in deps}.values(), key=lambda d: (d.ecosystem, d.name, d.version))
    todo = [d for d in unique if not any(fnmatch.fnmatch(d.name, pat) for pat in ignore)]

    def look(d: Dep):
        try:
            return d, registry.published(d.ecosystem, d.name, d.version), None
        except Exception as e:
            return d, None, str(e) or type(e).__name__

    fresh, unknown = [], []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for d, when, err in pool.map(look, todo):
            if when is None:
                unknown.append((d, err or "not found on registry"))
            elif now - when < max_age:
                fresh.append((d, when))
    fresh.sort(key=lambda x: x[1], reverse=True)
    return unique, todo, fresh, unknown


def rel(p: str) -> str:
    try:
        return os.path.relpath(p)
    except ValueError:
        return p


def color(s: str, code: str) -> str:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return s
    return f"\033[{code}m{s}\033[0m"


def main(argv: list[str] | None = None, registry: Registry | None = None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="too-fresh",
        description="Find dependencies in your lockfiles that were published in the last N days.",
    )
    ap.add_argument("paths", nargs="*", default=["."], help="lockfiles or directories to scan (default: .)")
    ap.add_argument("-d", "--days", type=float, default=7, help="minimum age in days (default: 7, decimals ok)")
    ap.add_argument("-i", "--ignore", action="append", default=[], metavar="NAME",
                    help="package name or glob to skip, e.g. '@myorg/*' (repeatable)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    ap.add_argument("--strict", action="store_true", help="also fail when a version can't be found on its registry")
    ap.add_argument("-j", "--jobs", type=int, default=32, help="parallel registry lookups (default: 32)")
    ap.add_argument("-V", "--version", action="version", version=f"too-fresh {__version__}")
    args = ap.parse_args(argv)

    registry = registry or Registry()
    now = now or datetime.now(timezone.utc)
    ignore = args.ignore + [p.strip() for p in os.environ.get("TOO_FRESH_IGNORE", "").split(",") if p.strip()]

    files: list[Path] = []
    for p in args.paths:
        path = Path(p)
        if not path.exists():
            print(f"too-fresh: {p}: no such file or directory", file=sys.stderr)
            return 2
        files += find_lockfiles(path)
    if not files:
        print("too-fresh: no lockfiles found", file=sys.stderr)
        return 2

    deps, parse_errors = collect(files)
    unique, checked, fresh, unknown = check(deps, registry, now, timedelta(days=args.days), ignore, args.jobs)
    failed = bool(fresh) or (args.strict and bool(unknown))

    if args.json:
        print(json.dumps({
            "max_age_days": args.days,
            "lockfiles": [str(f) for f in files],
            "checked": len(checked),
            "fresh": [{"ecosystem": d.ecosystem, "name": d.name, "version": d.version, "lockfile": d.source,
                       "published": w.isoformat(), "age_hours": round((now - w).total_seconds() / 3600, 1)}
                      for d, w in fresh],
            "unknown": [{"ecosystem": d.ecosystem, "name": d.name, "version": d.version, "reason": r} for d, r in unknown],
            "errors": parse_errors,
        }, indent=2))
        return 1 if failed else 0

    for e in parse_errors:
        print(color(f"warning: {e}", "33"), file=sys.stderr)
    print(f"Scanned {len(files)} lockfile{'s' * (len(files) != 1)}, {len(checked)} package{'s' * (len(checked) != 1)} "
          f"({len(unique) - len(checked)} ignored). Minimum age: {args.days:g} days.\n")
    if fresh:
        w = max(len(f"{d.name}@{d.version}") for d, _ in fresh)
        for d, when in fresh:
            print(f"  {color('FRESH', '31;1')}  {(d.name + '@' + d.version).ljust(w)}  {d.ecosystem:<6}  published {human_age(now - when)} ago ({when:%Y-%m-%d %H:%M} UTC)  {rel(d.source)}")
        print()
    if unknown:
        for d, reason in unknown[:20]:
            print(f"  {color('??', '33')}     {d.name}@{d.version}  {d.ecosystem}: {reason}")
        if len(unknown) > 20:
            print(f"  ... and {len(unknown) - 20} more")
        print()
    if fresh:
        print(color(f"{len(fresh)} package{'s' * (len(fresh) != 1)} younger than {args.days:g} days.", "31;1") +
              " Wait it out, or allow it with --ignore NAME if you know why it's there.")
    else:
        print(color(f"Nothing younger than {args.days:g} days.", "32"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
