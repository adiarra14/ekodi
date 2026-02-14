import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Lock, CheckCircle, ArrowLeft } from 'lucide-react';
import { authAPI } from '../services/api';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import './Auth.css';

export default function ResetPassword() {
  const { t } = useTranslation();
  const { token } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError(t('auth.passwords_mismatch'));
      return;
    }
    setLoading(true);
    try {
      await authAPI.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-header">
            <CheckCircle size={48} className="auth-success-icon" />
            <h1>{t('auth.reset_success_title')}</h1>
            <p>{t('auth.reset_success_desc')}</p>
          </div>
          <Link to="/login" className="auth-back-link">
            <ArrowLeft size={16} /> {t('auth.back_to_login')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <h1>{t('auth.reset_title')}</h1>
          <p>{t('auth.reset_subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}

          <Input
            label={t('auth.password')}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            icon={<Lock size={18} />}
            placeholder="••••••••"
            minLength={6}
            required
          />

          <Input
            label={t('auth.confirm_password')}
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            icon={<Lock size={18} />}
            placeholder="••••••••"
            minLength={6}
            required
          />

          <Button type="submit" variant="primary" size="lg" loading={loading} className="auth-submit">
            {t('auth.reset_btn')}
          </Button>
        </form>

        <Link to="/login" className="auth-back-link">
          <ArrowLeft size={16} /> {t('auth.back_to_login')}
        </Link>
      </div>
    </div>
  );
}
