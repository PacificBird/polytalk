# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    """
    Health check response schema.

    Attributes:
        status: Service status
        version: Application version
    """

    status: str
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """
    Error response schema.

    Attributes:
        success: Always False for errors
        error: Error message
        details: Optional detailed error information
    """

    success: bool = False
    error: str
    details: Optional[str] = None
