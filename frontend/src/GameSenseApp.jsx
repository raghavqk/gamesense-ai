import React, { useState } from 'react';
import Header from './components/Header';
import UploadPanel from './components/UploadPanel';
import MapBar from './components/MapBar';
import StatCards from './components/StatCards';
import { KillTimeline, WeaponChart } from './components/Charts';
import Heatmap from './components/Heatmap';
import MultiKillAndPlaystyle from './components/MultiKillAndPlaystyle';
import WeaponTable from './components/WeaponTable';
import AICoach from './components/AICoach';
import GroundTruthInput from './components/GroundTruthInput';
import AccuracyReport from './components/AccuracyReport';

// Normalize API response for backwards compatibility
const normalizeResponse = (apiResponse) => {
  if (apiResponse.hasOwnProperty('success')) {
    return {
      success: apiResponse.success,
      data: apiResponse.data || {},
      confidence: apiResponse.confidence || 0,
      pipeline: apiResponse.pipeline || null,
      error: apiResponse.error || null,
    };
  }
  return {
    success: apiResponse.status === 'ok',
    data: apiResponse.data || {},
    confidence: 0,
    pipeline: null,
    error: apiResponse.errors?.join(', ') || null,
  };
};

// Check if stats look empty/invalid
const getDataWarning = (data) => {
  if (!data) return null;
  const kills = data.kills ?? 0;
  const deaths = data.deaths ?? 0;
  const weaponCount = Object.keys(data.weapon_usage || {}).length;
  if (kills === 0 && deaths === 0 && weaponCount === 0) {
    return 'Analysis produced no detections. The video may not contain a visible kill feed or scoreboard. Try a longer clip or ensure the video is unedited first-person CS2 or Valorant footage.';
  }
  return null;
};

// Loading skeleton placeholder
const LoadingSkeleton = () => (
  <div style={{ marginTop: 32, display: 'flex', flexDirection: 'column', gap: 16 }}>
    <div className="shimmer" style={{ height: 80, borderRadius: 10 }} />
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 14 }}>
      {[...Array(6)].map((_, i) => (
        <div key={i} className="shimmer" style={{ height: 140, borderRadius: 10 }} />
      ))}
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div className="shimmer" style={{ height: 300, borderRadius: 10 }} />
      <div className="shimmer" style={{ height: 300, borderRadius: 10 }} />
    </div>
  </div>
);

