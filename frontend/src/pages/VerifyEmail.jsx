import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { authAPI } from '../services/api';
import './Auth.css';

export default function VerifyEmail() {
  const { t } = useTranslation();
  const { token } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading'); // loading | success | error
  const [message, setMessage] = useState('');
  const [countdown, setCountdown] = useState(5);

  useEffect(() => {
    authAPI.verify(token)
      .then(() => {
        setStatus('success');
        setMessage(t('auth.verify_success'));
      })
      .catch((err) => {
        setStatus('error');
        setMessage(err.message || t('auth.verify_error'));
      });
  }, [token, t]);

  // Auto-redirect to login after successful verification
  useEffect(() => {
    if (status !== 'success') return;
    const timer = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearInterval(timer);
          navigate('/login');
          return 0;
        }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [status, navigate]);

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          {status === 'loading' && (
            <>
              <Loader2 size={48} className="auth-spinner" />
              <h1>{t('auth.verifying')}</h1>
            </>
          )}
          {status === 'success' && (
            <>
              <CheckCircle size={48} className="auth-success-icon" />
              <h1>{t('auth.verify_success_title')}</h1>
              <p>{message}</p>
              <p className="auth-redirect-hint">
                {t('auth.redirect_to_login') || 'Redirecting to login'} ({countdown}s)
              </p>
            </>
          )}
          {status === 'error' && (
            <>
              <XCircle size={48} className="auth-error-icon" />
              <h1>{t('auth.verify_error_title')}</h1>
              <p>{message}</p>
            </>
          )}
        </div>
        <Link to="/login" className="auth-back-link">
          {t('auth.back_to_login')}
        </Link>
      </div>
    </div>
  );
}
