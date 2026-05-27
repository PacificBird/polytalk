# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Pydantic schemas package.
"""

from .translation import (
    HealthResponse,
    ErrorResponse,
)

__all__ = [
    "HealthResponse",
    "ErrorResponse",
]
