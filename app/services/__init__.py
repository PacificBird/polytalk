# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Services package.
"""

from .base import (
    TranscriptionResult,
    TranslationResult,
    TTSResult,
    BaseTranscriptionService,
    BaseTranslationService,
    BaseTTSService,
)

__all__ = [
    "TranscriptionResult",
    "TranslationResult",
    "TTSResult",
    "BaseTranscriptionService",
    "BaseTranslationService",
    "BaseTTSService",
]
