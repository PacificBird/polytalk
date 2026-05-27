# Contributing to PolyTalk CE

Thank you for taking the time to improve PolyTalk Community Edition.

## Before You Start

- Check existing issues and merge requests before opening a duplicate.
- Use the default mock configuration for local UI and service-flow changes.
- Do not commit `.env`, `config/config.yaml`, generated media, downloaded voice
  models, coverage output, or local cache files.
- Keep changes focused. Separate documentation, benchmarks, and runtime behavior
  changes when practical.

## Local Setup

```bash
cp .env.example .env
cp config/config.yaml.example config/config.yaml
pip install -r requirements.txt
pip install -r test-requirements.txt
```

The example config defaults to `mock_mode: true`, so it is safe to run without
real STT, translation, or TTS credentials.

Run the app locally:

```bash
python -m app.main
```

Run with Docker:

```bash
docker compose up -d --build
```

## Validation

Before opening a merge request, run:

```bash
pre-commit run --all-files
pytest tests/ -v
```

For Docker or streaming changes, also verify:

```bash
docker compose up -d --build
docker compose logs -f polytalk stt tts
```

## Code Guidelines

- Follow the existing FastAPI service structure.
- Use `get_config()` for configuration access.
- Keep provider-specific logic behind service classes where possible.
- Prefer environment variables for deployment-specific values and YAML for app
  behavior.
- Keep streaming logs useful but avoid noisy `INFO` logs for per-chunk internals;
  use `DEBUG` for diagnostics.
- Add tests for behavior changes and focused docs for new configuration.

## Commit and Merge Request Notes

- Use clear, present-tense commit messages.
- Include what changed, how it was tested, and any deployment/config impact.
- Mention whether the change affects STT, translation, TTS, frontend, Docker, or
  documentation.

## Licensing

By contributing, you agree that your contribution is licensed under AGPL-3.0-or-later
and that BizzAppDev Systems Pvt. Ltd. may use, modify, and relicense the
contribution as part of PolyTalk's dual-license model.
