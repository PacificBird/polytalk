#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Benchmark a Piper-compatible TTS HTTP service."""

from __future__ import annotations

import argparse
import asyncio
import time
from typing import Any

import httpx

from common import print_summary, read_lines, summarize, write_json


DEFAULT_TEXTS = [
    "Hello, this is a short text to speech benchmark.",
    "This sentence is a little longer and should produce a larger audio file.",
    "PolyTalk measures text to speech latency separately from translation latency.",
]


async def run_one(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    index: int,
    text: str,
) -> dict[str, Any]:
    """Run one TTS request."""
    payload: dict[str, Any] = {"text": text}
    if args.voice:
        payload["voice"] = args.voice

    started = time.perf_counter()
    error = None
    status_code = None
    bytes_received = 0

    try:
        response = await client.post(args.base_url.rstrip("/") + "/", json=payload)
        status_code = response.status_code
        response.raise_for_status()
        bytes_received = len(response.content)
    except Exception as exc:  # noqa: BLE001 - benchmark must report all failures.
        error = str(exc)

    duration = time.perf_counter() - started
    return {
        "index": index,
        "chars": len(text),
        "bytes": bytes_received,
        "duration": duration,
        "status_code": status_code,
        "success": error is None,
        "error": error,
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    """Run the benchmark."""
    texts = read_lines(args.input, DEFAULT_TEXTS) * args.repeat
    semaphore = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(timeout=args.timeout) as client:

        async def guarded(index: int, text: str) -> dict[str, Any]:
            async with semaphore:
                return await run_one(client, args, index, text)

        started = time.perf_counter()
        results = await asyncio.gather(
            *(guarded(index, text) for index, text in enumerate(texts))
        )
        wall_time = time.perf_counter() - started

    successful = [item for item in results if item["success"]]
    payload = {
        "service": "tts",
        "base_url": args.base_url,
        "voice": args.voice,
        "requests": len(results),
        "successes": len(successful),
        "failures": len(results) - len(successful),
        "concurrency": args.concurrency,
        "wall_time": wall_time,
        "latency": summarize(item["duration"] for item in successful),
        "audio_bytes": summarize(item["bytes"] for item in successful),
        "results": results,
    }
    return payload


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--voice", default="")
    parser.add_argument("--input")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json-output")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    payload = asyncio.run(run(args))
    print_summary("TTS Benchmark", payload)
    print_summary("Latency Seconds", payload["latency"])
    print_summary("Audio Bytes", payload["audio_bytes"])
    write_json(args.json_output, payload)


if __name__ == "__main__":
    main()
