import React, { useState } from 'react';

const API = 'http://localhost:8000';

function TrustScoreBadge({ score }) {
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : score >= 40 ? '#ef4444' : '#7c3aed';
  const label = score >= 80 ? 'LOW RISK' : score >= 60 ? 'MEDIUM RISK' : score >= 40 ? 'HIGH RISK' : 'CRITICAL';
  return (
    <div className="trust-score-badge" style={{ borderColor: color }}>
      <div className="score-number" style={{ color }}>{score}</div>
      <div className="score-label" style={{ color }}>{label}</div>
      <div className="score-sub">TrustScore / 100</div>
    </div>
  );
}

function ActionBadge({ action }) {
  const colors = {
    APPROVE: '#10b981', REVIEW: '#f59e0b',
    HOLD: '#ef4444', FREEZE: '#7c3aed'
  };
  const icons = { APPROVE: '✅', REVIEW: '👁️', HOLD: '⏸️', FREEZE: '🔒' };
  return (
    <div className="action-badge" style={{ background: colors[action.action] + '20', borderColor: colors[action.action] }}>
      <span className="action-icon">{icons[action.action]}</span>
      <div>
        <div className="action-name" style={{ color: colors[action.action] }}>{action.action}</div>
        <div className="action-reason">{action.reason}</div>
      </div>
    </div>
  );
}

export default function Analyzer() {
  const [docFile, setDocFile] = useState(null);
  const [faceFile, setFaceFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const analyze = async () => {
    if (!docFile || !faceFile) {
      setError('Please upload both a document and a face image.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('document', docFile);
    formData.append('face', faceFile);

    try {
      const res = await fetch(`${API}/analyze/full`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError('Failed to connect to NEXUS API. Make sure the backend is running.');
    }
    setLoading(false);
  };

  return (
    <div className="analyzer-page">
      <div className="upload-section">
        <h2 className="section-title">Upload Documents</h2>
        <p className="section-desc">Upload an ID document and a face photo to run full NEXUS analysis.</p>

        <div className="upload-grid">
          <div className="upload-box">
            <div className="upload-icon">🪪</div>
            <div className="upload-label">ID Document</div>
            <div className="upload-sub">Aadhaar, PAN, Passport</div>
            <input
              type="file"
              accept="image/*"
              onChange={e => setDocFile(e.target.files[0])}
              className="file-input"
              id="doc-input"
            />
            <label htmlFor="doc-input" className="upload-btn">
              {docFile ? `✓ ${docFile.name}` : 'Choose File'}
            </label>
          </div>

          <div className="upload-box">
            <div className="upload-icon">🤳</div>
            <div className="upload-label">Face / Selfie</div>
            <div className="upload-sub">Clear photo of face</div>
            <input
              type="file"
              accept="image/*"
              onChange={e => setFaceFile(e.target.files[0])}
              className="file-input"
              id="face-input"
            />
            <label htmlFor="face-input" className="upload-btn">
              {faceFile ? `✓ ${faceFile.name}` : 'Choose File'}
            </label>
          </div>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <button
          className="analyze-btn"
          onClick={analyze}
          disabled={loading}
        >
          {loading ? '🔄 Analyzing...' : '🚀 Run NEXUS Analysis'}
        </button>
      </div>

      {loading && (
        <div className="loading-section">
          <div className="loading-spinner"></div>
          <p>Running all 4 NEXUS modules...</p>
          <div className="loading-steps">
            <div className="loading-step">🔍 Document forgery analysis</div>
            <div className="loading-step">👤 Deepfake face detection</div>
            <div className="loading-step">🏭 Factory fingerprinting</div>
            <div className="loading-step">📊 TrustScore calculation</div>
          </div>
        </div>
      )}

      {result && (
        <div className="result-section">
          <h2 className="section-title">Analysis Result</h2>

          <div className="result-header">
            <TrustScoreBadge score={result.trust_score} />
            <div className="result-meta">
              <div className="account-id">Account: {result.account_id}</div>
              <ActionBadge action={result.action} />
            </div>
          </div>

          <div className="explanation-section">
            <h3 className="sub-title">Why this score?</h3>
            <div className="explanation-list">
              {result.explanation.map((exp, i) => (
                <div key={i} className="explanation-item">
                  <span className="exp-icon">
                    {exp.includes('HIGH') || exp.includes('CRITICAL') ? '🔴' :
                     exp.includes('MEDIUM') ? '🟡' :
                     exp.includes('FACTORY') ? '🏭' : '✅'}
                  </span>
                  <span>{exp}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="signals-grid">
            <div className="signal-card">
              <div className="signal-name">Document Risk</div>
              <div className="signal-bar-wrap">
                <div
                  className="signal-bar"
                  style={{
                    width: `${result.signal_breakdown.document_risk * 100}%`,
                    background: result.signal_breakdown.document_risk > 0.6 ? '#ef4444' :
                                result.signal_breakdown.document_risk > 0.3 ? '#f59e0b' : '#10b981'
                  }}
                ></div>
              </div>
              <div className="signal-value">{(result.signal_breakdown.document_risk * 100).toFixed(1)}%</div>
            </div>
            <div className="signal-card">
              <div className="signal-name">Face Risk</div>
              <div className="signal-bar-wrap">
                <div
                  className="signal-bar"
                  style={{
                    width: `${result.signal_breakdown.face_risk * 100}%`,
                    background: result.signal_breakdown.face_risk > 0.6 ? '#ef4444' :
                                result.signal_breakdown.face_risk > 0.3 ? '#f59e0b' : '#10b981'
                  }}
                ></div>
              </div>
              <div className="signal-value">{(result.signal_breakdown.face_risk * 100).toFixed(1)}%</div>
            </div>
            <div className="signal-card">
              <div className="signal-name">Device Risk</div>
              <div className="signal-bar-wrap">
                <div
                  className="signal-bar"
                  style={{
                    width: `${result.signal_breakdown.device_risk * 100}%`,
                    background: result.signal_breakdown.device_risk > 0.6 ? '#ef4444' :
                                result.signal_breakdown.device_risk > 0.3 ? '#f59e0b' : '#10b981'
                  }}
                ></div>
              </div>
              <div className="signal-value">{(result.signal_breakdown.device_risk * 100).toFixed(1)}%</div>
            </div>
            <div className="signal-card">
              <div className="signal-name">Factory Risk</div>
              <div className="signal-bar-wrap">
                <div
                  className="signal-bar"
                  style={{
                    width: `${result.signal_breakdown.factory_risk * 100}%`,
                    background: result.signal_breakdown.factory_risk > 0.6 ? '#ef4444' :
                                result.signal_breakdown.factory_risk > 0.3 ? '#f59e0b' : '#10b981'
                  }}
                ></div>
              </div>
              <div className="signal-value">{(result.signal_breakdown.factory_risk * 100).toFixed(1)}%</div>
            </div>
          </div>

          {result.factory.factory_id && (
            <div className="factory-alert-box">
              <div className="factory-alert-title">🏭 Factory Match Detected</div>
              <div>Factory ID: <strong>{result.factory.factory_id}</strong></div>
              <div>Cluster Size: <strong>{result.factory.cluster_size} accounts</strong></div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}