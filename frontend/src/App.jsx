import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  PhoneCall,
  Users,
  Mic,
  Activity,
  Layers,
  ShieldCheck,
  CheckCircle2,
  Sparkles
} from 'lucide-react';
import SalesOverview from './pages/SalesOverview';
import LiveVoiceAgent from './pages/LiveVoiceAgent';
import LeadManagement from './pages/LeadManagement';
import { fetchHealth } from './services/api';

export default function App() {
  const [currentPage, setCurrentPage] = useState('overview');
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetchHealth()
      .then(data => setHealth(data))
      .catch(() => setHealth({ status: 'offline', database: 'disconnected' }));
  }, []);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Application Navbar */}
      <nav className="navbar">
        <div className="nav-brand">
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff'
          }}>
            <Mic size={20} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>VoxLead AI</span>
            <span className="brand-badge">MVP</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="nav-links">
          <button
            className={`nav-btn ${currentPage === 'overview' ? 'active' : ''}`}
            onClick={() => setCurrentPage('overview')}
          >
            <BarChart3 size={16} /> Sales Overview
          </button>

          <button
            className={`nav-btn ${currentPage === 'voice' ? 'active' : ''}`}
            onClick={() => setCurrentPage('voice')}
          >
            <PhoneCall size={16} /> Live Voice Agent
          </button>

          <button
            className={`nav-btn ${currentPage === 'leads' ? 'active' : ''}`}
            onClick={() => setCurrentPage('leads')}
          >
            <Users size={16} /> Lead Management
          </button>
        </div>

        {/* System & Mode Status Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Mock Mode Pill */}
          <div className="status-badge" style={{ borderColor: 'rgba(245, 158, 11, 0.4)', background: 'rgba(245, 158, 11, 0.1)' }}>
            <span className="dot amber"></span>
            <span style={{ color: '#fbbf24', fontSize: '0.75rem' }}>
              {health?.mock_mode ? 'MOCK ADAPTERS' : 'PRODUCTION APIS'}
            </span>
          </div>

          {/* Backend / pgvector Health Pill */}
          <div className="status-badge">
            <span className={`dot ${health?.status === 'healthy' ? 'green' : 'red'}`}></span>
            <span style={{ fontSize: '0.75rem' }}>
              {health?.status === 'healthy' ? 'PGVECTOR ONLINE' : 'SYSTEM OFFLINE'}
            </span>
          </div>
        </div>
      </nav>

      {/* Main Page View */}
      <main style={{ flex: 1 }}>
        {currentPage === 'overview' && <SalesOverview onNavigate={(page) => setCurrentPage(page)} />}
        {currentPage === 'voice' && <LiveVoiceAgent />}
        {currentPage === 'leads' && <LeadManagement />}
      </main>

      {/* Footer */}
      <footer style={{
        padding: '1.25rem 2rem',
        borderTop: '1px solid var(--border)',
        backgroundColor: 'var(--bg-secondary)',
        fontSize: '0.8rem',
        color: 'var(--text-muted)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sparkles size={14} color="var(--primary)" />
          <span>VoxLead AI — Autonomous AI Sales Voice Agent</span>
        </div>
        <div>
          <span>Cascaded STT → LLM → TTS Architecture with RAG & Deterministic BANT Lead Scoring</span>
        </div>
      </footer>
    </div>
  );
}
