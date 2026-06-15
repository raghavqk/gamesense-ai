import React from 'react';

const Header = () => (
  <header style={{ paddingTop: 28, paddingBottom: 20, borderBottom: '1px solid var(--border)' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>

      {/* Logo mark */}
      <div style={{ position: 'relative', flexShrink: 0 }}>
        <div style={{
          width: 52, height: 52, borderRadius: 12,
          background: 'linear-gradient(135deg, var(--cyan) 0%, var(--green) 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 32px rgba(0,212,255,.4), 0 0 64px rgba(0,212,255,.15)',
          fontSize: 26, fontWeight: 900, color: '#000',
          fontFamily: 'var(--f-title)',
        }}>
          GS
        </div>
        {/* Ping indicator */}
        <div style={{
          position: 'absolute', top: -4, right: -4,
          width: 14, height: 14,
        }}>
          <div style={{
            position: 'absolute', inset: 0, borderRadius: '50%',
            background: 'var(--green)',
            animation: 'glow-ping 1.5s ease-out infinite',
            opacity: .7,
          }} />
          <div style={{
            position: 'absolute', inset: 2, borderRadius: '50%',
            background: 'var(--green)',
          }} />
        </div>
      </div>

      {/* Title block */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{
            fontFamily: 'var(--f-title)', fontWeight: 900,
            fontSize: 38, lineHeight: 1,
            background: 'linear-gradient(135deg, var(--cyan) 0%, var(--green) 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            letterSpacing: '.04em',
          }}>
            GAMESENSE AI
          </h1>
          <span style={{
            fontFamily: 'var(--f-mono)', fontSize: 9, letterSpacing: '.12em',
            padding: '3px 8px', borderRadius: 4,
            background: 'var(--cyan-10)', color: 'var(--cyan)',
            border: '1px solid var(--cyan)', verticalAlign: 'middle',
          }}>
            v4.0
          </span>
        </div>
        <div style={{
          fontFamily: 'var(--f-mono)', fontSize: 11,
          color: 'var(--t3)', letterSpacing: '.12em', marginTop: 4,
        }}>
          GAMEPLAY INTELLIGENCE PLATFORM · ML PIPELINE · AI COACHING
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Right: status chips */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>

        {/* LIVE badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 12px', background: 'var(--red-10)',
          border: '1px solid var(--red)', borderRadius: 6,
        }}>
          <span className="blink" style={{
            display: 'inline-block', width: 6, height: 6,
            borderRadius: '50%', background: 'var(--red)',
          }} />
          <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--red)', letterSpacing: '.1em' }}>
            LIVE
          </span>
        </div>

        {/* Game support */}
        <div style={{
          display: 'flex', gap: 6,
        }}>
          {['CS2', 'VALORANT'].map(g => (
            <span key={g} style={{
              fontFamily: 'var(--f-mono)', fontSize: 10, letterSpacing: '.06em',
              padding: '5px 10px', borderRadius: 4,
              background: g === 'CS2' ? 'rgba(0,212,255,.08)' : 'rgba(255,70,85,.08)',
              color: g === 'CS2' ? 'var(--cyan)' : '#ff4655',
              border: `1px solid ${g === 'CS2' ? 'rgba(0,212,255,.3)' : 'rgba(255,70,85,.3)'}`,
            }}>
              {g === 'CS2' ? '⊕ ' : '◈ '}{g}
            </span>
          ))}
        </div>

      </div>
    </div>

    {/* Sub tagline */}
    <div style={{
      marginTop: 14,
      display: 'flex', gap: 24, flexWrap: 'wrap',
      fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)',
      letterSpacing: '.08em',
    }}>
      {['🔒 100% LOCAL · NO API CALLS', '🧠 YOLOv8 + EasyOCR PIPELINE', '⚡ GEMINI AI COACHING', '📊 TRACKER.GG-STYLE ANALYTICS'].map((t, i) => (
        <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>{t}</span>
      ))}
    </div>
  </header>
);

export default Header;
