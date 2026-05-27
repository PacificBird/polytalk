#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Benchmark the PolyTalk STT streaming WebSocket service."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import wave
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
                    "STT benchmark expects 16 kHz mono 16-bit PCM WAV. "
                    f"Got channels={channels}, sample_width={sample_width}, "
                    f"sample_rate={sample_rate}, compression={compression}."
                )
            return wav.readframes(frames), frames / sample_rate
    except wave.Error as exc:
        raise ValueError(f"Invalid WAV file for STT benchmark: {wav_path}") from exc
    except EOFError as exc:
        raise ValueError(f"Incomplete WAV file for STT benchmark: {wav_path}") from exc


async def run(args: argparse.Namespace) -> dict[str, Any]:
    """Run the benchmark."""
    pcm, audio_duration = read_pcm_wav(args.audio)
    bytes_per_second = 16000 * 1 * 2
    chunk_size = int(args.chunk_seconds * bytes_per_second)
    chunk_size -= chunk_size % 2
    chunks = [
        pcm[index : index + chunk_size] for index in range(0, len(pcm), chunk_size)
    ]
    first_result_at = None
    last_result_at = None
    results = []

    started = time.perf_counter()
    async with websockets.connect(args.ws_url, ping_interval=None) as websocket:
        await websocket.send(json.dumps({"language": args.language, "task": args.task}))

        async def receiver() -> None:
            nonlocal first_result_at, last_result_at
            try:
                async for message in websocket:
                    received_at = time.perf_counter() - started
                    data = json.loads(message)
                    if data.get("text") and first_result_at is None:
                        first_result_at = received_at
                    if data.get("text"):
                        last_result_at = received_at
                    results.append({"received_at": received_at, **data})
            except websockets.exceptions.ConnectionClosed:
                return

        recv_task = asyncio.create_task(receiver())
        for chunk in chunks:
            await websocket.send(chunk)
            if args.realtime:
                await asyncio.sleep(args.chunk_seconds)

        await asyncio.sleep(args.drain_seconds)
        await websocket.close()
        await recv_task

    wall_time = time.perf_counter() - started
    text_results = [item for item in results if item.get("text")]
    errors = [item for item in results if item.get("error")]
    received_times = [item["received_at"] for item in text_results]
    final_text = text_results[-1]["text"] if text_results else ""

    return {
        "service": "stt",
        "ws_url": args.ws_url,
        "audio_seconds": audio_duration,
        "chunk_seconds": args.chunk_seconds,
        "chunks_sent": len(chunks),
        "realtime": args.realtime,
        "wall_time": wall_time,
        "first_result_at": first_result_at,
        "last_result_at": last_result_at,
        "result_count": len(text_results),
        "error_count": len(errors),
        "final_chars": len(final_text),
        "result_arrival_seconds": summarize(received_times),
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ws-url", default="ws://localhost:8000/v1/stream/transcriptions"
    )
    parser.add_argument("--audio", required=True, help="16 kHz mono int16 WAV file")
    parser.add_argument("--language", default="en")
    parser.add_argument(
        "--task", choices=["transcribe", "translate"], default="transcribe"
    )
    parser.add_argument("--chunk-seconds", type=float, default=0.25)
    parser.add_argument("--drain-seconds", type=float, default=5.0)
    parser.add_argument("--realtime", action="store_true")
    parser.add_argument("--json-output")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    payload = asyncio.run(run(args))
    print_summary("STT Benchmark", payload)
    print_summary("Result Arrival Seconds", payload["result_arrival_seconds"])
    write_json(args.json_output, payload)


if __name__ == "__main__":
    main()
