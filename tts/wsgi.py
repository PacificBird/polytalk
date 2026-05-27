# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from pathlib import Path
from flask import Flask, request, jsonify, Response
from piper.http_server import PiperVoice, _LOGGER, download_voice, SynthesisConfig
import io
import wave
import json

# Get model path from environment
model_path = os.environ.get("PIPER_MODEL", "/data/en_GB-jenny_dioco-medium")
data_dir = os.environ.get("PIPER_DATA_DIR", "/data")

# Create the Flask app
app = Flask(__name__)


# Load the voice model
def load_voice(voice_name=None):
    """Load the Piper voice model."""
    if voice_name:
        model_file = Path(data_dir) / f"{voice_name}.onnx"
    else:
        model_file = Path(model_path)

        # Check if model exists, if not look in data directories
        if not model_file.exists():
            maybe_model_path = Path(data_dir) / f"{model_path}.onnx"
            if maybe_model_path.exists():
                model_file = maybe_model_path

    if not model_file.exists():
        raise ValueError(f"Model not found: {model_file}")

    return PiperVoice.load(model_file, use_cuda=False)


# Voice cache to store loaded voices in memory
_voice_cache = {}

# Load voice at module import time
try:
    default_voice = load_voice()
    _voice_cache["default"] = default_voice
    _LOGGER.info(f"Loaded voice model: {model_path}")
except Exception as e:
    _LOGGER.warning(f"Could not load voice model: {e}")
    default_voice = None


def get_voice(voice_name=None):
    """Get a voice from cache or load it dynamically."""
    cache_key = voice_name if voice_name else "default"

    if cache_key in _voice_cache:
        return _voice_cache[cache_key]

    if voice_name:
        try:
            _voice_cache[cache_key] = load_voice(voice_name)
            _LOGGER.info(f"Loaded dynamic voice: {voice_name}")
            return _voice_cache[cache_key]
        except Exception as e:
            _LOGGER.error(f"Failed to load voice {voice_name}: {e}")
            return None
    else:
        return default_voice


@app.route("/", methods=["POST"])
def synthesize():
    """Synthesize text to speech (original endpoint)."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400

    text = data["text"]

    # Support dynamic voice selection from payload
    voice_name = data.get("voice") or data.get("voice_name")

    current_voice = get_voice(voice_name)
    if current_voice is None:
        voice_display = voice_name if voice_name else "default"
        return jsonify({"error": f"Voice not found: {voice_display}"}), 404

    # Synthesize with original default values
    syn_config = SynthesisConfig(
        speaker_id=data.get("speaker_id"),
        length_scale=float(data.get("length_scale", current_voice.config.length_scale)),
        noise_scale=float(data.get("noise_scale", current_voice.config.noise_scale)),
        noise_w_scale=float(
            data.get("noise_w_scale", current_voice.config.noise_w_scale)
        ),
    )

    with io.BytesIO() as wav_io:
        wav_file = wave.open(wav_io, "wb")
        with wav_file:
            wav_params_set = False
            for i, audio_chunk in enumerate(current_voice.synthesize(text, syn_config)):
                if not wav_params_set:
                    wav_file.setframerate(audio_chunk.sample_rate)
                    wav_file.setsampwidth(audio_chunk.sample_width)
                    wav_file.setnchannels(1)
                    wav_params_set = True

                if i > 0:
                    wav_file.writeframes(
                        b"\x00" * int(current_voice.config.sample_rate * 0.0)
                    )

                wav_file.writeframes(audio_chunk.audio_int16_bytes)

        return Response(wav_io.getvalue(), mimetype="audio/wav")


@app.route("/voices", methods=["GET"])
def list_voices():
    """List available voices."""
    voices = {}
    data_path = Path(data_dir)
    if data_path.exists():
        for config_file in data_path.glob("*.json"):
            voice_name = config_file.stem
            with open(config_file) as f:
                voices[voice_name] = json.load(f)
    return jsonify(voices)


@app.route("/all-voices", methods=["GET"])
def list_all_voices():
    """List all voices (alias)."""
    return list_voices()


@app.route("/download", methods=["POST"])
def download_voice_endpoint():
    """Download a voice model."""
    data = request.get_json()
    if not data or "voice" not in data:
        return jsonify({"error": "Missing 'voice' parameter"}), 400

    voice_name = data["voice"]
    try:
        download_voice(voice_name, Path(data_dir))
        return jsonify({"status": "downloaded", "voice": voice_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "voice_loaded": default_voice is not None,
            "cached_voices": len(_voice_cache),
        }
    )
