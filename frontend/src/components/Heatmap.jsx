import React, { useEffect, useRef } from 'react';

const CS2_ZONES  = ['CT SPAWN', 'A SITE', 'MID', 'T SPAWN', 'B SITE', 'A LONG', 'SHORT', 'RAMP'];
const VALO_ZONES = ['ATTACKER SPAWN', 'A SITE', 'MID', 'DEFENDER SPAWN', 'B SITE', 'FLANK', 'LOBBY', 'ARCH'];

const Heatmap = ({ points, mapName }) => {
  const canvasRef = useRef();

  // Normalize points to {x, y, intensity}
  const safePoints = (points || []).map((p, i) => ({
    x: typeof p.x === 'number' ? p.x : p[0] ?? 0.5,
    y: typeof p.y === 'number' ? p.y : p[1] ?? 0.5,
    intensity: typeof p.weight === 'number' ? Math.min(1, p.weight / 3)
      : typeof p.intensity === 'number' ? p.intensity
      : 0.5 + Math.random() * 0.5,
  }));

  const safeMapName = mapName || 'Unknown';
  const isValorant = ['Bind', 'Haven', 'Split', 'Ascent', 'Icebox', 'Breeze', 'Fracture', 'Pearl'].some(
    m => safeMapName.toLowerCase().includes(m.toLowerCase())
  );
  const zones = isValorant ? VALO_ZONES : CS2_ZONES;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;

    let alpha = 0;
    let animId;

    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      ctx.globalAlpha = alpha;

      // Dark background
      ctx.fillStyle = '#020810';
      ctx.fillRect(0, 0, W, H);

      // Subtle grid
      ctx.strokeStyle = '#0b1928';
      ctx.lineWidth = 1;
      for (let x = 0; x <= W; x += 48) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
      }
      for (let y = 0; y <= H; y += 48) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      }

      // Grid dots
      ctx.fillStyle = '#0d2030';
      for (let x = 0; x <= W; x += 48) {
        for (let y = 0; y <= H; y += 48) {
          ctx.beginPath(); ctx.arc(x, y, 1.5, 0, Math.PI * 2); ctx.fill();
        }
      }

      // Map watermark
      ctx.save();
      ctx.font = 'bold 52px Rajdhani, sans-serif';
      ctx.fillStyle = 'rgba(10,25,45,.9)';
      ctx.textAlign = 'left';
      ctx.fillText(safeMapName.toUpperCase(), 16, H - 16);
      ctx.restore();

      // Corner label
      ctx.save();
      ctx.font = '10px "Share Tech Mono", monospace';
      ctx.fillStyle = 'rgba(0,212,255,.4)';
      ctx.textAlign = 'left';
      ctx.fillText('ACTIVITY HEATMAP', 12, 20);
      ctx.restore();

      // Render heatmap blobs
      if (safePoints.length > 0) {
        safePoints.forEach((p, i) => {
          const px = p.x * W;
          const py = p.y * H;
          const radius = 50 + p.intensity * 50;

          // Outer glow
          const grad = ctx.createRadialGradient(px, py, 0, px, py, radius);
          grad.addColorStop(0,   `rgba(255,31,75,${0.35 + p.intensity * 0.5})`);
          grad.addColorStop(0.4, `rgba(255,80,0,${0.15 + p.intensity * 0.25})`);
          grad.addColorStop(1,   'rgba(255,31,75,0)');
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(px, py, radius, 0, Math.PI * 2);
          ctx.fill();

          // Inner bright dot
          const inner = ctx.createRadialGradient(px, py, 0, px, py, 8);
          inner.addColorStop(0, 'rgba(255,255,255,.9)');
          inner.addColorStop(1, 'rgba(255,50,80,0)');
          ctx.fillStyle = inner;
          ctx.beginPath();
          ctx.arc(px, py, 8, 0, Math.PI * 2);
          ctx.fill();

          // Zone label
          ctx.save();
          ctx.font = 'bold 10px "Share Tech Mono", monospace';
          ctx.fillStyle = 'rgba(255,255,255,.75)';
          ctx.textAlign = 'left';
          ctx.fillText(zones[i % zones.length], px + 10, py - 8);
          ctx.restore();
        });
      } else {
        // Default "no data" state
        ctx.save();
        ctx.font = '13px "Share Tech Mono", monospace';
        ctx.fillStyle = 'rgba(46,74,102,.8)';
        ctx.textAlign = 'center';
        ctx.fillText('KILL POSITIONS UNAVAILABLE', W / 2, H / 2 - 10);
        ctx.font = '10px "Share Tech Mono", monospace';
        ctx.fillText('Requires kill event timestamps', W / 2, H / 2 + 12);
        ctx.restore();
      }

      if (alpha < 1) {
        alpha = Math.min(1, alpha + 0.035);
        animId = requestAnimationFrame(draw);
      }
    };

    animId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animId);
  }, [safePoints, safeMapName]);

  return (
    <div className="card bracket anim-up delay-3" style={{ overflow: 'hidden', position: 'relative' }}>
      <div style={{
        position: 'absolute', top: 12, right: 12, zIndex: 10,
        fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--cyan)',
        background: 'rgba(5,13,26,.9)', border: '1px solid var(--border)',
        padding: '4px 10px', borderRadius: 4, letterSpacing: '.1em',
      }}>
        📍 KILL POSITION MAP
      </div>
      <canvas
        ref={canvasRef}
        width={700}
        height={420}
        style={{ display: 'block', width: '100%', height: 'auto' }}
      />
    </div>
  );
};

export default Heatmap;
