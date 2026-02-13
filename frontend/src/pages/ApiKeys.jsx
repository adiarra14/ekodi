import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiKeysAPI } from '../services/api';
import { Key, Plus, Copy, Trash2, CheckCircle } from 'lucide-react';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import './ApiKeys.css';

export default function ApiKeys() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [keys, setKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKey, setNewKey] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!user) { navigate('/login'); return; }
    loadKeys();
  }, [user, navigate]);

  const loadKeys = async () => {
    try {
      const data = await apiKeysAPI.list();
      setKeys(data);
    } catch { /* ignore */ }
  };

  const createKey = async () => {
    if (!newKeyName.trim()) return;
    setLoading(true);
    try {
      const data = await apiKeysAPI.create(newKeyName.trim());
      setNewKey(data.key);
      setNewKeyName('');
      loadKeys();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const revokeKey = async (id) => {
    try {
      await apiKeysAPI.revoke(id);
      loadKeys();
    } catch { /* ignore */ }
  };

  const copyKey = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="apikeys-page">
      <div className="apikeys-container">
        <h1><Key size={28} /> {t('api_page.title')}</h1>

        {/* Create Key */}
        <div className="apikeys-create">
          <Input
            placeholder={t('api_page.key_name')}
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && createKey()}
          />
          <Button onClick={createKey} loading={loading} icon={<Plus size={16} />}>
            {t('api_page.create_key')}
          </Button>
        </div>

        {/* New key display */}
        {newKey && (
          <div className="apikeys-new-key">
            <p>Your new API key (copy it now, it won't be shown again):</p>
            <div className="new-key-row">
              <code>{newKey}</code>
              <button onClick={copyKey}>
                {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
              </button>
            </div>
          </div>
        )}

        {/* Keys list */}
        <div className="apikeys-list">
          {keys.length === 0 && <p className="apikeys-empty">{t('api_page.no_keys')}</p>}
          {keys.map((k) => (
            <div key={k.id} className={`apikey-row ${!k.active ? 'revoked' : ''}`}>
              <div className="apikey-info">
                <span className="apikey-name">{k.name}</span>
                <code className="apikey-prefix">{k.key_prefix}</code>
              </div>
              <div className="apikey-meta">
                <span className="apikey-usage">{t('api_page.usage')}: {k.usage_count}</span>
                {k.active ? (
                  <button className="apikey-revoke" onClick={() => revokeKey(k.id)}>
                    <Trash2 size={14} /> {t('api_page.revoke')}
                  </button>
                ) : (
                  <span className="apikey-status-revoked">Revoked</span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* API Docs */}
        <div className="apikeys-docs">
          <h2>{t('api_page.docs_title')}</h2>
          <div className="doc-section">
            <h3>POST /api/v1/tts</h3>
            <pre>{`curl -X POST https://api.ekodi.ai/api/v1/tts \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "I ni ce"}'`}</pre>
          </div>
          <div className="doc-section">
            <h3>POST /api/v1/translate</h3>
            <pre>{`curl -X POST https://api.ekodi.ai/api/v1/translate \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Bonjour", "source": "fr", "target": "bm"}'`}</pre>
          </div>
          <div className="doc-section">
            <h3>POST /api/v1/chat</h3>
            <pre>{`curl -X POST https://api.ekodi.ai/api/v1/chat \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Comment tu vas?"}'`}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}
