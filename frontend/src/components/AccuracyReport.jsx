import React from 'react';

const AccuracyReport = ({ report }) => {
  if (!report) return null;

  const {
    detected_kills,
    ground_truth_kills,
    kill_error,
    precision,
    recall,
    f1_score,
    kill_accuracy_pct,
    overall_score,
    summary,
  } = report;

  const getScoreColor = (score) => {
    if (score >= 80) return 'var(--green)';
    if (score >= 60) return 'var(--yellow)';
    return 'var(--red)';
  };

  const MetricCard = ({ label, value, suffix = '' }) => (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: '16px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--f-mono)',
        fontSize: 10,
        color: 'var(--t3)',
        textTransform: 'uppercase',
        marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'var(--f-title)',
        fontSize: 28,
        fontWeight: 700,
        color: getScoreColor(value),
      }}>
        {typeof value === 'number' ? value.toFixed(1) : value}{suffix}
      </div>
    </div>
  );

  return (
    <div style={{
      background: 'var(--panel)',
      border: '1px solid var(--border)',
      borderTop: '2px solid var(--green)',
      borderRadius: 8,
      padding: '20px',
      marginTop: '20px',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 20,
      }}>
        <span style={{ fontSize: 20 }}>📊</span>
        <span style={{
          fontFamily: 'var(--f-title)',
          fontWeight: 600,
          fontSize: 18,
          color: 'var(--green)',
        }}>
          ACCURACY REPORT
        </span>
        <span style={{
          fontFamily: 'var(--f-mono)',
          fontSize: 11,
          color: 'var(--t3)',
          marginLeft: 'auto',
        }}>
          ML Pipeline vs Ground Truth
        </span>
      </div>

      {/* Stats Comparison */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 12,
        marginBottom: 20,
        padding: '16px',
        background: 'var(--deep)',
        borderRadius: 6,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontFamily: 'var(--f-mono)',
            fontSize: 10,
            color: 'var(--t3)',
            marginBottom: 4,
          }}>
            DETECTED KILLS
          </div>
          <div style={{
            fontFamily: 'var(--f-title)',
            fontSize: 24,
            color: 'var(--cyan)',
          }}>
            {detected_kills}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontFamily: 'var(--f-mono)',
            fontSize: 10,
            color: 'var(--t3)',
            marginBottom: 4,
          }}>
            ACTUAL KILLS
          </div>
          <div style={{
            fontFamily: 'var(--f-title)',
            fontSize: 24,
            color: 'var(--t1)',
          }}>
            {ground_truth_kills}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontFamily: 'var(--f-mono)',
            fontSize: 10,
            color: 'var(--t3)',
            marginBottom: 4,
          }}>
            DIFFERENCE
          </div>
          <div style={{
            fontFamily: 'var(--f-title)',
            fontSize: 24,
            color: kill_error === 0 ? 'var(--green)' : kill_error > 0 ? 'var(--yellow)' : 'var(--red)',
          }}>
            {kill_error > 0 ? `+${kill_error}` : kill_error}
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: 12,
        marginBottom: 20,
      }}>
        <MetricCard label="Precision" value={precision * 100} suffix="%" />
        <MetricCard label="Recall" value={recall * 100} suffix="%" />
        <MetricCard label="F1 Score" value={f1_score} />
        <MetricCard label="Kill Accuracy" value={kill_accuracy_pct} suffix="%" />
        <MetricCard label="Overall Score" value={overall_score} suffix="%" />
      </div>

      {/* Summary Text */}
      {summary && (
        <div style={{
          background: 'var(--deep)',
          border: '1px solid var(--border)',
          borderRadius: 6,
          padding: '16px',
        }}>
          <div style={{
            fontFamily: 'var(--f-mono)',
            fontSize: 10,
            color: 'var(--cyan)',
            marginBottom: 8,
            textTransform: 'uppercase',
          }}>
            Detailed Analysis
          </div>
          <pre style={{
            fontFamily: 'var(--f-mono)',
            fontSize: 12,
            color: 'var(--t2)',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.6,
            margin: 0,
          }}>
            {summary}
          </pre>
        </div>
      )}

      {/* Legend */}
      <div style={{
        marginTop: 16,
        paddingTop: 16,
        borderTop: '1px solid var(--border)',
        fontFamily: 'var(--f-mono)',
        fontSize: 10,
        color: 'var(--t3)',
      }}>
        <div style={{ marginBottom: 8 }}>
          <strong style={{ color: 'var(--green)' }}>● 80-100%</strong> Excellent — Ready for production use
        </div>
        <div style={{ marginBottom: 8 }}>
          <strong style={{ color: 'var(--yellow)' }}>● 60-79%</strong> Good — Minor improvements needed
        </div>
        <div>
          <strong style={{ color: 'var(--red)' }}>● Below 60%</strong> Fair — Requires more training data
        </div>
      </div>
    </div>
  );
};

export default AccuracyReport;
