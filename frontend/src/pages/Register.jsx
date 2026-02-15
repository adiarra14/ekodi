import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';
import { Mail, Lock, User, CheckCircle, RefreshCw } from 'lucide-react';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import LanguageSwitcher from '../components/ui/LanguageSwitcher';
import './Auth.css';

const RECAPTCHA_SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY || '';

export default function Register() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [resending, setResending] = useState(false);
  const captchaRef = useRef(null);
  const captchaWidgetRef = useRef(null);

  // Load reCAPTCHA script
  useEffect(() => {
    if (!RECAPTCHA_SITE_KEY) return;
    if (document.getElementById('recaptcha-script')) return;

    const script = document.createElement('script');
    script.id = 'recaptcha-script';
    script.src = 'https://www.google.com/recaptcha/api.js?render=explicit';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.grecaptcha && captchaRef.current && captchaWidgetRef.current === null) {
        window.grecaptcha.ready(() => {
          captchaWidgetRef.current = window.grecaptcha.render(captchaRef.current, {
            sitekey: RECAPTCHA_SITE_KEY,
            theme: 'dark',
          });
        });
      }
    };
    document.head.appendChild(script);
  }, []);

  // Render captcha when ref is ready (if script loaded before component)
  useEffect(() => {
    if (!RECAPTCHA_SITE_KEY) return;
    if (window.grecaptcha && captchaRef.current && captchaWidgetRef.current === null) {
      try {
        window.grecaptcha.ready(() => {
          captchaWidgetRef.current = window.grecaptcha.render(captchaRef.current, {
            sitekey: RECAPTCHA_SITE_KEY,
            theme: 'dark',
          });
        });
      } catch { /* already rendered */ }
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!consent) {
      setError(t('auth.consent_required'));
      return;
    }

    // Get CAPTCHA token
    let captchaToken = null;
    if (RECAPTCHA_SITE_KEY && window.grecaptcha) {
      captchaToken = window.grecaptcha.getResponse(captchaWidgetRef.current);
      if (!captchaToken) {
        setError(t('auth.captcha_required') || 'Please complete the CAPTCHA verification.');
        return;
      }
    }

    setLoading(true);
    try {
      await register(email, name, password, consent, captchaToken);
      setRegistered(true); // Show "check your email" screen
    } catch (err) {
      setError(err.message);
      // Reset CAPTCHA on error
      if (RECAPTCHA_SITE_KEY && window.grecaptcha) {
        try { window.grecaptcha.reset(captchaWidgetRef.current); } catch { /* ignore */ }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await authAPI.resendVerification();
      alert(t('auth.verify_resent') || 'Verification email sent!');
    } catch {
      alert(t('auth.verify_resend_error') || 'Failed to send email.');
    } finally {
      setResending(false);
    }
  };

  // ── Post-registration: "Check your email" screen ──
  if (registered) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-header">
            <Mail size={48} className="auth-verify-icon" />
            <h1>{t('auth.check_email_title') || 'Check Your Email'}</h1>
            <p>{t('auth.check_email_desc') || 'We sent a verification link to your email. Click the link to activate your account.'}</p>
            <p className="auth-verify-email">{email}</p>
          </div>
          <div className="auth-verify-actions">
            <Button
              variant="secondary"
              onClick={handleResend}
              loading={resending}
              className="auth-submit"
            >
              <RefreshCw size={16} /> {t('auth.resend_verification') || 'Resend Verification Email'}
            </Button>
            <Link to="/login" className="auth-back-link">
              {t('auth.back_to_login') || 'Back to Login'}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Registration form ──
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
          <h1>{t('auth.register_title')}</h1>
          <p>{t('auth.register_subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}

          <Input
            label={t('auth.name')}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            icon={<User size={18} />}
            placeholder="Moussa Keita"
            required
          />

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
            minLength={6}
            required
          />

          <label className="auth-consent">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            <span>
              {t('auth.consent_text')}{' '}
              <Link to="/privacy" target="_blank">{t('auth.privacy_link')}</Link>
            </span>
          </label>

          {/* reCAPTCHA widget */}
          {RECAPTCHA_SITE_KEY && (
            <div className="auth-captcha">
              <div ref={captchaRef} />
            </div>
          )}

          <Button type="submit" variant="primary" size="lg" loading={loading} className="auth-submit">
            {t('auth.register_btn')}
          </Button>
        </form>

        <p className="auth-switch">
          {t('auth.has_account')}{' '}
          <Link to="/login">{t('nav.login')}</Link>
        </p>

        <LanguageSwitcher className="auth-lang" />
      </div>
    </div>
  );
}
