import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mail, Lock, User } from 'lucide-react';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import LanguageSwitcher from '../components/ui/LanguageSwitcher';
import './Auth.css';

export default function Register() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(email, name, password);
      navigate('/chat');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <Link to="/" className="auth-logo">
            <img src="/logo-ekodi-std.png" alt="Ekodi" />
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
