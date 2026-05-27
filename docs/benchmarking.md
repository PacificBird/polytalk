# Benchmarking

PolyTalk includes small benchmark scripts for measuring STT, translation, TTS,
and full pipeline latency. These scripts are intended for staging and local
performance checks, not for load testing public production systems.

The scripts live in `tools/benchmarks/` and use the existing project
dependencies: `httpx` and `websockets`.

## Audio Input Format

STT and pipeline benchmarks expect a WAV file with:

- 16 kHz sample rate
- mono audio
- 16-bit PCM samples

The browser sends this same format during live streaming.

This repo includes a Piper-generated fixture at `samples/de_60s_16k_mono.wav`
and its source text at `samples/de_60s_transcript.txt`. It is useful for
repeatable tool checks, but final latency numbers should still be taken with
real test-team audio because synthetic speech does not match every speaker,
accent, and pause pattern.

## Translation Benchmark

Use this against OpenAI-compatible providers such as vLLM:

```bash
python tools/benchmarks/benchmark_translation.py \
  --base-url http://127.0.0.1:8001 \
  --model polytalk-translation \
  --source-language de \
  --target-language en \
  --concurrency 1 \
  --repeat 3
```

For authenticated providers, set `TRANSLATION_API_KEY` in the environment.
The script also accepts `--api-key`, but command-line secrets can be exposed
through shell history and process lists, so environment variables are preferred.

With a custom input file:

```bash
python tools/benchmarks/benchmark_translation.py \
  --base-url http://127.0.0.1:8001 \
  --model polytalk-translation \
  --input samples/de_chunks.txt \
  --json-output translation-benchmark.json
```

The input file should contain one source text chunk per line.

## TTS Benchmark

```bash
python tools/benchmarks/benchmark_tts.py \
  --base-url http://localhost:5000 \
  --voice en_GB-jenny_dioco-medium \
  --repeat 3
```

The result reports latency and generated audio bytes. If backend generation is
fast but browser audio feels delayed, the remaining delay is likely playback
queueing rather than Piper generation.

## STT Benchmark

Benchmark the standalone STT service:

```bash
python tools/benchmarks/benchmark_stt.py \
  --ws-url ws://localhost:8000/v1/stream/transcriptions \
  --audio samples/de_60s_16k_mono.wav \
  --language de \
  --realtime
```

Use `--realtime` to pace audio like a browser stream. Without it, audio is sent
as fast as possible, which is useful for capacity tests but not representative
of user latency.

## Full Pipeline Benchmark

Benchmark PolyTalk through its browser WebSocket endpoint:

```bash
python tools/benchmarks/benchmark_pipeline.py \
  --ws-url ws://localhost:9000/api/ws/translate \
  --audio samples/de_60s_16k_mono.wav \
  --source-language de \
  --target-language en \
  --realtime \
  --json-output pipeline-benchmark.json
```

The pipeline benchmark reports:

- first transcription time
- first translation time
- first TTS message time
- event counts
- p50/p95 arrival times for each event type

This measures server-side availability of results. It does not measure browser
audio playback start/end time.

## Suggested Baseline Runs

For each language pair, run:

```bash
python tools/benchmarks/benchmark_pipeline.py \
  --audio samples/<language>_60s_16k_mono.wav \
  --source-language <source> \
  --target-language en \
  --realtime \
  --json-output benchmark-<source>-en.json
```

Keep the JSON files from known-good deployments so future changes can be
compared against the same audio. Benchmark output files are ignored by Git by
default; commit only curated fixtures or summaries that are useful to future
contributors.

## Reading Results

Focus on:

- `first_transcription_at`: initial STT latency.
- `first_translation_at`: time until first translated text is available.
- `first_tts_at`: time until first generated speech URL is available.
- `wall_time - audio_seconds`: total lag after the source audio duration.
- p95 values: worst normal-case latency, more useful than average alone.

For live translation, a stable small lag is better than occasional fast output
with large queue spikes.
