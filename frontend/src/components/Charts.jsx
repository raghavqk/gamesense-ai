import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';

const CHART_STYLE = {
  background: 'transparent', fontFamily: 'var(--f-mono)',
};

const TOOLTIP_STYLE = {
  backgroundColor: '#0d1e32', border: '1px solid #1a3050',
  borderRadius: 6, fontFamily: 'var(--f-mono)', color: 'var(--cyan)', fontSize: 12,
};

const WEAPON_COLORS = {
  'AK-47': '#ff6b35', 'M4A4': '#00d4ff', 'M4A1-S': '#00aacc',
  'AWP': '#ffcc00', 'Desert Eagle': '#ff9900', 'Vandal': '#ff4040',
  'Phantom': '#4488ff', 'Operator': '#ffdd00', 'default': '#5577aa',
};

const fmtTime = (sec) => {
  const m = Math.floor(sec / 60), s = sec % 60;
  return m > 0 ? `${m}m${s}s` : `${s}s`;
};

export const KillTimeline = ({ data }) => {
  if (!data || data.length === 0) return (
    <div className="card bracket anim-up" style={{ padding: 24, height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center', color: 'var(--t3)', fontFamily: 'var(--f-mono)', fontSize: 12 }}>
        <div style={{ fontSize: 32, marginBottom: 10 }}>📊</div>
        Insufficient kill event timestamps
      </div>
    </div>
  );

  return (
    <div className="card bracket anim-up delay-1" style={{ padding: 20 }}>
      <div className="section-label">KILL TIMELINE</div>
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} style={CHART_STYLE}>
            <defs>
              <linearGradient id="kfGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--cyan)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="var(--cyan)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 4" stroke="#1a3050" vertical={false} />
            <XAxis dataKey="time_sec" tickFormatter={fmtTime} stroke="#1a3050" tick={{ fill: '#3a5a7a', fontFamily: 'var(--f-mono)', fontSize: 11 }} />
            <YAxis stroke="#1a3050" tick={{ fill: '#3a5a7a', fontFamily: 'var(--f-mono)', fontSize: 11 }} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={fmtTime} />
            <Area type="monotone" dataKey="kills" stroke="var(--cyan)" fill="url(#kfGrad)" strokeWidth={2} dot={{ r: 4, fill: 'var(--cyan)', strokeWidth: 0 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export const WeaponChart = ({ usageData }) => {
  const safeUsageData = usageData || {};
  const entries = Object.entries(safeUsageData).sort((a, b) => (b[1]?.count || 0) - (a[1]?.count || 0)).slice(0, 6);

  if (entries.length === 0) return (
    <div className="card bracket anim-up delay-2" style={{ padding: 24, height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center', color: 'var(--t3)', fontFamily: 'var(--f-mono)', fontSize: 12 }}>
        <div style={{ fontSize: 32, marginBottom: 10 }}>🔫</div>
        Weapon data unavailable<br />
        <span style={{ fontSize: 10, marginTop: 6, display: 'block' }}>Video may not show kill feed clearly</span>
      </div>
    </div>
  );

  const chartData = entries.map(([name, stats]) => ({
    name, 
    kills: stats?.count || 0, 
    hs_rate: stats?.hs_rate || 0,
    color: WEAPON_COLORS[name] || WEAPON_COLORS.default,
  }));

  return (
    <div className="card bracket anim-up delay-2" style={{ padding: 20 }}>
      <div className="section-label">WEAPON USAGE</div>
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" style={CHART_STYLE} margin={{ left: 10, right: 40 }}>
            <CartesianGrid strokeDasharray="3 4" stroke="#1a3050" horizontal={false} />
            <XAxis type="number" stroke="#1a3050" tick={{ fill: '#3a5a7a', fontFamily: 'var(--f-mono)', fontSize: 11 }} allowDecimals={false} />
            <YAxis dataKey="name" type="category" stroke="#1a3050" tick={{ fill: 'var(--t1)', fontFamily: 'var(--f-mono)', fontSize: 11 }} width={72} />
            <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(0,212,255,.05)' }}
              formatter={(val, name) => [val, name === 'kills' ? 'Kills' : 'HS%']} />
            <Bar dataKey="kills" radius={[0, 3, 3, 0]}>
              {chartData.map((e, i) => <Cell key={i} fill={e.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
