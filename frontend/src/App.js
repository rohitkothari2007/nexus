import React, { useState } from 'react';
import Analyzer from './pages/Analyzer';
import Dashboard from './pages/Dashboard';
import './App.css';

function App() {
  const [activePage, setActivePage] = useState('analyzer');

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-text">NEXUS</span>
          <span className="logo-sub">Fraud Intelligence</span>
        </div>
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActivePage('dashboard')}
          >
            <span className="nav-icon">📊</span>
            Dashboard
          </button>
          <button
            className={`nav-item ${activePage === 'analyzer' ? 'active' : ''}`}
            onClick={() => setActivePage('analyzer')}
          >
            <span className="nav-icon">🔍</span>
            Analyze Account
          </button>
          <button
            className={`nav-item ${activePage === 'factory' ? 'active' : ''}`}
            onClick={() => setActivePage('factory')}
          >
            <span className="nav-icon">🏭</span>
            Factory Clusters
          </button>
        </nav>
        <div className="sidebar-status">
          <div className="status-dot"></div>
          <span>API Online</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="top-header">
          <h1 className="page-title">
            {activePage === 'dashboard' && 'Live Dashboard'}
            {activePage === 'analyzer' && 'Account Analyzer'}
            {activePage === 'factory' && 'Factory Clusters'}
          </h1>
          <div className="header-badge">v0.3.0</div>
        </header>

        <div className="page-content">
          {activePage === 'dashboard' && <Dashboard />}
          {activePage === 'analyzer' && <Analyzer />}
          {activePage === 'factory' && <FactoryPage />}
        </div>
      </main>
    </div>
  );
}

function FactoryPage() {
  const [clusters, setClusters] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  const fetchClusters = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/factory/clusters');
      const data = await res.json();
      setClusters(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  React.useEffect(() => { fetchClusters(); }, []);

  return (
    <div className="factory-page">
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-value">{clusters?.total_clusters ?? 0}</div>
          <div className="stat-label">Factory Clusters</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{clusters?.total_accounts_indexed ?? 0}</div>
          <div className="stat-label">Accounts Indexed</div>
        </div>
      </div>

      {loading && <div className="loading">Loading clusters...</div>}

      {clusters?.clusters?.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">🏭</div>
          <p>No factory clusters detected yet.</p>
          <p>Analyze multiple accounts to detect fraud factories.</p>
        </div>
      )}

      {clusters?.clusters?.map(cluster => (
        <div key={cluster.factory_id} className="cluster-card">
          <div className="cluster-header">
            <span className="factory-id">{cluster.factory_id}</span>
            <span className="cluster-badge danger">
              {cluster.size} accounts
            </span>
          </div>
          <div className="cluster-accounts">
            {cluster.accounts.map(acc => (
              <span key={acc} className="account-chip">{acc}</span>
            ))}
          </div>
          <div className="cluster-meta">
            Created: {new Date(cluster.created_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}

export default App;