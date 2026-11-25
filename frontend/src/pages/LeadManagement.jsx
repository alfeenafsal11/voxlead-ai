import React, { useState, useEffect } from 'react';
import {
  Users,
  Search,
  Filter,
  Flame,
  Sun,
  Snowflake,
  Calendar,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  FileText,
  Clock,
  Building,
  Check
} from 'lucide-react';
import { fetchLeads, syncLeadCRM, fetchCalendarSlots, bookAppointment } from '../services/api';

export default function LeadManagement() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClass, setFilterClass] = useState('all');

  // Selected lead for summary drawer/modal
  const [selectedLead, setSelectedLead] = useState(null);

  // Booking modal state
  const [bookingLead, setBookingLead] = useState(null);
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [bookingLoading, setBookingLoading] = useState(false);

  const loadLeads = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchLeads();
      setLeads(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeads();
  }, []);

  const handleSyncCRM = async (lead) => {
    try {
      const res = await syncLeadCRM({
        customerId: lead.customer_id,
        dealName: `${lead.company || lead.customer_name} - VoxLead Opportunity`,
        amount: lead.budget || 35000,
      });
      alert(res.message);
      loadLeads();
    } catch (err) {
      alert(`Sync failed: ${err.message}`);
    }
  };

  const handleOpenBookingModal = async (lead) => {
    setBookingLead(lead);
    try {
      const available = await fetchCalendarSlots();
      setSlots(available);
      if (available.length > 0) {
        setSelectedSlot(available[0]);
      }
    } catch (err) {
      alert(`Failed to load calendar slots: ${err.message}`);
    }
  };

  const handleConfirmBooking = async () => {
    if (!bookingLead || !selectedSlot) return;
    try {
      setBookingLoading(true);
      const res = await bookAppointment({
        customerId: bookingLead.customer_id,
        title: `Product Demonstration: ${bookingLead.company}`,
        scheduledTime: selectedSlot.start_time,
        idempotency_key: `lead_book_${bookingLead.id}_${Date.now()}`
      });
      alert(`Appointment confirmed for ${selectedSlot.formatted}`);
      setBookingLead(null);
      loadLeads();
    } catch (err) {
      alert(`Booking failed: ${err.message}`);
    } finally {
      setBookingLoading(false);
    }
  };

  const filteredLeads = leads.filter((lead) => {
    const matchesSearch =
      (lead.customer_name?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
      (lead.company?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
      (lead.requirement?.toLowerCase() || '').includes(searchTerm.toLowerCase());

    const matchesClass = filterClass === 'all' || lead.classification === filterClass;
    return matchesSearch && matchesClass;
  });

  return (
    <div className="container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Lead Management</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
            Qualified Opportunities, Lead Intelligence Scores, Meeting Bookings & HubSpot Sync
          </p>
        </div>
        <button className="btn btn-outline btn-sm" onClick={loadLeads}>
          <RefreshCw size={14} /> Refresh Leads
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 260 }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search leads by customer, company or requirement..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              padding: '0.65rem 1rem 0.65rem 2.4rem',
              color: '#fff',
              fontSize: '0.9rem',
              outline: 'none'
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '0.4rem', background: 'var(--bg-secondary)', padding: '0.25rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
          {['all', 'hot', 'warm', 'cold'].map((cls) => (
            <button
              key={cls}
              onClick={() => setFilterClass(cls)}
              className={`btn btn-sm ${filterClass === cls ? 'btn-primary' : 'btn-outline'}`}
              style={{ textTransform: 'capitalize', border: 'none' }}
            >
              {cls === 'hot' && <Flame size={12} color="#f87171" />}
              {cls === 'warm' && <Sun size={12} color="#fbbf24" />}
              {cls === 'cold' && <Snowflake size={12} color="#60a5fa" />}
              {cls}
            </button>
          ))}
        </div>
      </div>

      {/* Leads Table */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '4rem 0' }}>
          <RefreshCw className="animate-spin" style={{ margin: '0 auto 1rem', width: 28, height: 28, color: 'var(--primary)' }} />
          <p style={{ color: 'var(--text-muted)' }}>Loading leads data...</p>
        </div>
      ) : filteredLeads.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
          <Users size={36} style={{ margin: '0 auto 1rem', opacity: 0.3 }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.5rem' }}>No Leads Found</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            {searchTerm ? 'No results matched your search criteria.' : 'Initiate a voice call or run seed data to populate leads.'}
          </p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Customer & Company</th>
                <th>Score & Tier</th>
                <th>Sentiment</th>
                <th>Timeline & Budget</th>
                <th>Appointment</th>
                <th>HubSpot CRM</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredLeads.map((lead) => (
                <tr key={lead.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{lead.customer_name}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {lead.company} {lead.company_size ? `(${lead.company_size} reps)` : ''}
                    </div>
                  </td>

                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontWeight: 700 }}>{lead.score}</span>
                      <span className={`badge badge-${lead.classification}`}>{lead.classification}</span>
                    </div>
                  </td>

                  <td>
                    <span className={`badge badge-${lead.sentiment === 'positive' ? 'pos' : lead.sentiment === 'frustrated' ? 'neg' : 'neu'}`}>
                      {lead.sentiment}
                    </span>
                  </td>

                  <td>
                    <div style={{ fontSize: '0.85rem' }}>{lead.timeline || 'Not specified'}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {lead.budget ? `$${lead.budget.toLocaleString()}` : 'Budget pending'}
                    </div>
                  </td>

                  <td>
                    {lead.appointment_status === 'Booked' ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--success)', fontSize: '0.85rem', fontWeight: 600 }}>
                        <CheckCircle2 size={14} /> Booked
                      </span>
                    ) : (
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => handleOpenBookingModal(lead)}
                        style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                      >
                        <Calendar size={12} /> Book Demo
                      </button>
                    )}
                  </td>

                  <td>
                    {lead.crm_status === 'Synced' ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--success)', fontSize: '0.85rem', fontWeight: 600 }}>
                        <Check size={14} /> Synced
                      </span>
                    ) : (
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => handleSyncCRM(lead)}
                        style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                      >
                        Sync CRM
                      </button>
                    )}
                  </td>

                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-outline btn-sm"
                      onClick={() => setSelectedLead(lead)}
                      style={{ fontSize: '0.75rem' }}
                    >
                      <FileText size={12} /> Summary
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Call Summary Modal */}
      {selectedLead && (
        <div className="modal-overlay" onClick={() => setSelectedLead(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                Lead Details: {selectedLead.customer_name}
              </h2>
              <button className="btn btn-outline btn-sm" onClick={() => setSelectedLead(null)}>✕</button>
            </div>

            <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 8, marginBottom: '1rem' }}>
              <h4 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>Call Summary</h4>
              <p style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                {selectedLead.call_summary || 'No call summary recorded yet.'}
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', borderRadius: 6 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Requirement</span>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{selectedLead.requirement || 'General CRM'}</div>
              </div>

              <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', borderRadius: 6 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Decision Maker</span>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{selectedLead.decision_maker ? 'Yes (Confirmed)' : 'No / Unknown'}</div>
              </div>
            </div>

            {selectedLead.objections && selectedLead.objections.length > 0 && (
              <div style={{ marginBottom: '1.25rem' }}>
                <h4 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>Stated Objections</h4>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
                  {selectedLead.objections.map((obj, i) => (
                    <li key={i}>{obj}</li>
                  ))}
                </ul>
              </div>
            )}

            <button className="btn btn-primary" onClick={() => setSelectedLead(null)} style={{ width: '100%' }}>
              Close
            </button>
          </div>
        </div>
      )}

      {/* Booking Calendar Slot Modal */}
      {bookingLead && (
        <div className="modal-overlay" onClick={() => setBookingLead(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                Schedule Product Demo
              </h2>
              <button className="btn btn-outline btn-sm" onClick={() => setBookingLead(null)}>✕</button>
            </div>

            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
              Select an available slot from Google Calendar for <strong>{bookingLead.customer_name}</strong> ({bookingLead.company}):
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '240px', overflowY: 'auto', marginBottom: '1.5rem' }}>
              {slots.map((slot, idx) => (
                <div
                  key={idx}
                  onClick={() => setSelectedSlot(slot)}
                  style={{
                    padding: '0.75rem 1rem',
                    borderRadius: 6,
                    background: selectedSlot?.start_time === slot.start_time ? 'var(--primary)' : 'var(--bg-primary)',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                    fontSize: '0.9rem',
                    fontWeight: 500
                  }}
                >
                  {slot.formatted}
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn btn-outline" onClick={() => setBookingLead(null)} style={{ flex: 1 }}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleConfirmBooking}
                disabled={bookingLoading || !selectedSlot}
                style={{ flex: 1 }}
              >
                {bookingLoading ? 'Booking...' : 'Confirm Demo Slot'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
