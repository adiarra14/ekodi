import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  Mic, Languages, Volume2, Code, ArrowRight, Sparkles,
  Sprout, ExternalLink, ThumbsUp, ThumbsDown, Check, Lock,
  MessageCircle, Send, ChevronRight, Headphones, Globe,
  FlaskConical, Heart,
} from 'lucide-react';
import Button from '../components/ui/Button';
import './Landing.css';

export default function Landing() {
  const { t } = useTranslation();

  return (
    <div className="land">

      {/* ━━━━━━━━━━ HERO ━━━━━━━━━━ */}
      <section className="hero">
        <div className="hero-bg" aria-hidden="true">
          <div className="hero-orb orb-1" />
          <div className="hero-orb orb-2" />
          <div className="hero-orb orb-3" />
        </div>

        <div className="hero-content">
          <div className="hero-badge">
            <Sparkles size={14} />
            <span>{t('hero.badge')}</span>
          </div>

          <h1>{t('hero.title')}</h1>
          <p className="hero-sub">{t('hero.subtitle')}</p>
          <p className="hero-motiv">{t('hero.leitmotiv')}</p>

          <div className="hero-actions">
            <Link to="/register">
              <Button variant="primary" size="lg" icon={<ArrowRight size={18} />}>{t('hero.cta_try')}</Button>
            </Link>
            <Link to="/api-keys">
              <Button variant="ghost-border" size="lg" icon={<Code size={16} />}>{t('hero.cta_api')}</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━ DEMO / CHAT PREVIEW ━━━━━━━━━━ */}
      <section className="demo">
        <div className="demo-window">
          <div className="demo-bar">
            <div className="demo-dots"><span /><span /><span /></div>
            <span className="demo-title">ekodi.ai</span>
            <div />
          </div>
          <div className="demo-body">
            {/* user message */}
            <div className="demo-msg demo-user">
              <div className="demo-avatar user-av">A</div>
              <div className="demo-bubble">
                <p>{t('demo.user_msg')}</p>
              </div>
            </div>
            {/* ai message */}
            <div className="demo-msg demo-ai">
              <div className="demo-avatar ai-av">
                <img src="/logo-ekodi-actif.png" alt="" />
              </div>
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
            {/* input */}
            <div className="demo-input">
              <MessageCircle size={16} className="demo-input-ico" />
              <span>{t('demo.input_placeholder')}</span>
              <Send size={16} className="demo-send-ico" />
            </div>
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━ PROJECT STATUS ━━━━━━━━━━ */}
      <section className="proj">
        <div className="proj-card">
          <div className="proj-badge">
            <FlaskConical size={14} />
            <span>{t('project.label')}</span>
          </div>
          <h3>{t('project.title')}</h3>
          <p>{t('project.desc')}</p>
        </div>
      </section>

      {/* ━━━━━━━━━━ STORY — Sambala ɲiɔ ━━━━━━━━━━ */}
      <section className="story">
        <div className="story-card">
          <Sprout size={36} className="story-icon" />
          <blockquote>{t('story.proverb')}</blockquote>
          <p>{t('story.desc')}</p>
        </div>
      </section>

      {/* ━━━━━━━━━━ FEATURES ━━━━━━━━━━ */}
      <section className="feat" id="features">
        <h2>{t('features.title')}</h2>
        <div className="feat-grid">
          <div className="feat-card">
            <div className="feat-ico orange"><Mic size={22} /></div>
            <h3>{t('features.voice_title')}</h3>
            <p>{t('features.voice_desc')}</p>
          </div>
          <div className="feat-card">
            <div className="feat-ico violet"><Languages size={22} /></div>
            <h3>{t('features.translate_title')}</h3>
            <p>{t('features.translate_desc')}</p>
          </div>
          <div className="feat-card">
            <div className="feat-ico teal"><Volume2 size={22} /></div>
            <h3>{t('features.tts_title')}</h3>
            <p>{t('features.tts_desc')}</p>
          </div>
          <div className="feat-card">
            <div className="feat-ico blue"><Code size={22} /></div>
            <h3>{t('features.api_title')}</h3>
            <p>{t('features.api_desc')}</p>
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━ HOW IT WORKS ━━━━━━━━━━ */}
      <section className="how">
        <h2>{t('how.title')}</h2>
        <div className="how-steps">
          {[
            { ico: <Mic size={20} />, h: t('how.step1'), p: t('how.step1_desc') },
            { ico: <Globe size={20} />, h: t('how.step2'), p: t('how.step2_desc') },
            { ico: <Sparkles size={20} />, h: t('how.step3'), p: t('how.step3_desc') },
            { ico: <Volume2 size={20} />, h: t('how.step4'), p: t('how.step4_desc') },
          ].map((s, i) => (
            <div className="how-step" key={i}>
              <div className="how-num">{i + 1}</div>
              <div className="how-ico">{s.ico}</div>
              <h4>{s.h}</h4>
              <p>{s.p}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ━━━━━━━━━━ STATS ━━━━━━━━━━ */}
      <section className="stats">
        <div className="stats-row">
          <div className="stat"><span>3+</span><small>{t('stats.languages')}</small></div>
          <div className="stat-divider" />
          <div className="stat"><span>&lt;3s</span><small>{t('stats.responses')}</small></div>
          <div className="stat-divider" />
          <div className="stat"><span>10</span><small>{t('stats.free')}</small></div>
          <div className="stat-divider" />
          <div className="stat"><span>24/7</span><small>{t('stats.available')}</small></div>
        </div>
      </section>

      {/* ━━━━━━━━━━ API SHOWCASE ━━━━━━━━━━ */}
      <section className="api-sec">
        <div className="api-inner">
          <div className="api-text">
            <h2>{t('api_showcase.title')}</h2>
            <p>{t('api_showcase.subtitle')}</p>
            <Link to="/register">
              <Button variant="primary" icon={<ChevronRight size={16} />}>{t('api_showcase.get_key')}</Button>
            </Link>
          </div>
          <div className="api-code">
            <div className="code-bar">
              <span className="cd r" /><span className="cd y" /><span className="cd g" />
            </div>
            <pre>{`curl -X POST https://api.ekodi.ai/v1/translate \\
  -H "X-API-Key: ek-your-key" \\
  -H "Content-Type: application/json" \\
  -d '{"text":"Bonjour","source":"fr","target":"bm"}'

{
  "translation": "I ni ce",
  "source": "fr",
  "target": "bm"
}`}</pre>
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━ PRICING ━━━━━━━━━━ */}
      <section className="price" id="pricing">
        <h2>{t('pricing.title')}</h2>
        <p className="price-sub">{t('pricing.subtitle')}</p>
        <div className="price-grid">
          <div className="price-card highlight">
            <span className="price-label">{t('pricing.free_tier')}</span>
            <div className="price-big">10 <small>prompts</small></div>
            <ul>
              <li><Check size={15} /> {t('pricing.free_features')}</li>
              <li><Check size={15} /> {t('feedback_cta.badge')}</li>
            </ul>
            <Link to="/register"><Button variant="primary" className="price-btn">{t('pricing.free_cta')}</Button></Link>
          </div>
          <div className="price-card muted">
            <span className="price-label">{t('pricing.pro_tier')}</span>
            <div className="price-big"><Sparkles size={20} /> <small>{t('pricing.pro_prompts')}</small></div>
            <ul>
              <li><Check size={15} /> {t('pricing.pro_features')}</li>
              <li><Lock size={15} /> {t('pricing.token_note')}</li>
            </ul>
            <Button variant="secondary" className="price-btn" disabled>{t('pricing.pro_cta')}</Button>
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━ FEEDBACK CTA ━━━━━━━━━━ */}
      <section className="fb">
        <div className="fb-card">
          <div className="fb-icons">
            <ThumbsUp size={24} className="fb-up" />
            <ThumbsDown size={24} className="fb-dn" />
          </div>
          <h3>{t('feedback_cta.title')}</h3>
          <p>{t('feedback_cta.subtitle')}</p>
          <p className="fb-note"><Heart size={14} /> {t('feedback_cta.note')}</p>
          <Link to="/register"><Button variant="primary">{t('feedback_cta.cta')}</Button></Link>
        </div>
      </section>

      {/* ━━━━━━━━━━ YNNOV ━━━━━━━━━━ */}
      <section className="ynv">
        <div className="ynv-inner">
          <div className="ynv-copy">
            <span className="ynv-badge">ynnov.io</span>
            <h2>{t('ynnov.title')}</h2>
            <p>{t('ynnov.desc')}</p>
            <p className="ynv-mission">{t('ynnov.mission')}</p>
            <a href="https://ynnov.io" target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="sm" icon={<ExternalLink size={14} />}>{t('ynnov.visit')}</Button>
            </a>
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━ FOOTER ━━━━━━━━━━ */}
      <footer className="foot">
        <div className="foot-inner">
          <div className="foot-brand">
            <img src="/logo-ekodi-std.png" alt="Ekodi" />
            <div>
              <strong>ekodi<span>.ai</span></strong>
              <small>{t('footer.powered')}</small>
            </div>
          </div>
          <nav className="foot-links">
            <Link to="/login">{t('nav.login')}</Link>
            <Link to="/register">{t('nav.register')}</Link>
            <a href="#features">{t('features.title')}</a>
            <a href="#pricing">Pricing</a>
          </nav>
          <p className="foot-copy">&copy; 2024–{new Date().getFullYear()} Ekodi · {t('footer.rights')}</p>
        </div>
      </footer>
    </div>
  );
}
