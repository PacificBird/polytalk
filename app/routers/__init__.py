# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Routers package.
"""

from .api import router as api_router
from .web import router as web_router

__all__ = ["api_router", "web_router"]
