import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { adminAPI } from '../services/api';
import {
  Users, MessageSquare, MessageCircle, Key, Activity,
  ThumbsUp, ThumbsDown, Shield, UserPlus, Search, Download,
  ChevronLeft, ChevronRight, Trash2, Eye, X, Check, Ban,
  RefreshCw, Settings,
} from 'lucide-react';
import './Admin.css';

const STAFF_ROLES = ['superadmin', 'admin', 'support', 'marketing', 'finance', 'moderator', 'developer'];

export default function Admin() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [adminInfo, setAdminInfo] = useState(null);
  const [stats, setStats] = useState(null);
  const [tab, setTab] = useState('');
  const [loading, setLoading] = useState(true);
  const [rolesConfig, setRolesConfig] = useState(null);

  // Users
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [userPage, setUserPage] = useState(1);
  const [userTotal, setUserTotal] = useState(0);
  const [userTierFilter, setUserTierFilter] = useState('');

  // Team
  const [team, setTeam] = useState([]);
  const [showCreateTeam, setShowCreateTeam] = useState(false);
  const [newTeam, setNewTeam] = useState({ email: '', name: '', password: '', role: 'support', department: 'support' });

  // Create external user
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [newUser, setNewUser] = useState({ email: '', name: '', password: '', tier: 'free' });

  // Feedback
  const [feedbackList, setFeedbackList] = useState([]);
  const [fbPage, setFbPage] = useState(1);
  const [fbTotal, setFbTotal] = useState(0);

  // API Keys
  const [apiKeys, setApiKeys] = useState([]);

  // Chat viewer
  const [viewingChats, setViewingChats] = useState(null); // { userId, name, conversations }
  const [selectedConvo, setSelectedConvo] = useState(null);

  // Status
  const [actionMsg, setActionMsg] = useState('');

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    if (!STAFF_ROLES.includes(user.role)) { navigate('/'); return; }
    loadInitial();
  }, [user, navigate]);

  const loadInitial = async () => {
    try {
      const [info, s, rc] = await Promise.all([
        adminAPI.me(),
        adminAPI.stats(),
        adminAPI.rolesConfig(),
      ]);
      setAdminInfo(info);
      setStats(s);
      setRolesConfig(rc);
      const firstTab = info.tabs?.[0] || 'stats';
      setTab(firstTab);
      setLoading(false);
    } catch {
      navigate('/');
    }
  };

  const loadUsers = useCallback(async () => {
    try {
      const res = await adminAPI.users({ search: userSearch, tier: userTierFilter, page: userPage, per_page: 50 });
      setUsers(res.users);
      setUserTotal(res.total);
    } catch { /* ignore */ }
  }, [userSearch, userTierFilter, userPage]);

  const loadTeam = async () => {
    try { setTeam(await adminAPI.team()); } catch { /* ignore */ }
  };

  const loadFeedback = useCallback(async () => {
    try {
      const res = await adminAPI.feedback({ page: fbPage, per_page: 50 });
      setFeedbackList(res.feedback || []);
      setFbTotal(res.total || 0);
    } catch { /* ignore */ }
  }, [fbPage]);

  const loadApiKeys = async () => {
    try { setApiKeys(await adminAPI.apiKeys()); } catch { /* ignore */ }
  };

  useEffect(() => {
    if (tab === 'users') loadUsers();
    if (tab === 'team') loadTeam();
    if (tab === 'feedback') loadFeedback();
    if (tab === 'apikeys') loadApiKeys();
  }, [tab, loadUsers, loadFeedback]);

  // ── Actions ──

  const flash = (msg) => { setActionMsg(msg); setTimeout(() => setActionMsg(''), 3000); };

  const toggleActive = async (id, current) => {
    await adminAPI.updateActive(id, !current);
    flash(`User ${!current ? 'activated' : 'deactivated'}`);
    loadUsers();
  };

  const changeRole = async (id, role) => {
    await adminAPI.updateRole(id, role);
    flash(`Role changed to ${role}`);
    loadUsers(); loadTeam();
  };

  const changeTier = async (id, tier) => {
    await adminAPI.updateTier(id, tier);
    flash(`Tier changed to ${tier}`);
    loadUsers();
  };

  const deleteUser = async (id, email) => {
    if (!confirm(`Delete user ${email}? This cannot be undone.`)) return;
    await adminAPI.deleteUser(id);
    flash(`User ${email} deleted`);
    loadUsers(); loadTeam();
  };

  const createTeamMember = async (e) => {
    e.preventDefault();
    try {
      await adminAPI.createTeamMember(newTeam);
      flash('Team member created');
      setShowCreateTeam(false);
      setNewTeam({ email: '', name: '', password: '', role: 'support', department: 'support' });
      loadTeam();
    } catch (err) { flash(`Error: ${err.message}`); }
  };

  const createExternalUser = async (e) => {
    e.preventDefault();
    try {
      await adminAPI.createUser(newUser);
      flash('User created');
      setShowCreateUser(false);
      setNewUser({ email: '', name: '', password: '', tier: 'free' });
      loadUsers();
    } catch (err) { flash(`Error: ${err.message}`); }
  };

  const viewUserChats = async (userId, name) => {
    try {
      const convos = await adminAPI.userConversations(userId);
      setViewingChats({ userId, name, conversations: convos });
      setSelectedConvo(null);
    } catch (err) { flash(`Error: ${err.message}`); }
  };

  const deleteUserChats = async (userId) => {
    if (!confirm('Delete all conversations for this user?')) return;
    await adminAPI.deleteUserConversations(userId);
    flash('Conversations deleted');
    setViewingChats(null);
  };

  const revokeApiKey = async (id) => {
    await adminAPI.revokeKey(id);
    flash('API key revoked');
    loadApiKeys();
  };

  const updateKeyLimit = async (id, limit) => {
    await adminAPI.updateKeyRateLimit(id, parseInt(limit));
    flash('Rate limit updated');
    loadApiKeys();
  };

  const deleteFb = async (id) => {
    await adminAPI.deleteFeedback(id);
    flash('Feedback deleted');
    loadFeedback();
  };

  const exportCSV = async () => {
    try {
      const blob = await adminAPI.exportUsersCSV();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ekodi-users.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch { flash('Export failed'); }
  };

  if (loading || !stats) return <div className="admin-loading">{t('common.loading')}</div>;

  const tabs = adminInfo?.tabs || [];

  return (
    <div className="admin-page">
      <div className="admin-container">
        <div className="admin-header">
          <h1><Shield size={28} /> {t('admin.title')}</h1>
          <span className="admin-role-badge">{adminInfo?.role}</span>
        </div>

        {actionMsg && <div className="admin-flash">{actionMsg}</div>}

        {/* Stats Cards */}
        {tabs.includes('stats') && (
          <div className="admin-stats">
            <StatCard icon={<Users size={24} />} val={stats.users} label={t('admin.users')} />
            <StatCard icon={<MessageSquare size={24} />} val={stats.conversations} label={t('admin.conversations')} />
            <StatCard icon={<MessageCircle size={24} />} val={stats.messages} label={t('admin.messages')} />
            <StatCard icon={<Key size={24} />} val={stats.api_keys} label={t('admin.api_keys')} />
            <StatCard icon={<Activity size={24} />} val={stats.api_usage} label={t('admin.api_usage')} />
            <StatCard icon={<ThumbsUp size={24} className="positive" />} val={stats.feedback?.positive || 0} label={t('admin.positive')} />
            <StatCard icon={<ThumbsDown size={24} className="negative" />} val={stats.feedback?.negative || 0} label={t('admin.negative')} />
          </div>
        )}

        {/* Tabs */}
        <div className="admin-tabs">
          {tabs.map((t_) => (
            <button key={t_} className={tab === t_ ? 'active' : ''} onClick={() => setTab(t_)}>
              {t_ === 'stats' && 'Stats'}
              {t_ === 'users' && 'Users'}
              {t_ === 'team' && 'Team'}
              {t_ === 'apikeys' && 'API Keys'}
              {t_ === 'feedback' && 'Feedback'}
              {t_ === 'chats' && 'Chats'}
            </button>
          ))}
        </div>

        {/* ── Users Tab ── */}
        {tab === 'users' && (
          <div className="admin-section">
            <div className="admin-toolbar">
              <div className="admin-search">
                <Search size={16} />
                <input placeholder="Search users..." value={userSearch} onChange={(e) => { setUserSearch(e.target.value); setUserPage(1); }} />
              </div>
              <select value={userTierFilter} onChange={(e) => { setUserTierFilter(e.target.value); setUserPage(1); }}>
                <option value="">All tiers</option>
                <option value="free">Free</option>
                <option value="standard">Standard</option>
                <option value="pro">Pro</option>
                <option value="business">Business</option>
              </select>
              <button className="admin-action-btn" onClick={() => setShowCreateUser(true)}><UserPlus size={16} /> New User</button>
              <button className="admin-action-btn" onClick={exportCSV}><Download size={16} /> Export CSV</button>
              <button className="admin-action-btn" onClick={loadUsers}><RefreshCw size={16} /></button>
            </div>

            {showCreateUser && (
              <form className="admin-create-form" onSubmit={createExternalUser}>
                <input placeholder="Name" required value={newUser.name} onChange={(e) => setNewUser({ ...newUser, name: e.target.value })} />
                <input placeholder="Email" type="email" required value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} />
                <input placeholder="Password" type="password" required minLength={6} value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} />
                <select value={newUser.tier} onChange={(e) => setNewUser({ ...newUser, tier: e.target.value })}>
                  <option value="free">Free</option>
                  <option value="standard">Standard</option>
                  <option value="pro">Pro</option>
                  <option value="business">Business</option>
                </select>
                <button type="submit"><Check size={16} /> Create</button>
                <button type="button" onClick={() => setShowCreateUser(false)}><X size={16} /></button>
              </form>
            )}

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Tier</th>
                    <th>Status</th>
                    <th>Verified</th>
                    <th>Last Login</th>
                    <th>Joined</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.name}</td>
                      <td>{u.email}</td>
                      <td>
                        <select className="inline-select" value={u.tier} onChange={(e) => changeTier(u.id, e.target.value)}>
                          <option value="free">free</option>
                          <option value="standard">standard</option>
                          <option value="pro">pro</option>
                          <option value="business">business</option>
                        </select>
                      </td>
                      <td><span className={`status-dot ${u.is_active ? 'active' : 'inactive'}`} />{u.is_active ? 'Active' : 'Inactive'}</td>
                      <td>{u.email_verified ? <Check size={14} className="text-green" /> : <X size={14} className="text-red" />}</td>
                      <td>{u.last_login ? new Date(u.last_login).toLocaleDateString() : '—'}</td>
                      <td>{new Date(u.created_at).toLocaleDateString()}</td>
                      <td className="action-cell">
                        <button title="View chats" onClick={() => viewUserChats(u.id, u.name)}><Eye size={14} /></button>
                        <button title={u.is_active ? 'Deactivate' : 'Activate'} onClick={() => toggleActive(u.id, u.is_active)}>
                          {u.is_active ? <Ban size={14} /> : <Check size={14} />}
                        </button>
                        <button title="Delete" onClick={() => deleteUser(u.id, u.email)}><Trash2 size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={userPage} total={userTotal} perPage={50} onChange={setUserPage} />
          </div>
        )}

        {/* ── Team Tab ── */}
        {tab === 'team' && (
          <div className="admin-section">
            <div className="admin-toolbar">
              <button className="admin-action-btn" onClick={() => setShowCreateTeam(true)}><UserPlus size={16} /> New Team Member</button>
              <button className="admin-action-btn" onClick={loadTeam}><RefreshCw size={16} /></button>
            </div>

            {showCreateTeam && (
              <form className="admin-create-form" onSubmit={createTeamMember}>
                <input placeholder="Name" required value={newTeam.name} onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })} />
                <input placeholder="Email" type="email" required value={newTeam.email} onChange={(e) => setNewTeam({ ...newTeam, email: e.target.value })} />
                <input placeholder="Password" type="password" required minLength={6} value={newTeam.password} onChange={(e) => setNewTeam({ ...newTeam, password: e.target.value })} />
                <select value={newTeam.role} onChange={(e) => setNewTeam({ ...newTeam, role: e.target.value })}>
                  {rolesConfig?.staff_roles?.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                <select value={newTeam.department} onChange={(e) => setNewTeam({ ...newTeam, department: e.target.value })}>
                  {rolesConfig?.departments?.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
                <button type="submit"><Check size={16} /> Create</button>
                <button type="button" onClick={() => setShowCreateTeam(false)}><X size={16} /></button>
              </form>
            )}

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Department</th>
                    <th>Status</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {team.map((m) => (
                    <tr key={m.id}>
                      <td>{m.name}</td>
                      <td>{m.email}</td>
                      <td>
                        <select className="inline-select role" value={m.role} onChange={(e) => changeRole(m.id, e.target.value)}>
                          {rolesConfig?.staff_roles?.map(r => <option key={r} value={r}>{r}</option>)}
                        </select>
                      </td>
                      <td>{m.department || '—'}</td>
                      <td><span className={`status-dot ${m.is_active ? 'active' : 'inactive'}`} />{m.is_active ? 'Active' : 'Inactive'}</td>
                      <td>{m.last_login ? new Date(m.last_login).toLocaleDateString() : '—'}</td>
                      <td className="action-cell">
                        <button title={m.is_active ? 'Deactivate' : 'Activate'} onClick={() => toggleActive(m.id, m.is_active)}>
                          {m.is_active ? <Ban size={14} /> : <Check size={14} />}
                        </button>
                        <button title="Delete" onClick={() => deleteUser(m.id, m.email)}><Trash2 size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── API Keys Tab ── */}
        {tab === 'apikeys' && (
          <div className="admin-section">
            <div className="admin-toolbar">
              <button className="admin-action-btn" onClick={loadApiKeys}><RefreshCw size={16} /> Refresh</button>
            </div>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Key Name</th>
                    <th>Prefix</th>
                    <th>Usage</th>
                    <th>Rate Limit</th>
                    <th>Active</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.map((k) => (
                    <tr key={k.id}>
                      <td>{k.user_name} <span className="text-muted">({k.user_email})</span></td>
                      <td>{k.name}</td>
                      <td className="mono">{k.key_prefix}</td>
                      <td>{k.usage_count}</td>
                      <td>
                        <input
                          type="number"
                          className="inline-input"
                          defaultValue={k.rate_limit}
                          onBlur={(e) => updateKeyLimit(k.id, e.target.value)}
                          style={{ width: '80px' }}
                        />
                      </td>
                      <td>{k.active ? <Check size={14} className="text-green" /> : <X size={14} className="text-red" />}</td>
                      <td>{new Date(k.created_at).toLocaleDateString()}</td>
                      <td className="action-cell">
                        {k.active && (
                          <button title="Revoke" onClick={() => revokeApiKey(k.id)}><Ban size={14} /></button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Feedback Tab ── */}
        {tab === 'feedback' && (
          <div className="admin-section">
            <div className="admin-toolbar">
              <button className="admin-action-btn" onClick={loadFeedback}><RefreshCw size={16} /> Refresh</button>
            </div>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Rating</th>
                    <th>Comment</th>
                    <th>User</th>
                    <th>Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {feedbackList.map((f) => (
                    <tr key={f.id}>
                      <td>{f.rating === 1 ? <ThumbsUp size={16} className="positive" /> : <ThumbsDown size={16} className="negative" />}</td>
                      <td>{f.comment || '—'}</td>
                      <td>{f.user_name} <span className="text-muted">({f.user_email})</span></td>
                      <td>{new Date(f.created_at).toLocaleDateString()}</td>
                      <td className="action-cell">
                        <button title="Delete" onClick={() => deleteFb(f.id)}><Trash2 size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={fbPage} total={fbTotal} perPage={50} onChange={setFbPage} />
          </div>
        )}

        {/* ── Chats Tab ── */}
        {tab === 'chats' && (
          <div className="admin-section">
            <p className="admin-hint">Select a user from the Users tab to view their chat history.</p>
          </div>
        )}

        {/* ── Chat Viewer Modal ── */}
        {viewingChats && (
          <div className="admin-modal-overlay" onClick={() => setViewingChats(null)}>
            <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
              <div className="admin-modal-header">
                <h2>Chats: {viewingChats.name}</h2>
                <div className="admin-modal-actions">
                  <button className="admin-action-btn danger" onClick={() => deleteUserChats(viewingChats.userId)}>
                    <Trash2 size={14} /> Delete All
                  </button>
                  <button className="admin-modal-close" onClick={() => setViewingChats(null)}><X size={20} /></button>
                </div>
              </div>
              <div className="admin-modal-body">
                {viewingChats.conversations.length === 0 ? (
                  <p className="admin-hint">No conversations found.</p>
                ) : (
                  <div className="chat-viewer">
                    <div className="chat-viewer-list">
                      {viewingChats.conversations.map((c) => (
                        <button
                          key={c.id}
                          className={`chat-viewer-item ${selectedConvo?.id === c.id ? 'active' : ''}`}
                          onClick={() => setSelectedConvo(c)}
                        >
                          <span className="chat-viewer-title">{c.title}</span>
                          <span className="chat-viewer-meta">{c.message_count} msgs</span>
                        </button>
                      ))}
                    </div>
                    <div className="chat-viewer-messages">
                      {selectedConvo ? (
                        selectedConvo.messages.map((m, i) => (
                          <div key={i} className={`chat-msg ${m.role}`}>
                            <span className="chat-msg-role">{m.role}</span>
                            <p>{m.text_fr || m.text_bm || '(empty)'}</p>
                            <span className="chat-msg-time">{new Date(m.created_at).toLocaleString()}</span>
                          </div>
                        ))
                      ) : (
                        <p className="admin-hint">Select a conversation to view messages.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Subcomponents ──

function StatCard({ icon, val, label }) {
  return (
    <div className="admin-stat">
      <div className="stat-icon">{icon}</div>
      <span className="stat-val">{val}</span>
      <span className="stat-lbl">{label}</span>
    </div>
  );
}

function Pagination({ page, total, perPage, onChange }) {
  const totalPages = Math.ceil(total / perPage) || 1;
  if (totalPages <= 1) return null;
  return (
    <div className="admin-pagination">
      <button disabled={page <= 1} onClick={() => onChange(page - 1)}><ChevronLeft size={16} /></button>
      <span>{page} / {totalPages} ({total} total)</span>
      <button disabled={page >= totalPages} onClick={() => onChange(page + 1)}><ChevronRight size={16} /></button>
    </div>
  );
}
