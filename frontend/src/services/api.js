/**
 * Ekodi API client — centralized fetch wrapper.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

function getToken() {
  return localStorage.getItem('ekodi_token');
}

function getRefreshToken() {
  return localStorage.getItem('ekodi_refresh_token');
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

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // Auto-refresh on 401
  if (res.status === 401) {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          localStorage.setItem('ekodi_token', data.token);
          localStorage.setItem('ekodi_refresh_token', data.refresh_token);
          localStorage.setItem('ekodi_user', JSON.stringify(data.user));
          // Retry original request
          headers['Authorization'] = `Bearer ${data.token}`;
          res = await fetch(`${API_BASE}${path}`, { ...options, headers });
        }
      } catch { /* ignore refresh failure */ }
    }
  }

  if (res.status === 401) {
    localStorage.removeItem('ekodi_token');
    localStorage.removeItem('ekodi_refresh_token');
    localStorage.removeItem('ekodi_user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  // Handle 503 — server busy
  if (res.status === 503) {
    const data = await res.json().catch(() => ({}));
    const err = new Error(data.detail || 'Server is currently busy. Please try again in a moment.');
    err.code = 'SERVER_BUSY';
    err.retryAfter = parseInt(res.headers.get('Retry-After') || '10', 10);
    // Dispatch global event for the busy banner
    window.dispatchEvent(new CustomEvent('ekodi-server-busy', {
      detail: { message: err.message, retryAfter: err.retryAfter },
    }));
    throw err;
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Error ${res.status}`);
  }

  // Handle non-JSON responses (e.g. audio, zip)
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('audio/')) return res.blob();
  if (ct.includes('application/zip')) return res.blob();
  if (ct.includes('text/csv')) return res.blob();
  return res.json();
}

// Auth
export const authAPI = {
  register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request('/auth/me'),
  refresh: (refresh_token) => request('/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  verify: (token) => request(`/auth/verify/${token}`),
  resendVerification: () => request('/auth/resend-verification', { method: 'POST' }),
  forgotPassword: (email) => request('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (token, new_password) => request('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, new_password }) }),
  deleteAccount: (password) => request('/auth/account', { method: 'DELETE', body: JSON.stringify({ password }) }),
  exportData: () => request('/auth/export'),
  deleteAllConversations: () => request('/auth/conversations/all', { method: 'DELETE' }),
  myUsage: () => request('/auth/me/usage'),
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

// Server Status (public, no auth)
export const statusAPI = {
  check: () => fetch(`${API_BASE}/status`).then(r => r.json()).catch(() => ({ status: 'unknown' })),
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
  me: () => request('/admin/me'),
  stats: () => request('/admin/stats'),
  rolesConfig: () => request('/admin/roles-config'),

  // Users (external)
  users: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/admin/users${qs ? '?' + qs : ''}`);
  },
  createUser: (data) => request('/admin/users', { method: 'POST', body: JSON.stringify(data) }),
  updateRole: (id, role) => request(`/admin/users/${id}/role`, { method: 'PATCH', body: JSON.stringify({ role }) }),
  updateTier: (id, tier) => request(`/admin/users/${id}/tier`, { method: 'PATCH', body: JSON.stringify({ tier }) }),
  updateActive: (id, is_active) => request(`/admin/users/${id}/active`, { method: 'PATCH', body: JSON.stringify({ is_active }) }),
  deleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE' }),

  // Team (staff)
  team: () => request('/admin/team'),
  createTeamMember: (data) => request('/admin/team', { method: 'POST', body: JSON.stringify(data) }),

  // API key admin
  apiKeys: () => request('/admin/api-keys'),
  updateKeyRateLimit: (id, rate_limit) => request(`/admin/api-keys/${id}/rate-limit`, { method: 'PATCH', body: JSON.stringify({ rate_limit }) }),
  revokeKey: (id) => request(`/admin/api-keys/${id}/revoke`, { method: 'PATCH' }),

  // Feedback management
  feedback: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/admin/feedback${qs ? '?' + qs : ''}`);
  },
  deleteFeedback: (id) => request(`/admin/feedback/${id}`, { method: 'DELETE' }),

  // Chat history
  userConversations: (userId) => request(`/admin/users/${userId}/conversations`),
  deleteUserConversations: (userId) => request(`/admin/users/${userId}/conversations`, { method: 'DELETE' }),

  // Exports
  exportUsersCSV: () => request('/admin/export/users'),

  // Session management
  sessions: () => request('/admin/sessions'),
  userSessions: (userId) => request(`/admin/users/${userId}/sessions`),
  forceLogout: (userId) => request(`/admin/users/${userId}/force-logout`, { method: 'POST' }),
  tokenConfig: () => request('/admin/token-config'),

  // Billing & Token Usage
  billingOverview: () => request('/admin/billing/overview'),
  billingUsers: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/admin/billing/users${qs ? '?' + qs : ''}`);
  },
  billingDaily: (days = 30) => request(`/admin/billing/daily?days=${days}`),
  billingUserDetail: (userId, params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/admin/billing/users/${userId}${qs ? '?' + qs : ''}`);
  },
  updateCredits: (userId, amount, reason) => request(`/admin/billing/users/${userId}/credits`, {
    method: 'POST',
    body: JSON.stringify({ amount, reason }),
  }),
  updateBudget: (userId, monthly_budget) => request(`/admin/billing/users/${userId}/budget`, {
    method: 'PATCH',
    body: JSON.stringify({ monthly_budget }),
  }),
  billingPricing: () => request('/admin/billing/pricing'),

  // Server Health
  serverHealth: () => request('/admin/health'),
};
