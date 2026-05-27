// SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
// SPDX-License-Identifier: AGPL-3.0-or-later

/**
 * PolyTalkApp Class
 * Main application class for PolyTalk
 */

class PolyTalkApp {
    /**
     * Main application class for PolyTalk
     */
    constructor() {
        this.audioRecorder = new AudioRecorder();
        this.recordedAudio = null;
        this.ws = null;
        this.isStreaming = false;
        this.isPaused = false;
        this.currentTranscript = '';
        this.currentTranslation = '';
        this.liveTranscriptText = '';
        this.liveTranslationText = '';
        this.autoPlayAudio = true;
        this.ttsQueue = [];
        this.isPlayingTTS = false;
        this.currentTTSPreload = null;
        this.readinessStages = {};
        this.sessionStartMode = null;
        this.isMobileDevice = false;
        this.isTabAudioSupported = true;
        this.isApplyingLanguageParams = false;

        this.initElements();
        this.applyLanguageParamsToView();
        this.initEventListeners();
        this.updateUIState('ready');
        this.initAsync();
    }

    /**
     * Cache for supported languages
     */
    supportedLanguages = null;

    /**
     * Initialize async operations
     */
    async initAsync() {
        await this.checkBrowserSupport();
        this.checkMobileDevice();
        await this.loadSupportedLanguages();
    }

    /**
     * Initialize DOM elements
     */
    initElements() {
        this.liveBtn = document.getElementById('live-btn');
        this.shareTabBtn = document.getElementById('share-tab-btn');
        this.recordingControls = document.getElementById('recording-controls');
        this.pauseBtn = document.getElementById('pause-btn');
        this.stopBtn = document.getElementById('stop-btn');
        this.sessionControls = document.getElementById('session-controls');
        this.swapLangsBtn = document.getElementById('swap-langs-btn');
        this.sourceLang = document.getElementById('source-lang');
        this.targetLang = document.getElementById('target-lang');
        this.microphoneSelect = document.getElementById('microphone-select');
        this.settingsBtn = document.getElementById('settings-btn');
        this.closeSettingsBtn = document.getElementById('close-settings-btn');
        this.settingsModal = document.getElementById('settings-modal');
        this.inputDeviceSelect = document.getElementById('input-device-select');
        this.outputDeviceSelect = document.getElementById('output-device-select');
        this.status = document.getElementById('status');
        this.recordingIndicator = document.getElementById('recording-indicator');
        this.transcript = document.getElementById('transcript');
        this.translation = document.getElementById('translation');
        this.audioContainer = document.getElementById('audio-container');
        this.audioPlayer = document.getElementById('audio-player');
        this.liveTranscript = document.getElementById('live-transcript');
        this.liveTranslation = document.getElementById('live-translation');
        this.readinessPanel = document.getElementById('readiness-panel');
        this.readinessSummary = document.getElementById('readiness-summary');
        this.readinessFlashTimer = null;

        // Enable buttons on init
        if (this.liveBtn) this.liveBtn.disabled = false;
        if (this.shareTabBtn) this.shareTabBtn.disabled = false;
        if (this.pauseBtn) this.pauseBtn.disabled = true;
        if (this.stopBtn) this.stopBtn.disabled = true;
        if (this.sessionControls) this.sessionControls.style.display = 'none';
    }

