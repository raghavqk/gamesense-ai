import React from 'react';

const WEAPON_ICON = {
  'AK-47':       '🔫', 'M4A4':       '🔫', 'M4A1-S':     '🔫',
  'AWP':         '🎯', 'Desert Eagle': '🔫', 'Glock-18':   '🔫',
  'USP-S':       '🔫', 'P250':        '🔫', 'Five-SeveN':  '🔫',
  'Tec-9':       '🔫', 'CZ75-Auto':   '🔫', 'Dual Berettas': '🔫',
  'MP9':         '🔫', 'MAC-10':      '🔫', 'UMP-45':      '🔫',
  'P90':         '🔫', 'Galil AR':    '🔫', 'FAMAS':       '🔫',
  'SG 553':      '🔫', 'AUG':         '🔫', 'SSG 08':      '🎯',
  'Knife':       '🔪',
  'HE Grenade':  '💣', 'Molotov':     '🔥',
  'Vandal':      '🔫', 'Phantom':     '🔫', 'Operator':    '🎯',
  'Ghost':       '🔫', 'Sheriff':     '🔫', 'Spectre':     '🔫',
  'Classic':     '🔫', 'Odin':        '🔫', 'Ares':        '🔫',
  'default':     '🔫',
};

const WEAPON_COLOR = {
  'AK-47': '#ff6b35', 'M4A4': '#00d4ff', 'M4A1-S': '#00aacc',
  'AWP': '#ffcc00', 'Desert Eagle': '#ff9900', 'Vandal': '#ff4040',
  'Phantom': '#4488ff', 'Operator': '#ffdd00', 'default': '#5577aa',
};

const WeaponTable = ({ usageData = {}, mostUsed }) => {
  const entries = Object.entries(usageData)
    .sort((a, b) => (b[1]?.count || 0) - (a[1]?.count || 0));

  if (entries.length === 0) return (
    <div className="card bracket anim-up delay-4" style={{
      padding: 24, textAlign: 'center',
      color: 'var(--t3)', fontFamily: 'var(--f-mono)', fontSize: 12,
    }}>
      <div style={{ fontSize: 32, marginBottom: 10 }}>🔫</div>
      No weapon data detected
      <div style={{ fontSize: 10, marginTop: 6, color: 'var(--t3)' }}>
        Video may not contain a visible kill feed
      </div>
    </div>
  );

  const maxKills = Math.max(...entries.map(([, s]) => s?.count || 0), 1);

  return (
    <div className="card bracket anim-up delay-4" style={{ padding: '20px 24px' }}>
      <div className="section-label">WEAPON LOADOUT</div>

      {/* Header row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '32px 1fr 120px 80px 80px',
        gap: 12, padding: '6px 16px', marginBottom: 8,
        fontFamily: 'var(--f-mono)', fontSize: 9,
        color: 'var(--t3)', letterSpacing: '.1em',
      }}>
        <span></span>
        <span>WEAPON</span>
        <span>KILL SHARE</span>
        <span style={{ textAlign: 'center' }}>KILLS</span>
        <span style={{ textAlign: 'center' }}>HS %</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {entries.map(([weapon, stats], i) => {
          const kills = stats?.count || 0;
          const hs = stats?.hs_rate || 0;
          const share = (kills / maxKills) * 100;
          const color = WEAPON_COLOR[weapon] || WEAPON_COLOR.default;
          const icon = WEAPON_ICON[weapon] || WEAPON_ICON.default;
          const isMostUsed = weapon === mostUsed;

          return (
            <div key={weapon} className={`anim-up delay-${Math.min(i + 1, 6)}`} style={{
              display: 'grid',
              gridTemplateColumns: '32px 1fr 120px 80px 80px',
              gap: 12, alignItems: 'center',
              padding: '10px 16px', borderRadius: 8,
              background: isMostUsed ? `${color}10` : 'transparent',
              border: isMostUsed ? `1px solid ${color}30` : '1px solid transparent',
              transition: 'all .2s',
              cursor: 'default',
            }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--surface)'}
              onMouseLeave={e => e.currentTarget.style.background = isMostUsed ? `${color}10` : 'transparent'}
            >
              {/* Icon */}
              <div style={{ fontSize: 18, textAlign: 'center' }}>{icon}</div>

              {/* Name */}
              <div>
                <div style={{
                  fontFamily: 'var(--f-title)', fontWeight: 700, fontSize: 16,
                  color: isMostUsed ? color : 'var(--t1)',
                }}>
                  {weapon}
                  {isMostUsed && (
                    <span style={{
                      marginLeft: 8, fontSize: 9, fontFamily: 'var(--f-mono)',
                      padding: '2px 6px', borderRadius: 3,
                      background: `${color}20`, color, border: `1px solid ${color}40`,
                    }}>PRIMARY</span>
                  )}
                </div>
              </div>

              {/* Kill share bar */}
              <div>
                <div style={{
                  height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%', width: `${share}%`,
                    background: `linear-gradient(90deg, ${color}, ${color}88)`,
                    borderRadius: 3,
                    boxShadow: `0 0 8px ${color}44`,
                    transition: 'width .8s ease',
                  }} />
                </div>
              </div>

              {/* Kills */}
              <div style={{
                textAlign: 'center',
                fontFamily: 'var(--f-title)', fontWeight: 700, fontSize: 22,
                color,
              }}>
                {kills}
              </div>

              {/* HS % */}
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  fontFamily: 'var(--f-mono)', fontSize: 13,
                  color: hs >= 50 ? 'var(--gold)' : hs >= 30 ? 'var(--t1)' : 'var(--t2)',
                }}>
                  {hs}%
                </div>
                <div style={{
                  height: 2, background: 'var(--border)', borderRadius: 1, overflow: 'hidden', marginTop: 4,
                }}>
                  <div style={{
                    height: '100%', width: `${hs}%`,
                    background: hs >= 50 ? 'var(--gold)' : 'var(--t2)',
                    borderRadius: 1,
                  }} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default WeaponTable;
