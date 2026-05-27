#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Benchmark an OpenAI-compatible translation endpoint."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from typing import Any

import httpx

from common import print_summary, read_lines, summarize, write_json


DEFAULT_TEXTS = [
    "Hast du schon einmal allein gesessen?",
    "Vielleicht ist es eine Entschuldigung, die du viel zu lange hinausgezögert hast.",
    "Wir treffen uns nächste Woche und besprechen die offenen Punkte per E-Mail.",
]


def resolve_api_key(args: argparse.Namespace) -> str:
    """Return API key from CLI or environment."""
    if args.api_key:
        print(
            "Warning: --api-key may be visible in shell history and process lists. "
            "Prefer TRANSLATION_API_KEY for shared systems.",
            file=sys.stderr,
        )
        return args.api_key
    return os.getenv("TRANSLATION_API_KEY", "")


def build_payload(args: argparse.Namespace, text: str) -> dict[str, Any]:
    """Build an OpenAI-compatible chat completions payload."""
    system_prompt = (
        "You are a professional translator. Translate the following text from "
        f"{args.source_language} to {args.target_language}. Return ONLY the "
        "translated text. Do not add explanations, summaries, or extra content."
    )
    return {
        "model": args.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }


async def run_one(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    index: int,
    text: str,
) -> dict[str, Any]:
    """Run one translation request."""
    url = args.base_url.rstrip("/") + args.endpoint
    started = time.perf_counter()
    error = None
    translated_chars = 0
    status_code = None

    try:
        response = await client.post(url, json=build_payload(args, text))
        status_code = response.status_code
        response.raise_for_status()
        data = response.json()
        translated = data["choices"][0]["message"]["content"]
        translated_chars = len(translated)
    except Exception as exc:  # noqa: BLE001 - benchmark must report all failures.
        error = str(exc)

    duration = time.perf_counter() - started
    return {
        "index": index,
        "chars": len(text),
        "translated_chars": translated_chars,
        "duration": duration,
        "status_code": status_code,
        "success": error is None,
        "error": error,
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    """Run the benchmark."""
    texts = read_lines(args.input, DEFAULT_TEXTS) * args.repeat
    headers = {}
    api_key = resolve_api_key(args)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    timeout = httpx.Timeout(args.timeout)
    limits = httpx.Limits(max_connections=args.concurrency * 2)
    semaphore = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        headers=headers,
    ) as client:

        async def guarded(index: int, text: str) -> dict[str, Any]:
            async with semaphore:
                return await run_one(client, args, index, text)

        started = time.perf_counter()
        results = await asyncio.gather(
            *(guarded(index, text) for index, text in enumerate(texts))
        )
        total_duration = time.perf_counter() - started

    successful = [item for item in results if item["success"]]
    durations = [item["duration"] for item in successful]
    payload = {
        "service": "translation",
        "base_url": args.base_url,
        "model": args.model,
        "requests": len(results),
        "successes": len(successful),
        "failures": len(results) - len(successful),
        "concurrency": args.concurrency,
        "wall_time": total_duration,
        "latency": summarize(durations),
        "results": results,
    }
    return payload


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Security note: prefer TRANSLATION_API_KEY over --api-key because "
            "command-line arguments can be exposed through shell history and "
            "process lists."
        ),
    )
    parser.add_argument("--base-url", required=True, help="Provider base URL")
    parser.add_argument("--endpoint", default="/v1/chat/completions")
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--api-key",
        default="",
        help="Bearer API key. Prefer TRANSLATION_API_KEY to avoid CLI exposure.",
    )
    parser.add_argument("--source-language", default="de")
    parser.add_argument("--target-language", default="en")
    parser.add_argument("--input", help="Text file with one source chunk per line")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=160)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json-output")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    payload = asyncio.run(run(args))
    print_summary("Translation Benchmark", payload)
    print_summary("Latency Seconds", payload["latency"])
    write_json(args.json_output, payload)


if __name__ == "__main__":
    main()
