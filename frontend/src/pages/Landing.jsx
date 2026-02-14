import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  Mic, Languages, Volume2, Code, ArrowRight, Sparkles,
  Sprout, ExternalLink, ThumbsUp, ThumbsDown, Check, Lock,
  MessageCircle, Send, ChevronRight, Headphones,
  FlaskConical, Heart, Mail, Users, Landmark, Scale, Globe,
  HandshakeIcon, Wallet, Cpu, Rocket, Megaphone,
} from 'lucide-react';
import Button from '../components/ui/Button';
import './Landing.css';

export default function Landing() {
  const { t } = useTranslation();

  return (
    <div className="land">

      {/* ━━ HERO ━━ */}
      <section className="hero">
        <div className="hero-bg" aria-hidden="true">
          <div className="hero-orb orb-1" />
          <div className="hero-orb orb-2" />
        </div>
        <div className="hero-content">
          <div className="hero-badge"><Sparkles size={14} /><span>{t('hero.badge')}</span></div>
          <h1>{t('hero.title')}</h1>
          <p className="hero-sub">{t('hero.subtitle')}</p>
          <p className="hero-motiv">{t('hero.leitmotiv')}</p>
          <div className="hero-actions">
            <Link to="/register"><Button variant="primary" size="lg" icon={<ArrowRight size={18} />}>{t('hero.cta_try')}</Button></Link>
            <Link to="/api-keys"><Button variant="ghost-border" size="lg" icon={<Code size={16} />}>{t('hero.cta_api')}</Button></Link>
          </div>
        </div>
      </section>

      {/* ━━ DEMO ━━ */}
      <section className="demo">
        <div className="demo-window">
          <div className="demo-bar">
            <div className="demo-dots"><span /><span /><span /></div>
            <span className="demo-title">ekodi.ai</span>
            <div />
          </div>
          <div className="demo-body">
            <div className="demo-msg demo-user">
              <div className="demo-avatar user-av">A</div>
              <div className="demo-bubble"><p>{t('demo.user_msg')}</p></div>
            </div>
            <div className="demo-msg demo-ai">
              <div className="demo-avatar ai-av"><img src="/logo-ekodi-actif.png" alt="" /></div>
              <div className="demo-bubble ai-bubble">
                <p>{t('demo.ai_msg')}</p>
                <div className="demo-audio-bar">
                  <Headphones size={14} />
                  <div className="demo-wave">
                    {Array.from({ length: 32 }).map((_, i) => (
                      <span key={i} style={{ height: `${4 + Math.sin(i * 0.5) * 12}px`, animationDelay: `${i * 35}ms` }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="demo-input">
              <MessageCircle size={16} className="demo-input-ico" />
              <span>{t('demo.input_placeholder')}</span>
              <Send size={16} className="demo-send-ico" />
            </div>
          </div>
        </div>
      </section>

      {/* ━━ STORY ━━ */}
      <section className="story">
        <div className="story-card">
          <Sprout size={28} className="story-icon" />
          <blockquote>{t('story.proverb')}</blockquote>
          <p>{t('story.desc')}</p>
        </div>
      </section>

      {/* ━━ FEATURES ━━ */}
      <section className="feat" id="features">
        <h2>{t('features.title')}</h2>
        <div className="feat-hero-card">
          <div className="feat-ico-lg orange"><MessageCircle size={24} /></div>
          <h3>{t('features.assistant_title')}</h3>
          <p>{t('features.assistant_desc')}</p>
        </div>
      </section>

      {/* ━━ IMPACT ━━ */}
      <section className="impact" id="impact">
        <h2>{t('impact.title')}</h2>
        <div className="impact-stat">
          <Globe size={22} />
          <strong>{t('impact.stat_speakers')}</strong>
          <span>{t('impact.stat_speakers_label')}</span>
        </div>
        <div className="impact-grid">
          <div className="impact-card">
            <div className="impact-ico orange"><Users size={20} /></div>
            <h3>{t('impact.farmer_title')}</h3>
            <p>{t('impact.farmer_desc')}</p>
          </div>
          <div className="impact-card">
            <div className="impact-ico violet"><Landmark size={20} /></div>
            <h3>{t('impact.institution_title')}</h3>
            <p>{t('impact.institution_desc')}</p>
          </div>
          <div className="impact-card">
            <div className="impact-ico teal"><Scale size={20} /></div>
            <h3>{t('impact.equality_title')}</h3>
            <p>{t('impact.equality_desc')}</p>
          </div>
          <div className="impact-card">
            <div className="impact-ico blue"><Sparkles size={20} /></div>
            <h3>{t('impact.company_title')}</h3>
            <p>{t('impact.company_desc')}</p>
          </div>
        </div>
        <div className="impact-cta">
          <Link to="/register"><Button variant="primary" icon={<ArrowRight size={16} />}>{t('impact.cta')}</Button></Link>
        </div>
      </section>

      {/* ━━ API ━━ */}
      <section className="api-sec">
        <div className="api-inner">
          <div className="api-text">
            <h2>{t('api_showcase.title')}</h2>
            <p>{t('api_showcase.subtitle')}</p>
            <Link to="/register"><Button variant="primary" icon={<ChevronRight size={16} />}>{t('api_showcase.get_key')}</Button></Link>
          </div>
          <div className="api-code">
            <div className="code-bar"><span className="cd r" /><span className="cd y" /><span className="cd g" /></div>
            <pre>{`curl -X POST https://api.ekodi.ai/v1/translate \\
  -H "X-API-Key: ek-your-key" \\
  -d '{"text":"Bonjour","source":"fr","target":"bm"}'

{ "translation": "I ni ce" }`}</pre>
          </div>
        </div>
      </section>

      {/* ━━ PRICING ━━ */}
      <section className="price" id="pricing">
        <h2>{t('pricing.title')}</h2>
        <p className="price-sub">{t('pricing.subtitle')}</p>
        <div className="price-grid">
          {/* FREE — active */}
          <div className="price-card highlight">
            <span className="price-label">{t('pricing.free_tier')}</span>
            <div className="price-amount">{t('pricing.free_price')}</div>
            <div className="price-prompts">{t('pricing.free_prompts')}</div>
            <ul>
              <li><Check size={14} /> {t('pricing.free_features')}</li>
              <li><Check size={14} /> {t('pricing.free_feedback')}</li>
            </ul>
            <Link to="/register"><Button variant="primary" className="price-btn">{t('pricing.free_cta')}</Button></Link>
          </div>
          {/* STANDARD — inactive */}
          <div className="price-card inactive">
            <span className="price-label">{t('pricing.standard_tier')}</span>
            <div className="price-amount">{t('pricing.standard_price')}</div>
            <div className="price-prompts">{t('pricing.standard_prompts')}</div>
            <ul>
              <li><Check size={14} /> {t('pricing.standard_features')}</li>
            </ul>
            <Button variant="secondary" className="price-btn" disabled><Lock size={13} /> {t('pricing.standard_cta')}</Button>
          </div>
          {/* PRO — inactive */}
          <div className="price-card inactive">
            <span className="price-label">{t('pricing.pro_tier')}</span>
            <div className="price-amount">{t('pricing.pro_price')}</div>
            <div className="price-prompts">{t('pricing.pro_prompts')}</div>
            <ul>
              <li><Check size={14} /> {t('pricing.pro_features')}</li>
            </ul>
            <Button variant="secondary" className="price-btn" disabled><Lock size={13} /> {t('pricing.pro_cta')}</Button>
          </div>
          {/* BUSINESS — inactive */}
          <div className="price-card inactive">
            <span className="price-label">{t('pricing.business_tier')}</span>
            <div className="price-amount">{t('pricing.business_price')}</div>
            <div className="price-prompts">{t('pricing.business_prompts')}</div>
            <ul>
              <li><Check size={14} /> {t('pricing.business_features')}</li>
            </ul>
            <Button variant="secondary" className="price-btn" disabled><Lock size={13} /> {t('pricing.business_cta')}</Button>
          </div>
        </div>
        <p className="price-inactive-note"><Lock size={12} /> {t('pricing.inactive_note')}</p>
      </section>

      {/* ━━ PARTNERS ━━ */}
      <section className="partners" id="partners">
        <h2>{t('partners.title')}</h2>
        <p className="partners-sub">{t('partners.subtitle')}</p>
        <div className="partners-grid">
          <Link to="/partners?type=financial" className="partner-card clickable">
            <div className="partner-ico orange"><Wallet size={20} /></div>
            <h3>{t('partners.financial_title')}</h3>
            <p>{t('partners.financial_desc')}</p>
            <span className="partner-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/partners?type=technical" className="partner-card clickable">
            <div className="partner-ico violet"><Cpu size={20} /></div>
            <h3>{t('partners.technical_title')}</h3>
            <p>{t('partners.technical_desc')}</p>
            <span className="partner-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/partners?type=expansion" className="partner-card clickable">
            <div className="partner-ico teal"><Rocket size={20} /></div>
            <h3>{t('partners.expansion_title')}</h3>
            <p>{t('partners.expansion_desc')}</p>
            <span className="partner-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/partners?type=promotion" className="partner-card clickable">
            <div className="partner-ico blue"><Megaphone size={20} /></div>
            <h3>{t('partners.promotion_title')}</h3>
            <p>{t('partners.promotion_desc')}</p>
            <span className="partner-arrow"><ArrowRight size={14} /></span>
          </Link>
        </div>
        <div className="partners-cta">
          <Link to="/partners"><Button variant="primary" icon={<ArrowRight size={16} />}>{t('partners.cta')}</Button></Link>
          <span className="partners-email">{t('partners.email_label')} <a href="mailto:support@ekodi.ai">support@ekodi.ai</a></span>
        </div>
      </section>

      {/* ━━ YNNOV ━━ */}
      <section className="ynv">
        <div className="ynv-copy">
          <img src="/ynnov-logo.png" alt="Ynnov" className="ynv-logo" />
          <p>{t('ynnov.desc')}</p>
          <p className="ynv-mission">{t('ynnov.mission')}</p>
          <div className="ynv-links">
            <a href="https://ynnov.io" target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="sm" icon={<ExternalLink size={14} />}>{t('ynnov.visit')}</Button>
            </a>
            <a href="mailto:contact@ynnov.io" className="ynv-email"><Mail size={14} /> contact@ynnov.io</a>
          </div>
        </div>
      </section>

      {/* ━━ PROJECT + FEEDBACK (combined, last) ━━ */}
      <section className="closing">
        <div className="closing-inner">
          <div className="closing-left">
            <div className="proj-badge"><FlaskConical size={14} /><span>{t('project.label')}</span></div>
            <h3>{t('project.title')}</h3>
            <p>{t('project.desc')}</p>
          </div>
          <div className="closing-right">
            <div className="fb-icons"><ThumbsUp size={22} className="fb-up" /><ThumbsDown size={22} className="fb-dn" /></div>
            <h3>{t('feedback_cta.title')}</h3>
            <p>{t('feedback_cta.subtitle')}</p>
            <p className="fb-note"><Heart size={14} /> {t('feedback_cta.note')}</p>
            <Link to="/register"><Button variant="primary">{t('feedback_cta.cta')}</Button></Link>
          </div>
        </div>
      </section>

      {/* ━━ FOOTER ━━ */}
      <footer className="foot">
        <div className="foot-inner">
          <div className="foot-top">
            <div className="foot-brand">
              <img src="/logo-ekodi-std.png" alt="Ekodi" />
              <div><strong>ekodi<span>.ai</span></strong><small>{t('footer.powered')}</small></div>
            </div>
            <nav className="foot-links">
              <Link to="/login">{t('nav.login')}</Link>
              <Link to="/register">{t('nav.register')}</Link>
              <a href="#features">{t('features.title')}</a>
              <a href="#pricing">Pricing</a>
            </nav>
          </div>
          <div className="foot-contacts">
            <a href="mailto:support@ekodi.ai"><Mail size={13} /> support@ekodi.ai</a>
            <a href="mailto:contact@ynnov.io"><Mail size={13} /> contact@ynnov.io</a>
          </div>
          <p className="foot-copy">&copy; {new Date().getFullYear()} Ynnov · {t('footer.rights')}</p>
        </div>
      </footer>
    </div>
  );
}
