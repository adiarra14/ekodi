import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { chatAPI, feedbackAPI } from '../services/api';
import {
  Plus, MessageSquare, Trash2, Send, Mic, MicOff, Volume2,
  ThumbsUp, ThumbsDown, LogOut, ChevronLeft, Pencil, Check, X, Settings,
} from 'lucide-react';
import LanguageSwitcher from '../components/ui/LanguageSwitcher';
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

  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

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

      // Play audio
      if (data.audio_base64) playAudio(data.audio_base64);
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== 'temp-user'));
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Voice recording
  const toggleRecording = async () => {
    if (recording) {
      mediaRecorderRef.current?.stop();
      setRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4' });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        await sendVoice(blob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
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

      if (data.audio_base64) playAudio(data.audio_base64);
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== 'temp-voice'));
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Audio playback
  const playAudio = (b64) => {
    const audio = new Audio(`data:audio/wav;base64,${b64}`);
    audio.play().catch(() => {});
  };

  // Feedback
  const sendFeedback = async (messageId, rating) => {
    try {
      await feedbackAPI.submit({ message_id: messageId, rating });
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
          <div className="sidebar-user">
            <span>{user.name}</span>
            <button onClick={() => { logout(); navigate('/'); }} title={t('nav.logout')}>
              <LogOut size={16} />
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
                <div className="msg-bubble">
                  {msg.text_bm && <p className="msg-text-main">{msg.text_bm}</p>}
                  {msg.text_fr && <p className="msg-text-sub">{msg.text_fr}</p>}
                </div>
                {msg.role === 'assistant' && msg.id && !msg.id.startsWith('temp') && (
                  <div className="msg-actions">
                    {msg.audio_base64 && (
                      <button onClick={() => playAudio(msg.audio_base64)} title="Play">
                        <Volume2 size={14} />
                      </button>
                    )}
                    <button onClick={() => sendFeedback(msg.id, 1)} title="Good">
                      <ThumbsUp size={14} />
                    </button>
                    <button onClick={() => sendFeedback(msg.id, -1)} title="Bad">
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
                <div className="msg-bubble typing">
                  <span className="dot" /><span className="dot" /><span className="dot" />
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

          <div className="input-row">
            <button
              className={`input-mic ${recording ? 'recording' : ''}`}
              onClick={toggleRecording}
              disabled={loading}
              title={recording ? t('chat.mic_recording') : t('chat.mic_tap')}
            >
              {recording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
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
            <button
              className="input-send"
              onClick={sendMessage}
              disabled={!input.trim() || loading}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
