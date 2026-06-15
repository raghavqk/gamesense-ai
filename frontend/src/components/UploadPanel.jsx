import React, { useState, useRef } from 'react';

const STEPS = [
  { label: 'Game Detection',    icon: '🎮' },
  { label: 'Frame Extraction',  icon: '🎬' },
  { label: 'Kill Feed OCR',     icon: '💀' },
  { label: 'Scoreboard Scan',   icon: '📊' },
  { label: 'Stats Aggregation', icon: '🧮' },
  { label: 'Report Build',      icon: '📋' },
];

const UploadPanel = ({ onUpload, loading, currentStep }) => {
  const [game, setGame] = useState('CS2');
  const [mode, setMode] = useState('quick');
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && (f.type.startsWith('video/') || f.name.endsWith('.mp4') || f.name.endsWith('.mov'))) {
      setFile(f);
    }
  };

  const handleSubmit = () => {
    if (!file) return;
    onUpload(file, game, mode);
  };

  const fmt = (bytes) => bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(0)} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;

  return (
    <div className="card bracket anim-up" style={{
      padding: 28, marginTop: 24,
      background: 'linear-gradient(135deg, var(--card) 0%, rgba(0,212,255,.03) 100%)',
      borderTop: '1px solid rgba(0,212,255,.15)',
    }}>
      <div className="section-label">MATCH FOOTAGE UPLOAD</div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.5fr', gap: 24, alignItems: 'start' }}>

        {/* Game selector */}
        <div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', marginBottom: 12, letterSpacing: '.1em' }}>
            SELECT GAME
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className={`game-pill ${game === 'CS2' ? 'active-cs2' : ''}`}
              onClick={() => setGame('CS2')}
            >
              ⊕ CS2
            </button>
            <button
              className={`game-pill ${game === 'VALORANT' ? 'active-valo' : ''}`}
              onClick={() => setGame('VALORANT')}
            >
              ◈ VALORANT
            </button>
          </div>

          {/* Game-specific tip */}
          <div style={{
            marginTop: 12, padding: '8px 12px', borderRadius: 6,
            background: 'var(--deep)', border: '1px solid var(--border)',
            fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)',
          }}>
            {game === 'CS2'
              ? '💡 Works with Matchmaking, Faceit, ESEA clips'
              : '💡 Works with Competitive, Unrated, Spike Rush'}
          </div>
        </div>

        {/* Mode selector */}
        <div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', marginBottom: 12, letterSpacing: '.1em' }}>
            ANALYSIS DEPTH
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className={`mode-pill ${mode === 'quick' ? 'active' : ''}`}
              onClick={() => setMode('quick')}
            >
              ⚡ QUICK
            </button>
            <button
              className={`mode-pill ${mode === 'deep' ? 'active' : ''}`}
              onClick={() => setMode('deep')}
            >
              🔬 DEEP
            </button>
          </div>
          <div style={{
            marginTop: 12, padding: '8px 12px', borderRadius: 6,
            background: 'var(--deep)', border: '1px solid var(--border)',
            fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)',
          }}>
            {mode === 'quick'
              ? '⚡ 1fps sampling · ~30-60s · Best for highlights'
              : '🔬 2fps sampling · ~60-120s · Full match analysis'}
          </div>
        </div>

        {/* Drop zone */}
        <div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', marginBottom: 12, letterSpacing: '.1em' }}>
            GAMEPLAY FOOTAGE
          </div>
          <div
            onClick={() => !loading && inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            style={{
              border: `2px dashed ${dragging ? 'var(--cyan)' : file ? 'var(--green)' : 'var(--border)'}`,
              borderRadius: 10, padding: '20px 16px', cursor: loading ? 'not-allowed' : 'pointer',
              textAlign: 'center',
              background: dragging ? 'var(--cyan-05)' : file ? 'rgba(0,255,136,.04)' : 'var(--deep)',
              transition: 'all .25s',
              boxShadow: dragging ? '0 0 24px var(--cyan-20)' : file ? '0 0 16px var(--green-20)' : 'none',
            }}
          >
            <div style={{ fontSize: 28, marginBottom: 8 }}>
              {file ? '✅' : dragging ? '📂' : '📹'}
            </div>
            <div style={{
              fontFamily: 'var(--f-mono)', fontSize: 11,
              color: file ? 'var(--green)' : dragging ? 'var(--cyan)' : 'var(--t2)',
            }}>
              {file ? file.name : 'Drop MP4 / MOV or click to browse'}
            </div>
            {file && (
              <div style={{
                fontFamily: 'var(--f-mono)', fontSize: 10,
                color: 'var(--t3)', marginTop: 4,
              }}>
                {fmt(file.size)}
              </div>
            )}
            <input
              ref={inputRef}
              type="file"
              accept="video/*,.mp4,.mov,.avi"
              style={{ display: 'none' }}
              onChange={(e) => setFile(e.target.files[0])}
            />
          </div>
        </div>
      </div>

      {/* Analyze button */}
      <div style={{ marginTop: 24 }}>
        <button
          className="btn-primary"
          style={{ width: '100%', fontSize: 20, letterSpacing: '.1em', padding: 16 }}
          onClick={handleSubmit}
          disabled={!file || loading}
        >
          {loading
            ? <span>⏳ ANALYZING FOOTAGE...</span>
            : <span>⚡ ANALYZE FOOTAGE</span>
          }
        </button>
      </div>

      {/* Pipeline progress */}
      {loading && (
        <div style={{ marginTop: 28 }}>
          {/* Progress track */}
          <div style={{
            display: 'flex', alignItems: 'flex-start', gap: 0,
            position: 'relative', padding: '0 14px',
          }}>
            {/* Track line */}
            <div style={{
              position: 'absolute', top: 13, left: 28, right: 28, height: 2,
              background: 'var(--border)', zIndex: 0,
            }} />
            {/* Active fill */}
            <div style={{
              position: 'absolute', top: 13, left: 28, height: 2, zIndex: 1,
              background: 'linear-gradient(90deg, var(--cyan), var(--green))',
              width: `${Math.min(100, (currentStep / STEPS.length) * 100)}%`,
              transition: 'width .6s ease',
              boxShadow: '0 0 10px var(--cyan)',
            }} />

            {STEPS.map((step, i) => {
              const done = i < currentStep;
              const active = i === currentStep;
              return (
                <div key={i} style={{
                  flex: 1, display: 'flex', flexDirection: 'column',
                  alignItems: 'center', position: 'relative', zIndex: 2,
                }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: done ? 12 : 11,
                    background: done ? 'var(--green)' : active ? 'var(--cyan)' : 'var(--deep)',
                    border: `2px solid ${done ? 'var(--green)' : active ? 'var(--cyan)' : 'var(--border)'}`,
                    color: (done || active) ? '#000' : 'var(--t3)',
                    boxShadow: active ? '0 0 16px var(--cyan)' : done ? '0 0 10px rgba(0,255,136,.4)' : 'none',
                    transition: 'all .4s',
                  }}>
                    {done ? '✓' : active ? step.icon : i + 1}
                  </div>
                  <div style={{
                    marginTop: 6, fontFamily: 'var(--f-mono)', fontSize: 8,
                    color: done ? 'var(--green)' : active ? 'var(--cyan)' : 'var(--t3)',
                    textAlign: 'center', letterSpacing: '.04em',
                    maxWidth: 70, lineHeight: 1.3,
                  }}>
                    {step.label.toUpperCase()}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Status message */}
          <div style={{
            marginTop: 16, textAlign: 'center',
            fontFamily: 'var(--f-mono)', fontSize: 11,
            color: 'var(--cyan)', letterSpacing: '.08em',
          }}>
            {currentStep < STEPS.length
              ? `${STEPS[Math.min(currentStep, STEPS.length - 1)]?.icon} Processing: ${STEPS[Math.min(currentStep, STEPS.length - 1)]?.label}...`
              : '✅ Analysis complete! Rendering results...'}
          </div>
        </div>
      )}
    </div>
  );
};

export default UploadPanel;
