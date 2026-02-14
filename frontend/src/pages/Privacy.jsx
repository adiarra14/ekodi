import { useTranslation } from 'react-i18next';
import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import './Privacy.css';

export default function Privacy() {
  const { t } = useTranslation();

  return (
    <div className="privacy-page">
      <div className="privacy-container">
        <Link to="/" className="privacy-back"><ArrowLeft size={16} /> {t('common.back')}</Link>

        <h1>{t('privacy.title')}</h1>
        <p className="privacy-updated">{t('privacy.last_updated')}</p>

        <section>
          <h2>{t('privacy.intro_title')}</h2>
          <p>{t('privacy.intro_text')}</p>
        </section>

        <section>
          <h2>{t('privacy.data_collected_title')}</h2>
          <ul>
            <li>{t('privacy.data_email')}</li>
            <li>{t('privacy.data_name')}</li>
            <li>{t('privacy.data_chats')}</li>
            <li>{t('privacy.data_voice')}</li>
            <li>{t('privacy.data_usage')}</li>
          </ul>
        </section>

        <section>
          <h2>{t('privacy.why_title')}</h2>
          <ul>
            <li>{t('privacy.why_service')}</li>
            <li>{t('privacy.why_improve')}</li>
            <li>{t('privacy.why_communicate')}</li>
          </ul>
        </section>

        <section>
          <h2>{t('privacy.retention_title')}</h2>
          <p>{t('privacy.retention_text')}</p>
        </section>

        <section>
          <h2>{t('privacy.rights_title')}</h2>
          <ul>
            <li>{t('privacy.rights_access')}</li>
            <li>{t('privacy.rights_export')}</li>
            <li>{t('privacy.rights_delete')}</li>
            <li>{t('privacy.rights_withdraw')}</li>
          </ul>
        </section>

        <section>
          <h2>{t('privacy.sharing_title')}</h2>
          <p>{t('privacy.sharing_text')}</p>
        </section>

        <section>
          <h2>{t('privacy.contact_title')}</h2>
          <p>{t('privacy.contact_text')}</p>
        </section>
      </div>
    </div>
  );
}