export default function GameSenseApp() {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('stats');
  const [accuracyReport, setAccuracyReport] = useState(null);
  const [pipelineInfo, setPipelineInfo] = useState(null);

  const handleUpload = async (file, gameTitle, mode) => {
    setLoading(true);
    setError(null);
    setAnalysis(null);
    setAccuracyReport(null);
    setPipelineInfo(null);
    setCurrentStep(1);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('game_title', gameTitle);
    formData.append('mode', mode);

    // Simulate step progression
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => prev < 5 ? prev + 1 : prev);
    }, mode === 'deep' ? 12000 : 8000);

    try {
      const res = await fetch('/api/pipeline/analyze-local', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errorText.slice(0, 200)}`);
      }

      const rawData = await res.json();
      const data = normalizeResponse(rawData);
      clearInterval(stepInterval);

      if (data.success) {
        setCurrentStep(6);
        setPipelineInfo({ pipeline: data.pipeline, confidence: data.confidence });
        setTimeout(() => {
          setAnalysis(data.data);
          setLoading(false);
          setCurrentStep(0);
          setActiveTab('stats'); // Always show stats first
        }, 800);
      } else {
        setError(data.error || 'Analysis failed. Please try again.');
        setLoading(false);
        setCurrentStep(0);
      }
    } catch (e) {
      clearInterval(stepInterval);
      setError(`Network error: ${e.message}. Is the backend running on port 8000?`);
      setLoading(false);
      setCurrentStep(0);
    }
  };

  const handleGroundTruthSubmit = async (groundTruth) => {
    try {
      const res = await fetch('/api/analysis/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          detected_stats: {
            kills: analysis?.kills || 0,
            deaths: analysis?.deaths || 0,
            assists: analysis?.assists || 0,
            headshot_percentage: analysis?.headshot_percentage || 0,
          },
          ground_truth: groundTruth,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setAccuracyReport(data.data);
      }
    } catch (e) {
      console.error('Comparison failed:', e);
    }
  };

  const dataWarning = getDataWarning(analysis);
  const isHeuristicFallback = analysis?.data_source === 'heuristic_fallback';

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--void)',
      paddingBottom: 80,
      position: 'relative',
      zIndex: 1,
    }}>
      <div className="hud-top-border" />

      <div style={{ maxWidth: 1360, margin: '0 auto', padding: '0 28px' }}>
        <Header />

        {/* Upload panel */}
        <UploadPanel onUpload={handleUpload} loading={loading} currentStep={currentStep} />

        {/* Error display */}
        {error && (
          <div className="anim-up" style={{
            marginTop: 20, padding: '16px 20px',
            background: 'var(--red-20)', border: '1px solid var(--red)',
            borderRadius: 10, fontFamily: 'var(--f-mono)', fontSize: 12, color: 'var(--red)',
            display: 'flex', gap: 12, alignItems: 'flex-start',
          }}>
            <span style={{ fontSize: 18 }}>⚠</span>
            <div>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>ANALYSIS ERROR</div>
              {error}
            </div>
          </div>
        )}

        {/* Loading skeletons */}
        {loading && <LoadingSkeleton />}

        {/* Results */}
        {analysis && !loading && (
          <div style={{ marginTop: 32 }}>

            {/* Heuristic fallback notice */}
            {isHeuristicFallback && (
              <div className="anim-up" style={{
                marginBottom: 16, padding: '10px 16px',
                background: 'var(--gold-20)', border: '1px solid var(--gold)',
                borderRadius: 8, fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--gold)',
                display: 'flex', gap: 10, alignItems: 'center',
              }}>
                <span>💡</span>
                <span>
                  <strong>HEURISTIC MODE:</strong> OCR could not detect text in kill feed — showing estimated stats based on video duration.
                  For better accuracy, use a clear, unedited gameplay clip where the kill feed is visible in the top-right corner.
                </span>
              </div>
            )}

            {/* Data warning */}
            {dataWarning && (
              <div className="anim-up" style={{
                marginBottom: 16, padding: '12px 16px',
                background: 'var(--gold-20)', border: '1px solid var(--gold)',
                borderRadius: 8, fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--gold)',
              }}>
                ⚠ {dataWarning}
              </div>
            )}

            {/* Tab navigation */}
            <div style={{
              display: 'flex', gap: 0, marginBottom: 28,
              background: 'var(--panel)',
              border: '1px solid var(--border)',
              borderRadius: 10, overflow: 'hidden',
              padding: 4,
            }}>
              {[
                ['stats',  '📊 STATISTICS',  'Match performance data, weapon analysis, kill timeline'],
                ['coach',  '🔥 AI COACH',     'Personalized coaching powered by Groq LLaMA'],
                ['compare','🎯 ACCURACY',    'Compare detected stats vs ground truth'],
              ].map(([key, label, desc]) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  style={{
                    flex: 1, fontFamily: 'var(--f-title)', fontWeight: 700, fontSize: 16,
                    letterSpacing: '.05em', cursor: 'pointer', padding: '12px 20px',
                    border: 'none', borderRadius: 8,
                    background: activeTab === key
                      ? 'linear-gradient(135deg, rgba(0,212,255,.15), rgba(0,212,255,.05))'
                      : 'transparent',
                    color: activeTab === key ? 'var(--cyan)' : 'var(--t2)',
                    boxShadow: activeTab === key ? 'inset 0 0 0 1px rgba(0,212,255,.3)' : 'none',
                    transition: 'all .2s',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* STATS TAB */}
            {activeTab === 'stats' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {/* Validation notice */}
                {analysis.validation && !analysis.validation.is_valid && (
                  <div style={{
                    padding: '10px 16px', background: 'var(--gold-20)',
                    border: '1px solid var(--gold)', borderRadius: 8,
                    fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--gold)',
                  }}>
                    ⚠ Auto-corrected {analysis.validation.issues?.length || 0} data issues
                  </div>
                )}

                <MapBar data={analysis} />
                <StatCards data={analysis} />

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                  <KillTimeline data={analysis.timeline || []} />
                  <WeaponChart usageData={analysis.weapon_usage || {}} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20 }}>
                  <Heatmap points={analysis.heatmap_points || []} mapName={analysis.map_name} />
                  <MultiKillAndPlaystyle data={analysis} />
                </div>

                <WeaponTable
                  usageData={analysis.weapon_usage || {}}
                  mostUsed={analysis.most_used_weapon}
                />
              </div>
            )}

            {/* AI COACH TAB */}
            {activeTab === 'coach' && (
              <AICoach contextData={analysis} />
            )}

            {/* ACCURACY TAB */}
            {activeTab === 'compare' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                <GroundTruthInput
                  detectedStats={analysis}
                  onSubmit={handleGroundTruthSubmit}
                />
                <AccuracyReport report={accuracyReport} />
              </div>
            )}
          </div>
        )}

        {/* Pre-analysis AI Coach setup panel */}
        {!analysis && !loading && !error && (
          <div className="anim-fade" style={{ marginTop: 40 }}>
            <div style={{
              fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)',
              letterSpacing: '.12em', marginBottom: 12,
            }}>
              🔥 AI COACH — CONFIGURE WHILE YOUR VIDEO UPLOADS
            </div>
            <AICoach contextData={null} />
            <div style={{
              marginTop: 60, textAlign: 'center',
              color: 'var(--t3)', fontFamily: 'var(--f-mono)', fontSize: 13,
            }}>
              <div style={{ fontSize: 48, marginBottom: 16, opacity: .3 }}>📹</div>
              <div style={{ letterSpacing: '.08em' }}>UPLOAD YOUR GAMEPLAY FOOTAGE ABOVE TO BEGIN ANALYSIS</div>
              <div style={{ fontSize: 11, marginTop: 8, color: 'var(--t3)', opacity: .6 }}>
                Supports CS2 and Valorant · MP4 and MOV · Any resolution
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
