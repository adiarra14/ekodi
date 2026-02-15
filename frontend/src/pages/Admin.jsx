import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { adminAPI } from '../services/api';
import {
  Users, MessageSquare, MessageCircle, Key, Activity,
  ThumbsUp, ThumbsDown, Shield, UserPlus, Search, Download,
  ChevronLeft, ChevronRight, Trash2, Eye, X, Check, Ban,
  RefreshCw, Settings, LogOut, Monitor, DollarSign,
  Heart, Cpu, HardDrive, Zap, AlertTriangle, Mail,
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

  // Sessions
  const [sessions, setSessions] = useState([]);
  const [tokenConfig, setTokenConfig] = useState(null);

  // Health
  const [serverHealth, setServerHealth] = useState(null);

  // Platform Settings
  const [platformSettings, setPlatformSettings] = useState(null);
  const [settingsSchema, setSettingsSchema] = useState(null);
  const [settingsSaving, setSettingsSaving] = useState(false);

  // Billing
  const [billingOverview, setBillingOverview] = useState(null);
  const [billingUsers, setBillingUsers] = useState([]);
  const [billingDaily, setBillingDaily] = useState([]);
  const [billingPricing, setBillingPricing] = useState(null);
  const [billingUserDetail, setBillingUserDetail] = useState(null);
  const [creditAmount, setCreditAmount] = useState('');
  const [creditReason, setCreditReason] = useState('');

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

  const loadSessions = async () => {
    try {
      const [sessRes, tcRes] = await Promise.all([
        adminAPI.sessions(),
        adminAPI.tokenConfig(),
      ]);
      setSessions(sessRes.sessions || []);
      setTokenConfig(tcRes);
    } catch { /* ignore */ }
  };

  const loadHealth = async () => {
    try { setServerHealth(await adminAPI.serverHealth()); } catch { /* ignore */ }
  };

  const loadSettings = async () => {
    try {
      const data = await adminAPI.settings();
      setPlatformSettings(data.settings || {});
      setSettingsSchema(data.schema || {});
    } catch { /* ignore */ }
  };

  const saveSettings = async (key, value) => {
    setSettingsSaving(true);
    try {
      await adminAPI.updateSettings({ [key]: value });
      flash(`Setting "${key}" updated to "${value}"`);
      loadSettings();
    } catch (e) {
      flash(e.message || 'Failed to save setting');
    } finally {
      setSettingsSaving(false);
    }
  };

  const loadBilling = async () => {
    try {
      const [overview, usersRes, daily, pricing] = await Promise.all([
        adminAPI.billingOverview(),
        adminAPI.billingUsers(),
        adminAPI.billingDaily(30),
        adminAPI.billingPricing(),
      ]);
      setBillingOverview(overview);
      setBillingUsers(usersRes.users || []);
      setBillingDaily(daily.days || []);
      setBillingPricing(pricing);
    } catch { /* ignore */ }
  };

  const viewUserBilling = async (userId) => {
    try {
      const res = await adminAPI.billingUserDetail(userId);
      setBillingUserDetail(res);
    } catch { /* ignore */ }
  };

  const addCredits = async (userId) => {
    const amount = parseFloat(creditAmount);
    if (isNaN(amount)) return;
    try {
      await adminAPI.updateCredits(userId, amount, creditReason || 'Manual adjustment');
      flash(`Credits updated for user`);
      setCreditAmount('');
      setCreditReason('');
      loadBilling();
      if (billingUserDetail) viewUserBilling(billingUserDetail.user.id);
    } catch (e) {
      flash(e.message || 'Failed to update credits');
    }
  };

  useEffect(() => {
    if (tab === 'users') loadUsers();
    if (tab === 'team') loadTeam();
    if (tab === 'feedback') loadFeedback();
    if (tab === 'apikeys') loadApiKeys();
    if (tab === 'sessions') loadSessions();
    if (tab === 'billing') loadBilling();
    if (tab === 'health') loadHealth();
    if (tab === 'settings') loadSettings();
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

  const forceLogoutUser = async (id, email) => {
    if (!confirm(`Force-logout ${email}? All their active sessions will be invalidated.`)) return;
    try {
      await adminAPI.forceLogout(id);
      flash(`All sessions for ${email} invalidated`);
      loadSessions();
    } catch (e) {
      flash(e.message || 'Force-logout failed');
    }
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
            {stats.billing && (
              <StatCard icon={<DollarSign size={24} />} val={`$${stats.billing.month_cost.toFixed(2)}`} label="Month Cost" />
            )}
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
              {t_ === 'sessions' && 'Sessions'}
              {t_ === 'billing' && 'Billing'}
              {t_ === 'health' && 'Health'}
              {t_ === 'settings' && 'Settings'}
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
                      <td>
                        {!u.is_active
                          ? <><span className="status-dot inactive" />Inactive</>
                          : !u.email_verified
                            ? <><span className="status-dot pending" />Pending</>
                            : <><span className="status-dot active" />Active</>
                        }
                      </td>
                      <td>{u.email_verified ? <Check size={14} className="text-green" /> : <X size={14} className="text-red" />}</td>
                      <td>{u.last_login ? new Date(u.last_login).toLocaleDateString() : '—'}</td>
                      <td>{new Date(u.created_at).toLocaleDateString()}</td>
                      <td className="action-cell">
                        <button title="View chats" onClick={() => viewUserChats(u.id, u.name)}><Eye size={14} /></button>
                        <button title={u.is_active ? 'Deactivate' : 'Activate'} onClick={() => toggleActive(u.id, u.is_active)}>
                          {u.is_active ? <Ban size={14} /> : <Check size={14} />}
                        </button>
                        <button title="Force Logout" onClick={() => forceLogoutUser(u.id, u.email)}><LogOut size={14} /></button>
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

        {/* ── Billing Tab ── */}
        {tab === 'billing' && (
          <div className="admin-section">
            <div className="admin-toolbar">
              <h3><Activity size={18} /> GPT Token Usage & Billing</h3>
              <button className="admin-action-btn" onClick={loadBilling}><RefreshCw size={14} /> Refresh</button>
            </div>

            {/* Overview Cards */}
            {billingOverview && (
              <>
                <div className="billing-cards">
                  <div className="billing-card">
                    <span className="billing-card-label">This Month Cost</span>
                    <span className="billing-card-value cost">${billingOverview.this_month.total_cost.toFixed(4)}</span>
                    <span className="billing-card-sub">{billingOverview.this_month.total_requests} requests</span>
                  </div>
                  <div className="billing-card">
                    <span className="billing-card-label">This Month Tokens</span>
                    <span className="billing-card-value">{billingOverview.this_month.total_tokens.toLocaleString()}</span>
                    <span className="billing-card-sub">{billingOverview.this_month.total_requests} calls</span>
                  </div>
                  <div className="billing-card">
                    <span className="billing-card-label">All-Time Cost</span>
                    <span className="billing-card-value cost">${billingOverview.all_time.total_cost.toFixed(4)}</span>
                    <span className="billing-card-sub">{billingOverview.all_time.total_requests} requests</span>
                  </div>
                  <div className="billing-card">
                    <span className="billing-card-label">All-Time Tokens</span>
                    <span className="billing-card-value">{billingOverview.all_time.total_tokens.toLocaleString()}</span>
                    <span className="billing-card-sub">{billingOverview.all_time.total_requests} calls</span>
                  </div>
                </div>

                {/* Per-Model Breakdown */}
                {billingOverview.by_model.length > 0 && (
                  <div className="billing-breakdown">
                    <h4>By Model</h4>
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>Model</th>
                          <th>Requests</th>
                          <th>Prompt Tokens</th>
                          <th>Completion Tokens</th>
                          <th>Total Tokens</th>
                          <th>Cost</th>
                        </tr>
                      </thead>
                      <tbody>
                        {billingOverview.by_model.map((m) => (
                          <tr key={m.model}>
                            <td><strong>{m.model}</strong></td>
                            <td>{m.requests}</td>
                            <td>{m.prompt_tokens.toLocaleString()}</td>
                            <td>{m.completion_tokens.toLocaleString()}</td>
                            <td>{m.total_tokens.toLocaleString()}</td>
                            <td className="cost-cell">${m.total_cost.toFixed(4)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Per-Endpoint */}
                {billingOverview.by_endpoint.length > 0 && (
                  <div className="billing-breakdown">
                    <h4>By Endpoint</h4>
                    <div className="billing-endpoint-chips">
                      {billingOverview.by_endpoint.map((e) => (
                        <div key={e.endpoint} className="billing-chip">
                          <span className="billing-chip-label">{e.endpoint}</span>
                          <span className="billing-chip-val">{e.requests} req · ${e.total_cost.toFixed(4)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Pricing Reference */}
            {billingPricing && (
              <div className="billing-breakdown">
                <h4>Model Pricing (per 1M tokens)</h4>
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Input ($/1M)</th>
                      <th>Output ($/1M)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(billingPricing.models).map(([model, pricing]) => (
                      <tr key={model} className={model === billingPricing.default_model ? 'active-model' : ''}>
                        <td><strong>{model}</strong> {model === billingPricing.default_model && <span className="badge-active">active</span>}</td>
                        <td>${pricing.prompt.toFixed(2)}</td>
                        <td>${pricing.completion.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Daily Chart (simple bar representation) */}
            {billingDaily.length > 0 && (
              <div className="billing-breakdown">
                <h4>Daily Usage (Last 30 Days)</h4>
                <div className="billing-daily-chart">
                  {billingDaily.map((d) => {
                    const maxCost = Math.max(...billingDaily.map(x => x.total_cost), 0.001);
                    const height = Math.max(4, (d.total_cost / maxCost) * 100);
                    return (
                      <div key={d.date} className="billing-bar-wrap" title={`${d.date}\n$${d.total_cost.toFixed(4)} · ${d.total_tokens} tokens · ${d.requests} req`}>
                        <div className="billing-bar" style={{ height: `${height}%` }} />
                        <span className="billing-bar-label">{d.date.slice(5)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Per-User Costs */}
            <div className="billing-breakdown">
              <h4>Cost Per User</h4>
              {billingUsers.length === 0 ? (
                <p className="admin-hint">No usage recorded yet.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Tier</th>
                      <th>Requests</th>
                      <th>Tokens</th>
                      <th>Cost</th>
                      <th>Credits</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {billingUsers.map((u) => (
                      <tr key={u.user_id}>
                        <td>
                          <div>{u.name}</div>
                          <small style={{ color: '#71717a' }}>{u.email}</small>
                        </td>
                        <td><span className={`admin-role-badge role-${u.tier}`}>{u.tier}</span></td>
                        <td>{u.requests}</td>
                        <td>{u.total_tokens.toLocaleString()}</td>
                        <td className="cost-cell">${u.total_cost.toFixed(4)}</td>
                        <td className="cost-cell">${u.credits_balance.toFixed(4)}</td>
                        <td>
                          <button className="admin-action-btn" onClick={() => viewUserBilling(u.user_id)}>
                            <Eye size={14} /> Detail
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* User Detail Modal */}
            {billingUserDetail && (
              <div className="admin-modal-overlay" onClick={() => setBillingUserDetail(null)}>
                <div className="admin-modal billing-modal" onClick={(e) => e.stopPropagation()}>
                  <div className="admin-modal-header">
                    <h2>Usage: {billingUserDetail.user.name}</h2>
                    <button onClick={() => setBillingUserDetail(null)}><X size={20} /></button>
                  </div>
                  <div className="billing-user-summary">
                    <div className="billing-card small">
                      <span className="billing-card-label">Total Cost</span>
                      <span className="billing-card-value cost">${billingUserDetail.user.total_cost.toFixed(4)}</span>
                    </div>
                    <div className="billing-card small">
                      <span className="billing-card-label">Total Tokens</span>
                      <span className="billing-card-value">{billingUserDetail.user.total_tokens_used.toLocaleString()}</span>
                    </div>
                    <div className="billing-card small">
                      <span className="billing-card-label">Credits</span>
                      <span className="billing-card-value">${billingUserDetail.user.credits_balance.toFixed(4)}</span>
                    </div>
                    <div className="billing-card small">
                      <span className="billing-card-label">Monthly Budget</span>
                      <span className="billing-card-value">{billingUserDetail.user.monthly_budget > 0 ? `$${billingUserDetail.user.monthly_budget.toFixed(2)}` : 'Unlimited'}</span>
                    </div>
                  </div>

                  {/* Credits adjustment */}
                  <div className="billing-credit-form">
                    <h4>Adjust Credits</h4>
                    <div className="billing-credit-row">
                      <input type="number" step="0.01" placeholder="Amount ($)" value={creditAmount} onChange={(e) => setCreditAmount(e.target.value)} />
                      <input type="text" placeholder="Reason" value={creditReason} onChange={(e) => setCreditReason(e.target.value)} />
                      <button className="admin-action-btn" onClick={() => addCredits(billingUserDetail.user.id)}>
                        <Check size={14} /> Apply
                      </button>
                    </div>
                    <small style={{ color: '#71717a' }}>Positive = add credits, negative = deduct</small>
                  </div>

                  {/* Recent usage */}
                  <div className="billing-usage-list">
                    <h4>Recent API Calls</h4>
                    {billingUserDetail.usage.length === 0 ? (
                      <p className="admin-hint">No usage recorded.</p>
                    ) : (
                      <table className="admin-table compact">
                        <thead>
                          <tr>
                            <th>Time</th>
                            <th>Model</th>
                            <th>Endpoint</th>
                            <th>In</th>
                            <th>Out</th>
                            <th>Total</th>
                            <th>Cost</th>
                          </tr>
                        </thead>
                        <tbody>
                          {billingUserDetail.usage.map((u) => (
                            <tr key={u.id}>
                              <td>{new Date(u.created_at).toLocaleString()}</td>
                              <td>{u.model}</td>
                              <td>{u.endpoint}</td>
                              <td>{u.prompt_tokens}</td>
                              <td>{u.completion_tokens}</td>
                              <td>{u.total_tokens}</td>
                              <td className="cost-cell">${u.total_cost.toFixed(6)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Health Tab ── */}
        {tab === 'health' && (
          <div className="admin-section">
            <div className="admin-toolbar">
              <h3><Heart size={18} /> Server Health</h3>
              <button className="admin-action-btn" onClick={loadHealth}><RefreshCw size={14} /> Refresh</button>
            </div>

            {serverHealth ? (
              <>
                {/* Status indicator */}
                <div className={`health-status-banner health-${serverHealth.status}`}>
                  <div className="health-status-dot" />
                  <span className="health-status-text">
                    {serverHealth.status === 'healthy' && 'All systems operational'}
                    {serverHealth.status === 'warning' && 'Server under load'}
                    {serverHealth.status === 'critical' && 'Server overloaded — requests being rejected'}
                  </span>
                  {serverHealth.is_overloaded && (
                    <span className="health-overload-reason">
                      <AlertTriangle size={14} /> {serverHealth.overload_reason}
                    </span>
                  )}
                </div>

                {/* Metrics cards */}
                <div className="health-cards">
                  <div className="health-card">
                    <Cpu size={20} className="health-card-icon" />
                    <div className="health-card-body">
                      <span className="health-card-label">CPU</span>
                      <span className="health-card-value">{serverHealth.cpu_percent}%</span>
                      <div className="health-bar">
                        <div className="health-bar-fill" style={{
                          width: `${serverHealth.cpu_percent}%`,
                          background: serverHealth.cpu_percent > 80 ? '#ef4444' : serverHealth.cpu_percent > 60 ? '#f59e0b' : '#34d399',
                        }} />
                      </div>
                    </div>
                  </div>

                  <div className="health-card">
                    <HardDrive size={20} className="health-card-icon" />
                    <div className="health-card-body">
                      <span className="health-card-label">Memory</span>
                      <span className="health-card-value">{serverHealth.memory_percent}%</span>
                      <div className="health-bar">
                        <div className="health-bar-fill" style={{
                          width: `${serverHealth.memory_percent}%`,
                          background: serverHealth.memory_percent > 80 ? '#ef4444' : serverHealth.memory_percent > 60 ? '#f59e0b' : '#34d399',
                        }} />
                      </div>
                      <small style={{ color: '#71717a' }}>
                        {serverHealth.memory_used_mb > 0 ? `${serverHealth.memory_used_mb.toFixed(0)}MB / ${serverHealth.memory_total_mb.toFixed(0)}MB` : '—'}
                      </small>
                    </div>
                  </div>

                  <div className="health-card">
                    <Zap size={20} className="health-card-icon" />
                    <div className="health-card-body">
                      <span className="health-card-label">Active Requests</span>
                      <span className="health-card-value">
                        {serverHealth.active_requests}
                        <small style={{ fontSize: '0.6em', color: '#71717a' }}> / {serverHealth.limits?.max_concurrent}</small>
                      </span>
                      <div className="health-bar">
                        <div className="health-bar-fill" style={{
                          width: `${Math.min(100, (serverHealth.active_requests / (serverHealth.limits?.max_concurrent || 20)) * 100)}%`,
                          background: '#a78bfa',
                        }} />
                      </div>
                    </div>
                  </div>

                  <div className="health-card">
                    <Activity size={20} className="health-card-icon" />
                    <div className="health-card-body">
                      <span className="health-card-label">Avg Response</span>
                      <span className="health-card-value">{serverHealth.avg_response_time_ms}ms</span>
                    </div>
                  </div>
                </div>

                {/* Counters */}
                <div className="health-counters">
                  <div className="health-counter">
                    <span className="health-counter-val">{serverHealth.total_requests.toLocaleString()}</span>
                    <span className="health-counter-label">Total Requests</span>
                  </div>
                  <div className="health-counter">
                    <span className="health-counter-val text-red">{serverHealth.total_errors}</span>
                    <span className="health-counter-label">Errors</span>
                  </div>
                  <div className="health-counter">
                    <span className="health-counter-val text-yellow">{serverHealth.total_rejected}</span>
                    <span className="health-counter-label">Rejected (503)</span>
                  </div>
                  <div className="health-counter">
                    <span className="health-counter-val">{serverHealth.error_rate}%</span>
                    <span className="health-counter-label">Error Rate</span>
                  </div>
                  <div className="health-counter">
                    <span className="health-counter-val">{Math.floor(serverHealth.uptime_seconds / 3600)}h {Math.floor((serverHealth.uptime_seconds % 3600) / 60)}m</span>
                    <span className="health-counter-label">Uptime</span>
                  </div>
                </div>

                {/* Limits */}
                {serverHealth.limits && (
                  <div className="health-limits">
                    <h4>Protection Thresholds</h4>
                    <div className="health-limits-grid">
                      <span>Max Concurrent Requests: <strong>{serverHealth.limits.max_concurrent}</strong></span>
                      <span>CPU Threshold: <strong>{serverHealth.limits.cpu_threshold}%</strong></span>
                      <span>Memory Threshold: <strong>{serverHealth.limits.memory_threshold}%</strong></span>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="admin-hint">Loading health data...</p>
            )}
          </div>
        )}

        {/* ── Settings Tab ── */}
        {tab === 'settings' && (
          <div className="admin-section">
            <div className="admin-toolbar">
              <h3><Settings size={18} /> Platform Settings</h3>
              <button className="admin-action-btn" onClick={loadSettings}><RefreshCw size={14} /> Refresh</button>
            </div>

            {platformSettings ? (
              <div className="settings-cards">
                {/* Translation Engine */}
                <div className="settings-card">
                  <div className="settings-card-header">
                    <h4>Translation Engine</h4>
                    <p className="settings-card-desc">
                      Choose which engine translates between Bambara and French in the chat.
                    </p>
                  </div>
                  <div className="settings-card-body">
                    <label className={`settings-radio ${platformSettings.translation_engine === 'gpt' ? 'active' : ''}`}>
                      <input
                        type="radio"
                        name="translation_engine"
                        value="gpt"
                        checked={platformSettings.translation_engine === 'gpt'}
                        onChange={() => saveSettings('translation_engine', 'gpt')}
                        disabled={settingsSaving}
                      />
                      <div className="settings-radio-content">
                        <strong>GPT-4o-mini</strong>
                        <span className="settings-radio-desc">
                          Uses OpenAI API. Better conversational quality, no local model needed.
                          Cost: ~$0.0001 per message (negligible).
                        </span>
                      </div>
                    </label>
                    <label className={`settings-radio ${platformSettings.translation_engine === 'nllb' ? 'active' : ''}`}>
                      <input
                        type="radio"
                        name="translation_engine"
                        value="nllb"
                        checked={platformSettings.translation_engine === 'nllb'}
                        onChange={() => saveSettings('translation_engine', 'nllb')}
                        disabled={settingsSaving}
                      />
                      <div className="settings-radio-content">
                        <strong>NLLB (Local)</strong>
                        <span className="settings-radio-desc">
                          Meta NLLB model running locally. Free, but requires ~3GB RAM and model download.
                          Purpose-built for low-resource languages.
                        </span>
                      </div>
                    </label>
                    <p className="settings-hint">
                      {settingsSaving ? 'Saving...' : 'Changes apply immediately to new messages. If the chosen engine fails, the other is used as fallback.'}
                    </p>
                  </div>
                </div>

                {/* ── SMTP Test ── */}
                <div className="settings-card">
                  <div className="settings-card-header">
                    <h4>Email (SMTP)</h4>
                    <p className="settings-hint" style={{ marginTop: 4 }}>
                      Send a test email to verify SMTP is configured correctly.
                    </p>
                  </div>
                  <div className="settings-card-body">
                    <button
                      className="admin-action-btn"
                      onClick={async () => {
                        try {
                          const res = await adminAPI.testEmail();
                          if (res.success) {
                            alert(`✓ Test email sent to ${res.diagnostic?.to || 'your address'}.\nCheck your inbox (and spam).`);
                          } else {
                            alert(
                              `✗ Email failed!\n\nError: ${res.error}\n\n` +
                              `SMTP Host: ${res.diagnostic?.smtp_host}:${res.diagnostic?.smtp_port}\n` +
                              `SMTP User: ${res.diagnostic?.smtp_user}\n` +
                              `SMTP From: ${res.diagnostic?.smtp_from}\n` +
                              `Password set: ${res.diagnostic?.smtp_password_set}`
                            );
                          }
                        } catch (err) {
                          alert(`Request failed: ${err.message}`);
                        }
                      }}
                    >
                      <Mail size={14} /> Send Test Email
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <p className="admin-hint">Loading settings...</p>
            )}
          </div>
        )}

        {/* ── Sessions Tab ── */}
        {tab === 'sessions' && (
          <div className="admin-section">
            <div className="admin-toolbar">
              <h3><Monitor size={18} /> Active Sessions</h3>
              <button className="admin-action-btn" onClick={loadSessions}><RefreshCw size={14} /> Refresh</button>
            </div>

            {tokenConfig && (
              <div className="admin-token-config">
                <h4>Token Duration Policy</h4>
                <div className="token-config-grid">
                  <div className="token-config-card">
                    <span className="token-config-label">Staff Access Token</span>
                    <span className="token-config-value">{tokenConfig.staff.access_hours}h</span>
                  </div>
                  <div className="token-config-card">
                    <span className="token-config-label">Staff Refresh Token</span>
                    <span className="token-config-value">{tokenConfig.staff.refresh_days}d</span>
                  </div>
                  <div className="token-config-card">
                    <span className="token-config-label">User Access Token</span>
                    <span className="token-config-value">{tokenConfig.user.access_hours}h</span>
                  </div>
                  <div className="token-config-card">
                    <span className="token-config-label">User Refresh Token</span>
                    <span className="token-config-value">{tokenConfig.user.refresh_days}d</span>
                  </div>
                </div>
              </div>
            )}

            {sessions.length === 0 ? (
              <p className="admin-hint">No active sessions tracked.</p>
            ) : (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Active Sessions</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s) => (
                    <tr key={s.user_id}>
                      <td>{s.name}</td>
                      <td>{s.email}</td>
                      <td>
                        <span className={`admin-role-badge role-${s.role}`}>
                          {s.is_staff ? <Shield size={12} /> : null} {s.role}
                        </span>
                      </td>
                      <td>
                        <span className="session-count">{s.active_sessions}</span>
                      </td>
                      <td>{s.last_login ? new Date(s.last_login).toLocaleString() : '—'}</td>
                      <td>
                        <button
                          className="admin-action-btn danger"
                          onClick={() => forceLogoutUser(s.user_id, s.email)}
                          title="Force-logout all sessions"
                        >
                          <LogOut size={14} /> Force Logout
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
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
