# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Audio utilities for PolyTalk application.

Provides helper functions for audio handling and conversion.
"""

import io
import wave
from typing import Optional
import struct


def convert_webm_to_wav(webm_bytes: bytes) -> bytes:
    """
    Convert WebM audio to WAV format.

    NOTE: This is a placeholder. In production, you'd use ffmpeg or similar.
    For now, returns the original bytes assuming the client sends WAV.

    Args:
        webm_bytes: WebM audio data

    Returns:
        WAV audio data
    """
    return webm_bytes


def create_wav_header(
    num_channels: int = 1,
    sample_width: int = 2,
    framerate: int = 16000,
    num_frames: int = 0,
) -> bytes:
    """
    Create a WAV file header.

    Args:
        num_channels: Number of audio channels
        sample_width: Sample width in bytes
        framerate: Sample rate
        num_frames: Number of frames

    Returns:
        WAV header bytes
    """
    block_align = num_channels * sample_width
    byte_rate = framerate * block_align
    data_size = num_frames * block_align

    header = io.BytesIO()

    header.write(b"RIFF")
    header.write(struct.pack("<I", 36 + data_size))
    header.write(b"WAVE")

    header.write(b"fmt ")
    header.write(struct.pack("<I", 16))
    header.write(struct.pack("<H", 1))
    header.write(struct.pack("<H", num_channels))
    header.write(struct.pack("<I", framerate))
    header.write(struct.pack("<I", byte_rate))
    header.write(struct.pack("<H", block_align))
    header.write(struct.pack("<H", 16))

    header.write(b"data")
    header.write(struct.pack("<I", data_size))

    return header.getvalue()


def estimate_audio_duration(audio_bytes: bytes) -> float:
    """
    Estimate audio duration from raw bytes.

    Args:
        audio_bytes: Raw audio data

    Returns:
        Estimated duration in seconds
    """
    try:
        wav_file = io.BytesIO(audio_bytes)
        with wave.open(wav_file, "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            if rate > 0:
                return frames / rate
    except Exception:
        pass

    return 5.0


def get_audio_format_extension(content_type: Optional[str]) -> str:
    """
    Get file extension based on content type.

    Args:
        content_type: MIME type of audio

    Returns:
        File extension with dot (e.g., '.wav')
    """
    if not content_type:
        return ".wav"

    content_type = content_type.lower()

    extensions = {
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
        "audio/mp3": ".mp3",
        "audio/mpeg": ".mp3",
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/aac": ".aac",
        "audio/flac": ".flac",
    }

    return extensions.get(content_type, ".wav")


def validate_audio_file(audio_bytes: bytes, max_size_mb: int = 50) -> tuple[bool, str]:
    """
    Validate audio file.

    Args:
        audio_bytes: Raw audio data
        max_size_mb: Maximum allowed file size in MB

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not audio_bytes:
        return False, "No audio data provided"

    if len(audio_bytes) > max_size_mb * 1024 * 1024:
        return False, f"Audio file too large. Maximum size is {max_size_mb}MB"

    if len(audio_bytes) < 44:
        return False, "Audio file too small to be valid"

    return True, ""
