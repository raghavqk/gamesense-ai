import React from 'react';

const PLAYSTYLE_COLOR = {
  'Aggressive Fragger': 'var(--red)',
  'Entry Fragger':      'var(--red)',
  'Rifler / Duelist':   'var(--cyan)',
  'Defensive Anchor':   'var(--green)',
  'Roamer / Support':   'var(--purple)',
  'Passive Lurker':     'var(--purple)',
};

const PLAYSTYLE_ICON = {
  'Aggressive Fragger': '🔥', 'Entry Fragger': '⚡',
  'Rifler / Duelist': '🎯',   'Defensive Anchor': '🛡️',
  'Roamer / Support': '🗺️',  'Passive Lurker': '👁️',
};

const PLAYSTYLE_DESC = {
  'Aggressive Fragger': 'High-impact player who creates picks and forces engagements. Focus on grenade setups and counter-strafing.',
  'Entry Fragger':      'First through the door — leads site executes and creates space for the team.',
  'Rifler / Duelist':   'Consistent rifler who wins 1v1s. Strong mid-round impact and map control.',
  'Defensive Anchor':   'Holds angles and denies space. Critical for CT retakes and information gathering.',
  'Roamer / Support':   'Creates chaos and info plays. Key role in flashing teammates and lurking.',
  'Passive Lurker':     'Patient player who looks for late-round impact through map control and flanks.',
};

const MultiKillAndPlaystyle = ({ data }) => {
  const mk = data?.multi_kills || { '2k': 0, '3k': 0, '4k+': 0 };
  const conf = data?.playstyle_confidence || {};
  const playstyle = data?.playstyle || 'Unknown';
  const psColor = PLAYSTYLE_COLOR[playstyle] || 'var(--cyan)';
  const psIcon = PLAYSTYLE_ICON[playstyle] || '🎮';
  const psDesc = PLAYSTYLE_DESC[playstyle] || 'Player profile determined from match statistics.';

  const hasConfidence = Object.keys(conf).length > 0;

  // Calculate multikill total
  const totalMK = (mk['2k'] || 0) + (mk['3k'] || 0) + (mk['4k+'] || 0);

  return (
    <div className="card bracket anim-up delay-4" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Multi-kills */}
      <div>
        <div className="section-label">MULTI-KILL ROUNDS</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
          {[
            { label: '2K', key: '2k', color: 'var(--green)', icon: '✌️', desc: 'Double' },
            { label: '3K', key: '3k', color: 'var(--cyan)',  icon: '3️⃣', desc: 'Triple' },
            { label: '4K+', key: '4k+', color: 'var(--gold)', icon: '💎', desc: 'Ace' },
          ].map(({ label, key, color, icon, desc }) => {
            const val = mk[key] ?? 0;
            return (
              <div key={key} style={{
                background: val > 0
                  ? `linear-gradient(135deg, ${color}18, var(--deep))`
                  : 'var(--deep)',
                border: `1px solid ${val > 0 ? color + '44' : 'var(--border)'}`,
                borderRadius: 10, padding: '14px 8px', textAlign: 'center',
                boxShadow: val > 0 ? `0 0 20px ${color}20` : 'none',
                transition: 'all .3s',
              }}>
                <div style={{ fontSize: 18, marginBottom: 4 }}>{icon}</div>
                <div style={{
                  fontFamily: 'var(--f-title)', fontWeight: 800, fontSize: 48,
                  color: val > 0 ? color : 'var(--t3)', lineHeight: 1,
                  textShadow: val > 0 ? `0 0 24px ${color}55` : 'none',
                }}>
                  {val}
                </div>
                <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--t3)', marginTop: 4, letterSpacing: '.08em' }}>
                  {label} · {desc}
                </div>
              </div>
            );
          })}
        </div>

        {/* Total MK summary */}
        {totalMK > 0 && (
          <div style={{
            marginTop: 10, padding: '8px 12px', borderRadius: 6,
            background: 'var(--surface)', border: '1px solid var(--border)',
            fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--t2)',
            textAlign: 'center',
          }}>
            🎖️ {totalMK} multi-kill round{totalMK !== 1 ? 's' : ''} total
          </div>
        )}
      </div>

      {/* Playstyle */}
      <div>
        <div className="section-label">PLAYSTYLE PROFILE</div>

        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14,
          padding: '12px 14px', borderRadius: 8,
          background: `linear-gradient(135deg, ${psColor}15, var(--deep))`,
          border: `1px solid ${psColor}33`,
          boxShadow: `0 0 20px ${psColor}12`,
        }}>
          <span style={{ fontSize: 24 }}>{psIcon}</span>
          <div>
            <div style={{
              fontFamily: 'var(--f-title)', fontWeight: 700, fontSize: 20,
              color: psColor, letterSpacing: '.04em',
              textShadow: `0 0 16px ${psColor}44`,
            }}>
              {playstyle}
            </div>
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', marginTop: 2, lineHeight: 1.4 }}>
              {psDesc}
            </div>
          </div>
        </div>

        {/* Confidence bars */}
        {hasConfidence && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {Object.entries(conf).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([style, val]) => {
              const barColor = PLAYSTYLE_COLOR[style] || 'var(--t3)';
              return (
                <div key={style}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                    <span style={{
                      fontFamily: 'var(--f-ui)', fontSize: 12,
                      color: style === playstyle ? 'var(--t1)' : 'var(--t2)',
                    }}>{style}</span>
                    <span style={{
                      fontFamily: 'var(--f-mono)', fontSize: 10,
                      color: style === playstyle ? barColor : 'var(--t3)',
                    }}>
                      {Math.round(val * 100)}%
                    </span>
                  </div>
                  <div className="prog-bar">
                    <div className="prog-bar-fill" style={{
                      width: `${val * 100}%`,
                      background: style === playstyle
                        ? `linear-gradient(90deg, ${barColor}, ${barColor}88)`
                        : 'var(--border-hi)',
                      boxShadow: style === playstyle ? `0 0 8px ${barColor}55` : 'none',
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default MultiKillAndPlaystyle;
