const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch('/health');
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchDashboardOverview() {
  const res = await fetch(`${API_BASE}/dashboard/overview`);
  if (!res.ok) throw new Error('Failed to fetch dashboard metrics');
  return res.json();
}

export async function fetchLeads() {
  const res = await fetch(`${API_BASE}/leads`);
  if (!res.ok) throw new Error('Failed to fetch leads');
  return res.json();
}

export async function startVoiceSession({ participantName, roomName, language }) {
  const res = await fetch(`${API_BASE}/voice/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      participant_name: participantName || 'Sales Prospect',
      room_name: roomName || `room_${Date.now()}`,
      language: language || 'en',
    }),
  });
  if (!res.ok) throw new Error('Failed to initialize voice session');
  return res.json();
}

export async function sendVoiceTurn({ callId, message, language }) {
  const res = await fetch(`${API_BASE}/voice/turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      call_id: callId,
      message,
      language,
    }),
  });
  if (!res.ok) throw new Error('Voice turn failed');
  return res.json();
}

export async function endVoiceSession({ callId }) {
  const res = await fetch(`${API_BASE}/voice/end`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ call_id: callId }),
  });
  if (!res.ok) throw new Error('Failed to end voice session');
  return res.json();
}

export async function fetchCalendarSlots() {
  const res = await fetch(`${API_BASE}/calendar/availability`);
  if (!res.ok) throw new Error('Failed to fetch calendar availability');
  return res.json();
}

export async function bookAppointment({ customerId, title, scheduledTime, idempotencyKey, callId }) {
  const res = await fetch(`${API_BASE}/calendar/book`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer_id: customerId,
      title,
      scheduled_time: scheduledTime,
      idempotency_key: idempotencyKey,
      call_id: callId,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to book appointment');
  }
  return res.json();
}

export async function syncLeadCRM({ customerId, dealName, amount }) {
  const res = await fetch(`${API_BASE}/crm/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer_id: customerId,
      deal_name: dealName,
      amount,
    }),
  });
  if (!res.ok) throw new Error('CRM synchronization failed');
  return res.json();
}
