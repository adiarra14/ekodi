import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { adminAPI } from '../services/api';
import {
  Users, MessageSquare, MessageCircle, Key, Activity,
  ThumbsUp, ThumbsDown, Shield,
} from 'lucide-react';
import './Admin.css';

export default function Admin() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [feedbackList, setFeedbackList] = useState([]);
  const [tab, setTab] = useState('stats');

  useEffect(() => {
    if (!user || user.role !== 'admin') { navigate('/'); return; }
    loadData();
  }, [user, navigate]);

  const loadData = async () => {
    try {
      const [s, u, f] = await Promise.all([
        adminAPI.stats(),
        adminAPI.users(),
        adminAPI.feedback(),
      ]);
      setStats(s);
      setUsers(u);
      setFeedbackList(f);
    } catch { /* ignore */ }
  };

  if (!stats) return <div className="admin-loading">{t('common.loading')}</div>;

  return (
    <div className="admin-page">
      <div className="admin-container">
        <h1><Shield size={28} /> {t('admin.title')}</h1>

        {/* Stats Cards */}
        <div className="admin-stats">
          <div className="admin-stat">
            <Users size={24} className="stat-icon" />
            <span className="stat-val">{stats.users}</span>
            <span className="stat-lbl">{t('admin.users')}</span>
          </div>
          <div className="admin-stat">
            <MessageSquare size={24} className="stat-icon" />
            <span className="stat-val">{stats.conversations}</span>
            <span className="stat-lbl">{t('admin.conversations')}</span>
          </div>
          <div className="admin-stat">
            <MessageCircle size={24} className="stat-icon" />
            <span className="stat-val">{stats.messages}</span>
            <span className="stat-lbl">{t('admin.messages')}</span>
          </div>
          <div className="admin-stat">
            <Key size={24} className="stat-icon" />
            <span className="stat-val">{stats.api_keys}</span>
            <span className="stat-lbl">{t('admin.api_keys')}</span>
          </div>
          <div className="admin-stat">
            <Activity size={24} className="stat-icon" />
            <span className="stat-val">{stats.api_usage}</span>
            <span className="stat-lbl">{t('admin.api_usage')}</span>
          </div>
          <div className="admin-stat">
            <ThumbsUp size={24} className="stat-icon positive" />
            <span className="stat-val">{stats.feedback?.positive || 0}</span>
            <span className="stat-lbl">{t('admin.positive')}</span>
          </div>
          <div className="admin-stat">
            <ThumbsDown size={24} className="stat-icon negative" />
            <span className="stat-val">{stats.feedback?.negative || 0}</span>
            <span className="stat-lbl">{t('admin.negative')}</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="admin-tabs">
          <button className={tab === 'stats' ? 'active' : ''} onClick={() => setTab('stats')}>
            {t('admin.users')}
          </button>
          <button className={tab === 'feedback' ? 'active' : ''} onClick={() => setTab('feedback')}>
            {t('admin.feedback')}
          </button>
        </div>

        {/* Users Table */}
        {tab === 'stats' && (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t('auth.name')}</th>
                  <th>{t('auth.email')}</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Joined</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name}</td>
                    <td>{u.email}</td>
                    <td><span className={`role-badge ${u.role}`}>{u.role}</span></td>
                    <td>{u.is_active ? 'Active' : 'Inactive'}</td>
                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Feedback Table */}
        {tab === 'feedback' && (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Rating</th>
                  <th>Comment</th>
                  <th>User</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {feedbackList.map((f) => (
                  <tr key={f.id}>
                    <td>
                      {f.rating === 1 ? <ThumbsUp size={16} className="positive" /> : <ThumbsDown size={16} className="negative" />}
                    </td>
                    <td>{f.comment || '—'}</td>
                    <td>{f.user_id.slice(0, 8)}...</td>
                    <td>{new Date(f.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
