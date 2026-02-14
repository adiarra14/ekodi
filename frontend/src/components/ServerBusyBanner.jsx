import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, X, RefreshCw } from 'lucide-react';
import './ServerBusyBanner.css';

export default function ServerBusyBanner() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    const handleBusy = (e) => {
      const { retryAfter } = e.detail;
      setVisible(true);
      setCountdown(retryAfter || 10);
    };

    window.addEventListener('ekodi-server-busy', handleBusy);
    return () => window.removeEventListener('ekodi-server-busy', handleBusy);
  }, []);

  // Countdown timer
  useEffect(() => {
    if (countdown > 0 && visible) {
      timerRef.current = setTimeout(() => setCountdown((c) => c - 1), 1000);
    }
    if (countdown <= 0 && visible) {
      // Auto-hide after countdown
      const hideTimer = setTimeout(() => setVisible(false), 2000);
      return () => clearTimeout(hideTimer);
    }
    return () => clearTimeout(timerRef.current);
  }, [countdown, visible]);

  const dismiss = () => {
    setVisible(false);
    setCountdown(0);
  };

  if (!visible) return null;

  return (
    <div className="server-busy-banner" role="alert">
      <div className="server-busy-content">
        <AlertTriangle size={20} className="server-busy-icon" />
        <div className="server-busy-text">
          <strong>{t('server.busy_title') || 'Server is busy'}</strong>
          <p>{t('server.busy_message') || 'Too many requests right now. Please wait a moment and try again.'}</p>
          {countdown > 0 && (
            <span className="server-busy-countdown">
              <RefreshCw size={14} className="spin" />
              {t('server.retry_in') || 'Retry in'} {countdown}s
            </span>
          )}
        </div>
        <button className="server-busy-close" onClick={dismiss} aria-label="Close">
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
