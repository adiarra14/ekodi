import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { chatAPI, feedbackAPI, authAPI } from '../services/api';
import {
  Plus, MessageSquare, Trash2, Send, Mic, MicOff, Volume2,
  ThumbsUp, ThumbsDown, LogOut, ChevronLeft, Pencil, Check, X,
  Settings, Mail, RefreshCw, Shield, Key, User as UserIcon, ChevronUp,
} from 'lucide-react';
import LanguageSwitcher from '../components/ui/LanguageSwitcher';
import AudioWaveform from '../components/AudioWaveform';
import './Chat.css';

export default function Chat() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // If not logged in, redirect
  useEffect(() => {
    if (!user) navigate('/login');
  }, [user, navigate]);

  // State
  const [conversations, setConversations] = useState([]);
  const [activeConvo, setActiveConvo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [inputLang, setInputLang] = useState('fr');
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [recording, setRecording] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  // Audio waveform state
  const [playingMsgId, setPlayingMsgId] = useState(null);
  const [playAnalyser, setPlayAnalyser] = useState(null);
  const [recAnalyser, setRecAnalyser] = useState(null);
  const [recSeconds, setRecSeconds] = useState(0); // recording duration counter

  // Feedback state: { messageId: rating (1 or -1) }
  const [feedbackMap, setFeedbackMap] = useState({});

  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const audioCtxRef = useRef(null);
  const recAudioCtxRef = useRef(null);
  const vadRef = useRef(null); // Voice Activity Detection interval

  // Recording duration timer
  useEffect(() => {
    if (!recording) { setRecSeconds(0); return; }
    const t = setInterval(() => setRecSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [recording]);

  // Load conversations
  const loadConversations = useCallback(async () => {
    try {
      const data = await chatAPI.listConversations();
      setConversations(data);
    } catch {
      // Ignore
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load messages when active convo changes
  useEffect(() => {
    if (!activeConvo) {
      setMessages([]);
      return;
    }
    chatAPI.getConversation(activeConvo).then((data) => {
      setMessages(data.messages || []);
    }).catch(() => {});
  }, [activeConvo]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // New chat
  const newChat = () => {
    setActiveConvo(null);
    setMessages([]);
  };

  // Select conversation
  const selectConvo = (id) => {
    setActiveConvo(id);
    if (window.innerWidth < 768) setSidebarOpen(false);
  };

  // Delete conversation
  const deleteConvo = async (id) => {
    await chatAPI.deleteConversation(id);
    if (activeConvo === id) {
      setActiveConvo(null);
      setMessages([]);
    }
    loadConversations();
  };

  // Rename conversation
  const startRename = (id, currentTitle) => {
    setEditingId(id);
    setEditTitle(currentTitle);
  };

  const confirmRename = async () => {
    if (editingId && editTitle.trim()) {
      await chatAPI.renameConversation(editingId, editTitle.trim());
      loadConversations();
    }
    setEditingId(null);
  };

  // Send text message
  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput('');
    setLoading(true);

    // Optimistic user message
    const tempUserMsg = { id: 'temp-user', role: 'user', text_fr: inputLang === 'fr' ? text : null, text_bm: inputLang === 'bm' ? text : null };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const data = await chatAPI.sendText({
        text,
        input_lang: inputLang,
        conversation_id: activeConvo,
      });

      // If new conversation was created
      if (data.conversation_id && data.conversation_id !== activeConvo) {
        setActiveConvo(data.conversation_id);
        loadConversations();
      }

      // Replace temp + add AI message
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== 'temp-user');
        const userMsg = {
          id: 'user-' + Date.now(),
          role: 'user',
          text_fr: data.user_text_fr || text,
          text_bm: inputLang === 'bm' ? text : null,
        };
        const aiMsg = {
          id: data.message_id || 'ai-' + Date.now(),
          role: 'assistant',
          text_fr: data.ai_text_fr,
          text_bm: data.ai_text_bm,
          audio_base64: data.audio_base64,
        };
        return [...filtered, userMsg, aiMsg];
      });

      // Play audio with waveform
      if (data.audio_base64) playAudio(data.audio_base64, data.message_id || 'ai-' + Date.now());
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== 'temp-user'));
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Voice recording with live waveform + Voice Activity Detection (auto-stop on silence)
  const stopRecording = useCallback(() => {
    if (vadRef.current) { clearInterval(vadRef.current); vadRef.current = null; }
    mediaRecorderRef.current?.stop();
    setRecording(false);
    setRecAnalyser(null);
    if (recAudioCtxRef.current) {
      try { recAudioCtxRef.current.close(); } catch { /* ignore */ }
      recAudioCtxRef.current = null;
    }
  }, []);

  const toggleRecording = async () => {
    if (recording) {
      stopRecording();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4' });
      chunksRef.current = [];

      // Create analyser for live mic waveform + VAD
      const recCtx = new (window.AudioContext || window.webkitAudioContext)();
      recAudioCtxRef.current = recCtx;
      const micSource = recCtx.createMediaStreamSource(stream);
      const analyser = recCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.65;
      micSource.connect(analyser);
      setRecAnalyser(analyser);

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecAnalyser(null);
        if (vadRef.current) { clearInterval(vadRef.current); vadRef.current = null; }
        if (recAudioCtxRef.current) {
          try { recAudioCtxRef.current.close(); } catch { /* ignore */ }
          recAudioCtxRef.current = null;
        }
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        // Only send if we have meaningful audio (> 0.5s worth of data)
        if (blob.size > 5000) {
          await sendVoice(blob);
        }
      };

      recorder.start(250); // collect data every 250ms for responsiveness
      mediaRecorderRef.current = recorder;
      setRecording(true);

      // ── Voice Activity Detection (VAD) ──
      // Auto-stop when user is silent for ~1.8 seconds
      const VAD_SILENCE_THRESHOLD = 12;   // audio level below this = silence (0–255 scale)
      const VAD_SILENCE_DURATION = 1800;  // ms of silence before auto-stop
      const VAD_MIN_SPEECH_TIME = 600;    // minimum recording time before VAD kicks in
      const VAD_CHECK_INTERVAL = 100;     // check every 100ms
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      let silentSince = null;
      const startTime = Date.now();

      vadRef.current = setInterval(() => {
        // Don't auto-stop too early (let user start speaking)
        if (Date.now() - startTime < VAD_MIN_SPEECH_TIME) return;

        analyser.getByteFrequencyData(dataArray);
        // Compute average volume level
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
        const avgLevel = sum / dataArray.length;

        if (avgLevel < VAD_SILENCE_THRESHOLD) {
          if (!silentSince) silentSince = Date.now();
          if (Date.now() - silentSince >= VAD_SILENCE_DURATION) {
            // User has been silent long enough → auto-stop
            stopRecording();
          }
        } else {
          silentSince = null; // speaking, reset silence timer
        }
      }, VAD_CHECK_INTERVAL);

    } catch {
      alert('Microphone access denied');
    }
  };

  const sendVoice = async (blob) => {
    setLoading(true);
    const tempMsg = { id: 'temp-voice', role: 'user', text_fr: t('chat.mic_processing') };
    setMessages((prev) => [...prev, tempMsg]);

    try {
      const fd = new FormData();
      const ext = blob.type.includes('webm') ? 'webm' : 'mp4';
      fd.append('audio', blob, `rec.${ext}`);
      fd.append('input_lang', inputLang);
      if (activeConvo) fd.append('conversation_id', activeConvo);

      const data = await chatAPI.sendVoice(fd);

      if (data.conversation_id && data.conversation_id !== activeConvo) {
        setActiveConvo(data.conversation_id);
        loadConversations();
      }

      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== 'temp-voice');
        const msgs = [];
        if (data.user_text) {
          msgs.push({
            id: 'user-' + Date.now(),
            role: 'user',
            text_fr: data.user_text_fr,
            text_bm: data.input_lang === 'bm' ? data.user_text : null,
          });
        }
        if (data.ai_text_bm) {
          msgs.push({
            id: data.message_id || 'ai-' + Date.now(),
            role: 'assistant',
            text_fr: data.ai_text_fr,
            text_bm: data.ai_text_bm,
            audio_base64: data.audio_base64,
          });
        }
        return [...filtered, ...msgs];
      });

      if (data.audio_base64) playAudio(data.audio_base64, data.message_id || 'ai-' + Date.now());
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== 'temp-voice'));
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Audio playback with waveform visualiser
  const playAudio = (b64, msgId) => {
    // Stop any previous playback context
    if (audioCtxRef.current) {
      try { audioCtxRef.current.close(); } catch { /* ignore */ }
    }

    const audio = new Audio(`data:audio/wav;base64,${b64}`);
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    audioCtxRef.current = ctx;

    const source = ctx.createMediaElementSource(audio);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.7;

    source.connect(analyser);
    analyser.connect(ctx.destination);

    setPlayAnalyser(analyser);
    if (msgId) setPlayingMsgId(msgId);

    audio.addEventListener('ended', () => {
      setPlayingMsgId(null);
      setPlayAnalyser(null);
      try { ctx.close(); } catch { /* ignore */ }
    });

    audio.play().catch(() => {
      setPlayingMsgId(null);
      setPlayAnalyser(null);
    });
  };

  // Feedback with visual confirmation
  const sendFeedback = async (messageId, rating) => {
    try {
      await feedbackAPI.submit({ message_id: messageId, rating });
      setFeedbackMap((prev) => ({ ...prev, [messageId]: rating }));
    } catch {
      // Ignore
    }
  };

  // Key handler
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!user) return null;

  // ── Email verification gate ──
  if (!user.email_verified && !user.is_staff) {
    return (
      <div className="chat-page">
        <div className="verify-gate">
          <Mail size={48} className="verify-gate-icon" />
          <h2>{t('auth.verify_required_title') || 'Verify Your Email'}</h2>
          <p>{t('auth.verify_required_desc') || 'Please verify your email address to access the chat. Check your inbox for the verification link.'}</p>
          <p className="verify-gate-email">{user.email}</p>
          <div className="verify-gate-actions">
            <button
              className="verify-gate-resend"
              onClick={async () => {
                try {
                  await authAPI.resendVerification();
                  alert(t('auth.verify_resent') || 'Verification email sent! Check your inbox.');
                } catch {
                  alert(t('auth.verify_resend_error') || 'Failed to send verification email.');
                }
              }}
            >
              <RefreshCw size={16} /> {t('auth.resend_verification') || 'Resend Verification Email'}
            </button>
            <button className="verify-gate-logout" onClick={() => { logout(); navigate('/'); }}>
              <LogOut size={16} /> {t('nav.logout') || 'Logout'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-page">
      {/* ── Sidebar ── */}
      <aside className={`chat-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <button className="sidebar-new" onClick={newChat}>
            <Plus size={18} /> {t('chat.new_chat')}
          </button>
        </div>

        <div className="sidebar-convos">
          <p className="sidebar-label">{t('chat.conversations')}</p>
          {conversations.length === 0 && (
            <p className="sidebar-empty">{t('chat.no_conversations')}</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`sidebar-convo ${activeConvo === c.id ? 'active' : ''}`}
              onClick={() => selectConvo(c.id)}
            >
              <MessageSquare size={16} />
              {editingId === c.id ? (
                <div className="convo-edit" onClick={(e) => e.stopPropagation()}>
                  <input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && confirmRename()}
                    autoFocus
                  />
                  <button onClick={confirmRename}><Check size={14} /></button>
                  <button onClick={() => setEditingId(null)}><X size={14} /></button>
                </div>
              ) : (
                <>
                  <span className="convo-title">{c.title}</span>
                  <div className="convo-actions" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => startRename(c.id, c.title)} title="Rename"><Pencil size={13} /></button>
                    <button onClick={() => deleteConvo(c.id)} title="Delete"><Trash2 size={13} /></button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <LanguageSwitcher />

          {/* ── User profile menu ── */}
          <div className="sidebar-profile">
            {profileMenuOpen && (
              <div className="profile-menu">
                <button onClick={() => { navigate('/settings'); setProfileMenuOpen(false); }}>
                  <Settings size={15} /> {t('nav.settings') || 'Settings'}
                </button>
                <button onClick={() => { navigate('/api-keys'); setProfileMenuOpen(false); }}>
                  <Key size={15} /> {t('nav.api') || 'API Keys'}
                </button>
                {['superadmin','admin','support','marketing','finance','moderator','developer'].includes(user.role) && (
                  <button onClick={() => { navigate('/admin'); setProfileMenuOpen(false); }}>
                    <Shield size={15} /> {t('nav.admin') || 'Admin'}
                  </button>
                )}
                <div className="profile-menu-divider" />
                <button className="profile-menu-logout" onClick={() => { logout(); navigate('/'); }}>
                  <LogOut size={15} /> {t('nav.logout') || 'Logout'}
                </button>
              </div>
            )}
            <button
              className="sidebar-user-btn"
              onClick={() => setProfileMenuOpen(!profileMenuOpen)}
            >
              <div className="sidebar-user-avatar">{user.name?.[0] || 'U'}</div>
              <div className="sidebar-user-info">
                <span className="sidebar-user-name">{user.name}</span>
                <span className="sidebar-user-email">{user.email}</span>
              </div>
              <ChevronUp size={16} className={`sidebar-user-chevron ${profileMenuOpen ? 'open' : ''}`} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="chat-main">
        <div className="chat-topbar">
          <button className="topbar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
            {sidebarOpen ? <ChevronLeft size={20} /> : <MessageSquare size={20} />}
          </button>
          <div className="topbar-info">
            <span className="topbar-title">
              {activeConvo
                ? conversations.find((c) => c.id === activeConvo)?.title || 'Chat'
                : t('chat.new_chat')}
            </span>
          </div>
          <div className="topbar-actions">
            <Settings size={18} />
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && !loading && (
            <div className="chat-welcome">
              <img src="/logo-ekodi-std.png" alt="Ekodi" className="welcome-logo" />
              <h2>{t('chat.welcome')}</h2>
              <p>{t('chat.welcome_hint')}</p>

              {/* ── Example prompts ── */}
              <div className="welcome-examples">
                <p className="welcome-examples-label">{t('chat.try_asking') || 'Try asking:'}</p>
                <div className="welcome-examples-grid">
                  {[
                    t('chat.example_1') || 'Parle-moi de la lune',
                    t('chat.example_2') || 'Je veux apprendre à bien cultiver le riz',
                    t('chat.example_3') || "Qu'est-ce qui se passe dans le monde ?",
                  ].map((ex, i) => (
                    <button
                      key={i}
                      className="welcome-example-btn"
                      onClick={() => { setInput(ex); }}
                    >
                      <MessageSquare size={14} />
                      <span>{ex}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* ── Feedback explanation ── */}
              <div className="welcome-feedback-info">
                <p className="welcome-feedback-title">{t('chat.feedback_title') || 'Help ekodi learn!'}</p>
                <div className="welcome-feedback-items">
                  <div className="welcome-fb-item">
                    <ThumbsUp size={16} className="welcome-fb-good" />
                    <span>{t('chat.feedback_good') || 'Good answer – helps ekodi improve'}</span>
                  </div>
                  <div className="welcome-fb-item">
                    <ThumbsDown size={16} className="welcome-fb-bad" />
                    <span>{t('chat.feedback_bad') || 'Bad answer – tells ekodi to do better'}</span>
                  </div>
                </div>
                <p className="welcome-feedback-hint">
                  {t('chat.feedback_hint') || 'Your feedback helps train the AI to better understand Bamanankan.'}
                </p>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`chat-msg ${msg.role}`}>
              <div className="msg-avatar">
                {msg.role === 'assistant' ? (
                  <img src="/logo-ekodi-actif.png" alt="Ekodi" />
                ) : (
                  <div className="user-avatar">{user.name?.[0] || 'U'}</div>
                )}
              </div>
              <div className="msg-content">
                <div className={`msg-bubble ${playingMsgId === msg.id ? 'speaking' : ''}`}>
                  {msg.text_bm && <p className="msg-text-main">{msg.text_bm}</p>}
                  {msg.text_fr && <p className="msg-text-sub">{msg.text_fr}</p>}
                  {/* Playback waveform inside bubble when this message is speaking */}
                  {playingMsgId === msg.id && playAnalyser && (
                    <AudioWaveform
                      analyserNode={playAnalyser}
                      active={true}
                      color="#ff7a2f"
                      height={28}
                      barWidth={2.5}
                      barGap={1.5}
                      className="msg-waveform"
                    />
                  )}
                </div>
                {msg.role === 'assistant' && msg.id && !msg.id.startsWith('temp') && (
                  <div className="msg-actions">
                    {msg.audio_base64 && (
                      <button
                        onClick={() => playAudio(msg.audio_base64, msg.id)}
                        title="Play"
                        className={playingMsgId === msg.id ? 'playing' : ''}
                      >
                        <Volume2 size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => sendFeedback(msg.id, 1)}
                      title="Good"
                      className={feedbackMap[msg.id] === 1 ? 'fb-active fb-good' : ''}
                    >
                      <ThumbsUp size={14} />
                    </button>
                    <button
                      onClick={() => sendFeedback(msg.id, -1)}
                      title="Bad"
                      className={feedbackMap[msg.id] === -1 ? 'fb-active fb-bad' : ''}
                    >
                      <ThumbsDown size={14} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="chat-msg assistant">
              <div className="msg-avatar">
                <img src="/logo-ekodi-innactif.png" alt="Ekodi thinking" />
              </div>
              <div className="msg-content">
                <div className="msg-bubble typing wave-loader">
                  <span className="wave-bar" />
                  <span className="wave-bar" />
                  <span className="wave-bar" />
                  <span className="wave-bar" />
                  <span className="wave-bar" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ── Input Area ── */}
        <div className="chat-input-area">
          <div className="input-lang-row">
            <span className="input-lang-label">{t('chat.speak_in')}</span>
            <div className="input-lang-toggle">
              <button
                className={`ilt-btn ${inputLang === 'fr' ? 'active' : ''}`}
                onClick={() => setInputLang('fr')}
              >
                {t('chat.french')}
              </button>
              <button
                className={`ilt-btn ${inputLang === 'bm' ? 'active' : ''}`}
                onClick={() => setInputLang('bm')}
              >
                {t('chat.bambara')}
              </button>
            </div>
          </div>

          <div className={`input-row ${recording ? 'input-row--recording' : ''}`}>
            <button
              className={`input-mic ${recording ? 'recording' : ''}`}
              onClick={toggleRecording}
              disabled={loading}
              title={recording ? t('chat.mic_recording') : t('chat.mic_tap')}
            >
              {recording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>

            {recording && recAnalyser ? (
              <div className="input-rec-wave">
                <span className="rec-timer">
                  <span className="rec-dot" />
                  {Math.floor(recSeconds / 60)}:{String(recSeconds % 60).padStart(2, '0')}
                </span>
                <AudioWaveform
                  analyserNode={recAnalyser}
                  active={recording}
                  color="#ef4444"
                  height={28}
                  barWidth={2.5}
                  barGap={1.5}
                />
                <span className="rec-hint">{t('chat.auto_stop_hint') || 'Auto-stops on silence'}</span>
              </div>
            ) : (
              <input
                type="text"
                className="input-text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('chat.type_message')}
                disabled={loading}
                maxLength={2000}
              />
            )}

            <button
              className="input-send"
              onClick={sendMessage}
              disabled={(!input.trim() || loading) && !recording}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
