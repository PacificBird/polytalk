# Security Policy

## Supported Version

Security fixes are accepted for the current `main` branch of PolyTalk Community
Edition.

## Reporting a Vulnerability

Please do not open a public issue for sensitive security reports.

Email security reports to:

```text
security@bizzappdev.com
```

Include:

- Affected component, endpoint, or deployment mode
- Reproduction steps or proof of concept
- Expected impact
- Relevant logs, configuration, or Docker details with secrets removed

We will acknowledge valid reports as soon as practical and coordinate a fix or
mitigation before public disclosure.

## Handling Secrets

- Never commit `.env`, API keys, Hugging Face tokens, private model URLs, or
  production `config/config.yaml`.
- Redact transcripts, translations, generated audio paths, and customer data from
  public issues unless they are synthetic test data.
- Use `config/config.yaml.example` and `.env.example` for shareable examples.

## Deployment Notes

- Set `APP_DEBUG=false` in production.
- Set `ALLOWED_ORIGINS` to explicit browser origins.
- Put PolyTalk behind a reverse proxy that supports WebSocket upgrades.
- Restrict direct access to internal STT, TTS, and translation services.
- Treat transcripts, translations, and generated speech as user data.
