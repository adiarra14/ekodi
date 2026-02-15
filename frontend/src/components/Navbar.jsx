import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from './ui/LanguageSwitcher';
import { Menu, X } from 'lucide-react';
import { useState } from 'react';
import './Navbar.css';

/**
 * Public website navbar – only for the landing page and auth pages.
 * Does NOT appear inside the app (chat, admin, settings, api-keys).
 */
export default function Navbar() {
  const { t } = useTranslation();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

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
          {/* Landing page sections */}
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

          <Link to="/login" className="nav-link" onClick={() => setMenuOpen(false)}>
            {t('nav.login')}
          </Link>
          <Link to="/register" className="nav-link nav-cta" onClick={() => setMenuOpen(false)}>
            {t('nav.register')}
          </Link>

          <LanguageSwitcher />
        </div>
      </div>
    </nav>
  );
}
