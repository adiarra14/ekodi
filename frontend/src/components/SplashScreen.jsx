import { useState, useEffect } from 'react';
import './SplashScreen.css';

const LOGOS = [
  '/logo-ekodi-std.png',
  '/logo-ekodi-actif.png',
  '/logo-ekodi-blue.png',
  '/logo-ekodi-innactif.png',
];

export default function SplashScreen({ onDone }) {
  const [phase, setPhase] = useState('enter');
  const [logoIdx, setLogoIdx] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('hold'), 100);
    const t2 = setTimeout(() => setPhase('exit'), 2300);
    const t3 = setTimeout(() => onDone(), 3000);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [onDone]);

  // Cycle logos every 500ms once visible
  useEffect(() => {
    const iv = setInterval(() => setLogoIdx(i => (i + 1) % LOGOS.length), 500);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className={`splash ${phase}`}>
      <div className="splash-bg">
        <div className="splash-orb s-orb-1" />
        <div className="splash-orb s-orb-2" />
        <div className="splash-orb s-orb-3" />
      </div>

      <div className="splash-center">
        {/* Logo with rings */}
        <div className="splash-rings">
          <span className="s-ring s-r1" />
          <span className="s-ring s-r2" />
          <span className="s-ring s-r3" />
          <div className="splash-logo-stack">
            {LOGOS.map((src, i) => (
              <img
                key={src}
                src={src}
                alt=""
                className={`splash-logo ${i === logoIdx ? 'active' : ''}`}
              />
            ))}
          </div>
        </div>

        {/* Text */}
        <div className="splash-text">
          <span className="s-l" style={{ animationDelay: '0.3s' }}>e</span>
          <span className="s-l" style={{ animationDelay: '0.4s' }}>k</span>
          <span className="s-l" style={{ animationDelay: '0.5s' }}>o</span>
          <span className="s-l" style={{ animationDelay: '0.6s' }}>d</span>
          <span className="s-l" style={{ animationDelay: '0.7s' }}>i</span>
          <span className="s-dot" style={{ animationDelay: '0.85s' }}>.ai</span>
        </div>

        {/* Tagline */}
        <p className="splash-tag">Bamanankan AI</p>
      </div>
    </div>
  );
}
