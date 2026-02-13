/**
 * Ekodi API client — centralized fetch wrapper.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

function getToken() {
  return localStorage.getItem('ekodi_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('ekodi_token');
    localStorage.removeItem('ekodi_user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Error ${res.status}`);
  }

  // Handle non-JSON responses (e.g. audio)
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('audio/')) {
    return res.blob();
  }
  return res.json();
}

// Auth
export const authAPI = {
  register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request('/auth/me'),
};

// Conversations
export const chatAPI = {
  listConversations: () => request('/conversations'),
  createConversation: (title) =>
    request('/conversations', { method: 'POST', body: JSON.stringify({ title }) }),
  getConversation: (id) => request(`/conversations/${id}`),
  renameConversation: (id, title) =>
    request(`/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: 'DELETE' }),
  sendText: (data) => request('/chat', { method: 'POST', body: JSON.stringify(data) }),
  sendVoice: (formData) => request('/voice-chat', { method: 'POST', body: formData }),
};

// TTS
export const ttsAPI = {
  synthesize: (text) =>
    request('/tts', { method: 'POST', body: JSON.stringify({ text }) }),
};

// API Keys
export const apiKeysAPI = {
  list: () => request('/api/v1/keys'),
  create: (name) => request('/api/v1/keys', { method: 'POST', body: JSON.stringify({ name }) }),
  revoke: (id) => request(`/api/v1/keys/${id}`, { method: 'DELETE' }),
};

// Feedback
export const feedbackAPI = {
  submit: (data) => request('/feedback', { method: 'POST', body: JSON.stringify(data) }),
};

// Admin
export const adminAPI = {
  stats: () => request('/admin/stats'),
  users: () => request('/admin/users'),
  feedback: () => request('/admin/feedback'),
};
