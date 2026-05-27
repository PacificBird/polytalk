# PolyTalk TTS Deployment

Standalone Piper-backed TTS service for PolyTalk.

## Quick Start

### 1. Build Docker Image

```bash
cd tts
docker build -t polytalk-tts:latest .
```

### 2. Download Voices

```bash
./setup-voices.sh
```

Or manually:

```bash
mkdir -p voices
docker run --rm --entrypoint python -v "$(pwd)/voices:/data" polytalk-tts:latest -m piper.download_voices --data-dir /data en_GB-jenny_dioco-medium
```

### 3. Start Server

```bash
docker compose up -d tts
```

### 4. Test

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test."}' \
  -o output.wav \
  localhost:5000
```

## API Usage

### Generate Speech

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "voice": "en_GB-jenny_dioco-medium",
    "length_scale": 1.0
  }' \
  -o output.wav \
  http://localhost:5000
```

### Available Parameters

- `text` (required): Text to synthesize
- `voice` (optional): Voice name (default: en_GB-jenny_dioco-medium)
- `speaker` (optional): Speaker name for multi-speaker voices
- `length_scale` (optional): Speaking speed (default: 1.0)
- `noise_scale` (optional): Voice variability (default: 0.667)
- `noise_w_scale` (optional): Phoneme width variability (default: 0.8)

### List Available Voices

```bash
curl localhost:5000/voices
```

## Voice Options

The default setup script downloads the same Piper voice set used by the demo:

- `ar_JO-kareem-medium` - Arabic
- `de_DE-karlsson-low` - German
- `en_GB-jenny_dioco-medium` - English
- `es_ES-davefx-medium` - Spanish
- `es_MX-claude-high` - Spanish (Mexico)
- `fr_FR-siwis-medium` - French
- `hi_IN-priyamvada-medium` - Hindi
- `it_IT-paola-medium` - Italian
- `ml_IN-arjun-medium` - Malayalam
- `nl_NL-ronnie-medium` - Dutch
- `nl_BE-nathalie-medium` - Dutch (Belgium)
- `ro_RO-mihai-medium` - Romanian
- `ru_RU-denis-medium` - Russian
- `tr_TR-dfki-medium` - Turkish
- `zh_CN-huayan-medium` - Chinese

## Integration with PolyTalk

Update `.env`:

```env
TTS_BASE_URL=http://host.docker.internal:5000
```

Or for production:

```env
TTS_BASE_URL=http://tts:5000
```

## Stopping

```bash
docker compose down
```
