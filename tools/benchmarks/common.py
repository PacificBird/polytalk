#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Shared helpers for PolyTalk benchmark scripts."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Iterable


def read_lines(path: str | None, defaults: list[str]) -> list[str]:
    """Read non-empty lines from a file or return defaults."""
    if not path:
        return defaults

    lines = [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        raise ValueError(f"No benchmark input lines found in {path}")
    return lines


def percentile(values: list[float], pct: float) -> float:
    """Return a simple nearest-rank percentile."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * pct)
    return sorted_values[index]


def summarize(values: Iterable[float]) -> dict[str, float | int]:
    """Create timing summary stats."""
    items = list(values)
    if not items:
        return {
            "count": 0,
            "avg": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "max": 0.0,
            "min": 0.0,
        }

    return {
        "count": len(items),
        "avg": statistics.fmean(items),
        "p50": percentile(items, 0.50),
        "p95": percentile(items, 0.95),
        "max": max(items),
        "min": min(items),
    }


def print_summary(title: str, summary: dict[str, Any]) -> None:
    """Print a compact benchmark summary."""
    print(f"\n{title}")
    print("-" * len(title))
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key}: {value:.3f}")
        else:
            print(f"{key}: {value}")


def write_json(path: str | None, payload: dict[str, Any]) -> None:
    """Write JSON output when requested."""
    if not path:
        return
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
