import React, { useState, useEffect } from 'react';

const API = 'http://localhost:8000';

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [healthRes, statsRes] = await Promise.all([
          fetch(`${API}/health`),
          fetch(`${API}/factory/stats`)
        ]);
        const healthData = await healthRes.json();
        const statsData = await statsRes.json();
        setHealth(healthData);
        setStats(statsData);
      } catch (e) {
        console.error('Failed to fetch dashboard data');
      }
      setLoading(false);
    };
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="loading">Loading dashboard...</div>;

  return (
    <div className="dashboard-page">
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon">🔍</div>
          <div className="stat-value">{health?.accounts_indexed ?? 0}</div>
          <div className="stat-label">Accounts Analyzed</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🏭</div>
          <div className="stat-value">{health?.factory_clusters ?? 0}</div>
          <div className="stat-label">Factory Clusters</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⚠️</div>
          <div className="stat-value">{stats?.largest_cluster ?? 0}</div>
          <div className="stat-label">Largest Cluster</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-value" style={{color:'#10b981'}}>ONLINE</div>
          <div className="stat-label">API Status</div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="dash-card">
          <h3 className="dash-card-title">System Status</h3>
          <div className="status-list">
            <div className="status-item">
              <span>Document Analyzer</span>
              <span className="status-on">● Active</span>
            </div>
            <div className="status-item">
              <span>Face Analyzer</span>
              <span className="status-on">● Active</span>
            </div>
            <div className="status-item">
              <span>Device Analyzer</span>
              <span className="status-on">● Active</span>
            </div>
            <div className="status-item">
              <span>Factory Fingerprinting</span>
              <span className="status-on">● Active</span>
            </div>
            <div className="status-item">
              <span>TrustScore Engine</span>
              <span className="status-on">● Active</span>
            </div>
            <div className="status-item">
              <span>PostgreSQL Database</span>
              <span className="status-on">● Connected</span>
            </div>
          </div>
        </div>

        <div className="dash-card">
          <h3 className="dash-card-title">Factory Intelligence</h3>
          {stats?.clusters?.length === 0 ? (
            <div className="empty-state-small">
              <p>No factory clusters yet.</p>
              <p>Analyze accounts to detect fraud factories.</p>
            </div>
          ) : (
            <div className="cluster-list">
              {stats?.clusters?.map(c => (
                <div key={c.factory_id} className="cluster-row">
                  <span className="factory-id-small">{c.factory_id}</span>
                  <span className="cluster-size-badge">{c.size} accounts</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="dash-card how-it-works">
        <h3 className="dash-card-title">How NEXUS Works</h3>
        <div className="flow-steps">
          <div className="flow-step">
            <div className="flow-num">1</div>
            <div className="flow-text">
              <div className="flow-title">Document Analysis</div>
              <div className="flow-desc">ELA + noise + edge detection on ID cards</div>
            </div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step">
            <div className="flow-num">2</div>
            <div className="flow-text">
              <div className="flow-title">Face Detection</div>
              <div className="flow-desc">Neural network deepfake classification</div>
            </div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step">
            <div className="flow-num">3</div>
            <div className="flow-text">
              <div className="flow-title">Factory Fingerprint</div>
              <div className="flow-desc">64-dim FAISS similarity clustering</div>
            </div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step">
            <div className="flow-num">4</div>
            <div className="flow-text">
              <div className="flow-title">TrustScore</div>
              <div className="flow-desc">Weighted ensemble 0-100 with explanation</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}