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
  'Aggressive Fragger': '🔥',
  'Entry Fragger':      '⚡',
  'Rifler / Duelist':   '🎯',
  'Defensive Anchor':   '🛡️',
  'Roamer / Support':   '🗺️',
  'Passive Lurker':     '👁️',
};

const CONFIDENCE_COLOR = { HIGH: 'var(--green)', MEDIUM: 'var(--gold)', LOW: 'var(--red)' };

const CS2_MAPS = ['Dust2', 'Mirage', 'Inferno', 'Nuke', 'Overpass', 'Anubis', 'Ancient', 'Vertigo'];
const VALO_MAPS = ['Bind', 'Haven', 'Split', 'Ascent', 'Icebox', 'Breeze', 'Fracture', 'Pearl'];

const MapBar = ({ data }) => {
  const psColor = PLAYSTYLE_COLOR[data.playstyle] || 'var(--cyan)';
  const psIcon = PLAYSTYLE_ICON[data.playstyle] || '🎮';
  const confColor = CONFIDENCE_COLOR[data.source_confidence] || 'var(--gold)';
  const isCS2 = data.game !== 'VALORANT';
  const gameColor = isCS2 ? 'var(--cyan)' : '#ff4655';
  const gameAccent = isCS2 ? 'rgba(0,212,255,' : 'rgba(255,70,85,';

  const mapName = data.map_name && data.map_name !== 'Unknown'
    ? data.map_name
    : (isCS2 ? 'Mirage' : 'Bind');

  const videoInfo = data.video_info;

  return (
    <div className="card anim-up delay-1" style={{
      padding: '18px 24px',
      background: `linear-gradient(135deg, var(--card) 0%, ${gameAccent}.04) 60%, var(--card) 100%)`,
      borderLeft: `3px solid ${gameColor}`,
      borderTop: `1px solid ${gameAccent}.15)`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>

        {/* Game badge */}
        <div style={{
          padding: '8px 16px', borderRadius: 8,
          background: `${gameAccent}.12)`,
          border: `1px solid ${gameAccent}.35)`,
          boxShadow: `0 0 16px ${gameAccent}.15)`,
        }}>
          <div style={{
            fontFamily: 'var(--f-title)', fontWeight: 900, fontSize: 22,
            color: gameColor, letterSpacing: '.06em',
          }}>
            {data.game || 'CS2'}
          </div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--t3)', letterSpacing: '.1em' }}>
            GAME DETECTED
          </div>
        </div>

        {/* Map */}
        <div>
          <div style={{
            fontFamily: 'var(--f-title)', fontWeight: 800, fontSize: 34,
            color: 'var(--t1)', letterSpacing: '.02em', textTransform: 'uppercase',
            textShadow: `0 0 30px ${gameAccent}.2)`,
          }}>
            {mapName.toUpperCase()}
          </div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', marginTop: 2 }}>
            MAP NAME
          </div>
        </div>

        <div style={{ flex: 1 }} />

        {/* Playstyle */}
        <div style={{
          padding: '10px 18px', borderRadius: 8,
          background: `${psColor.replace(')', '').replace('var(', '')}22`.includes('var') ? `${psColor}22` : 'var(--surface)',
          border: `1px solid ${psColor}55`,
          boxShadow: `0 0 16px ${psColor}22`,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 20, marginBottom: 2 }}>{psIcon}</div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: psColor, letterSpacing: '.08em' }}>
            {data.playstyle}
          </div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--t3)', marginTop: 2 }}>
            PLAYSTYLE
          </div>
        </div>

        {/* Confidence + source */}
        <div style={{ textAlign: 'right' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end', marginBottom: 6 }}>
            <span className="pulse" style={{
              display: 'inline-block', width: 8, height: 8,
              borderRadius: '50%', background: confColor,
              boxShadow: `0 0 8px ${confColor}`,
            }} />
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: confColor }}>
              {data.source_confidence || 'MEDIUM'} CONFIDENCE
            </span>
          </div>
          {videoInfo && (
            <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)' }}>
              {videoInfo.resolution} · {videoInfo.fps}fps · {Math.floor(videoInfo.duration_sec / 60)}m{Math.round(videoInfo.duration_sec % 60)}s
            </div>
          )}
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--t3)', marginTop: 2, letterSpacing: '.08em' }}>
            SRC: {data.data_source?.toUpperCase()?.replace('_', ' ')}
          </div>
        </div>

      </div>
    </div>
  );
};

export default MapBar;