    /**
     * Initialize event listeners
     */
    initEventListeners() {
        this.liveBtn = document.getElementById('live-btn');
        if (this.liveBtn) {
            this.liveBtn.addEventListener('click', () => this.startLiveTranslation());
        }
        this.shareTabBtn = document.getElementById('share-tab-btn');
        if (this.shareTabBtn) {
            this.shareTabBtn.addEventListener('click', () => this.startShareTabAudio());
        }
        this.pauseBtn = document.getElementById('pause-btn');
        if (this.pauseBtn) {
            this.pauseBtn.addEventListener('click', () => this.togglePause());
        }
        this.stopBtn = document.getElementById('stop-btn');
        if (this.stopBtn) {
            this.stopBtn.addEventListener('click', () => this.stopRecording());
        }
        this.swapLangsBtn = document.getElementById('swap-langs-btn');
        if (this.swapLangsBtn) {
            this.swapLangsBtn.addEventListener('click', () => this.handleSwapLanguages());
        }
        if (this.sourceLang) {
            this.sourceLang.addEventListener('change', () => this.handleLanguageChange());
        }
        if (this.targetLang) {
            this.targetLang.addEventListener('change', () => this.handleLanguageChange());
        }
        window.addEventListener('popstate', () => {
            try {
                this.applyLanguageParamsToView();
            } catch (error) {
                console.error('Failed to apply language params from browser history:', error);
            }
        });
        this.microphoneSelect = document.getElementById('microphone-select');
        if (this.microphoneSelect) {
            this.microphoneSelect.addEventListener('change', (e) => this.handleMicrophoneChange(e));
        }
        this.settingsBtn = document.getElementById('settings-btn');
        if (this.settingsBtn) {
            this.settingsBtn.addEventListener('click', () => {
                this.openSettings();
            });
        }
        this.closeSettingsBtn = document.getElementById('close-settings-btn');
        if (this.closeSettingsBtn) {
            this.closeSettingsBtn.addEventListener('click', () => this.closeSettings());
        }
        if (this.settingsModal) {
            this.settingsModal.addEventListener('click', (e) => {
                if (e.target === this.settingsModal) {
                    this.closeSettings();
                }
            });
        }
        this.inputDeviceSelect = document.getElementById('input-device-select');
        if (this.inputDeviceSelect) {
            this.inputDeviceSelect.addEventListener('change', (e) => this.handleInputDeviceChange(e));
        }
        this.outputDeviceSelect = document.getElementById('output-device-select');
        if (this.outputDeviceSelect) {
            this.outputDeviceSelect.addEventListener('change', (e) => this.handleOutputDeviceChange(e));
        }
        const saveSettingsBtn = document.getElementById('save-settings-btn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }
    }

    /**
     * Handle source/target language dropdown changes.
     */
    handleLanguageChange() {
        if (this.isApplyingLanguageParams) {
            return;
        }
        this.updateLanguageParamsInUrl();
    }

    /**
     * Apply source and target language query parameters to the dropdowns.
     */
    applyLanguageParamsToView() {
        if (this.isApplyingLanguageParams || !this.sourceLang || !this.targetLang) {
            return;
        }

        this.isApplyingLanguageParams = true;
        try {
            const params = new URLSearchParams(window.location.search);
            const sourceLanguage = this.getFirstQueryParam(params, [
                'source_language',
                'source_lang',
                'source'
            ]);
            const targetLanguage = this.getFirstQueryParam(params, [
                'target_language',
                'target_lang',
                'target'
            ]);

            let appliedParam = false;
            if (sourceLanguage && this.isEnabledLanguageOption(this.sourceLang, sourceLanguage)) {
                this.sourceLang.value = sourceLanguage;
                appliedParam = true;
            }
            if (targetLanguage && this.isEnabledLanguageOption(this.targetLang, targetLanguage)) {
                this.targetLang.value = targetLanguage;
                appliedParam = true;
            }

            if (appliedParam) {
                this.updateLanguageParamsInUrl({ replace: true });
            }
        } finally {
            this.isApplyingLanguageParams = false;
        }
    }

    /**
     * Return the first present query parameter value from a list of names.
     * @param {URLSearchParams} params - Current query params
     * @param {Array<string>} names - Accepted parameter names
     * @returns {string|null} - First matching parameter value
     */
    getFirstQueryParam(params, names) {
        for (const name of names) {
            const value = params.get(name);
            if (value) {
                return value;
            }
        }
        return null;
    }

    /**
     * Check whether a language code exists as an enabled option in a select.
     * @param {HTMLSelectElement} select - Language select element
     * @param {string} languageCode - Language code from URL or UI
     * @returns {boolean} - Whether the option can be selected
     */
    isEnabledLanguageOption(select, languageCode) {
        return Array.from(select.options).some(
            option => option.value === languageCode && !option.disabled
        );
    }

    /**
     * Get the currently selected source and target language values.
     * @returns {Object} - Current language pair
     */
    getCurrentLanguagePair() {
        return {
            sourceLanguage: this.sourceLang?.value || '',
            targetLanguage: this.targetLang?.value || ''
        };
    }

    /**
     * Keep source and target language query params in sync with the current UI.
     * @param {Object} options - Sync options
     * @param {boolean} options.replace - Replace current history entry instead of adding one
     */
    updateLanguageParamsInUrl({ replace = true } = {}) {
        if (!this.sourceLang || !this.targetLang) {
            return;
        }

        const url = new URL(window.location.href);
        const { sourceLanguage, targetLanguage } = this.getCurrentLanguagePair();

        // Normalize supported legacy aliases to the canonical parameter names.
        url.searchParams.delete('source_lang');
        url.searchParams.delete('target_lang');
        url.searchParams.delete('source');
        url.searchParams.delete('target');

        if (sourceLanguage) {
            url.searchParams.set('source_language', sourceLanguage);
        } else {
            url.searchParams.delete('source_language');
        }

        if (targetLanguage) {
            url.searchParams.set('target_language', targetLanguage);
        } else {
            url.searchParams.delete('target_language');
        }

        if (url.href === window.location.href) {
            return;
        }

        const historyMethod = replace ? 'replaceState' : 'pushState';
        window.history[historyMethod]({}, '', url);
    }



    /**
     * Handle microphone selection change
     * @param {Event} event - Change event
     */
    handleMicrophoneChange(event) {
        const deviceId = event.target.value;
        this.audioRecorder.setDeviceId(deviceId);
        this.showStatus(`Microphone changed to: ${event.target.options[event.target.selectedIndex].text}`, 'info');
        if (this.inputDeviceSelect) {
            this.inputDeviceSelect.value = deviceId;
        }
    }

    /**
     * Handle input device selection change (from settings modal)
     * @param {Event} event - Change event
     */
    handleInputDeviceChange(event) {
        const deviceId = event.target.value;
        this.audioRecorder.setDeviceId(deviceId);
        this.showStatus(`Microphone changed to: ${event.target.options[event.target.selectedIndex].text}`, 'info');
        if (this.microphoneSelect) {
            this.microphoneSelect.value = deviceId;
        }
    }

    /**
     * Handle output device selection change
     * @param {Event} event - Change event
     */
    handleOutputDeviceChange(event) {
        const deviceId = event.target.value;
        this.audioRecorder.setOutputDeviceId(deviceId);
        this.applyOutputDeviceToAudioPlayer(deviceId);
        this.showStatus(`Output device changed to: ${event.target.options[event.target.selectedIndex].text}`, 'info');
    }

    /**
     * Apply output device to audio player element
     * @param {string} deviceId - Device ID
     */
    applyOutputDeviceToAudioPlayer(deviceId) {
        this.applyOutputDeviceToAudioElement(this.audioPlayer, deviceId);
    }

    /**
     * Apply output device to any audio element
     * @param {HTMLAudioElement} audioElement - Audio element
     * @param {string} deviceId - Device ID
     */
    applyOutputDeviceToAudioElement(audioElement, deviceId) {
        if (audioElement && deviceId && deviceId !== 'default' && audioElement.setSinkId) {
            audioElement.setSinkId(deviceId).catch(err => {
                console.error('Failed to set audio output device:', err);
            });
        }
    }

    /**
     * Open settings modal
     */
    async openSettings() {
        if (this.settingsModal) {
            this.settingsModal.classList.add('active');

            // Request microphone permission first to ensure all devices are visible
            const hasPermission = await this.audioRecorder.requestPermission();
            if (!hasPermission) {
                alert('Microphone permission is required to view available devices.');
                return;
            }

            await this.loadInputDevices();
            await this.loadOutputDevices();
            this.loadSavedDevicePreferences();
        } else {
            console.error('Settings modal not found in DOM!');
        }
    }

    /**
     * Close settings modal
     */
    closeSettings() {
        if (this.settingsModal) {
            this.settingsModal.classList.remove('active');
        }
    }

    /**
     * Save settings and close modal
     */
    saveSettings() {
        const inputDeviceId = this.inputDeviceSelect?.value || 'default';
        const outputDeviceId = this.outputDeviceSelect?.value || 'default';

        localStorage.setItem('polytalk_input_device', inputDeviceId);
        localStorage.setItem('polytalk_output_device', outputDeviceId);

        this.audioRecorder.selectedDeviceId = inputDeviceId;
        this.audioRecorder.setOutputDeviceId(outputDeviceId);

        if (this.microphoneSelect) {
            this.microphoneSelect.value = inputDeviceId;
        }

        this.applyOutputDeviceToAudioPlayer(outputDeviceId);

        this.showStatus('Settings saved successfully!', 'success');
        this.closeSettings();
    }

    /**
     * Load saved device preferences
     */
    loadSavedDevicePreferences() {
        const savedInputDevice = localStorage.getItem('polytalk_input_device');
        const savedOutputDevice = localStorage.getItem('polytalk_output_device');

        if (savedInputDevice) {
            this.audioRecorder.selectedDeviceId = savedInputDevice;
        }

        if (savedOutputDevice) {
            this.audioRecorder.selectedOutputDeviceId = savedOutputDevice;
            this.applyOutputDeviceToAudioPlayer(savedOutputDevice);
        }
    }

    /**
     * Load available input devices (microphones)
     * Assumes permission has already been granted in openSettings()
     */
    async loadInputDevices() {
        if (!this.inputDeviceSelect) return;

        // Get saved device before rebuilding the list
        const savedDevice = localStorage.getItem('polytalk_input_device');

        const devices = await this.audioRecorder.enumerateDevices();

        this.inputDeviceSelect.innerHTML = '';

        devices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.textContent = device.label || `Microphone ${index + 1}`;
            this.inputDeviceSelect.appendChild(option);
        });

