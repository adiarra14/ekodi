import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { authAPI } from '../services/api';
import './Auth.css';

export default function VerifyEmail() {
  const { t } = useTranslation();
  const { token } = useParams();
  const [status, setStatus] = useState('loading'); // loading | success | error
  const [message, setMessage] = useState('');

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
