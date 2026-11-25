import React, { useState, useEffect, useRef } from 'react';
import {
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Send,
  Globe,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileText,
  User,
  Building,
  Calendar
} from 'lucide-react';
import { startVoiceSession, sendVoiceTurn, endVoiceSession } from '../services/api';

const SAMPLE_SCENARIOS = [
  { label: "Pricing Inquiry", text: "What is the price of your Professional tier and what does it include?" },
  { label: "Spreadsheet Objection", text: "We have 45 sales reps and we manage all our leads manually in spreadsheets." },
  { label: "Hindi Inquiry", text: "Namaste! Kya aap mujhe VoxLead CRM ka live demo dikha sakte hain?" },
  { label: "Confirm Booking", text: "Yes, tomorrow at 2:00 PM UTC works perfectly for me. Please confirm the meeting." },
];

export default function LiveVoiceAgent() {
  const [callActive, setCallActive] = useState(false);
  const [callSession, setCallSession] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [language, setLanguage] = useState('en');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [processing, setProcessing] = useState(false);
  const [callSummary, setCallSummary] = useState(null);

  // Customer form inputs
  const [customerName, setCustomerName] = useState('Alex Vance');
  const [company, setCompany] = useState('Lumina Health');

  // Live status
  const [liveLead, setLiveLead] = useState({ score: 0, classification: 'cold', sentiment: 'neutral' });

  const chatBottomRef = useRef(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleStartCall = async () => {
    try {
      setProcessing(true);
      setCallSummary(null);
      const session = await startVoiceSession({
        participantName: customerName,
        language: language,
        roomName: `voxlead_${Date.now()}`
      });

      setCallSession(session);
      setCallActive(true);

      // Welcome message
      const initialGreeting = language === 'hi'
        ? "नमस्ते! मैं VoxLead से Ava हूँ। मैं आपके सेल्स प्रोसेस को ऑटोमेट करने में कैसे मदद कर सकती हूँ?"
        : "Hello! I am Ava from VoxLead AI. We help sales teams automate lead qualification and eliminate admin work. What are you looking to achieve with your sales pipeline?";

      setMessages([{
        id: 'msg-0',
        role: 'assistant',
        content: initialGreeting,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
    } catch (err) {
      alert(`Error starting session: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleEndCall = async () => {
    if (!callSession) return;
    try {
      setProcessing(true);
      const summary = await endVoiceSession({ callId: callSession.call_id });
      setCallSummary(summary);
      setCallActive(false);
    } catch (err) {
      alert(`Error ending call: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleSendTurn = async (textToSend) => {
    const text = textToSend || inputText;
    if (!text.trim() || !callSession || processing) return;

    const userMsg = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setProcessing(true);

    try {
      const res = await sendVoiceTurn({
        callId: callSession.call_id,
        message: text,
        language: language,
      });

      const assistantMsg = {
        id: `msg-resp-${Date.now()}`,
        role: 'assistant',
        content: res.response_text,
        sources: res.sources,
        actionTriggered: res.action_triggered,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages(prev => [...prev, assistantMsg]);
      setLiveLead({
        score: res.lead_score,
        classification: res.lead_classification,
        sentiment: res.sentiment,
      });

      if (res.language && res.language !== language) {
        setLanguage(res.language);
      }
    } catch (err) {
      alert(`Turn failed: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Live Voice Agent</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
            Real-Time Multilingual Speech Interaction, RAG Context Grounding & Live Lead Scoring
          </p>
        </div>

        {/* Live Call Control Pills */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div className="status-badge">
            <span className={`dot ${callActive ? 'green' : 'amber'}`}></span>
            {callActive ? 'CALL ACTIVE (WebRTC)' : 'DISCONNECTED'}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'var(--bg-secondary)', padding: '0.35rem 0.6rem', borderRadius: 8, border: '1px solid var(--border)' }}>
            <Globe size={14} color="var(--primary)" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              style={{ background: 'transparent', color: '#fff', border: 'none', outline: 'none', cursor: 'pointer', fontSize: '0.85rem' }}
            >
              <option value="en" style={{ background: '#1f2937' }}>English (US)</option>
              <option value="hi" style={{ background: '#1f2937' }}>हिंदी (Hindi)</option>
            </select>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1.5rem' }}>
        {/* Main Conversation & Audio Stream Column */}
        <div>
          {/* Audio Waveform Bar */}
          <div className="card" style={{ marginBottom: '1.25rem', padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                {callActive ? <Mic size={16} color="var(--success)" /> : <MicOff size={16} color="var(--text-muted)" />}
                <span>{callActive ? (isMuted ? 'Microphone Muted' : 'Acoustic Audio Channel Active') : 'Microphone Inactive'}</span>
              </div>
              {callActive && (
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setIsMuted(!isMuted)}
                  style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                >
                  {isMuted ? 'Unmute' : 'Mute Mic'}
                </button>
              )}
            </div>

            <div className="waveform-container">
              {[...Array(28)].map((_, i) => (
                <div
                  key={i}
                  className="wave-bar"
                  style={{
                    animationDuration: callActive ? `${0.4 + (i % 6) * 0.15}s` : '0s',
                    height: callActive ? undefined : 6,
                    opacity: callActive ? (isMuted ? 0.3 : 1) : 0.2
                  }}
                />
              ))}
            </div>
          </div>

          {/* Interactive Live Transcript */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '480px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)', marginBottom: '0.75rem' }}>
              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Live Conversation Transcript</span>
              {callActive && (
                <span className="badge badge-pos" style={{ fontSize: '0.7rem' }}>Streaming</span>
              )}
            </div>

            <div className="chat-box" style={{ flex: 1 }}>
              {messages.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', margin: 'auto' }}>
                  <Phone size={32} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
                  <p>Initiate a call to begin speaking with Ava</p>
                </div>
              ) : (
                messages.map((m) => (
                  <div key={m.id} className={`chat-bubble ${m.role}`}>
                    <div>{m.content}</div>

                    {/* Sources Badge if RAG Grounded */}
                    {m.sources && m.sources.length > 0 && (
                      <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                        {m.sources.map((s, idx) => (
                          <span key={idx} style={{ fontSize: '0.7rem', background: 'rgba(79, 70, 229, 0.25)', border: '1px solid rgba(79, 70, 229, 0.5)', padding: '0.15rem 0.45rem', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 3 }}>
                            <FileText size={10} /> {s.filename} (sim: {s.similarity})
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Action Trigger Badge */}
                    {m.actionTriggered === 'book_appointment' && (
                      <div style={{ marginTop: '0.5rem', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid rgba(16, 185, 129, 0.4)', color: '#34d399', padding: '0.25rem 0.5rem', borderRadius: 4, fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Calendar size={12} /> Appointment Booking Executed & Confirmed
                      </div>
                    )}

                    <div className="bubble-meta">
                      <span>{m.role === 'assistant' ? 'Ava (AI Agent)' : 'Customer'}</span>
                      <span>•</span>
                      <span>{m.time}</span>
                    </div>
                  </div>
                ))
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Quick Demo Scenario Prompt Buttons */}
            {callActive && (
              <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.75rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
                {SAMPLE_SCENARIOS.map((sc, i) => (
                  <button
                    key={i}
                    className="btn btn-outline btn-sm"
                    onClick={() => handleSendTurn(sc.text)}
                    disabled={processing}
                    style={{ fontSize: '0.75rem', whiteSpace: 'nowrap', padding: '0.3rem 0.6rem' }}
                  >
                    <Sparkles size={11} color="var(--primary)" /> {sc.label}
                  </button>
                ))}
              </div>
            )}

            {/* Turn Input Bar */}
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
              <input
                type="text"
                placeholder={callActive ? "Type or speak customer response..." : "Start call to enable conversation..."}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendTurn()}
                disabled={!callActive || processing}
                style={{
                  flex: 1,
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border)',
                  borderRadius: '0.5rem',
                  padding: '0.65rem 1rem',
                  color: '#fff',
                  fontSize: '0.9rem',
                  outline: 'none'
                }}
              />
              <button
                className="btn btn-primary"
                onClick={() => handleSendTurn()}
                disabled={!callActive || processing || !inputText.trim()}
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Right Info Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Call Action Card */}
          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Call Controls</h3>

            {!callActive ? (
              <button
                className="btn btn-primary"
                onClick={handleStartCall}
                disabled={processing}
                style={{ width: '100%', padding: '0.85rem' }}
              >
                <Phone size={18} /> Start Sales Call
              </button>
            ) : (
              <button
                className="btn btn-danger"
                onClick={handleEndCall}
                disabled={processing}
                style={{ width: '100%', padding: '0.85rem' }}
              >
                <PhoneOff size={18} /> End Call & Summarize
              </button>
            )}

            <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Customer Name</label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                disabled={callActive}
                style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 4, padding: '0.4rem 0.6rem', color: '#fff', fontSize: '0.85rem', marginBottom: '0.6rem' }}
              />

              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Company</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                disabled={callActive}
                style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 4, padding: '0.4rem 0.6rem', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Real-time Qualification Card */}
          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Live Intelligence</h3>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Lead Score</span>
                <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>{liveLead.score} / 100</span>
              </div>
              <div style={{ width: '100%', height: 6, background: 'var(--bg-primary)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${liveLead.score}%`, height: '100%', background: liveLead.score >= 70 ? 'var(--danger)' : liveLead.score >= 40 ? 'var(--warning)' : 'var(--primary)' }}></div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Classification</span>
              <span className={`badge badge-${liveLead.classification}`}>{liveLead.classification}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Sentiment</span>
              <span className={`badge badge-${liveLead.sentiment === 'positive' ? 'pos' : liveLead.sentiment === 'frustrated' ? 'neg' : 'neu'}`}>
                {liveLead.sentiment}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Post-Call Summary Modal */}
      {callSummary && (
        <div className="modal-overlay" onClick={() => setCallSummary(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 color="var(--success)" size={22} /> Post-Call Summary & Intelligence
              </h2>
              <button className="btn btn-outline btn-sm" onClick={() => setCallSummary(null)}>✕</button>
            </div>

            <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 8, marginBottom: '1rem' }}>
              <p style={{ fontSize: '0.95rem', lineHeight: 1.5 }}>{callSummary.summary_text}</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
              <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', borderRadius: 6 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Lead Score</span>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>{callSummary.lead_score} / 100</div>
              </div>
              <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', borderRadius: 6 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>HubSpot CRM</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--success)', textTransform: 'capitalize' }}>
                  {callSummary.crm_sync_status}
                </div>
              </div>
            </div>

            <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Key Insights</h4>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-main)', marginBottom: '1rem' }}>
              {callSummary.key_insights?.map((item, idx) => (
                <li key={idx} style={{ marginBottom: '0.25rem' }}>{item}</li>
              ))}
            </ul>

            <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Action Items</h4>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-main)', marginBottom: '1.5rem' }}>
              {callSummary.action_items?.map((item, idx) => (
                <li key={idx} style={{ marginBottom: '0.25rem' }}>{item}</li>
              ))}
            </ul>

            <button className="btn btn-primary" onClick={() => setCallSummary(null)} style={{ width: '100%' }}>
              Close Summary
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
