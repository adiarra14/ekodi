import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react';
import { authAPI } from '../services/api';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import './Auth.css';

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await authAPI.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-header">
            <CheckCircle size={48} className="auth-success-icon" />
            <h1>{t('auth.reset_sent_title')}</h1>
            <p>{t('auth.reset_sent_desc')}</p>
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
          <h1>{t('auth.forgot_title')}</h1>
          <p>{t('auth.forgot_subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}

          <Input
            label={t('auth.email')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            icon={<Mail size={18} />}
            placeholder="you@example.com"
            required
          />

          <Button type="submit" variant="primary" size="lg" loading={loading} className="auth-submit">
            {t('auth.send_reset_link')}
          </Button>
        </form>

        <Link to="/login" className="auth-back-link">
          <ArrowLeft size={16} /> {t('auth.back_to_login')}
        </Link>
      </div>
    </div>
  );
}
