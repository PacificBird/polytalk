# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Sanitization helpers for user-provided guidance."""

import re


def normalize_instruction(value: object, max_chars: int | None = None) -> str:
    """Normalize custom instruction text and optionally bound its length."""
    without_control_chars = re.sub(r"[\x00-\x1f\x7f]", " ", str(value or ""))
    normalized = " ".join(without_control_chars.split())
    if max_chars is None or max_chars <= 0:
        return normalized
    return normalized[:max_chars]
