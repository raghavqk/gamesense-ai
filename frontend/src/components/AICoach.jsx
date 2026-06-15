import React, { useState, useEffect, useRef } from 'react';

const SUGGESTIONS = [
  '🎯 How can I improve my aim?',
  "⚠️ What's my biggest weakness?",
  '🧠 How do I play my playstyle better?',
  '🔫 Analyze my weapon choices',
  '📈 Give me a 1-week improvement plan',
  '💡 Best drills for my stats?',
];

const renderBold = (text) =>
  text.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--cyan)">$1</strong>');

const TypingDots = () => (
  <div style={{ display: 'flex', gap: 5, padding: '12px 0' }}>
    {[0, 1, 2].map(i => (
      <span key={i} className="pulse" style={{
        display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
        background: 'var(--cyan)', animationDelay: `${i * 0.25}s`,
      }} />
    ))}
  </div>
);

const CoachAvatar = () => (
  <div style={{
    width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
    background: 'linear-gradient(135deg, #f97316, #f59e0b)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 18,
    boxShadow: '0 0 16px rgba(249,115,22,.35)',
  }}>
    🔥
  </div>
);

// ── Tiny status pill ──────────────────────────────────────────────────────────
const StatusPill = ({ status }) => {
  const map = {
    connected:   { color: 'var(--green)',  dot: 'var(--green)',  label: 'CONNECTED',   glow: '0 0 10px #22c55e' },
    disconnected:{ color: '#ef4444',       dot: '#ef4444',       label: 'DISCONNECTED', glow: '0 0 10px #ef4444' },
    checking:    { color: 'var(--gold)',   dot: 'var(--gold)',   label: 'CHECKING…',   glow: '0 0 10px #f59e0b' },
    idle:        { color: 'var(--t3)',     dot: 'var(--t3)',     label: 'NOT TESTED',  glow: 'none' },
  };
  const s = map[status] || map.idle;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span className={status === 'connected' ? 'pulse' : ''} style={{
        width: 8, height: 8, borderRadius: '50%',
        background: s.dot, display: 'inline-block',
        boxShadow: s.glow,
      }} />
      <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: s.color, letterSpacing: '.1em' }}>
        {s.label}
      </span>
    </div>
  );
};

