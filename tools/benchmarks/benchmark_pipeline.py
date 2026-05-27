#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Benchmark the full PolyTalk WebSocket pipeline with a WAV file."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import wave
from collections import Counter
from pathlib import Path
from typing import Any

import websockets

from common import print_summary, summarize, write_json


def read_pcm_wav(path: str) -> tuple[bytes, float]:
    """Read a 16 kHz mono int16 WAV file and return PCM bytes plus duration."""
    wav_path = Path(path)
    if not wav_path.exists():
        raise ValueError(f"Audio file not found: {wav_path}")
    if not wav_path.is_file():
        raise ValueError(f"Audio path is not a file: {wav_path}")

    try:
        with wave.open(str(wav_path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frames = wav.getnframes()
            compression = wav.getcomptype()
            if (
                channels != 1
                or sample_width != 2
                or sample_rate != 16000
                or compression != "NONE"
            ):
                raise ValueError(
                    "Pipeline benchmark expects 16 kHz mono 16-bit PCM WAV. "
                    f"Got channels={channels}, sample_width={sample_width}, "
                    f"sample_rate={sample_rate}, compression={compression}."
                )
            return wav.readframes(frames), frames / sample_rate
    except wave.Error as exc:
        raise ValueError(
            f"Invalid WAV file for pipeline benchmark: {wav_path}"
        ) from exc
    except EOFError as exc:
        raise ValueError(
            f"Incomplete WAV file for pipeline benchmark: {wav_path}"
        ) from exc


async def run(args: argparse.Namespace) -> dict[str, Any]:
    """Run the benchmark."""
    pcm, audio_duration = read_pcm_wav(args.audio)
    bytes_per_second = 16000 * 1 * 2
    chunk_size = int(args.chunk_seconds * bytes_per_second)
    chunk_size -= chunk_size % 2
    chunks = [
        pcm[index : index + chunk_size] for index in range(0, len(pcm), chunk_size)
    ]

    query = (
        f"source_language={args.source_language}&target_language={args.target_language}"
    )
    ws_url = args.ws_url.rstrip("?") + "?" + query
    started = time.perf_counter()
    events = []

    async with websockets.connect(ws_url, ping_interval=None) as websocket:

        async def receiver() -> None:
            try:
                async for message in websocket:
                    received_at = time.perf_counter() - started
                    data = json.loads(message)
                    events.append({"received_at": received_at, **data})
                    if data.get("type") == "complete":
                        return
            except websockets.exceptions.ConnectionClosed:
                return

        recv_task = asyncio.create_task(receiver())
        for chunk in chunks:
            await websocket.send(chunk)
            if args.realtime:
                await asyncio.sleep(args.chunk_seconds)

        await websocket.send(json.dumps({"type": "end"}))
        try:
            await asyncio.wait_for(recv_task, timeout=args.drain_seconds)
        except asyncio.TimeoutError:
            await websocket.close()
            await recv_task

    wall_time = time.perf_counter() - started
    counts = Counter(event.get("type", "unknown") for event in events)

    def first_event(event_type: str) -> float | None:
        for event in events:
            if event.get("type") == event_type:
                return event["received_at"]
        return None

    def event_times(event_type: str) -> list[float]:
        return [
            event["received_at"] for event in events if event.get("type") == event_type
        ]

    return {
        "service": "pipeline",
        "ws_url": ws_url,
        "audio_seconds": audio_duration,
        "chunk_seconds": args.chunk_seconds,
        "chunks_sent": len(chunks),
        "realtime": args.realtime,
        "wall_time": wall_time,
        "event_counts": dict(counts),
        "first_transcription_at": first_event("transcription"),
        "first_translation_at": first_event("translation"),
        "first_tts_at": first_event("tts"),
        "transcription_arrival_seconds": summarize(event_times("transcription")),
        "translation_arrival_seconds": summarize(event_times("translation")),
        "tts_arrival_seconds": summarize(event_times("tts")),
        "events": events,
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ws-url", default="ws://localhost:9000/api/ws/translate")
    parser.add_argument("--audio", required=True, help="16 kHz mono int16 WAV file")
    parser.add_argument("--source-language", default="en")
    parser.add_argument("--target-language", default="hi")
    parser.add_argument("--chunk-seconds", type=float, default=0.25)
    parser.add_argument("--drain-seconds", type=float, default=60.0)
    parser.add_argument("--realtime", action="store_true")
    parser.add_argument("--json-output")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    payload = asyncio.run(run(args))
    print_summary("Pipeline Benchmark", payload)
    print_summary(
        "Transcription Arrival Seconds", payload["transcription_arrival_seconds"]
    )
    print_summary("Translation Arrival Seconds", payload["translation_arrival_seconds"])
    print_summary("TTS Arrival Seconds", payload["tts_arrival_seconds"])
    write_json(args.json_output, payload)


if __name__ == "__main__":
    main()
