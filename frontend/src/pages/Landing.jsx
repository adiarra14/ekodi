import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useRef, useState, useEffect, useCallback } from 'react';
import {
  ArrowRight, Sparkles, Sprout, ExternalLink,
  Check, Lock, MessageCircle, Send, ChevronRight, Headphones,
  Play, Pause,
  Mail, Users, Landmark, Scale, Globe,
  Wallet, Cpu, Rocket, Megaphone,
} from 'lucide-react';
import Button from '../components/ui/Button';
import './Landing.css';

export default function Landing() {
  const { t } = useTranslation();
  const audioRef = useRef(null);
  const analyserRef = useRef(null);
  const ctxRef = useRef(null);
  const barsRef = useRef(null);
  const rafRef = useRef(null);
  const [playing, setPlaying] = useState(false);

  const BAR_COUNT = 48;

  // Setup Web Audio analyser (once)
  const ensureAnalyser = useCallback(() => {
    if (analyserRef.current) return;
    const a = audioRef.current;
    if (!a) return;
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const src = ctx.createMediaElementSource(a);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 128;
    analyser.smoothingTimeConstant = 0.75;
    src.connect(analyser);
    analyser.connect(ctx.destination);
    ctxRef.current = ctx;
    analyserRef.current = analyser;
  }, []);

  // Animation loop: read frequency data and update bar heights
  const animate = useCallback(() => {
    const analyser = analyserRef.current;
    const bars = barsRef.current;
    if (!analyser || !bars) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);
    const step = Math.max(1, Math.floor(data.length / BAR_COUNT));
    for (let i = 0; i < BAR_COUNT; i++) {
      const val = data[Math.min(i * step, data.length - 1)] / 255;
      const h = 3 + val * 28;
      if (bars.children[i]) bars.children[i].style.height = `${h}px`;
    }
    rafRef.current = requestAnimationFrame(animate);
  }, []);

  // Start/stop animation with play state
  useEffect(() => {
    if (playing) {
      rafRef.current = requestAnimationFrame(animate);
    } else {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      // Reset bars to idle
      const bars = barsRef.current;
      if (bars) {
        for (let i = 0; i < bars.children.length; i++) {
          bars.children[i].style.height = `${5 + Math.sin(i * 0.4) * 6}px`;
        }
      }
    }
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [playing, animate]);

  const toggleAudio = (e) => {
    e.preventDefault();
    e.stopPropagation();
    ensureAnalyser();
    const a = audioRef.current;
    if (!a) return;
    if (ctxRef.current?.state === 'suspended') ctxRef.current.resume();
    if (a.paused) { a.play(); setPlaying(true); }
    else { a.pause(); setPlaying(false); }
  };

  return (
    <div className="land">

      {/* ━━ HERO ━━ */}
      <section className="hero" id="hero">
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
            <a href="#impact"><Button variant="ghost-border" size="lg" icon={<Globe size={16} />}>{t('nav.section_impact')}</Button></a>
          </div>
        </div>
      </section>

      {/* ━━ DEMO ━━ */}
      <section className="demo">
        <Link to="/register" className="demo-window clickable">
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
              <div className={`demo-avatar ai-av ${playing ? 'ai-speaking' : ''}`}><img src="/logo-ekodi-actif.png" alt="" /></div>
              <div className="demo-bubble ai-bubble">
                <button className={`demo-audio-main ${playing ? 'is-playing' : ''}`} onClick={toggleAudio} type="button">
                  <span className="demo-play-btn-lg">
                    {playing ? <Pause size={18} /> : <Play size={18} />}
                  </span>
                  <div className="demo-wave-lg" ref={barsRef}>
                    {Array.from({ length: BAR_COUNT }).map((_, i) => (
                      <span key={i} style={{ height: `${5 + Math.sin(i * 0.4) * 6}px` }} />
                    ))}
                  </div>
                  <Headphones size={15} className="demo-headphones" />
                </button>
                <audio ref={audioRef} src="/demo-voice.wav" onEnded={() => setPlaying(false)} preload="auto" />
              </div>
            </div>
            <div className="demo-input">
              <MessageCircle size={16} className="demo-input-ico" />
              <span>{t('demo.input_placeholder')}</span>
              <Send size={16} className="demo-send-ico" />
            </div>
          </div>
        </Link>
      </section>

      {/* ━━ STORY ━━ */}
      <section className="story" id="features">
        <div className="story-card">
          <div className="story-icon-wrap">
            <span className="story-ring ring-1" />
            <span className="story-ring ring-2" />
            <span className="story-ring ring-3" />
            <Sprout size={48} className="story-icon" />
          </div>
          <div className="story-text">
            <h3 className="story-title">Sambala ɲiɔ</h3>
            <blockquote>{t('story.proverb')}</blockquote>
            <p>{t('story.desc')}</p>
          </div>
        </div>
      </section>

      {/* ━━ IMPACT ━━ */}
      <section className="impact" id="impact">
        <h2>{t('impact.title')}</h2>
        <div className="impact-stat">
          <Globe size={20} />
          <strong>{t('impact.stat_speakers')}</strong>
          <span>{t('impact.stat_speakers_label')}</span>
        </div>
        <div className="impact-grid">
          <Link to="/register" className="impact-card clickable orange-hover">
            <div className="impact-ico orange"><Users size={18} /></div>
            <h3>{t('impact.farmer_title')}</h3>
            <p>{t('impact.farmer_desc')}</p>
            <span className="card-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/register" className="impact-card clickable violet-hover">
            <div className="impact-ico violet"><Landmark size={18} /></div>
            <h3>{t('impact.institution_title')}</h3>
            <p>{t('impact.institution_desc')}</p>
            <span className="card-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/register" className="impact-card clickable teal-hover">
            <div className="impact-ico teal"><Scale size={18} /></div>
            <h3>{t('impact.equality_title')}</h3>
            <p>{t('impact.equality_desc')}</p>
            <span className="card-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/register" className="impact-card clickable blue-hover">
            <div className="impact-ico blue"><Sparkles size={18} /></div>
            <h3>{t('impact.company_title')}</h3>
            <p>{t('impact.company_desc')}</p>
            <span className="card-arrow"><ArrowRight size={14} /></span>
          </Link>
        </div>
      </section>

      {/* ━━ API ━━ */}
      <section className="api-sec" id="api">
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
          <Link to="/register" className="price-card highlight clickable">
            <span className="price-label">{t('pricing.free_tier')}</span>
            <div className="price-amount">{t('pricing.free_price')}</div>
            <div className="price-prompts">{t('pricing.free_prompts')}</div>
            <ul>
              <li><Check size={14} /> {t('pricing.free_features')}</li>
              <li><Check size={14} /> {t('pricing.free_feedback')}</li>
            </ul>
            <span className="price-btn-link">{t('pricing.free_cta')} <ArrowRight size={14} /></span>
          </Link>
          <div className="price-card inactive">
            <span className="price-label">{t('pricing.standard_tier')}</span>
            <div className="price-amount">{t('pricing.standard_price')}</div>
            <div className="price-prompts">{t('pricing.standard_prompts')}</div>
            <ul>
              <li><Check size={14} /> {t('pricing.standard_features')}</li>
            </ul>
            <span className="price-btn-lock"><Lock size={13} /> {t('pricing.standard_cta')}</span>
          </div>
          <div className="price-card inactive">
            <span className="price-label">{t('pricing.pro_tier')}</span>
            <div className="price-amount">{t('pricing.pro_price')}</div>
            <div className="price-prompts">{t('pricing.pro_prompts')}</div>
            <ul>
              <li><Check size={14} /> {t('pricing.pro_features')}</li>
            </ul>
            <span className="price-btn-lock"><Lock size={13} /> {t('pricing.pro_cta')}</span>
          </div>
          <div className="price-card inactive">
            <span className="price-label">{t('pricing.business_tier')}</span>
            <div className="price-amount">{t('pricing.business_price')}</div>
            <div className="price-prompts">{t('pricing.business_prompts')}</div>
            <ul>
              <li><Check size={14} /> {t('pricing.business_features')}</li>
            </ul>
            <span className="price-btn-lock"><Lock size={13} /> {t('pricing.business_cta')}</span>
          </div>
        </div>
        <p className="price-inactive-note"><Lock size={12} /> {t('pricing.inactive_note')}</p>
      </section>

      {/* ━━ PARTNERS ━━ */}
      <section className="partners" id="partners">
        <h2>{t('partners.title')}</h2>
        <p className="partners-sub">{t('partners.subtitle')}</p>
        <div className="partners-grid">
          <Link to="/partners?type=financial" className="partner-card clickable orange-hover">
            <div className="partner-ico orange"><Wallet size={18} /></div>
            <h3>{t('partners.financial_title')}</h3>
            <p>{t('partners.financial_desc')}</p>
            <span className="partner-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/partners?type=technical" className="partner-card clickable violet-hover">
            <div className="partner-ico violet"><Cpu size={18} /></div>
            <h3>{t('partners.technical_title')}</h3>
            <p>{t('partners.technical_desc')}</p>
            <span className="partner-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/partners?type=expansion" className="partner-card clickable teal-hover">
            <div className="partner-ico teal"><Rocket size={18} /></div>
            <h3>{t('partners.expansion_title')}</h3>
            <p>{t('partners.expansion_desc')}</p>
            <span className="partner-arrow"><ArrowRight size={14} /></span>
          </Link>
          <Link to="/partners?type=promotion" className="partner-card clickable blue-hover">
            <div className="partner-ico blue"><Megaphone size={18} /></div>
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
      <section className="ynv" id="ynnov">
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

      {/* ━━ PROJECT BANNER ━━ */}
      <section className="proj-banner" id="project">
        <Sprout size={16} />
        <p>{t('project.desc')}</p>
        <Link to="/register" className="proj-banner-cta">{t('feedback_cta.cta')} <ArrowRight size={14} /></Link>
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
              <a href="#features">{t('nav.section_ekodi')}</a>
              <a href="#impact">{t('nav.section_impact')}</a>
              <a href="#pricing">{t('nav.section_pricing')}</a>
              <a href="#partners">{t('nav.section_partners')}</a>
              <Link to="/login">{t('nav.login')}</Link>
              <Link to="/register">{t('nav.register')}</Link>
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
