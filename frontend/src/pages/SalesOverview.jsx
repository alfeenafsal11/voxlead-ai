import React, { useEffect, useState } from 'react';
import { PhoneCall, Users, Award, Calendar, BarChart3, TrendingUp, RefreshCw, Flame, Sun, Snowflake } from 'lucide-react';
import { fetchDashboardOverview } from '../services/api';

export default function SalesOverview({ onNavigate }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchDashboardOverview();
      setMetrics(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: '5rem 0' }}>
        <RefreshCw className="animate-spin" style={{ margin: '0 auto 1rem', width: 32, height: 32, color: 'var(--primary)' }} />
        <p style={{ color: 'var(--text-muted)' }}>Loading real-time sales analytics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="card" style={{ borderLeft: '4px solid var(--danger)', padding: '1.5rem' }}>
          <h3 style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>Analytics Unavailable</h3>
          <p style={{ color: 'var(--text-muted)' }}>{error}</p>
          <button className="btn btn-outline btn-sm" onClick={loadMetrics} style={{ marginTop: '1rem' }}>
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      </div>
    );
  }

  const {
    total_calls,
    total_leads,
    qualified_leads,
    hot_leads,
    warm_leads,
    cold_leads,
    average_lead_score,
    appointments_booked,
    sentiment_distribution,
  } = metrics;

  const totalSentiment = Object.values(sentiment_distribution).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Sales Overview</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
            Autonomous AI Sales Pipeline, Qualification Metrics & Booking Performance
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-outline btn-sm" onClick={loadMetrics}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => onNavigate('voice')}>
            <PhoneCall size={14} /> Launch Live Agent
          </button>
        </div>
      </div>

      {/* Top High-level Metric Cards */}
      <div className="grid-cards">
        <div className="card">
          <div className="stat-header">
            <span>Total Calls Conducted</span>
            <PhoneCall size={18} color="var(--primary)" />
          </div>
          <div className="stat-value">{total_calls}</div>
          <div className="stat-sub">Across all active campaigns</div>
        </div>

        <div className="card">
          <div className="stat-header">
            <span>Total Identified Leads</span>
            <Users size={18} color="var(--info)" />
          </div>
          <div className="stat-value">{total_leads}</div>
          <div className="stat-sub">{qualified_leads} Qualified (Score ≥ 40)</div>
        </div>

        <div className="card">
          <div className="stat-header">
            <span>Average Lead Score</span>
            <Award size={18} color="var(--warning)" />
          </div>
          <div className="stat-value">{average_lead_score}<span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}> / 100</span></div>
          <div className="stat-sub">Deterministic BANT evaluation</div>
        </div>

        <div className="card">
          <div className="stat-header">
            <span>Booked Demos</span>
            <Calendar size={18} color="var(--success)" />
          </div>
          <div className="stat-value" style={{ color: 'var(--success)' }}>{appointments_booked}</div>
          <div className="stat-sub">Synchronized to Google Calendar</div>
        </div>
      </div>

      {/* Pipeline Distribution & Sentiment Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Lead Classification Breakdown */}
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <TrendingUp size={18} color="var(--primary)" /> Lead Classification Distribution
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', fontSize: '0.875rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#f87171' }}>
                  <Flame size={16} /> Hot Leads (70 - 100)
                </span>
                <span style={{ fontWeight: 600 }}>{hot_leads}</span>
              </div>
              <div style={{ width: '100%', height: 8, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${total_leads ? (hot_leads / total_leads) * 100 : 0}%`, height: '100%', background: '#ef4444' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', fontSize: '0.875rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#fbbf24' }}>
                  <Sun size={16} /> Warm Leads (40 - 69)
                </span>
                <span style={{ fontWeight: 600 }}>{warm_leads}</span>
              </div>
              <div style={{ width: '100%', height: 8, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${total_leads ? (warm_leads / total_leads) * 100 : 0}%`, height: '100%', background: '#f59e0b' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', fontSize: '0.875rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#60a5fa' }}>
                  <Snowflake size={16} /> Cold Leads (0 - 39)
                </span>
                <span style={{ fontWeight: 600 }}>{cold_leads}</span>
              </div>
              <div style={{ width: '100%', height: 8, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${total_leads ? (cold_leads / total_leads) * 100 : 0}%`, height: '100%', background: '#3b82f6' }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Sentiment Analysis Distribution */}
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BarChart3 size={18} color="var(--info)" /> Caller Sentiment Analysis
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {Object.entries(sentiment_distribution).map(([sent, count]) => {
              const pct = Math.round((count / totalSentiment) * 100);
              let color = 'var(--text-muted)';
              if (sent === 'positive') color = 'var(--success)';
              if (sent === 'frustrated') color = 'var(--danger)';
              if (sent === 'negative') color = '#fb923c';

              return (
                <div key={sent}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                    <span style={{ textTransform: 'capitalize', color }}>{sent}</span>
                    <span style={{ fontWeight: 600 }}>{count} ({pct}%)</span>
                  </div>
                  <div style={{ width: '100%', height: 6, background: 'var(--bg-primary)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: color }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
