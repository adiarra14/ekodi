import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Cookie, X } from 'lucide-react';
import './ConsentBanner.css';

export default function ConsentBanner() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('ekodi_consent');
    if (!consent) {
      // Delay slightly so it doesn't show during splash screen
      const timer = setTimeout(() => setVisible(true), 4000);
      return () => clearTimeout(timer);
    }
  }, []);

  const accept = () => {
    localStorage.setItem('ekodi_consent', 'accepted');
    setVisible(false);
  };

  const reject = () => {
    localStorage.setItem('ekodi_consent', 'rejected');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="consent-banner">
      <div className="consent-content">
        <Cookie size={20} className="consent-icon" />
        <p>
          {t('consent.message')}{' '}
          <Link to="/privacy">{t('consent.learn_more')}</Link>
        </p>
      </div>
      <div className="consent-actions">
        <button className="consent-accept" onClick={accept}>{t('consent.accept')}</button>
        <button className="consent-reject" onClick={reject}>{t('consent.reject')}</button>
      </div>
      <button className="consent-close" onClick={reject} aria-label="Close">
        <X size={16} />
      </button>
    </div>
  );
}
