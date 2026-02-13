import { useTranslation } from 'react-i18next';
import './LanguageSwitcher.css';

const LANGS = [
  { code: 'fr', label: 'FR', flag: '\u{1F1EB}\u{1F1F7}' },
  { code: 'bm', label: 'BM', flag: '\u{1F1F2}\u{1F1F1}' },
  { code: 'en', label: 'EN', flag: '\u{1F1EC}\u{1F1E7}' },
];

export default function LanguageSwitcher({ className = '' }) {
  const { i18n } = useTranslation();

  return (
    <div className={`lang-switcher ${className}`}>
      {LANGS.map((l) => (
        <button
          key={l.code}
          className={`lang-btn ${i18n.language === l.code ? 'active' : ''}`}
          onClick={() => i18n.changeLanguage(l.code)}
          title={l.label}
        >
          <span className="lang-flag">{l.flag}</span>
          <span className="lang-code">{l.label}</span>
        </button>
      ))}
    </div>
  );
}
