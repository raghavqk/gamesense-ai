import React, { useState } from 'react';

const GroundTruthInput = ({ detectedStats, onSubmit }) => {
  const [stats, setStats] = useState({
    kills: '',
    deaths: '',
    assists: '',
    headshot_pct: '',
    map_name: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (field, value) => {
    setStats(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    await onSubmit({
      kills: parseInt(stats.kills) || 0,
      deaths: parseInt(stats.deaths) || 0,
      assists: parseInt(stats.assists) || 0,
      headshot_pct: parseInt(stats.headshot_pct) || 0,
      map_name: stats.map_name || 'Unknown',
    });
    setIsSubmitting(false);
  };

  return (
    <div style={{
      background: 'var(--panel)',
      border: '1px solid var(--border)',
      borderTop: '2px solid var(--cyan)',
      borderRadius: 8,
      padding: '20px',
      marginTop: '20px',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 16,
      }}>
        <span style={{ fontSize: 20 }}>🎯</span>
        <span style={{
          fontFamily: 'var(--f-title)',
          fontWeight: 600,
          fontSize: 18,
          color: 'var(--cyan)',
        }}>
          GROUND TRUTH INPUT
        </span>
        <span style={{
          fontFamily: 'var(--f-mono)',
          fontSize: 11,
          color: 'var(--t3)',
          marginLeft: 'auto',
        }}>
          Enter actual scoreboard stats for accuracy comparison
        </span>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: 12,
        marginBottom: 16,
      }}>
        {[
          { key: 'kills', label: 'Kills', placeholder: '15' },
          { key: 'deaths', label: 'Deaths', placeholder: '4' },
          { key: 'assists', label: 'Assists', placeholder: '3' },
          { key: 'headshot_pct', label: 'HS %', placeholder: '62' },
        ].map(({ key, label, placeholder }) => (
          <div key={key}>
            <label style={{
              display: 'block',
              fontFamily: 'var(--f-mono)',
              fontSize: 10,
              color: 'var(--t3)',
              marginBottom: 4,
              textTransform: 'uppercase',
            }}>
              {label}
            </label>
            <input
              type="number"
              value={stats[key]}
              onChange={(e) => handleChange(key, e.target.value)}
              placeholder={placeholder}
              style={{
                width: '100%',
                padding: '8px 12px',
                background: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: 4,
                color: 'var(--t1)',
                fontFamily: 'var(--f-mono)',
                fontSize: 14,
              }}
            />
          </div>
        ))}
        
        <div>
          <label style={{
            display: 'block',
            fontFamily: 'var(--f-mono)',
            fontSize: 10,
            color: 'var(--t3)',
            marginBottom: 4,
            textTransform: 'uppercase',
          }}>
            Map
          </label>
          <input
            type="text"
            value={stats.map_name}
            onChange={(e) => handleChange('map_name', e.target.value)}
            placeholder="de_mirage"
            style={{
              width: '100%',
              padding: '8px 12px',
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              color: 'var(--t1)',
              fontFamily: 'var(--f-mono)',
              fontSize: 14,
            }}
          />
        </div>
      </div>

      <div style={{
        display: 'flex',
        gap: 12,
        alignItems: 'center',
      }}>
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          style={{
            padding: '10px 24px',
            background: 'var(--cyan)',
            border: 'none',
            borderRadius: 4,
            color: '#000',
            fontFamily: 'var(--f-title)',
            fontWeight: 600,
            fontSize: 14,
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            opacity: isSubmitting ? 0.6 : 1,
          }}
        >
          {isSubmitting ? 'COMPARING...' : 'COMPARE ACCURACY →'}
        </button>

        {detectedStats && (
          <div style={{
            fontFamily: 'var(--f-mono)',
            fontSize: 11,
            color: 'var(--t3)',
          }}>
            Detected: {detectedStats.kills}K / {detectedStats.deaths}D / {detectedStats.assists}A
          </div>
        )}
      </div>
    </div>
  );
};

export default GroundTruthInput;
