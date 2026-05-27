# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Web router for PolyTalk application.

Serves the frontend pages and static assets.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..config import get_config

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """
    Serve the main application page.

    Args:
        request: FastAPI request object

    Returns:
        HTML response with the main page
    """
    app_config = get_config().app
    auto_play = app_config.get("auto_play_audio", True)

    template = templates.get_template("index.html")
    html = template.render(auto_play=auto_play, request=request)

    return HTMLResponse(content=html)
