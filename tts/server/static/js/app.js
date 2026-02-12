/**
 * Ekodi Voice Platform – Main Application
 *
 * Features:
 *   - Text-to-speech synthesis via /tts API
 *   - Audio waveform visualization
 *   - Playback history with replay
 *   - Download audio as WAV
 *   - Dark/light theme
 *   - i18n (Bambara, French, English)
 */

(function () {
  'use strict';

  // ── State ─────────────────────────────────────────────────
  const state = {
    isLoading: false,
    isPlaying: false,
    currentAudio: null,
    currentBlob: null,
    history: [],
    theme: localStorage.getItem('ekodi-theme') || 'light',
  };

  // ── DOM References ────────────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  let els = {};

  function cacheDom() {
    els = {
      textInput: $('#text-input'),
      charCount: $('#char-count'),
      btnSpeak: $('#btn-speak'),
      btnSpeakText: $('#btn-speak-text'),
      btnDownload: $('#btn-download'),
      btnClear: $('#btn-clear'),
      statusDot: $('#status-dot'),
      statusText: $('#status-text'),
      playerSection: $('#player-section'),
      waveformCanvas: $('#waveform-canvas'),
      playerDuration: $('#player-duration'),
      playerSize: $('#player-size'),
      historyList: $('#history-list'),
      historyEmpty: $('#history-empty'),
      toastContainer: $('#toast-container'),
    };
  }

  // ── Theme ─────────────────────────────────────────────────
  function setTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ekodi-theme', theme);

    $$('.theme-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === theme);
    });
  }

  // ── Language buttons ──────────────────────────────────────
  function updateLangButtons() {
    $$('.lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.lang === window.i18n.locale);
    });
  }

  // ── Status ────────────────────────────────────────────────
  function setStatus(statusKey, dotClass = '') {
    els.statusDot.className = 'status-dot ' + dotClass;
    els.statusText.textContent = window.i18n.t(statusKey);
  }

  // ── Toast ─────────────────────────────────────────────────
  function showToast(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    els.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // ── Character count ───────────────────────────────────────
  function updateCharCount() {
    const len = els.textInput.value.length;
    els.charCount.textContent = `${len} ${window.i18n.t('chars')}`;
  }

  // ── Waveform Drawing ──────────────────────────────────────
  function drawWaveform(audioBuffer) {
    const canvas = els.waveformCanvas;
    const ctx = canvas.getContext('2d');

    // High-DPI
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const data = audioBuffer.getChannelData(0);
    const step = Math.ceil(data.length / width);
    const midY = height / 2;

    ctx.clearRect(0, 0, width, height);

    // Gradient
    const style = getComputedStyle(document.documentElement);
    const primary = style.getPropertyValue('--brand-primary').trim() || '#6C5CE7';
    const accent = style.getPropertyValue('--brand-accent').trim() || '#00CEC9';

    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, primary);
    gradient.addColorStop(1, accent);

    ctx.fillStyle = gradient;

    for (let i = 0; i < width; i++) {
      let min = 1.0, max = -1.0;
      for (let j = 0; j < step; j++) {
        const val = data[i * step + j] || 0;
        if (val < min) min = val;
        if (val > max) max = val;
      }
      const barHeight = Math.max(2, (max - min) * midY * 0.9);
      const y = midY - barHeight / 2;
      ctx.fillRect(i, y, 1, barHeight);
    }
  }

  // ── Synthesize ────────────────────────────────────────────
  async function synthesize() {
    const text = els.textInput.value.trim();
    if (!text) {
      showToast(window.i18n.t('error_empty'), 'error');
      return;
    }

    if (state.isPlaying && state.currentAudio) {
      stopPlayback();
      return;
    }

    state.isLoading = true;
    updateSpeakButton();
    setStatus('status_loading', 'loading');

    try {
      const resp = await fetch('/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, speaker: 'ekodi' }),
      });

      if (!resp.ok) {
        throw new Error(`Server error: ${resp.status}`);
      }

      const blob = await resp.blob();
      state.currentBlob = blob;

      // Decode audio for waveform
      const arrayBuffer = await blob.arrayBuffer();
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer.slice(0));

      // Show player
      els.playerSection.classList.add('visible');
      drawWaveform(audioBuffer);

      const duration = audioBuffer.duration.toFixed(2);
      const sizeKb = (blob.size / 1024).toFixed(1);
      els.playerDuration.textContent = `${duration} ${window.i18n.t('seconds')}`;
      els.playerSize.textContent = `${sizeKb} KB`;

      // Play audio
      const audioUrl = URL.createObjectURL(blob);
      if (state.currentAudio) {
        state.currentAudio.pause();
        URL.revokeObjectURL(state.currentAudio.src);
      }
      state.currentAudio = new Audio(audioUrl);
      state.currentAudio.onended = () => {
        state.isPlaying = false;
        updateSpeakButton();
        setStatus('status_ready', '');
      };
      state.currentAudio.play();
      state.isPlaying = true;
      setStatus('status_speaking', 'speaking');

      // Add to history
      addToHistory(text, blob, duration);

      // Enable download
      els.btnDownload.disabled = false;

    } catch (e) {
      console.error('Synthesis error:', e);
      showToast(window.i18n.t('error_network'), 'error');
      setStatus('status_error', 'error');
    } finally {
      state.isLoading = false;
      updateSpeakButton();
    }
  }

  function stopPlayback() {
    if (state.currentAudio) {
      state.currentAudio.pause();
      state.currentAudio.currentTime = 0;
    }
    state.isPlaying = false;
    updateSpeakButton();
    setStatus('status_ready', '');
  }

  function updateSpeakButton() {
    if (state.isLoading) {
      els.btnSpeakText.innerHTML = '<span class="spinner"></span>';
      els.btnSpeak.disabled = true;
    } else if (state.isPlaying) {
      els.btnSpeakText.innerHTML = `<span class="sound-wave"><span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span></span> ${window.i18n.t('btn_stop')}`;
      els.btnSpeak.disabled = false;
      els.btnSpeak.classList.add('speaking');
    } else {
      els.btnSpeakText.textContent = window.i18n.t('btn_speak');
      els.btnSpeak.disabled = false;
      els.btnSpeak.classList.remove('speaking');
    }
  }

  // ── Download ──────────────────────────────────────────────
  function downloadAudio() {
    if (!state.currentBlob) return;
    const url = URL.createObjectURL(state.currentBlob);
    const a = document.createElement('a');
    a.href = url;
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-');
    a.download = `ekodi-bambara-${timestamp}.wav`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Download started', 'success');
  }

  // ── Clear ─────────────────────────────────────────────────
  function clearInput() {
    els.textInput.value = '';
    updateCharCount();
    stopPlayback();
    els.playerSection.classList.remove('visible');
    state.currentBlob = null;
    els.btnDownload.disabled = true;
    els.textInput.focus();
  }

  // ── History ───────────────────────────────────────────────
  function addToHistory(text, blob, duration) {
    state.history.unshift({ text, blob, duration, time: new Date() });
    if (state.history.length > 20) state.history.pop();
    renderHistory();
  }

  function renderHistory() {
    if (state.history.length === 0) {
      els.historyEmpty.style.display = 'block';
      els.historyList.innerHTML = '';
      return;
    }

    els.historyEmpty.style.display = 'none';
    els.historyList.innerHTML = state.history.map((item, idx) => `
      <div class="history-item" data-idx="${idx}">
        <button class="history-play-btn" data-idx="${idx}" title="Play">&#9654;</button>
        <span class="history-text">${escapeHtml(item.text)}</span>
        <span class="history-meta">${item.duration}s</span>
      </div>
    `).join('');

    // Re-attach click handlers
    els.historyList.querySelectorAll('.history-item').forEach(item => {
      item.addEventListener('click', () => {
        const idx = parseInt(item.dataset.idx);
        playHistoryItem(idx);
      });
    });
  }

  function playHistoryItem(idx) {
    const item = state.history[idx];
    if (!item) return;

    stopPlayback();
    const url = URL.createObjectURL(item.blob);
    state.currentAudio = new Audio(url);
    state.currentAudio.onended = () => {
      state.isPlaying = false;
      updateSpeakButton();
      setStatus('status_ready', '');
    };
    state.currentAudio.play();
    state.isPlaying = true;
    state.currentBlob = item.blob;
    els.btnDownload.disabled = false;
    setStatus('status_speaking', 'speaking');
    updateSpeakButton();
  }

  // ── Helpers ───────────────────────────────────────────────
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Keyboard shortcuts ────────────────────────────────────
  function handleKeyDown(e) {
    // Ctrl+Enter = Speak
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      synthesize();
    }
    // Escape = Stop
    if (e.key === 'Escape' && state.isPlaying) {
      stopPlayback();
    }
  }

  // ── Init ──────────────────────────────────────────────────
  async function init() {
    cacheDom();

    // Theme
    setTheme(state.theme);

    // i18n
    await window.i18n.init();
    updateLangButtons();
    updateCharCount();
    setStatus('status_ready', '');
    updateSpeakButton();

    // Event listeners
    els.textInput.addEventListener('input', updateCharCount);
    els.btnSpeak.addEventListener('click', synthesize);
    els.btnDownload.addEventListener('click', downloadAudio);
    els.btnClear.addEventListener('click', clearInput);
    document.addEventListener('keydown', handleKeyDown);

    // Language buttons
    $$('.lang-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        window.i18n.setLocale(btn.dataset.lang);
        updateLangButtons();
        updateCharCount();
        setStatus('status_ready', '');
        updateSpeakButton();
      });
    });

    // Theme buttons
    $$('.theme-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        setTheme(btn.dataset.theme);
      });
    });

    // i18n change listener
    window.i18n.onChange(() => {
      updateCharCount();
      renderHistory();
    });

    // Render empty history
    renderHistory();

    console.log('Ekodi Voice Platform initialized');
  }

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
