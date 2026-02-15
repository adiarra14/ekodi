import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';
import { Mail, Lock, RefreshCw } from 'lucide-react';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import LanguageSwitcher from '../components/ui/LanguageSwitcher';
import './Auth.css';

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resending, setResending] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setNeedsVerification(false);
    setLoading(true);
    try {
      const u = await login(email, password);
      // Staff → admin dashboard, regular users → chat
      const staffRoles = ['superadmin','admin','support','marketing','finance','moderator','developer'];
      navigate(staffRoles.includes(u.role) ? '/admin' : '/chat');
    } catch (err) {
      const msg = err.message || '';
      // Detect email verification error
      if (msg.toLowerCase().includes('verify your email') || msg.toLowerCase().includes('verify')) {
        setNeedsVerification(true);
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await authAPI.resendVerificationPublic(email);
      alert(t('auth.verify_resent') || 'Verification email sent! Check your inbox.');
    } catch {
      alert(t('auth.verify_resend_error') || 'Failed to send email.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <Link to="/" className="auth-logo-anim">
            <div className="auth-logo-ring">
              <span className="auth-ring r1" />
              <span className="auth-ring r2" />
              <img src="/logo-ekodi-std.png" alt="Ekodi" className="auth-logo-img" />
            </div>
            <div className="auth-logo-text">
              <span className="auth-txt-e">e</span>
              <span className="auth-txt-k">k</span>
              <span className="auth-txt-o">o</span>
              <span className="auth-txt-d">d</span>
              <span className="auth-txt-i">i</span>
              <span className="auth-txt-dot">.ai</span>
            </div>
          </Link>
          <h1>{t('auth.login_title')}</h1>
          <p>{t('auth.login_subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="auth-error">
              {error}
              {needsVerification && (
                <button
                  type="button"
                  className="auth-error-resend"
                  onClick={handleResend}
                  disabled={resending}
                >
                  <RefreshCw size={14} className={resending ? 'spinning' : ''} />
                  {resending
                    ? (t('common.sending') || 'Sending...')
                    : (t('auth.resend_verification') || 'Resend Verification Email')
                  }
                </button>
              )}
            </div>
          )}

          <Input
            label={t('auth.email')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            icon={<Mail size={18} />}
            placeholder="you@example.com"
            required
          />

          <Input
            label={t('auth.password')}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            icon={<Lock size={18} />}
            placeholder="••••••••"
            required
          />

          <div className="auth-forgot">
            <Link to="/forgot-password">{t('auth.forgot_password')}</Link>
          </div>

          <Button type="submit" variant="primary" size="lg" loading={loading} className="auth-submit">
            {t('auth.login_btn')}
          </Button>
        </form>

        <p className="auth-switch">
          {t('auth.no_account')}{' '}
          <Link to="/register">{t('nav.register')}</Link>
        </p>

        <LanguageSwitcher className="auth-lang" />
      </div>
    </div>
  );
}
