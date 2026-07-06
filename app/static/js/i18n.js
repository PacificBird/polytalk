// SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
    const config = window.POLYTALK_I18N || {};
    const messages = config.messages || {};
    const exactMap = messages._text || {};
    let displayNamesCache = null;

    function format(template, params = {}) {
        return String(template).replace(/\{([a-zA-Z0-9_]+)\}/g, (match, key) => {
            return Object.prototype.hasOwnProperty.call(params, key) ? params[key] : match;
        });
    }

    function hasOwn(object, key) {
        return Object.prototype.hasOwnProperty.call(object, key);
    }

    function t(key, params = {}) {
        const value = hasOwn(messages, key) ? messages[key] : (hasOwn(exactMap, key) ? exactMap[key] : key);
        return format(value, params);
    }

    function text(value, params = {}) {
        const raw = String(value ?? '');
        return format(hasOwn(exactMap, raw) ? exactMap[raw] : raw, params);
    }

    function translateAttributes(element) {
        ['aria-label', 'title', 'placeholder', 'alt'].forEach((attribute) => {
            const value = element.getAttribute(attribute);
            if (value && hasOwn(exactMap, value)) {
                element.setAttribute(attribute, exactMap[value]);
            }
        });
    }

    function translateTextNode(node) {
        const value = node.nodeValue;
        if (!value || !value.trim()) return;
        const leading = value.match(/^\s*/)?.[0] || '';
        const trailing = value.match(/\s*$/)?.[0] || '';
        const trimmed = value.trim();
        if (hasOwn(exactMap, trimmed)) {
            node.nodeValue = `${leading}${exactMap[trimmed]}${trailing}`;
        }
    }

    function displayLanguageName(code) {
        const raw = String(code || '');
        const normalized = raw.replace('_', '-');
        if (!normalized) return '';
        const mapped = messages._languages?.[raw] || messages._languages?.[normalized.replace('-', '_')];
        if (mapped) return mapped;
        try {
            displayNamesCache = displayNamesCache || new Intl.DisplayNames([config.locale || 'en'], { type: 'language' });
            return displayNamesCache.of(normalized) || displayNamesCache.of(normalized.split('-')[0]) || '';
        } catch (error) {
            return '';
        }
    }

    function titleCaseLanguageName(value) {
        return String(value || '').replace(/(^|[\s(])([^\s()])/g, (match, prefix, letter) => {
            return `${prefix}${letter.toLocaleUpperCase(config.locale || 'en')}`;
        });
    }

    function shouldTranslateLanguageSelect(select) {
        return select instanceof HTMLSelectElement
            && ['source-lang', 'target-lang'].includes(select.id)
            && !select.hasAttribute('data-ui-locale-switcher');
    }

    function translateLanguageOptions(root = document) {
        const disabledSuffix = text('Experimental');
        root.querySelectorAll('select').forEach((select) => {
            if (!shouldTranslateLanguageSelect(select)) return;
            Array.from(select.options).forEach((option) => {
                const value = option.value;
                if (!value) return;
                const name = displayLanguageName(value);
                if (!name) return;
                const original = option.dataset.originalLabel || option.textContent || '';
                option.dataset.originalLabel = original;
                const suffix = /\(Experimental\)/i.test(original) ? ` (${disabledSuffix})` : '';
                const translated = `${titleCaseLanguageName(name)}${suffix}`;
                option.textContent = translated;
                option.dataset.searchLabel = translated;
            });
        });
    }

    function translateSelectOptions(root = document) {
        root.querySelectorAll('select option').forEach((option) => {
            if (option.closest('[data-ui-locale-switcher]') || option.dataset.originalLabel) return;
            const original = option.dataset.originalTextLabel || option.textContent || '';
            option.dataset.originalTextLabel = original;
            const translated = text(original);
            option.textContent = translated;
            option.dataset.searchLabel = translated;
        });
    }

    function shouldSkip(element) {
        return Boolean(element.closest(
            '.conversation-turn, .live-transcript-text, .live-translation-text, script, style, code, pre'
        ));
    }

    function translateStaticText(root = document.body) {
        if (!root) return;
        translateLanguageOptions(root);
        translateSelectOptions(root);
        root.querySelectorAll('*').forEach((element) => {
            if (!shouldSkip(element)) translateAttributes(element);
        });
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
                const parent = node.parentElement;
                if (!parent || shouldSkip(parent)) return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            }
        });
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(translateTextNode);
    }

    function setLocaleCookie(locale) {
        const encoded = encodeURIComponent(locale);
        const secure = window.location.protocol === 'https:' ? '; Secure' : '';
        document.cookie = `polytalk_ui_locale=${encoded}; Max-Age=31536000; Path=/; SameSite=Lax${secure}`;
    }

    function reloadWithLocale(locale) {
        const url = new URL(window.location.href);
        url.searchParams.set('ui_locale', locale);
        window.location.assign(url.toString());
    }

    function initLocaleSwitchers() {
        document.querySelectorAll('[data-ui-locale-switcher]').forEach((select) => {
            select.addEventListener('change', () => {
                const locale = select.value;
                if (!locale || locale === (config.locale || 'en')) return;
                select.disabled = true;
                setLocaleCookie(locale);
                reloadWithLocale(locale);
            });
        });
    }

    window.PolyTalkI18n = {
        locale: config.locale || 'en',
        messages,
        t,
        text,
        format,
        translateStaticText,
        translateLanguageOptions,
        translateSelectOptions,
        initLocaleSwitchers,
        displayLanguageName
    };

    document.addEventListener('DOMContentLoaded', () => {
        translateStaticText();
        initLocaleSwitchers();
    });
}());
