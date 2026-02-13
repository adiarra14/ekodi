import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import LanguageSwitcher from './ui/LanguageSwitcher';
import { MessageSquare, Key, Shield, LogOut, Menu, X } from 'lucide-react';
import { useState } from 'react';
import './Navbar.css';

export default function Navbar() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  // Hide navbar on chat page (it has its own layout)
  if (location.pathname === '/chat') return null;

  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/" className="nav-logo">
          <img src="/logo-ekodi-std.png" alt="Ekodi" className="nav-logo-img" />
          <span className="nav-logo-text">ekodi</span>
          <span className="nav-logo-ai">.ai</span>
        </Link>

        <button className="nav-menu-toggle" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        <div className={`nav-links ${menuOpen ? 'open' : ''}`}>
          <Link to="/" className="nav-link" onClick={() => setMenuOpen(false)}>
            {t('nav.home')}
          </Link>

          {user ? (
            <>
              <Link to="/chat" className="nav-link" onClick={() => setMenuOpen(false)}>
                <MessageSquare size={16} /> {t('nav.chat')}
              </Link>
              <Link to="/api-keys" className="nav-link" onClick={() => setMenuOpen(false)}>
                <Key size={16} /> {t('nav.api')}
              </Link>
              {user.role === 'admin' && (
                <Link to="/admin" className="nav-link" onClick={() => setMenuOpen(false)}>
                  <Shield size={16} /> {t('nav.admin')}
                </Link>
              )}
              <button className="nav-link nav-logout" onClick={() => { logout(); setMenuOpen(false); }}>
                <LogOut size={16} /> {t('nav.logout')}
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="nav-link" onClick={() => setMenuOpen(false)}>
                {t('nav.login')}
              </Link>
              <Link to="/register" className="nav-link nav-cta" onClick={() => setMenuOpen(false)}>
                {t('nav.register')}
              </Link>
            </>
          )}

          <LanguageSwitcher />
        </div>
      </div>
    </nav>
  );
}
