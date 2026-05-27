// SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
// SPDX-License-Identifier: AGPL-3.0-or-later

/**
 * PolyTalk Frontend JavaScript
 * Handles microphone recording and API communication
 */

class AudioRecorder {
    /**
     * AudioRecorder class for handling microphone recording
     */
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.onChunk = null;
        this.chunkInterval = null;
        this.audioContext = null;
        this.source = null;
        this.processor = null;
        this.selectedDeviceId = '';
        this.selectedOutputDeviceId = '';
        this.isTabAudioMode = false;
        this.hasPermission = false;
    }

    /**
     * Enumerate available audio input devices
     * @returns {Promise<Array>} - List of audio input devices
     */
    async enumerateDevices() {
        try {
            // Only request permissions if we haven't already
            if (!this.hasPermission) {
                await navigator.mediaDevices.getUserMedia({ audio: true });
                this.hasPermission = true;
            }

            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.filter(device => device.kind === 'audioinput');
        } catch (error) {
            console.error('Failed to enumerate input devices:', error);
            return [];
        }
    }

    /**
     * Enumerate available audio output devices
     * @returns {Promise<Array>} - List of audio output devices
     */
    async enumerateOutputDevices() {
        try {
            // Ensure we have permission first
            if (!this.hasPermission) {
                await navigator.mediaDevices.getUserMedia({ audio: true });
                this.hasPermission = true;
            }

            // Check if browser supports audio output device enumeration
            if (!('setSinkId' in AudioContext.prototype)) {
                return [];
            }

            const devices = await navigator.mediaDevices.enumerateDevices();
            const hasOutputDeviceSupport = devices.some(d => d.kind === 'audiooutput');
            if (!hasOutputDeviceSupport) {
                return [];
            }
            return devices.filter(device => device.kind === 'audiooutput');
        } catch (error) {
            console.error('Failed to enumerate output devices:', error);
            return [];
        }
    }

    /**
     * Set selected output device ID
     * @param {string} deviceId - Device ID to select
     */
    setOutputDeviceId(deviceId) {
        this.selectedOutputDeviceId = deviceId;
        if (this.audioContext) {
            this.applyOutputDevice();
        }
    }

    /**
     * Apply output device to audio context
     * Only called when audioContext is guaranteed to exist
     */
    applyOutputDevice() {
        if (this.audioContext && this.selectedOutputDeviceId && this.selectedOutputDeviceId !== 'default') {
            if (this.audioContext.setSinkId) {
                this.audioContext.setSinkId(this.selectedOutputDeviceId).catch(err => {
                    console.error('Failed to set output device:', err);
                });
            }
        }
    }

    /**
     * Request microphone permission explicitly
     * @returns {Promise<boolean>} - True if permission granted
     */
    async requestPermission() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                alert("getUserMedia is not supported in this browser.");
                return false;
            }

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Stop stream after checking permission
            stream.getTracks().forEach((track) => track.stop());

            return true;
        } catch (error) {
            console.error("Microphone permission denied or failed:", error);
            alert(`Microphone access failed: ${error.name} - ${error.message}`);
            return false;
        }
    }

    /**
     * Set selected device ID
     * @param {string} deviceId - Device ID to select
     */
    setDeviceId(deviceId) {
        this.selectedDeviceId = deviceId;
    }

    /**
     * Start recording audio from microphone with PCM conversion
     * @param {Function} onChunk - Callback for audio chunks (for streaming)
     * @returns {Promise<boolean>} - Success status
     */
    async startMicrophone(onChunk = null) {
        try {
            const audioConstraints = {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 16000
            };

            if (this.selectedDeviceId) {
                audioConstraints.deviceId = { exact: this.selectedDeviceId };
            }

            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: audioConstraints
            });

            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });

            this.applyOutputDevice();

            const source = this.audioContext.createMediaStreamSource(this.stream);
            const scriptProcessor = this.audioContext.createScriptProcessor(2048, 1, 1);

            this.onChunk = onChunk;

            scriptProcessor.onaudioprocess = (event) => {
                const input = event.inputBuffer.getChannelData(0);

                const int16Array = new Int16Array(input.length);
                for (let i = 0; i < input.length; i++) {
                    const s = Math.max(-1, Math.min(1, input[i]));
                    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }

                const buffer = int16Array.buffer;

                if (this.onChunk && buffer.byteLength > 0) {
                    this.onChunk(buffer);
                }
            };

            source.connect(scriptProcessor);
            scriptProcessor.connect(this.audioContext.destination);

            this.processor = scriptProcessor;
            this.source = source;
            this.isRecording = true;
            this.isTabAudioMode = false;

            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Start recording audio from tab/screen audio with PCM conversion
     * @param {Function} onChunk - Callback for audio chunks (for streaming)
     * @returns {Promise<boolean>} - Success status
     */
    async startTabAudio(onChunk = null) {
        try {
            this.isTabAudioMode = true;
            this.onChunk = onChunk;

            const displayMediaOptions = {
                video: true,
                audio: true,
                selfBrowserSurface: 'include',
                systemAudio: 'include'
            };

            const stream = await navigator.mediaDevices.getDisplayMedia(displayMediaOptions);

            if (!stream || stream.getTracks().length === 0) {
                throw new Error('User cancelled screen sharing');
            }

            const audioTrack = stream.getAudioTracks()[0];

            if (!audioTrack) {
                stream.getTracks().forEach(track => track.stop());
                throw new Error('No audio track found. Please select a tab with audio and enable "Share audio".');
            }

            this.originalStream = stream;
            const audioOnlyStream = new MediaStream([audioTrack]);

            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });

            const source = this.audioContext.createMediaStreamSource(audioOnlyStream);
            const scriptProcessor = this.audioContext.createScriptProcessor(2048, 1, 1);

            scriptProcessor.onaudioprocess = (event) => {
                const input = event.inputBuffer.getChannelData(0);

                const int16Array = new Int16Array(input.length);
                for (let i = 0; i < input.length; i++) {
                    const s = Math.max(-1, Math.min(1, input[i]));
                    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }

                const buffer = int16Array.buffer;
                if (this.onChunk && buffer.byteLength > 0) {
                    this.onChunk(buffer);
                }
            };

            source.connect(scriptProcessor);
            scriptProcessor.connect(this.audioContext.destination);

            this.processor = scriptProcessor;
            this.source = source;
            this.stream = audioOnlyStream;
            this.isRecording = true;

            const handleStreamStopped = async () => {
                if (this.onChunk) {
                    this.onChunk = null;
                }
                await this.stop();
                if (window.polyTalkApp) {
                    window.polyTalkApp.handleTabShareStopped();
                }
            };

            stream.getVideoTracks()[0]?.addEventListener('ended', handleStreamStopped);

            return true;
        } catch (error) {
            if (error.name === 'NotAllowedError' || error.name === 'NotAllowedError') {
                throw new Error('Screen sharing permission denied. Please allow screen sharing and try again.');
            }
            throw error;
        }
    }

    /**
     * Stop recording audio
     * @returns {Promise<Blob>} - Recorded audio blob
     */
    async stop() {
        return new Promise((resolve) => {
            if (this.processor) {
                this.processor.disconnect();
                this.source.disconnect();
            }
            if (this.audioContext) {
                this.audioContext.close();
            }
            this.stream?.getTracks().forEach(track => track.stop());
            if (this.originalStream) {
                this.originalStream.getTracks().forEach(track => track.stop());
                this.originalStream = null;
            }
            this.isRecording = false;
            resolve(new Blob([], { type: 'audio/pcm' }));
        });
    }

    /**
     * Check if browser supports audio recording
     * @returns {boolean} - Support status
     */
    static isSupported() {
        return !!(navigator.mediaDevices && window.AudioContext);
    }

    /**
     * Check if browser supports tab audio sharing
     * @returns {boolean} - Support status
     */
    static isTabAudioSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia);
    }
}