// ── API Key Panel ─────────────────────────────────────────────────────────────
const ApiKeyPanel = ({ apiKey, setApiKey, status, onTest, onClear, testResult }) => {
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState(status !== 'connected');

  return (
    <div style={{
      borderBottom: '1px solid var(--border)',
      background: status === 'connected'
        ? 'linear-gradient(90deg, rgba(34,197,94,.06), var(--deep))'
        : 'linear-gradient(90deg, rgba(249,115,22,.06), var(--deep))',
      transition: 'background .4s',
    }}>
      {/* Collapsible header */}
      <div
        onClick={() => setExpanded(e => !e)}
        style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 24px', cursor: 'pointer',
        }}
      >
        <span style={{ fontSize: 14 }}>🔑</span>
        <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t2)', letterSpacing: '.08em', flex: 1 }}>
          GROQ API KEY CONFIGURATION
        </span>
        <StatusPill status={status} />
        <span style={{ color: 'var(--t3)', fontSize: 12, marginLeft: 8 }}>
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {/* Expandable body */}
      {expanded && (
        <div style={{ padding: '0 24px 16px' }}>
          <div style={{
            fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)',
            marginBottom: 10, lineHeight: 1.7,
          }}>
            Get a free API key at{' '}
            <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer"
              style={{ color: 'var(--cyan)', textDecoration: 'none' }}>
              console.groq.com/keys
            </a>
            {' '}→ Paste it below → Click <strong style={{ color: 'var(--gold)' }}>TEST CONNECTION</strong>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {/* Key input */}
            <div style={{ position: 'relative', flex: 1 }}>
              <input
                type={visible ? 'text' : 'password'}
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: 'var(--deep)', border: '1px solid var(--border)',
                  borderRadius: 6, padding: '9px 40px 9px 12px',
                  fontFamily: 'var(--f-mono)', fontSize: 12, color: 'var(--t1)',
                  outline: 'none',
                  transition: 'border-color .2s',
                }}
                onFocus={e => e.target.style.borderColor = 'var(--cyan)'}
                onBlur={e => e.target.style.borderColor = 'var(--border)'}
              />
              {/* Show/hide toggle */}
              <button
                onClick={() => setVisible(v => !v)}
                title={visible ? 'Hide key' : 'Show key'}
                style={{
                  position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--t3)', fontSize: 14, padding: 0, lineHeight: 1,
                }}
              >
                {visible ? '🙈' : '👁️'}
              </button>
            </div>

            {/* Test button */}
            <button
              onClick={onTest}
              disabled={status === 'checking' || !apiKey.trim()}
              style={{
                fontFamily: 'var(--f-mono)', fontSize: 11, fontWeight: 700,
                padding: '9px 18px', borderRadius: 6, cursor: 'pointer',
                background: status === 'checking'
                  ? 'var(--card)' : 'linear-gradient(135deg, #f97316, #f59e0b)',
                border: 'none', color: '#000',
                whiteSpace: 'nowrap',
                opacity: (!apiKey.trim() || status === 'checking') ? 0.5 : 1,
                transition: 'all .2s',
              }}
            >
              {status === 'checking' ? '⟳ TESTING…' : '⚡ TEST CONNECTION'}
            </button>

            {/* Clear button */}
            {apiKey && (
              <button
                onClick={onClear}
                title="Clear key"
                style={{
                  background: 'none', border: '1px solid var(--border)',
                  borderRadius: 6, padding: '9px 12px', cursor: 'pointer',
                  color: 'var(--t3)', fontSize: 12, fontFamily: 'var(--f-mono)',
                }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Result message */}
          {testResult && (
            <div style={{
              marginTop: 10, padding: '8px 14px', borderRadius: 6,
              background: testResult.success ? 'rgba(34,197,94,.1)' : 'rgba(239,68,68,.1)',
              border: `1px solid ${testResult.success ? 'rgba(34,197,94,.3)' : 'rgba(239,68,68,.3)'}`,
              fontFamily: 'var(--f-mono)', fontSize: 11,
              color: testResult.success ? 'var(--green)' : '#f87171',
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span>{testResult.success ? '✅' : '❌'}</span>
              <span>{testResult.message}</span>
              {testResult.model && (
                <span style={{ marginLeft: 'auto', color: 'var(--t3)', fontSize: 10 }}>
                  Model: {testResult.model}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ── Main AICoach Component ────────────────────────────────────────────────────
const AICoach = ({ contextData }) => {
  const [question, setQuestion]  = useState('');
  const [loading,  setLoading]   = useState(false);
  const [apiKey,   setApiKey]    = useState('');
  const [connStatus, setConnStatus] = useState('idle'); // idle | checking | connected | disconnected
  const [testResult, setTestResult] = useState(null);
  const chatRef = useRef(null);

  const [history, setHistory] = useState([
    {
      role: 'coach',
      text: contextData
        ? `Analysis complete. I've reviewed your footage — **${contextData.kills} kills, ${contextData.deaths} deaths** (${contextData.kd_ratio} K/D) on ${contextData.map_name || 'the map'} with ${contextData.headshot_percentage}% headshot rate.\n\nPaste your **Groq API key** above and click **TEST CONNECTION** to activate coaching.`
        : 'Welcome to GameSense AI Coach — powered by **Groq LLaMA**. Paste your Groq API key above and click **TEST CONNECTION** to activate personalized coaching.',
    },
  ]);

  // Load saved key from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('gamesense_groq_key');
    if (saved) {
      setApiKey(saved);
      setConnStatus('idle'); // Don't auto-test; let user confirm
    }
  }, []);

  const scrollToBottom = () => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  };

  // Test connection
  const handleTest = async () => {
    if (!apiKey.trim()) return;
    setConnStatus('checking');
    setTestResult(null);

    try {
      const res  = await fetch('/api/coach/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey.trim() }),
      });
      const data = await res.json();
      const result = data.data || {};

      if (data.success) {
        setConnStatus('connected');
        localStorage.setItem('gamesense_groq_key', apiKey.trim());
        setTestResult({ success: true, message: result.message, model: result.model });
        setHistory(prev => [...prev, {
          role: 'coach',
          text: `✅ **Connected via ${result.model}!** I'm ready to coach you. Ask me anything about your gameplay.`,
        }]);
        setTimeout(scrollToBottom, 100);
      } else {
        setConnStatus('disconnected');
        setTestResult({ success: false, message: result.message || 'Connection failed.' });
      }
    } catch (err) {
      setConnStatus('disconnected');
      setTestResult({ success: false, message: `Network error: ${err.message}` });
    }
  };

  const handleClear = () => {
    setApiKey('');
    setConnStatus('idle');
    setTestResult(null);
    localStorage.removeItem('gamesense_groq_key');
  };

  // Send chat message
  const handleAsk = async (q) => {
    const text = (q || question).trim();
    if (!text) return;

    if (connStatus !== 'connected' && !apiKey.trim()) {
      setHistory(prev => [...prev, {
        role: 'coach',
        text: '⚠️ Please paste your **Groq API key** and click **TEST CONNECTION** first.',
      }]);
      setTimeout(scrollToBottom, 100);
      return;
    }

    setHistory(prev => [...prev, { role: 'user', text }]);
    setQuestion('');
    setLoading(true);
    setTimeout(scrollToBottom, 50);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: text,
          analysis_context: { data: contextData },
          api_key: apiKey.trim(),
        }),
      });
      const data   = await res.json();
      const answer = data.success
        ? data.data?.answer
        : (data.error || 'Coach is unavailable. Try again.');
      setHistory(prev => [...prev, { role: 'coach', text: answer }]);
    } catch {
      setHistory(prev => [...prev, {
        role: 'coach',
        text: '⚠️ Connection error. Ensure the backend is running on port 8000.',
      }]);
    } finally {
      setLoading(false);
      setTimeout(scrollToBottom, 100);
    }
  };

  const ctx = contextData;
  const ctxBadges = ctx ? [
    { label: `${ctx.kills}K/${ctx.deaths}D/${ctx.assists || 0}A`, color: 'var(--cyan)' },
    { label: `KD ${ctx.kd_ratio}`,   color: ctx.kd_ratio >= 1.5 ? 'var(--green)' : 'var(--gold)' },
    { label: `${ctx.headshot_percentage}% HS`, color: 'var(--gold)' },
    { label: ctx.most_used_weapon,   color: 'var(--purple)' },
    { label: ctx.playstyle,          color: 'var(--cyan)' },
    { label: ctx.map_name,           color: 'var(--t2)' },
  ].filter(b => b.label && b.label !== 'undefined' && b.label !== 'Unknown') : [];

  return (
    <div style={{
      background: 'var(--panel)',
      border: '1px solid var(--border)',
      borderTop: '2px solid #f97316',
      borderRadius: 10,
      overflow: 'hidden',
      boxShadow: '0 0 40px rgba(249,115,22,.07)',
    }}>

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '16px 24px', borderBottom: '1px solid var(--border)',
        background: 'linear-gradient(90deg, var(--deep), rgba(249,115,22,.04))',
      }}>
        <CoachAvatar />
        <div>
          <div style={{
            fontFamily: 'var(--f-title)', fontWeight: 700, fontSize: 22,
            color: '#f97316', letterSpacing: '.04em',
          }}>
            GAMESENSE AI COACH
          </div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', letterSpacing: '.08em' }}>
            POWERED BY GROQ · LLAMA 3.3 70B · PERSONALIZED ESPORTS COACHING
          </div>
        </div>
        <div style={{ flex: 1 }} />
        <StatusPill status={connStatus} />
      </div>

      {/* ── API Key Panel ───────────────────────────────────────────────── */}
      <ApiKeyPanel
        apiKey={apiKey}
        setApiKey={setApiKey}
        status={connStatus}
        onTest={handleTest}
        onClear={handleClear}
        testResult={testResult}
      />

      {/* ── Context strip ───────────────────────────────────────────────── */}
      {ctxBadges.length > 0 && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 8, padding: '10px 24px',
          borderBottom: '1px solid var(--border)', background: 'var(--card)',
        }}>
          <span style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--t3)', letterSpacing: '.1em', marginRight: 4, alignSelf: 'center' }}>
            MATCH CONTEXT:
          </span>
          {ctxBadges.map((b, i) => (
            <span key={i} style={{
              fontFamily: 'var(--f-mono)', fontSize: 10,
              padding: '3px 10px', borderRadius: 4,
              background: `${b.color}18`,
              color: b.color,
              border: `1px solid ${b.color}35`,
            }}>
              {b.label}
            </span>
          ))}
        </div>
      )}

      {/* ── Chat history ────────────────────────────────────────────────── */}
      <div ref={chatRef} style={{
        height: 340, overflowY: 'auto', padding: '20px 24px',
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        {history.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', gap: 10 }}>
            {msg.role === 'coach' && <CoachAvatar />}
            <div style={{
              maxWidth: '76%', padding: '12px 18px', borderRadius: 10,
              background: msg.role === 'user'
                ? 'linear-gradient(135deg, #f97316, #f59e0b)'
                : 'linear-gradient(135deg, var(--deep), var(--card))',
              borderLeft: msg.role === 'coach' ? '3px solid #f97316' : 'none',
              color: msg.role === 'user' ? '#000' : 'var(--t1)',
              fontSize: 14, lineHeight: 1.65,
              boxShadow: msg.role === 'user'
                ? '0 4px 20px rgba(249,115,22,.28)'
                : '0 2px 12px rgba(0,0,0,.4)',
            }}>
              {msg.role === 'coach' && (
                <div style={{
                  fontFamily: 'var(--f-mono)', fontSize: 9,
                  color: '#f97316', marginBottom: 8, letterSpacing: '.12em',
                }}>
                  🔥 COACH AI — GROQ LLaMA
                </div>
              )}
              <div
                style={{ fontFamily: 'var(--f-ui)', fontSize: 14 }}
                dangerouslySetInnerHTML={{ __html: renderBold(msg.text || '') }}
              />
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: 10 }}>
            <CoachAvatar />
            <div style={{
              padding: '12px 18px', borderRadius: 10,
              background: 'var(--deep)', borderLeft: '3px solid #f97316',
            }}>
              <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: '#f97316', marginBottom: 4 }}>
                COACH AI — ANALYZING...
              </div>
              <TypingDots />
            </div>
          </div>
        )}
      </div>

      {/* ── Quick suggestions ───────────────────────────────────────────── */}
      <div style={{
        padding: '12px 24px',
        borderTop: '1px solid var(--border)',
        background: 'var(--card)',
      }}>
        <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--t3)', letterSpacing: '.1em', marginBottom: 8 }}>
          QUICK QUESTIONS:
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              onClick={() => handleAsk(s.replace(/^[^ ]+ /, ''))}
              disabled={loading}
              style={{
                fontFamily: 'var(--f-mono)', fontSize: 11, cursor: 'pointer',
                background: 'var(--panel)', border: '1px solid var(--border)',
                color: 'var(--t2)', padding: '5px 12px', borderRadius: 5,
                transition: 'all .2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = '#f97316';
                e.currentTarget.style.borderColor = '#f97316';
                e.currentTarget.style.background = 'rgba(249,115,22,.08)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = 'var(--t2)';
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.background = 'var(--panel)';
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* ── Input area ──────────────────────────────────────────────────── */}
      <div style={{ padding: '14px 24px', borderTop: '1px solid var(--border)', background: 'var(--deep)' }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <textarea
            className="chat-input"
            rows={2}
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
            placeholder={connStatus === 'connected'
              ? '>_ Ask your coach anything about your performance...'
              : '>_ Connect your Groq API key above to start coaching...'}
            disabled={loading}
          />
          <button
            className="btn-primary"
            onClick={() => handleAsk()}
            disabled={loading || !question.trim()}
            style={{
              padding: '0 28px', whiteSpace: 'nowrap', fontSize: 15, minWidth: 110,
              background: connStatus === 'connected'
                ? 'linear-gradient(135deg, #f97316, #f59e0b)'
                : 'var(--card)',
              border: connStatus === 'connected' ? 'none' : '1px solid var(--border)',
              color: connStatus === 'connected' ? '#000' : 'var(--t3)',
            }}
          >
            {loading ? <span className="spin" style={{ display: 'inline-block' }}>⟳</span> : 'ASK ›'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AICoach;
