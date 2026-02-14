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

  if (location.pathname === '/chat') return null;

  const isHome = location.pathname === '/';

  const scrollTo = (id) => {
    setMenuOpen(false);
    if (!isHome) {
      window.location.href = `/#${id}`;
      return;
    }
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

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
          {/* Section anchors (visible on landing or navigate to landing) */}
          <button className="nav-link nav-section" onClick={() => scrollTo('features')}>
            {t('nav.section_ekodi')}
          </button>
          <button className="nav-link nav-section" onClick={() => scrollTo('impact')}>
            {t('nav.section_impact')}
          </button>
          <button className="nav-link nav-section" onClick={() => scrollTo('pricing')}>
            {t('nav.section_pricing')}
          </button>
          <button className="nav-link nav-section" onClick={() => scrollTo('partners')}>
            {t('nav.section_partners')}
          </button>

          <span className="nav-divider" />

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