        // Restore saved selection if still available
        if (savedDevice) {
            const optionExists = Array.from(this.inputDeviceSelect.options).some(
                opt => opt.value === savedDevice
            );
            if (optionExists) {
                this.inputDeviceSelect.value = savedDevice;
            }
        }
    }

    /**
     * Load available output devices
     * Assumes permission has already been granted in openSettings()
     */
    async loadOutputDevices() {
        if (!this.outputDeviceSelect) return;

        // Get saved device before rebuilding the list
        const savedDevice = localStorage.getItem('polytalk_output_device');

        const devices = await this.audioRecorder.enumerateOutputDevices();
        this.outputDeviceSelect.innerHTML = '';

        devices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.textContent = device.label || `Speaker ${index + 1}`;
            this.outputDeviceSelect.appendChild(option);
        });

        // Restore saved selection if still available
        if (savedDevice) {
            const optionExists = Array.from(this.outputDeviceSelect.options).some(
                opt => opt.value === savedDevice
            );
            if (optionExists) {
                this.outputDeviceSelect.value = savedDevice;
            }
        }
    }

    /**
     * Handle swap languages button click
     */
    async handleSwapLanguages() {
        const {
            sourceLanguage: sourceValue,
            targetLanguage: targetValue
        } = this.getCurrentLanguagePair();

        // Prevent swap if same language
        if (sourceValue === targetValue) {
            this.showStatus('Source and target languages must be different.', 'warning');
            return;
        }

        // Swap the values
        this.sourceLang.value = targetValue;
        this.targetLang.value = sourceValue;
        this.updateLanguageParamsInUrl();

        // If streaming, send swap message to backend via WebSocket
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify({
                    type: 'swap_languages',
                    source_language: targetValue,
                    target_language: sourceValue
                }));
                this.showStatus('Language swap requested...', 'info');
            } catch (err) {
                console.error('Failed to send swap message:', err);
                this.showStatus('Failed to swap languages.', 'error');
                // Revert dropdown values
                this.sourceLang.value = sourceValue;
                this.targetLang.value = targetValue;
                this.updateLanguageParamsInUrl();
            }
        } else {
            // Not streaming, just show success
            this.showStatus('Languages swapped!', 'info');
        }
    }

    /**
     * Check if device is mobile and disable tab audio accordingly
     */
    checkMobileDevice() {
        this.isMobileDevice =
            window.innerWidth <= 768 || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        this.updateShareTabAvailability();
    }

    /**
     * Update the Share Tab Audio button based on browser and device support.
     */
    updateShareTabAvailability() {
        if (!this.shareTabBtn) {
            return;
        }

        const disabled = this.isMobileDevice || !this.isTabAudioSupported;
        this.shareTabBtn.disabled = disabled;
        if (this.isMobileDevice) {
            this.shareTabBtn.title = 'Not supported on mobile yet';
        } else if (!this.isTabAudioSupported) {
            this.shareTabBtn.title = 'Tab audio sharing is not supported in this browser';
        } else {
            this.shareTabBtn.title = 'Share Tab Audio';
        }
    }

    /**
     * Check if browser supports audio recording
     */
    async checkBrowserSupport() {
        this.isTabAudioSupported = AudioRecorder.isTabAudioSupported();

        if (!AudioRecorder.isSupported()) {
            this.showStatus(
                'Your browser does not support audio recording. Please use a modern browser like Chrome, Firefox, or Edge.',
                'error'
            );
            if (this.liveBtn) this.liveBtn.disabled = true;
        }
        if (!this.isTabAudioSupported) {
            this.showStatus(
                'Your browser does not support tab audio sharing.',
                'warning'
            );
        }

        // Check if we already have permission
        const permission = await navigator.permissions.query({ name: 'microphone' });

        if (permission.state === 'granted') {
            // Permission already granted, load microphones
            await this.loadMicrophones();
            this.showStatus('Ready to use microphone for live translation', 'success');
        } else if (permission.state === 'denied') {
            // Permission denied
            this.showStatus(
                'Microphone permission denied. Click the lock icon in your browser address bar and allow microphone access to use live translation.',
                'error'
            );
            if (this.liveBtn) this.liveBtn.disabled = true;
        } else {
            // Need to request permission
            this.showStatus(
                'Requesting microphone access...',
                'info'
            );

            // Auto-request permission
            const hasPermission = await this.audioRecorder.requestPermission();
            if (hasPermission) {
                await this.loadMicrophones();
                this.showStatus('Microphone access granted! Ready for live translation.', 'success');
                if (this.liveBtn) this.liveBtn.disabled = false;
            } else {
                this.showStatus(
                    'Microphone access needed. Click "Live Translate" and allow microphone permission when prompted.',
                    'info'
                );
                if (this.liveBtn) this.liveBtn.disabled = false;
            }
        }

        // Enable buttons by default
        if (this.liveBtn) this.liveBtn.disabled = false;
        this.updateShareTabAvailability();
        if (this.stopBtn) this.stopBtn.disabled = true;
    }

    /**
     * Load available microphones
     */
    async loadMicrophones() {
        if (!this.microphoneSelect) return;

        const devices = await this.audioRecorder.enumerateDevices();
        this.microphoneSelect.innerHTML = '<option value="">Select Microphone</option>';

        devices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.textContent = device.label || `Microphone ${index + 1}`;
            this.microphoneSelect.appendChild(option);
        });
    }

    /**
     * Reset the visible session readiness panel.
     * @param {string} summary - Short readiness summary
     */
    resetReadinessPanel(summary = 'Preparing session') {
        this.readinessStages = {};
        this.preserveReadinessNotice = false;
        this.flashReadiness(summary, 'active', false);
    }

    /**
     * Flash a compact readiness update.
     * @param {string} message - Short readiness message
     * @param {string} status - active, done, warning, or error
     * @param {boolean} autoHide - Whether to hide the flash after a short delay
     */
    flashReadiness(message, status = 'active', autoHide = true) {
        if (this.readinessFlashTimer) {
            clearTimeout(this.readinessFlashTimer);
            this.readinessFlashTimer = null;
        }
        if (this.readinessPanel) {
            this.readinessPanel.classList.remove('active', 'done', 'warning', 'error');
            this.readinessPanel.classList.add('active');
            if (status !== 'active') {
                this.readinessPanel.classList.add(status);
            }
        }
        if (this.readinessSummary) {
            this.readinessSummary.textContent = message;
        }
        if (autoHide && status !== 'error') {
            this.readinessFlashTimer = setTimeout(() => this.setReadinessIdle(), 1300);
        }
    }

    /**
     * Return readiness UI to its idle state.
     */
    setReadinessIdle() {
        this.readinessStages = {};
        this.preserveReadinessNotice = false;
        if (this.readinessFlashTimer) {
            clearTimeout(this.readinessFlashTimer);
            this.readinessFlashTimer = null;
        }
        if (this.readinessPanel) {
            this.readinessPanel.classList.remove('active', 'done', 'warning', 'error');
        }
        if (this.readinessSummary) {
            this.readinessSummary.textContent = 'Ready';
        }
    }

    /**
     * Update one readiness stage in the startup panel.
     * @param {string} stage - Stage identifier
     * @param {string} status - pending, active, done, warning, or error
     * @param {string} message - Short summary for the panel header
     */
    updateReadinessStage(stage, status, message = '') {
        this.readinessStages[stage] = status;
        if (message && status !== 'pending') {
            this.flashReadiness(message, status, false);
        }
        this.maybeMarkSessionListening();
    }

    /**
     * Mark the session as listening once capture and backend readiness are done.
     */
    maybeMarkSessionListening() {
        const hasAudio = this.readinessStages.audio_capture === 'done';
        const hasServer = this.readinessStages.server_connected === 'done';
        const hasPipeline = ['done', 'warning'].includes(
            this.readinessStages.pipeline_ready
        );
        if (!hasAudio || !hasServer || !hasPipeline) {
            return;
        }

        this.readinessStages.listening = 'done';
        this.flashReadiness('Ready. Listening now.', 'done', true);
        this.isStreaming = true;
        this.isPaused = false;
        this.updateUIState('streaming');
        this.scrollToStatusMessage();
    }

    /**
     * Bring the status/readiness area into view on small screens.
     */
    scrollToStatusMessage() {
        if (!this.status) {
            return;
        }
        if (!window.matchMedia('(max-width: 768px)').matches) {
            return;
        }

        window.requestAnimationFrame(() => {
            this.status.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
                inline: 'nearest'
            });
        });
    }

    /**
     * Handle backend connection and pipeline readiness updates.
     * @param {Object} result - Pipeline status result
     */
    handlePipelineStatus(result) {
        const stage = result.stage;
        const status = result.status || 'active';
        const message = result.message || 'Preparing session';

        if (stage === 'pipeline_warming') {
            this.updateReadinessStage('pipeline_ready', 'active', message);
            return;
        }

        this.updateReadinessStage(stage, status, message);

        if (status === 'error' || status === 'warning') {
            const log = status === 'error' ? console.error : console.warn;
            log(`Pipeline ${stage} ${status}: ${message}`);
        }
    }

    /**
     * Start live translation with microphone
     */
    async startLiveTranslation() {
        const {
            sourceLanguage: sourceLang,
            targetLanguage: targetLang
        } = this.getCurrentLanguagePair();

        if (sourceLang === targetLang) {
            this.showStatus('Source and target languages must be different.', 'warning');
            return;
        }

        this.sessionStartMode = 'microphone';
        this.resetReadinessPanel('Requesting microphone access');
        this.updateReadinessStage('audio_permission', 'active', 'Requesting microphone access');
        this.updateUIState('connecting');
        this.clearLiveResults();

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/translate?source_language=${sourceLang}&target_language=${targetLang}`;

        this.updateReadinessStage('server_connected', 'active', 'Connecting to server');
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.updateReadinessStage('server_connected', 'done', 'Server connected');
        };

        this.ws.onmessage = (event) => {
            const result = JSON.parse(event.data);
            this.handleStreamResult(result);
        };

        this.ws.onerror = (error) => {
            this.showSessionNotice('Connection issue detected. Please try again.', 'error');
            this.closeWebSocket();
        };

        this.ws.onclose = () => {
            this.isStreaming = false;
            this.isPaused = false;
            this.updateUIState('ready');
        };

        const success = await this.audioRecorder.startMicrophone((chunk) => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN && !this.isPaused) {
                this.ws.send(chunk);
            }
        });

        if (!success) {
            this.showSessionNotice('Failed to start microphone. Please check permissions.', 'error');
            this.updateReadinessStage('audio_permission', 'error', 'Microphone unavailable');
            this.closeWebSocket();
            this.updateUIState('ready');
            return;
        }

        this.updateReadinessStage('audio_permission', 'done', 'Microphone ready');
        this.updateReadinessStage('audio_capture', 'done', 'Audio capture ready');
    }

    /**
     * Handle streaming result from WebSocket
     */
    handleStreamResult(result) {
        // Handle language swap confirmation first (not part of switch)
        if (result.type === 'language_swapped') {
            this.handleLanguageSwap(result);
            return;
        }
        if (result.type === 'pipeline_status') {
            this.handlePipelineStatus(result);
            return;
        }

        switch (result.type) {
            case 'transcription':
                if (result.transcript) {
                    // Backend streaming transcription is cumulative.
                    this.liveTranscriptText = result.transcript;
                }
                this.updateLiveTranscript(this.liveTranscriptText, result.is_partial);
                break;

            case 'translation':
                if (result.translated_text) {
                    // Backend sends full accumulated translation, so we replace
                    this.liveTranslationText = result.translated_text;
                }
                this.updateLiveTranslation(this.liveTranslationText);
                break;

            case 'tts':
                if (result.audio_url) {
                    // Add sequence number for ordering (default to current queue length)
                    const sequence = result.sequence !== undefined ? result.sequence : this.ttsQueue.length;
                    this.ttsQueue.push(this.createTTSQueueItem(result.audio_url, sequence));
                    if (!this.isPlayingTTS) {
                        this.playNextTTS();
                    }
                }
                break;

            case 'complete':
                this.showSessionNotice('Live translation complete!', 'success');
                if (result.transcript) {
                    this.transcript.innerHTML = this.escapeHtml(result.transcript);
                }
                if (result.translated_text) {
                    this.translation.innerHTML = this.escapeHtml(result.translated_text);
                }
                setTimeout(() => {
                    this.updateUIState('ready');
                }, 2000);
                break;

            case 'error':
                this.showSessionNotice(`Error: ${result.error}`, 'error');
                this.closeWebSocket();
                break;
        }
    }

    /**
     * Play next TTS in queue (sorted by sequence number)
     */
    async playNextTTS() {
        if (this.ttsQueue.length === 0) {
            this.isPlayingTTS = false;
            this.cleanupTTSPreload(this.currentTTSPreload);
            this.currentTTSPreload = null;
            return;
        }

        // Sort queue by sequence number to ensure correct order
        this.ttsQueue.sort((a, b) => a.sequence - b.sequence);

        this.isPlayingTTS = true;
        const item = this.ttsQueue.shift();
        const audioUrl = item.url;
        this.cleanupTTSPreload(this.currentTTSPreload);
        this.currentTTSPreload = item.audio;

        this.audioPlayer.src = audioUrl;
        this.audioContainer.style.display = 'block';
        this.audioPlayer.load();

        try {
            await this.audioPlayer.play();
            // Wait for audio to finish playing
            await new Promise(resolve => {
                const done = () => resolve();
                this.audioPlayer.addEventListener('ended', done, { once: true });
                this.audioPlayer.addEventListener('error', done, { once: true });
            });
        } catch (err) {
            console.warn('TTS playback error:', err);
        } finally {
            if (this.currentTTSPreload === item.audio) {
                this.cleanupTTSPreload(this.currentTTSPreload);
                this.currentTTSPreload = null;
            }
        }

        // Play next in queue
        this.playNextTTS();
    }

    /**
     * Create a queued TTS item and begin loading it immediately.
     */
    createTTSQueueItem(audioUrl, sequence) {
        const audio = new Audio(audioUrl);
        audio.preload = 'auto';
        this.applyOutputDeviceToAudioElement(audio, this.audioRecorder.selectedOutputDeviceId);
        audio.load();
        return { url: audioUrl, sequence: sequence, audio: audio };
    }

    /**
     * Stop a preloaded TTS audio element and release its media resource.
     */
    cleanupTTSPreload(audio) {
        if (!audio) {
            return;
        }
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
    }

    /**
     * Clear queued and active TTS playback.
     */
    resetTTSPlayback() {
        this.ttsQueue.forEach(item => {
            if (item.audio !== this.currentTTSPreload) {
                this.cleanupTTSPreload(item.audio);
            }
        });
        this.ttsQueue = [];
        this.isPlayingTTS = false;
        this.cleanupTTSPreload(this.currentTTSPreload);
        this.currentTTSPreload = null;
        if (this.audioPlayer) {
            this.audioPlayer.pause();
            this.audioPlayer.removeAttribute('src');
            this.audioPlayer.load();
        }
    }

    /**
     * Update live transcript display
     */
    updateLiveTranscript(text, isPartial) {
        if (this.liveTranscript) {
            // Clean up multiple spaces
            const cleanText = text.replace(/\s+/g, ' ');
            this.currentTranscript = cleanText;

            // Preserve separator elements if they exist
            const separators = this.liveTranscript.querySelectorAll('.language-swap-separator');
            const hasSeparators = separators.length > 0;

            if (hasSeparators) {
                // Keep separators, update only the text element
                let textElement = this.liveTranscript.querySelector('.live-transcript-text');
                if (!textElement) {
                    textElement = document.createElement('div');
                    textElement.className = 'live-transcript-text';
                    this.liveTranscript.insertBefore(textElement, separators[0]);
                }
                textElement.textContent = cleanText + (isPartial ? '...' : '');
                textElement.style.fontStyle = isPartial ? 'italic' : 'normal';
            } else {
                this.liveTranscript.innerHTML = this.escapeHtml(cleanText) + (isPartial ? '...' : '');
                this.liveTranscript.style.fontStyle = isPartial ? 'italic' : 'normal';
            }
        }
    }

    /**
     * Update live translation display
     */
    updateLiveTranslation(text) {
        if (this.liveTranslation) {
            // Preserve separator elements if they exist
            const separators = this.liveTranslation.querySelectorAll('.language-swap-separator');
            const hasSeparators = separators.length > 0;

            if (hasSeparators) {
                // Keep separators, update only the text element
                let textElement = this.liveTranslation.querySelector('.live-translation-text');
                if (!textElement) {
                    textElement = document.createElement('div');
                    textElement.className = 'live-translation-text';
                    this.liveTranslation.insertBefore(textElement, separators[0]);
                }
                textElement.textContent = text;
            } else {
                this.liveTranslation.innerHTML = this.escapeHtml(text);
            }
        }
    }

    /**
     * Clear live results
     */
    clearLiveResults() {
        this.liveTranscriptText = '';
        this.liveTranslationText = '';
        this.resetTTSPlayback();
        if (this.liveTranscript) {
            // Only clear text elements, keep separators
            const textElement = this.liveTranscript.querySelector('.live-transcript-text');
            if (textElement) {
                textElement.textContent = '';
                textElement.style.fontStyle = 'normal';
            }
        }
        if (this.liveTranslation) {
            // Only clear text elements, keep separators
            const textElement = this.liveTranslation.querySelector('.live-translation-text');
            if (textElement) {
                textElement.textContent = '';
            }
        }
    }

    /**
     * Close WebSocket connection
     */
    closeWebSocket() {
        if (this.ws) {
            const ws = this.ws;
            this.ws = null;

            if (ws.readyState === WebSocket.OPEN) {
                try {
                    ws.send(JSON.stringify({ type: 'end' }));
                    setTimeout(() => {
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.close();
                        }
                    }, 100);
                } catch (e) {
                    ws.close();
                }
            } else {
                ws.close();
            }
        }
        this.isStreaming = false;
        this.resetTTSPlayback();
    }

    /**
     * Start sharing tab audio for live translation
     */
    async startShareTabAudio() {
        const {
            sourceLanguage: sourceLang,
            targetLanguage: targetLang
        } = this.getCurrentLanguagePair();

        if (sourceLang === targetLang) {
            this.showStatus('Source and target languages must be different.', 'warning');
            return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
            this.showStatus(
                'Tab audio sharing is not supported on mobile devices. Please use "Live Translate (Microphone)" instead, or switch to a desktop browser.',
                'error'
            );
            this.updateUIState('ready');
            return;
        }

        this.sessionStartMode = 'tab';
        this.resetReadinessPanel('Opening screen sharing dialog');
        this.updateReadinessStage('audio_permission', 'active', 'Opening screen sharing dialog');
        this.updateUIState('connecting');
        this.clearLiveResults();

        // First, try to get tab audio sharing - this will show the dialog
        try {
            const success = await this.audioRecorder.startTabAudio((chunk) => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN && !this.isPaused) {
                    this.ws.send(chunk);
                }
            });

            if (!success) {
                throw new Error('Failed to start tab audio capture');
            }
        } catch (error) {
            this.showSessionNotice(`Failed to share tab audio: ${error.message}`, 'error');
            this.updateReadinessStage('audio_permission', 'error', 'Tab audio unavailable');
            this.updateUIState('ready');
            this.audioRecorder.stop();
            return;
        }

        this.updateReadinessStage('audio_permission', 'done', 'Tab audio selected');
        this.updateReadinessStage('audio_capture', 'done', 'Tab audio captured');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/translate?source_language=${sourceLang}&target_language=${targetLang}`;

        this.updateReadinessStage('server_connected', 'active', 'Connecting to server');
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.updateReadinessStage('server_connected', 'done', 'Server connected');
        };

        this.ws.onmessage = (event) => {
            const result = JSON.parse(event.data);
            this.handleStreamResult(result);
        };

        this.ws.onerror = (error) => {
            this.showSessionNotice('Connection issue detected. Please try again.', 'error');
            this.closeWebSocket();
        };

        this.ws.onclose = () => {
            this.isStreaming = false;
            this.isPaused = false;
            this.updateUIState('ready');
        };
    }

    /**
     * Toggle pause/resume
     */
    togglePause() {
        if (!this.isStreaming) return;

        this.isPaused = !this.isPaused;

        // Send pause/resume signal to server
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const signal = this.isPaused ? 'pause' : 'resume';
            this.ws.send(JSON.stringify({ type: signal }));
        }

        if (this.isPaused) {
            this.showSessionNotice('Paused. Audio transmission stopped.', 'info');
            if (this.pauseBtn) {
                this.pauseBtn.innerHTML = '<span class="control-icon control-icon-play" aria-hidden="true"></span><span class="btn-text">Resume</span>';
                this.pauseBtn.className = 'btn btn-resume';
                this.pauseBtn.setAttribute('aria-label', 'Resume live translation');
            }
            this.updateUIState('paused');
        } else {
            this.showSessionNotice('Resumed. Audio transmission continues.', 'success');
            if (this.pauseBtn) {
                this.pauseBtn.innerHTML = '<span class="control-icon control-icon-pause" aria-hidden="true"></span><span class="btn-text">Pause</span>';
                this.pauseBtn.className = 'btn btn-tertiary';
                this.pauseBtn.setAttribute('aria-label', 'Pause live translation');
            }
            this.updateUIState('streaming');
        }
    }

    /**
     * Stop live translation
     */
    async stopRecording() {
        if (this.isStreaming) {
            this.closeWebSocket();
        }
        await this.audioRecorder.stop();
        this.isPaused = false;
        if (this.pauseBtn) {
            this.pauseBtn.innerHTML = '<span class="control-icon control-icon-pause" aria-hidden="true"></span><span class="btn-text">Pause</span>';
            this.pauseBtn.className = 'btn btn-tertiary';
            this.pauseBtn.setAttribute('aria-label', 'Pause live translation');
        }
        this.updateUIState('ready');
        this.showSessionNotice('Live translation stopped.', 'success');
    }

    /**
     * Handle tab share stopped externally (from Chrome's white strip)
     */
    handleTabShareStopped() {
        if (this.isStreaming) {
            this.closeWebSocket();
        }
        this.updateUIState('ready');
        this.showSessionNotice('Tab sharing stopped.', 'success');
    }

    /**
     * Display translation result
     * @param {Object} result - API response result
     */
    displayResult(result) {
        // Handle language swap confirmation
        if (result.type === 'language_swapped') {
            this.handleLanguageSwap(result);
            return;
        }

        if (result.transcript) {
            this.transcript.innerHTML = this.escapeHtml(result.transcript);
        }

        if (result.translated_text) {
            this.translation.innerHTML = this.escapeHtml(result.translated_text);
        }

        if (result.audio_url) {
            this.audioPlayer.src = result.audio_url;
            this.audioContainer.style.display = 'block';

            const autoPlay = document.querySelector('meta[name="auto-play"]')?.content === 'true';
            if (autoPlay) {
                this.audioPlayer.play().catch(() => {
                    // Auto-play prevented by browser
                });
            }
        }
    }

    /**
     * Handle language swap confirmation from backend
     * @param {Object} result - Backend response with new languages
     */
    handleLanguageSwap(result) {
        // Add visual separator in live translation display
        this.appendLanguageSwapSeparator(result.source_language, result.target_language);

        this.showStatus(
            `Language swapped: ${this.getLanguageName(result.source_language)} → ${this.getLanguageName(result.target_language)}`,
            'success'
        );
    }

    /**
     * Append visual separator for language swap
     * @param {string} oldSource - Previous source language
     * @param {string} oldTarget - Previous target language (now active)
     */
    appendLanguageSwapSeparator(oldSource, oldTarget) {
        // Add to live transcript display - update existing or create new
        if (this.liveTranscript) {
            // First, wrap existing text in a text container if not already done
            const existingText = this.liveTranscript.textContent || '';
            if (existingText.trim() && !this.liveTranscript.querySelector('.live-transcript-text')) {
                const textElement = document.createElement('div');
                textElement.className = 'live-transcript-text';
                textElement.textContent = existingText;
                this.liveTranscript.innerHTML = '';
                this.liveTranscript.appendChild(textElement);
            }

            // Check if separator already exists, update it if so
            let separator = this.liveTranscript.querySelector('.language-swap-separator');
            if (!separator) {
                separator = document.createElement('div');
                separator.className = 'language-swap-separator';
                this.liveTranscript.appendChild(separator);
            }

            separator.innerHTML = `
                <div class="swap-line"></div>
                <div class="swap-text">Language swap to → ${this.getLanguageName(oldSource)}</div>
                <div class="swap-line"></div>
            `;
        }

        // Add to live translation display - update existing or create new
        if (this.liveTranslation) {
            // First, wrap existing text in a text container if not already done
            const existingText = this.liveTranslation.textContent || '';
            if (existingText.trim() && !this.liveTranslation.querySelector('.live-translation-text')) {
                const textElement = document.createElement('div');
                textElement.className = 'live-translation-text';
                textElement.textContent = existingText;
                this.liveTranslation.innerHTML = '';
                this.liveTranslation.appendChild(textElement);
            }

            // Check if separator already exists, update it if so
            let separator = this.liveTranslation.querySelector('.language-swap-separator');
            if (!separator) {
                separator = document.createElement('div');
                separator.className = 'language-swap-separator';
                this.liveTranslation.appendChild(separator);
            }

            separator.innerHTML = `
                <div class="swap-line"></div>
                <div class="swap-text">Language swap to → ${this.getLanguageName(oldTarget)}</div>
                <div class="swap-line"></div>
            `;
        }
    }

    /**
     * Get enabled languages from HTML dropdowns
     * Returns array of enabled language codes (excludes disabled options)
     */
    getEnabledLanguages() {
        const enabledLangs = [];
        const options = this.sourceLang ? this.sourceLang.options : [];

        for (let i = 0; i < options.length; i++) {
            if (!options[i].disabled) {
                enabledLangs.push({
                    code: options[i].value,
                    name: options[i].textContent.trim()
                });
            }
        }

        return enabledLangs;
    }

    /**
     * Load supported languages from backend API (deprecated - no longer used)
     * Kept for backward compatibility only
     */
    async loadSupportedLanguages() {
        // No longer needed - languages are hardcoded in HTML
        this.supportedLanguages = this.getEnabledLanguages();
        console.info(`Loaded ${this.supportedLanguages.length} enabled languages from HTML dropdowns`);
    }

    /**
     * Populate language dropdowns with supported languages
     * Note: Dropdowns are hardcoded in HTML - this method is no longer used
     */
    populateLanguageDropdowns() {
        // This method is deprecated - HTML has hardcoded language options
        // Kept for backward compatibility only
    }

    /**
     * Get language name from code (uses backend-sourced list)
     * @param {string} code - Language code (e.g., 'en')
     * @returns {string} - Friendly name (e.g., 'English')
     */
    getLanguageName(code) {
        if (this.supportedLanguages) {
            const lang = this.supportedLanguages.find(l => l.code === code);
            if (lang) {
                return lang.name;
            }
        }
        // Fallback to uppercase code if not found
        return code.toUpperCase();
    }

    /**
     * Update UI state based on recording state
     * States: 'ready', 'connecting', 'streaming', 'paused'
     */
    updateUIState(state) {
        switch (state) {
            case 'connecting':
                if (this.liveBtn) this.liveBtn.disabled = true;
                if (this.shareTabBtn) this.shareTabBtn.disabled = true;
                if (this.recordingControls) this.recordingControls.style.display = 'none';
                if (this.pauseBtn) this.pauseBtn.disabled = true;
                if (this.stopBtn) this.stopBtn.disabled = false;
                if (this.sessionControls) this.sessionControls.style.display = 'flex';
                this.setRecordingIndicator('Preparing...', true);
                this.setLanguageFieldsDisabled(true);
                break;

            case 'streaming':
                if (this.liveBtn) this.liveBtn.disabled = true;
                if (this.shareTabBtn) this.shareTabBtn.disabled = true;
                if (this.recordingControls) this.recordingControls.style.display = 'none';
                if (this.pauseBtn) this.pauseBtn.disabled = false;
                if (this.stopBtn) this.stopBtn.disabled = false;
                if (this.sessionControls) this.sessionControls.style.display = 'flex';
                this.setRecordingIndicator('Listening...', true);
                this.setLanguageFieldsDisabled(true);
                break;

            case 'paused':
                if (this.liveBtn) this.liveBtn.disabled = true;
                if (this.shareTabBtn) this.shareTabBtn.disabled = true;
                if (this.recordingControls) this.recordingControls.style.display = 'none';
                if (this.pauseBtn) this.pauseBtn.disabled = false;
                if (this.stopBtn) this.stopBtn.disabled = false;
                if (this.sessionControls) this.sessionControls.style.display = 'flex';
                this.setRecordingIndicator('Paused', false);
                this.setLanguageFieldsDisabled(true);
                break;

            case 'ready':
                if (this.liveBtn) this.liveBtn.disabled = false;
                this.updateShareTabAvailability();
                if (this.recordingControls) this.recordingControls.style.display = 'flex';
                if (this.pauseBtn) this.pauseBtn.disabled = true;
                if (this.stopBtn) this.stopBtn.disabled = true;
                if (this.sessionControls) this.sessionControls.style.display = 'none';
                this.setRecordingIndicator('Recording', false);
                if (!this.preserveReadinessNotice) {
                    this.setReadinessIdle();
                }
                this.setLanguageFieldsDisabled(false);
                break;

            default:
                // Fail-safe: disable language fields for unknown states
                // This prevents changing languages during unexpected states
                if (this.liveBtn) this.liveBtn.disabled = false;
                this.updateShareTabAvailability();
                if (this.recordingControls) this.recordingControls.style.display = 'flex';
                if (this.pauseBtn) this.pauseBtn.disabled = true;
                if (this.stopBtn) this.stopBtn.disabled = true;
                if (this.sessionControls) this.sessionControls.style.display = 'none';
                this.setRecordingIndicator('Recording', false);
                this.setLanguageFieldsDisabled(true);
        }
    }

    /**
     * Update the recording indicator while preserving its wave markup.
     * @param {string} text - Indicator text
     * @param {boolean} visible - Whether the indicator should be visible
     */
    setRecordingIndicator(text, visible) {
        if (!this.recordingIndicator) {
            return;
        }
        this.recordingIndicator.classList.toggle('visible', visible);
        this.recordingIndicator.setAttribute('aria-label', text);
        this.recordingIndicator.innerHTML = `
            <span class="listening-wave-side listening-wave-left" aria-hidden="true">
                <span></span>
                <span></span>
                <span></span>
            </span>
            <span class="listening-mic" aria-hidden="true">
                <span class="mic-base"></span>
            </span>
            <span class="listening-wave-side listening-wave-right" aria-hidden="true">
                <span></span>
                <span></span>
                <span></span>
            </span>
        `;
    }

    /**
     * Set language fields disabled/readonly state
     * @param {boolean} disabled - Whether to disable the fields
     */
    setLanguageFieldsDisabled(disabled) {
        if (this.sourceLang) {
            this.sourceLang.disabled = disabled;
            this.sourceLang.style.opacity = disabled ? '0.5' : '1';
            this.sourceLang.style.cursor = disabled ? 'not-allowed' : 'pointer';
        }
        if (this.targetLang) {
            this.targetLang.disabled = disabled;
            this.targetLang.style.opacity = disabled ? '0.5' : '1';
            this.targetLang.style.cursor = disabled ? 'not-allowed' : 'pointer';
        }
    }

    /**
     * Show status message
     * @param {string} message - Status message
     * @param {string} type - Status type ('info', 'success', 'error', 'warning')
     */
    showStatus(message, type = 'info') {
        this.status.textContent = message;
        this.status.className = `status visible ${type}`;

        if (type === 'info') {
            setTimeout(() => {
                this.status.classList.remove('visible');
            }, 5000);
        }
    }

    /**
     * Show live-session notifications in the compact readiness flash.
     * @param {string} message - Notification message
     * @param {string} type - Status type ('info', 'success', 'error', 'warning')
     */
    showSessionNotice(message, type = 'info') {
        const readinessType = {
            info: 'active',
            success: 'done',
            warning: 'warning',
            error: 'error'
        }[type] || 'active';

        this.preserveReadinessNotice = true;
        this.flashReadiness(message, readinessType, true);
        this.scrollToStatusMessage();
        if (this.status) {
            this.status.classList.remove('visible');
        }
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} - Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
