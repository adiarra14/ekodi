import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Wallet, Cpu, Rocket, Megaphone, Send, ArrowLeft, CheckCircle } from 'lucide-react';
import Button from '../components/ui/Button';
import './PartnerForm.css';

const PARTNER_TYPES = [
  { key: 'financial', icon: Wallet, color: 'orange' },
  { key: 'technical', icon: Cpu, color: 'violet' },
  { key: 'expansion', icon: Rocket, color: 'teal' },
  { key: 'promotion', icon: Megaphone, color: 'blue' },
];

export default function PartnerForm() {
  const { t } = useTranslation();
  const [form, setForm] = useState({ name: '', email: '', org: '', type: '', message: '' });
  const [sent, setSent] = useState(false);

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();
    const typeLabel = form.type ? t(`partner_form.type_${form.type}`) : '';
    const subject = `[ekodi partenariat] ${typeLabel} - ${form.org || form.name}`;
    const body = [
      `Nom: ${form.name}`,
      `Email: ${form.email}`,
      form.org ? `Organisation: ${form.org}` : '',
      `Type de partenariat: ${typeLabel}`,
      '',
      form.message,
    ].filter(Boolean).join('\n');

    window.location.href = `mailto:support@ekodi.ai?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    setSent(true);
  };

  if (sent) {
    return (
      <div className="pf-page">
        <div className="pf-card pf-success">
          <CheckCircle size={40} className="pf-success-icon" />
          <h2>{t('partner_form.success_title')}</h2>
          <p>{t('partner_form.success_desc')}</p>
          <Link to="/"><Button variant="primary" icon={<ArrowLeft size={16} />}>{t('partner_form.back_home')}</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="pf-page">
      <div className="pf-card">
        <Link to="/" className="pf-back"><ArrowLeft size={14} /> {t('partner_form.back_home')}</Link>
        <h2>{t('partner_form.title')}</h2>
        <p className="pf-sub">{t('partner_form.subtitle')}</p>

        <form onSubmit={handleSubmit} className="pf-form">
          <div className="pf-field">
            <label>{t('partner_form.name')} *</label>
            <input type="text" value={form.name} onChange={update('name')} required placeholder={t('partner_form.name_ph')} />
          </div>

          <div className="pf-field">
            <label>{t('partner_form.email')} *</label>
            <input type="email" value={form.email} onChange={update('email')} required placeholder={t('partner_form.email_ph')} />
          </div>

          <div className="pf-field">
            <label>{t('partner_form.org')}</label>
            <input type="text" value={form.org} onChange={update('org')} placeholder={t('partner_form.org_ph')} />
          </div>

          <div className="pf-field">
            <label>{t('partner_form.type')} *</label>
            <div className="pf-types">
              {PARTNER_TYPES.map(({ key, icon: Icon, color }) => (
                <button
                  key={key}
                  type="button"
                  className={`pf-type-btn ${color} ${form.type === key ? 'active' : ''}`}
                  onClick={() => setForm({ ...form, type: key })}
                >
                  <Icon size={16} />
                  <span>{t(`partner_form.type_${key}`)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="pf-field">
            <label>{t('partner_form.message')} *</label>
            <textarea value={form.message} onChange={update('message')} required rows={4} placeholder={t('partner_form.message_ph')} />
          </div>

          <Button type="submit" variant="primary" icon={<Send size={16} />} disabled={!form.name || !form.email || !form.type || !form.message}>
            {t('partner_form.submit')}
          </Button>
        </form>
      </div>
    </div>
  );
}
