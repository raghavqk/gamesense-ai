import React from 'react';

const getTier = (kd) => {
  if (kd >= 3.0) return { label: 'LEGENDARY', cls: 'tier-diamond', icon: '💎' };
  if (kd >= 2.0) return { label: 'DIAMOND',   cls: 'tier-diamond', icon: '💜' };
  if (kd >= 1.5) return { label: 'PLATINUM',  cls: 'tier-plat',    icon: '🔷' };
  if (kd >= 1.0) return { label: 'GOLD',      cls: 'tier-gold',    icon: '🥇' };
  if (kd >= 0.7) return { label: 'SILVER',    cls: 'tier-silver',  icon: '🥈' };
  return         { label: 'BRONZE',   cls: 'tier-bronze',  icon: '🥉' };
};

const CARD_CONFIG = [
  {
    key: 'kills', label: 'KILLS', color: 'var(--green)',
    icon: '💀',
    sub: (d) => d.kills > 20 ? '🔥 Dominant' : d.kills > 10 ? '📈 Above avg' : '📉 Below avg',
  },
  {
    key: 'deaths', label: 'DEATHS', color: 'var(--red)',
    icon: '☠️',
    sub: (d) => d.deaths < 5 ? '🏆 Near flawless' : d.deaths < 10 ? '✅ Controlled' : '⚠️ High deaths',
  },
  {
    key: 'kd_ratio', label: 'K/D RATIO', color: 'var(--cyan)',
    icon: '⚡',
    sub: (d) => getTier(d.kd_ratio).label,
    special: 'kd',
  },
  {
    key: 'headshot_percentage', label: 'HEADSHOT %', color: 'var(--gold)',
    icon: '🎯',
    sub: (d) => d.headshot_percentage >= 50 ? '🎯 Aim specialist' : d.headshot_percentage >= 30 ? '✅ Good precision' : '📍 Work on aim',
  },
  {
    key: 'accuracy', label: 'ACCURACY', color: 'var(--purple)',
    icon: '📊',
    sub: () => 'Composite score',
  },
  {
    key: 'performance_rating', label: 'RATING', color: 'var(--gold)',
    icon: '🏆',
    sub: () => 'Overall score',
    isRating: true,
  },
];

const RatingRing = ({ value, color }) => {
  const r = 36, circ = 2 * Math.PI * r;
  const dash = (value / 100) * circ;
  return (
    <svg width={90} height={90} style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}>
      <circle cx={45} cy={45} r={r} fill="none" stroke="var(--border)" strokeWidth={5} />
      <circle cx={45} cy={45} r={r} fill="none" stroke={color} strokeWidth={5}
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 45 45)"
        style={{
          filter: `drop-shadow(0 0 8px ${color})`,
          transition: 'stroke-dasharray 1s ease',
        }}
      />
    </svg>
  );
};

const StatCard = ({ cfg, data, delay }) => {
  const val = data[cfg.key];
  const display = cfg.key === 'headshot_percentage' ? `${val}%`
    : cfg.key === 'accuracy' ? `${val}%`
    : val;

  const tier = cfg.special === 'kd' ? getTier(val) : null;

  return (
    <div className={`card bracket anim-up delay-${delay}`} style={{
      padding: '20px 14px',
      borderLeft: `3px solid ${cfg.color}66`,
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      textAlign: 'center', position: 'relative', overflow: 'hidden',
      minHeight: 148,
      background: `linear-gradient(160deg, var(--card) 60%, ${cfg.color}06 100%)`,
    }}>
      {/* Ambient glow bg */}
      <div style={{
        position: 'absolute', bottom: -20, right: -20,
        width: 80, height: 80, borderRadius: '50%',
        background: cfg.color, opacity: .04,
        filter: 'blur(20px)',
      }} />

      <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--t3)', letterSpacing: '.12em', marginBottom: 6 }}>
        {cfg.icon} {cfg.label}
      </div>

      {cfg.isRating ? (
        <div style={{ position: 'relative', width: 90, height: 90, margin: '2px auto 0' }}>
          <RatingRing value={val} color={cfg.color} />
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%,-50%)',
            fontFamily: 'var(--f-title)', fontWeight: 800, fontSize: 26,
            color: cfg.color,
          }}>{val}</div>
        </div>
      ) : (
        <div className="stat-num" style={{
          fontSize: cfg.special === 'kd' ? 44 : 52,
          color: cfg.color,
          textShadow: `0 0 28px ${cfg.color}44`,
          marginTop: 4,
        }}>
          {display}
        </div>
      )}

      {tier && (
        <span className={`badge ${tier.cls}`} style={{ marginTop: 6, fontSize: 9 }}>
          {tier.icon} {tier.label}
        </span>
      )}

      {!tier && (
        <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t2)', marginTop: 6 }}>
          {cfg.sub(data)}
        </div>
      )}

      {/* Bottom accent line */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 2,
        background: `linear-gradient(90deg, transparent, ${cfg.color}44, transparent)`,
      }} />
    </div>
  );
};

const StatCards = ({ data }) => {
  const safeData = {
    kills: data?.kills ?? 0,
    deaths: data?.deaths ?? 0,
    assists: data?.assists ?? 0,
    kd_ratio: data?.kd_ratio ?? 0,
    headshot_percentage: data?.headshot_percentage ?? 0,
    accuracy: data?.accuracy ?? 0,
    performance_rating: data?.performance_rating ?? 0,
  };

  return (
    <div>
      {/* K/D/A Summary strip */}
      <div style={{
        display: 'flex', gap: 0, marginBottom: 16,
        background: 'var(--panel)', borderRadius: 8,
        border: '1px solid var(--border)', overflow: 'hidden',
      }}>
        {[
          { label: 'K', val: safeData.kills, color: 'var(--green)' },
          { label: 'D', val: safeData.deaths, color: 'var(--red)' },
          { label: 'A', val: safeData.assists, color: 'var(--purple)' },
        ].map(({ label, val, color }, i) => (
          <div key={i} style={{
            flex: 1, textAlign: 'center', padding: '12px 0',
            borderRight: i < 2 ? '1px solid var(--border)' : 'none',
            background: `linear-gradient(160deg, transparent, ${color}06)`,
          }}>
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', letterSpacing: '.1em' }}>{label}</div>
            <div style={{
              fontFamily: 'var(--f-title)', fontWeight: 800, fontSize: 32,
              color, textShadow: `0 0 20px ${color}44`,
            }}>{val}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 14 }}>
        {CARD_CONFIG.map((cfg, i) => (
          <StatCard key={cfg.key} cfg={cfg} data={safeData} delay={Math.min(i + 1, 6)} />
        ))}
      </div>
    </div>
  );
};

export default StatCards;
