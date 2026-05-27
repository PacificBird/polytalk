#!/bin/bash

# PolyTalk TTS Setup Script
# Downloads required voices for the PolyTalk TTS image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TTS_IMAGE="${TTS_IMAGE:-polytalk-tts:latest}"
VOICES_DIR="${VOICES_DIR:-${SCRIPT_DIR}/voices}"

echo "Setting up PolyTalk TTS voices using image: ${TTS_IMAGE}"

# Create voices directory if not exists
mkdir -p "${VOICES_DIR}"

# Download voices using Piper's download module (override ENTRYPOINT)
VOICES=(
  "ar_JO-kareem-medium"
  "de_DE-karlsson-low"
  "en_GB-jenny_dioco-medium"
  "es_ES-davefx-medium"
  "es_MX-claude-high"
  "fr_FR-siwis-medium"
  "hi_IN-priyamvada-medium"
  "it_IT-paola-medium"
  "ml_IN-arjun-medium"
  "nl_NL-ronnie-medium"
  "nl_BE-nathalie-medium"
  "ro_RO-mihai-medium"
  "ru_RU-denis-medium"
  "tr_TR-dfki-medium"
  "zh_CN-huayan-medium"
)

for voice in "${VOICES[@]}"; do
  echo "Downloading ${voice}..."
  docker run --rm --entrypoint python -v "${VOICES_DIR}:/data" "${TTS_IMAGE}" -m piper.download_voices --data-dir /data "${voice}"
done

echo "Voices downloaded successfully."
echo ""
echo "To start the PolyTalk TTS service:"
echo "  docker compose up -d"
echo ""
echo "Available voices:"
printf '  - %s\n' "${VOICES[@]}"
