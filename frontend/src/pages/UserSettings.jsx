import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';
import {
  User, Shield, Download, Trash2, MessageSquare, AlertTriangle,
} from 'lucide-react';
import Button from '../components/ui/Button';
import './UserSettings.css';

export default function UserSettings() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [deletePassword, setDeletePassword] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState('');
  const [success, setSuccess] = useState('');

  if (!user) { navigate('/login'); return null; }

  const handleExport = async () => {
    setLoading('export');
    setError('');
    try {
      const blob = await authAPI.exportData();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ekodi-data-export.zip';
      a.click();
      URL.revokeObjectURL(url);
      setSuccess(t('settings.export_success'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading('');
    }
  };

  const handleDeleteAllChats = async () => {
    if (!confirm(t('settings.delete_chats_confirm'))) return;
    setLoading('chats');
    setError('');
    try {
      const res = await authAPI.deleteAllConversations();
      setSuccess(res.message || t('settings.chats_deleted'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading('');
    }
  };

  const handleDeleteAccount = async () => {
    setError('');
    setLoading('delete');
    try {
      await authAPI.deleteAccount(deletePassword);
      await logout();
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading('');
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-container">
        <h1><User size={24} /> {t('settings.title')}</h1>

        {error && <div className="settings-error">{error}</div>}
        {success && <div className="settings-success">{success}</div>}

        {/* Profile Info */}
        <div className="settings-section">
          <h2>{t('settings.profile')}</h2>
          <div className="settings-info">
            <div className="settings-row">
              <span className="settings-label">{t('auth.name')}</span>
              <span>{user.name}</span>
            </div>
            <div className="settings-row">
              <span className="settings-label">{t('auth.email')}</span>
              <span>{user.email}</span>
            </div>
            <div className="settings-row">
              <span className="settings-label">{t('settings.tier')}</span>
              <span className="tier-badge">{user.tier || 'free'}</span>
            </div>
            <div className="settings-row">
              <span className="settings-label">{t('settings.email_status')}</span>
              <span className={user.email_verified ? 'text-green' : 'text-yellow'}>
                {user.email_verified ? t('settings.verified') : t('settings.not_verified')}
              </span>
            </div>
          </div>
        </div>

        {/* Data Actions */}
        <div className="settings-section">
          <h2><Shield size={18} /> {t('settings.data_privacy')}</h2>

          <div className="settings-actions">
            <Button
              variant="secondary"
              onClick={handleExport}
              loading={loading === 'export'}
              className="settings-btn"
            >
              <Download size={16} /> {t('settings.export_data')}
            </Button>

            <Button
              variant="secondary"
              onClick={handleDeleteAllChats}
              loading={loading === 'chats'}
              className="settings-btn"
            >
              <MessageSquare size={16} /> {t('settings.delete_all_chats')}
            </Button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="settings-section danger">
          <h2><AlertTriangle size={18} /> {t('settings.danger_zone')}</h2>
          <p className="settings-danger-desc">{t('settings.delete_account_desc')}</p>

          {!showDeleteConfirm ? (
            <Button
              variant="danger"
              onClick={() => setShowDeleteConfirm(true)}
              className="settings-btn"
            >
              <Trash2 size={16} /> {t('settings.delete_account')}
            </Button>
          ) : (
            <div className="settings-delete-confirm">
              <p>{t('settings.delete_confirm_text')}</p>
              <input
                type="password"
                placeholder={t('auth.password')}
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                className="settings-input"
              />
              <div className="settings-delete-actions">
                <Button
                  variant="danger"
                  onClick={handleDeleteAccount}
                  loading={loading === 'delete'}
                  disabled={!deletePassword}
                >
                  {t('settings.confirm_delete')}
                </Button>
                <Button variant="secondary" onClick={() => { setShowDeleteConfirm(false); setDeletePassword(''); }}>
                  {t('common.cancel')}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
