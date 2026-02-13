/**
 * Ekodi Voice AI Platform
 *
 * Pipeline:
 *   French  → Whisper → GPT(fr) → translate → Bambara TTS
 *   Bambara → MMS-ASR → translate → GPT(fr) → translate → Bambara TTS
 */

(function () {
  'use strict';

  const state = {
    mode: 'chat',
    inputLang: 'fr',     // 'fr' or 'bm'
    isLoading: false,
    isPlaying: false,
    isRecording: false,
    currentAudio: null,
    currentBlob: null,
    history: [],
    theme: localStorage.getItem('ekodi-theme') || 'light',
    sessionId: 'session-' + Date.now(),
  };

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
      historySection: $('#history-section'),
      toastContainer: $('#toast-container'),
      modeText: $('#mode-text'),
      modeChat: $('#mode-chat'),
      sectionText: $('#section-text'),
      sectionChat: $('#section-chat'),
      chatContainer: $('#chat-container'),
      chatMessages: $('#chat-messages'),
      chatWelcome: $('#chat-welcome'),
      btnChatMic: $('#btn-chat-mic'),
      chatMicStatus: $('#chat-mic-status'),
      chatTextInput: $('#chat-text-input'),
      btnChatSend: $('#btn-chat-send'),
      langFr: $('#lang-fr'),
      langBm: $('#lang-bm'),
    };
  }

  // ── Theme ─────────────────────────────────────────────────
  function setTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ekodi-theme', theme);
    $$('.theme-btn').forEach(b => b.classList.toggle('active', b.dataset.theme === theme));
  }

  function updateLangButtons() {
    $$('.lang-btn').forEach(b => b.classList.toggle('active', b.dataset.lang === window.i18n.locale));
  }

  // ── Input Language Toggle ─────────────────────────────────
  function setInputLang(lang) {
    state.inputLang = lang;
    if (els.langFr) els.langFr.classList.toggle('active', lang === 'fr');
    if (els.langBm) els.langBm.classList.toggle('active', lang === 'bm');
  }

  // ── Mode Switching ────────────────────────────────────────
  function setMode(mode) {
    state.mode = mode;
    els.modeText.classList.toggle('active', mode === 'text');
    els.modeChat.classList.toggle('active', mode === 'chat');
    els.sectionText.style.display = mode === 'text' ? '' : 'none';
    els.sectionChat.style.display = mode === 'chat' ? '' : 'none';
    if (els.historySection) els.historySection.style.display = mode === 'text' ? '' : 'none';
    if (mode === 'text' && els.textInput) els.textInput.focus();
  }

  function setStatus(key, cls) {
    if (els.statusDot) els.statusDot.className = 'status-dot ' + (cls || '');
    if (els.statusText) els.statusText.textContent = window.i18n.t(key);
  }

  function showToast(msg, type) {
    const t = document.createElement('div');
    t.className = `toast ${type || 'error'}`;
    t.textContent = msg;
    els.toastContainer.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3500);
  }

  function updateCharCount() {
    if (els.textInput) {
      els.charCount.textContent = `${els.textInput.value.length} ${window.i18n.t('chars')}`;
    }
  }

  // ── Waveform ──────────────────────────────────────────────
  function drawWaveform(buf) {
    const c = els.waveformCanvas; if (!c) return;
    const ctx = c.getContext('2d');
    const dpr = devicePixelRatio || 1;
    const r = c.getBoundingClientRect();
    c.width = r.width * dpr; c.height = r.height * dpr;
    ctx.scale(dpr, dpr);
    const w = r.width, h = r.height, d = buf.getChannelData(0);
    const step = Math.ceil(d.length / w), mid = h / 2;
    ctx.clearRect(0, 0, w, h);
    const s = getComputedStyle(document.documentElement);
    const g = ctx.createLinearGradient(0, 0, w, 0);
    g.addColorStop(0, s.getPropertyValue('--brand-primary').trim() || '#6C5CE7');
    g.addColorStop(1, s.getPropertyValue('--brand-accent').trim() || '#00CEC9');
    ctx.fillStyle = g;
    for (let i = 0; i < w; i++) {
      let mn = 1, mx = -1;
      for (let j = 0; j < step; j++) { const v = d[i*step+j]||0; if(v<mn)mn=v; if(v>mx)mx=v; }
      const bh = Math.max(2, (mx-mn)*mid*0.9);
      ctx.fillRect(i, mid-bh/2, 1, bh);
    }
  }

  // ══════════════════════════════════════════════════════════
  //   TEXT MODE
  // ══════════════════════════════════════════════════════════
  async function synthesize() {
    const text = els.textInput.value.trim();
    if (!text) { showToast(window.i18n.t('error_empty')); return; }
    if (state.isPlaying && state.currentAudio) { stopPlayback(); return; }
    state.isLoading = true; updateSpeakButton(); setStatus('status_loading', 'loading');
    try {
      const r = await fetch('/tts', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text,speaker:'ekodi'}) });
      if (!r.ok) throw new Error(r.status);
      const blob = await r.blob(); state.currentBlob = blob;
      const ab = await blob.arrayBuffer();
      const ac = new (AudioContext||webkitAudioContext)();
      const buf = await ac.decodeAudioData(ab.slice(0));
      els.playerSection.classList.add('visible'); drawWaveform(buf);
      els.playerDuration.textContent = `${buf.duration.toFixed(2)} ${window.i18n.t('seconds')}`;
      els.playerSize.textContent = `${(blob.size/1024).toFixed(1)} KB`;
      const url = URL.createObjectURL(blob);
      if (state.currentAudio) { state.currentAudio.pause(); URL.revokeObjectURL(state.currentAudio.src); }
      state.currentAudio = new Audio(url);
      state.currentAudio.onended = () => { state.isPlaying=false; updateSpeakButton(); setStatus('status_ready',''); };
      state.currentAudio.play(); state.isPlaying = true; setStatus('status_speaking','speaking');
      addToHistory(text, blob, buf.duration.toFixed(2)); els.btnDownload.disabled = false;
    } catch(e) { showToast(window.i18n.t('error_network')); setStatus('status_error','error'); }
    finally { state.isLoading=false; updateSpeakButton(); }
  }

  function stopPlayback() {
    if (state.currentAudio) { state.currentAudio.pause(); state.currentAudio.currentTime=0; }
    state.isPlaying=false; updateSpeakButton(); setStatus('status_ready','');
  }

  function updateSpeakButton() {
    if (!els.btnSpeakText) return;
    if (state.isLoading) { els.btnSpeakText.innerHTML='<span class="spinner"></span>'; els.btnSpeak.disabled=true; }
    else if (state.isPlaying) { els.btnSpeakText.innerHTML=`<span class="sound-wave"><span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span></span> ${window.i18n.t('btn_stop')}`; els.btnSpeak.disabled=false; els.btnSpeak.classList.add('speaking'); }
    else { els.btnSpeakText.textContent=window.i18n.t('btn_speak'); els.btnSpeak.disabled=false; els.btnSpeak.classList.remove('speaking'); }
  }

  function downloadAudio() {
    if (!state.currentBlob) return;
    const a=document.createElement('a'); a.href=URL.createObjectURL(state.currentBlob);
    a.download=`ekodi-${new Date().toISOString().slice(0,19).replace(/[T:]/g,'-')}.wav`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  function clearInput() {
    els.textInput.value=''; updateCharCount(); stopPlayback();
    els.playerSection.classList.remove('visible'); state.currentBlob=null; els.btnDownload.disabled=true;
  }

  function addToHistory(text, blob, dur) {
    state.history.unshift({text,blob,duration:dur,time:new Date()});
    if(state.history.length>20) state.history.pop();
    renderHistory();
  }

  function renderHistory() {
    if(!els.historyList) return;
    if(!state.history.length) { els.historyEmpty.style.display='block'; els.historyList.innerHTML=''; return; }
    els.historyEmpty.style.display='none';
    els.historyList.innerHTML=state.history.map((h,i)=>`<div class="history-item" data-idx="${i}"><button class="history-play-btn">&#9654;</button><span class="history-text">${esc(h.text)}</span><span class="history-meta">${h.duration}s</span></div>`).join('');
    els.historyList.querySelectorAll('.history-item').forEach(el=>el.addEventListener('click',()=>playHistory(+el.dataset.idx)));
  }

  function playHistory(i) {
    const h=state.history[i]; if(!h)return; stopPlayback();
    state.currentAudio=new Audio(URL.createObjectURL(h.blob));
    state.currentAudio.onended=()=>{state.isPlaying=false;updateSpeakButton();setStatus('status_ready','');};
    state.currentAudio.play(); state.isPlaying=true;
  }

  function esc(s) { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

  // ══════════════════════════════════════════════════════════
  //   CHAT MODE – Interactive AI
  // ══════════════════════════════════════════════════════════

  let mediaRecorder = null, audioChunks = [];

  function addMsg(role, textMain, textSub) {
    els.chatWelcome.style.display = 'none';
    const row = document.createElement('div');
    row.className = `chat-msg chat-msg-${role}`;

    const av = document.createElement('div');
    av.className = `chat-avatar chat-avatar-${role}`;
    av.textContent = role === 'user' ? '🗣' : '🤖';

    const bub = document.createElement('div');
    bub.className = `chat-bubble chat-bubble-${role}`;

    // Main text
    const main = document.createElement('div');
    main.className = 'chat-text-main';
    main.textContent = textMain;
    bub.appendChild(main);

    // Secondary text (translation)
    if (textSub) {
      const sub = document.createElement('div');
      sub.className = 'chat-text-sub';
      sub.textContent = textSub;
      bub.appendChild(sub);
    }

    if (role === 'user') { row.appendChild(bub); row.appendChild(av); }
    else { row.appendChild(av); row.appendChild(bub); }

    els.chatMessages.appendChild(row);
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
    return bub;
  }

  function addTyping() {
    els.chatWelcome.style.display = 'none';
    const row = document.createElement('div');
    row.className = 'chat-msg chat-msg-ai'; row.id = 'chat-typing';
    const av = document.createElement('div'); av.className='chat-avatar chat-avatar-ai'; av.textContent='🤖';
    const bub = document.createElement('div'); bub.className='chat-bubble chat-bubble-ai typing';
    bub.innerHTML='<span class="typing-dots"><span></span><span></span><span></span></span>';
    row.appendChild(av); row.appendChild(bub);
    els.chatMessages.appendChild(row);
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  }

  function removeTyping() { const el=document.getElementById('chat-typing'); if(el)el.remove(); }

  // ── Send text message ─────────────────────────────────────
  async function sendText(text) {
    if (!text.trim() || state.isLoading) return;
    state.isLoading = true;
    addMsg('user', text, null);
    els.chatTextInput.value = '';
    addTyping();
    els.chatMicStatus.textContent = window.i18n.t('chat_thinking');

    try {
      const r = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text, input_lang: state.inputLang, session_id: state.sessionId
        }),
      });
      if (!r.ok) { const e = await r.json().catch(()=>({})); throw new Error(e.detail || r.status); }
      const d = await r.json();
      removeTyping();

      // Show AI response: Bambara (main) + French (subtitle)
      const bub = addMsg('ai', d.ai_text_bm, d.ai_text_fr);

      if (d.audio_base64) {
        playB64(d.audio_base64);
        addReplayBtn(bub, d.audio_base64);
      }
      els.chatMicStatus.textContent = window.i18n.t('mic_tap');
    } catch(e) {
      removeTyping();
      showToast(e.message || window.i18n.t('error_network'));
      els.chatMicStatus.textContent = window.i18n.t('mic_tap');
    } finally { state.isLoading = false; }
  }

  // ── Send voice message ────────────────────────────────────
  async function sendVoice(blob) {
    state.isLoading = true;
    addTyping();
    els.chatMicStatus.textContent = window.i18n.t('chat_processing');

    try {
      const fd = new FormData();
      const ext = blob.type.includes('webm')?'webm': blob.type.includes('mp4')?'mp4':'wav';
      fd.append('audio', blob, `rec.${ext}`);
      fd.append('input_lang', state.inputLang);
      fd.append('session_id', state.sessionId);

      const r = await fetch('/voice-chat', { method:'POST', body:fd });
      if (!r.ok) { const e=await r.json().catch(()=>({})); throw new Error(e.detail||r.status); }
      const d = await r.json();
      removeTyping();

      // User message
      if (d.user_text) {
        const userSub = d.input_lang === 'bm' ? d.user_text_fr : null;
        addMsg('user', d.user_text, userSub);
      }

      // AI response: Bambara main + French subtitle
      if (d.ai_text_bm) {
        const bub = addMsg('ai', d.ai_text_bm, d.ai_text_fr);
        if (d.audio_base64) {
          playB64(d.audio_base64);
          addReplayBtn(bub, d.audio_base64);
        }
      } else if (!d.user_text) {
        showToast(window.i18n.t('mic_no_speech'));
      }
      els.chatMicStatus.textContent = window.i18n.t('mic_tap');
    } catch(e) {
      removeTyping();
      showToast(e.message || window.i18n.t('error_network'));
      els.chatMicStatus.textContent = window.i18n.t('mic_tap');
    } finally { state.isLoading = false; }
  }

  function addReplayBtn(bub, b64) {
    const btn = document.createElement('button');
    btn.className = 'chat-replay-btn'; btn.innerHTML = '🔊'; btn.title = 'Replay';
    btn.addEventListener('click', e => { e.stopPropagation(); playB64(b64); });
    bub.appendChild(btn);
  }

  function playB64(b64) {
    if (state.currentAudio) { state.currentAudio.pause(); URL.revokeObjectURL(state.currentAudio.src); }
    const bytes = Uint8Array.from(atob(b64), c=>c.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bytes], {type:'audio/wav'}));
    state.currentAudio = new Audio(url);
    state.currentAudio.play();
    state.isPlaying = true;
    state.currentAudio.onended = () => { state.isPlaying = false; };
  }

  // ── Mic Recording ─────────────────────────────────────────
  function toggleRec() { state.isRecording ? stopRec() : startRec(); }

  async function startRec() {
    if (state.isLoading) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio:true});
      mediaRecorder = new MediaRecorder(stream, {mimeType:bestMime()});
      audioChunks = [];
      mediaRecorder.ondataavailable = e => { if(e.data.size>0) audioChunks.push(e.data); };
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(t=>t.stop());
        if (audioChunks.length) sendVoice(new Blob(audioChunks, {type:mediaRecorder.mimeType}));
      };
      mediaRecorder.start();
      state.isRecording = true;
      els.btnChatMic.classList.add('recording');
      els.chatMicStatus.textContent = window.i18n.t('mic_listening');
    } catch(e) {
      showToast(e.name==='NotAllowedError'? window.i18n.t('mic_denied') : window.i18n.t('mic_not_supported'));
    }
  }

  function stopRec() {
    if (mediaRecorder && state.isRecording) { state.isRecording=false; mediaRecorder.stop(); }
    if (els.btnChatMic) els.btnChatMic.classList.remove('recording');
  }

  function bestMime() {
    for (const t of ['audio/webm;codecs=opus','audio/webm','audio/mp4','audio/ogg'])
      if (MediaRecorder.isTypeSupported(t)) return t;
    return '';
  }

  // ── Keyboard ──────────────────────────────────────────────
  function onKey(e) {
    if (e.ctrlKey && e.key==='Enter' && state.mode==='text') { e.preventDefault(); synthesize(); }
    if (e.key==='Escape') { if(state.isRecording)stopRec(); else if(state.isPlaying)stopPlayback(); }
    if (e.key==='Enter' && !e.shiftKey && document.activeElement===els.chatTextInput) {
      e.preventDefault(); sendText(els.chatTextInput.value);
    }
  }

  // ── Init ──────────────────────────────────────────────────
  async function init() {
    cacheDom();
    setTheme(state.theme);
    await window.i18n.init();
    updateLangButtons(); updateCharCount(); setStatus('status_ready',''); updateSpeakButton();

    els.modeText.addEventListener('click', ()=>setMode('text'));
    els.modeChat.addEventListener('click', ()=>setMode('chat'));

    if(els.textInput) els.textInput.addEventListener('input', updateCharCount);
    if(els.btnSpeak) els.btnSpeak.addEventListener('click', synthesize);
    if(els.btnDownload) els.btnDownload.addEventListener('click', downloadAudio);
    if(els.btnClear) els.btnClear.addEventListener('click', clearInput);

    els.btnChatMic.addEventListener('click', toggleRec);
    els.btnChatSend.addEventListener('click', ()=>sendText(els.chatTextInput.value));

    // Input language toggle
    if(els.langFr) els.langFr.addEventListener('click', ()=>setInputLang('fr'));
    if(els.langBm) els.langBm.addEventListener('click', ()=>setInputLang('bm'));

    document.addEventListener('keydown', onKey);
    $$('.lang-btn').forEach(b=>b.addEventListener('click',()=>{
      window.i18n.setLocale(b.dataset.lang); updateLangButtons(); updateCharCount(); setStatus('status_ready',''); updateSpeakButton();
    }));
    $$('.theme-btn').forEach(b=>b.addEventListener('click',()=>setTheme(b.dataset.theme)));
    window.i18n.onChange(()=>{ updateCharCount(); renderHistory(); });
    renderHistory();
    setMode('chat');
    console.log('Ekodi Voice AI ready');
  }

  document.readyState==='loading' ? document.addEventListener('DOMContentLoaded',init) : init();
})();
