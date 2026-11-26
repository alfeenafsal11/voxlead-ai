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
  Volume2,
  VolumeX,
  User,
  Building,
  Calendar
} from 'lucide-react';
import { startVoiceSession, sendVoiceTurn, endVoiceSession } from '../services/api';

const SAMPLE_SCENARIOS = [
  { label: "Pricing Inquiry", text: "What is your pricing for 45 sales reps and what does it include?" },
  { label: "Spreadsheet Objection", text: "We manage all our leads manually in spreadsheets and reps forget follow-ups." },
  { label: "Demo Booking", text: "Yes, tomorrow at 2:00 PM UTC works for me. Please book the demo." },
  { label: "हिंदी में बात करें", text: "नमस्ते! क्या आप मुझे VoxLead CRM का लाइव डेमो दिखा सकते हैं?" },
];

export default function LiveVoiceAgent() {
  const [callActive, setCallActive] = useState(false);
  const [callSession, setCallSession] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [language, setLanguage] = useState('en');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [interimSpeech, setInterimSpeech] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [callSummary, setCallSummary] = useState(null);

  // Customer form inputs
  const [customerName, setCustomerName] = useState('Alex Vance');
  const [company, setCompany] = useState('Lumina Health');

  // Live status
  const [liveLead, setLiveLead] = useState({ score: 0, classification: 'cold', sentiment: 'neutral' });

  const chatBottomRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, interimSpeech]);

  // Clean up speech synthesis & recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Text to Speech playback function
  const speakAssistantResponse = (text, lang) => {
    if (!ttsEnabled || isMuted || !window.speechSynthesis) return;

    try {
      window.speechSynthesis.cancel(); // Stop any active speech
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang === 'hi' ? 'hi-IN' : 'en-US';
      utterance.rate = 1.0;
      utterance.pitch = 1.05;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('Speech synthesis error:', e);
      setIsSpeaking(false);
    }
  };

  // Initialize Web Speech Recognition
  const initSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('Web Speech API not supported in this browser.');
      return null;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            final += transcript;
          } else {
            interim += transcript;
          }
        }

        setInterimSpeech(interim);

        if (final.trim()) {
          setInterimSpeech('');
          handleSendTurn(final.trim());
        }
      };

      recognition.onerror = (event) => {
        if (event.error !== 'no-speech') {
          console.warn('Speech recognition error:', event.error);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        // Automatically restart if call is active and unmuted
        if (callActive && !isMuted) {
          try {
            recognition.start();
          } catch (e) {}
        }
      };

      return recognition;
    } catch (e) {
      console.warn('Speech recognition initialization failed:', e);
      return null;
    }
  };

  // Handle Starting the Call
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

      // Initial Greeting
      const initialGreeting = language === 'hi'
        ? `नमस्ते ${customerName}! मैं VoxLead AI से Ava हूँ। मैं ${company} के सेल्स प्रोसेस को ऑटोमेट करने में कैसे मदद कर सकती हूँ?`
        : `Hello ${customerName}! I am Ava from VoxLead AI. We help sales teams eliminate manual admin work and automate qualification. What are you looking to achieve with your sales pipeline at ${company}?`;

      setMessages([{
        id: 'msg-0',
        role: 'assistant',
        content: initialGreeting,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);

      speakAssistantResponse(initialGreeting, language);

      // Start Microphone Recognition
      const rec = initSpeechRecognition();
      if (rec) {
        recognitionRef.current = rec;
        try {
          rec.start();
        } catch (e) {}
      }
    } catch (err) {
      alert(`Error starting session: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  // Handle Ending the Call & Generating Post-Call Summary
  const handleEndCall = async () => {
    if (!callSession) return;
    try {
      setProcessing(true);

      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setIsListening(false);
      setIsSpeaking(false);

      const summary = await endVoiceSession({
        callId: callSession.call_id,
        customerName: customerName,
        company: company,
        messages: messages
      });

      setCallSummary(summary);
      setCallActive(false);
    } catch (err) {
      alert(`Error ending call: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  // Handle Sending a Voice or Text Turn
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
    setInterimSpeech('');
    setProcessing(true);

    try {
      const res = await sendVoiceTurn({
        callId: callSession.call_id,
        message: text,
        language: language,
        customerName: customerName,
        company: company,
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

      // Speak Ava's response out loud
      speakAssistantResponse(res.response_text, res.language || language);
    } catch (err) {
      console.error('Turn error:', err);
    } finally {
      setProcessing(false);
    }
  };

  // Toggle Mute / Unmute
  const toggleMute = () => {
    if (isMuted) {
      setIsMuted(false);
      if (recognitionRef.current && callActive) {
        try { recognitionRef.current.start(); } catch (e) {}
      }
    } else {
      setIsMuted(true);
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
      setIsListening(false);
    }
  };

  return (
    <div className="container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Live Voice Agent</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
            Real-Time Speech Interaction (STT), Consultative Reasoning, RAG Grounding & Live BANT Scoring
          </p>
        </div>

        {/* Live Call Control Pills */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div className="status-badge" style={{ borderColor: callActive ? 'rgba(16, 185, 129, 0.4)' : 'rgba(107, 114, 128, 0.4)' }}>
            <span className={`dot ${callActive ? 'green' : 'gray'}`}></span>
            {callActive ? 'VOICE CHANNEL ACTIVE' : 'STANDBY'}
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
          {/* Audio Waveform & Microphone Status Bar */}
          <div className="card" style={{ marginBottom: '1.25rem', padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                {callActive ? (
                  isListening ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#34d399', fontWeight: 600 }}>
                      <Mic size={16} /> Listening to your microphone...
                    </span>
                  ) : isSpeaking ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#818cf8', fontWeight: 600 }}>
                      <Volume2 size={16} /> Ava is speaking...
                    </span>
                  ) : (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Mic size={16} color="var(--success)" /> Acoustic Channel Ready
                    </span>
                  )
                ) : (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <MicOff size={16} color="var(--text-muted)" /> Microphone Inactive
                  </span>
                )}
              </div>

              {callActive && (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => setTtsEnabled(!ttsEnabled)}
                    style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                    title={ttsEnabled ? "Mute Agent Voice" : "Enable Agent Voice"}
                  >
                    {ttsEnabled ? <Volume2 size={13} /> : <VolumeX size={13} />}
                    {ttsEnabled ? "Voice On" : "Voice Off"}
                  </button>

                  <button
                    className="btn btn-outline btn-sm"
                    onClick={toggleMute}
                    style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                  >
                    {isMuted ? <MicOff size={13} color="var(--danger)" /> : <Mic size={13} color="var(--success)" />}
                    {isMuted ? 'Unmute Mic' : 'Mute Mic'}
                  </button>
                </div>
              )}
            </div>

            {/* Audio Waveform Bars */}
            <div className="waveform-container">
              {[...Array(28)].map((_, i) => (
                <div
                  key={i}
                  className="wave-bar"
                  style={{
                    animationDuration: (callActive && (isListening || isSpeaking)) ? `${0.35 + (i % 6) * 0.12}s` : '0s',
                    height: (callActive && (isListening || isSpeaking)) ? undefined : 6,
                    opacity: callActive ? (isMuted ? 0.25 : 1) : 0.2,
                    background: isSpeaking ? 'linear-gradient(180deg, #818cf8, #4f46e5)' : undefined
                  }}
                />
              ))}
            </div>

            {/* Live speech feedback pill */}
            {interimSpeech && (
              <div style={{ marginTop: '0.65rem', padding: '0.4rem 0.75rem', borderRadius: 6, background: 'rgba(79, 70, 229, 0.15)', border: '1px solid rgba(79, 70, 229, 0.3)', fontSize: '0.825rem', color: '#c7d2fe', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span className="dot green" style={{ animation: 'pulse 1s infinite' }}></span>
                <span>Transcribing: "{interimSpeech}"</span>
              </div>
            )}
          </div>

          {/* Interactive Live Transcript */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '480px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)', marginBottom: '0.75rem' }}>
              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Live Conversation Transcript</span>
              {callActive && (
                <span className="badge badge-pos" style={{ fontSize: '0.7rem' }}>
                  {isListening ? "Listening" : processing ? "Thinking" : "Online"}
                </span>
              )}
            </div>

            <div className="chat-box" style={{ flex: 1 }}>
              {messages.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', margin: 'auto' }}>
                  <Phone size={32} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
                  <p>Click "Start Sales Call" to begin speaking with Ava</p>
                  <p style={{ fontSize: '0.8rem', marginTop: '0.35rem' }}>You can speak directly into your microphone or type your response</p>
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
                        <Calendar size={12} /> Appointment Booked on Google Calendar & Synced to CRM
                      </div>
                    )}

                    <div className="bubble-meta">
                      <span>{m.role === 'assistant' ? 'Ava (AI Representative)' : customerName}</span>
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
                placeholder={callActive ? "Speak into mic or type message here..." : "Start call to enable conversation..."}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleSendTurn();
                  }
                }}
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
                style={{ minWidth: '44px' }}
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
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Prospect Name</label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                disabled={callActive}
                style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 4, padding: '0.4rem 0.6rem', color: '#fff', fontSize: '0.85rem', marginBottom: '0.6rem' }}
              />

              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Company Name</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                disabled={callActive}
                style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 4, padding: '0.4rem 0.6rem', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Real-time BANT Qualification Card */}
          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Live BANT Scoring</h3>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Lead Score</span>
                <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>{liveLead.score} / 100</span>
              </div>
              <div style={{ width: '100%', height: 6, background: 'var(--bg-primary)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${liveLead.score}%`, height: '100%', background: liveLead.score >= 70 ? 'var(--danger)' : liveLead.score >= 40 ? 'var(--warning)' : 'var(--primary)', transition: 'width 0.4s ease' }}></div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Classification</span>
              <span className={`badge badge-${liveLead.classification}`} style={{ textTransform: 'uppercase' }}>
                {liveLead.classification}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Sentiment</span>
              <span className={`badge badge-${liveLead.sentiment === 'positive' ? 'pos' : liveLead.sentiment === 'frustrated' ? 'neg' : 'neu'}`} style={{ textTransform: 'capitalize' }}>
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

            <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 8, marginBottom: '1rem', borderLeft: '4px solid var(--primary)' }}>
              <p style={{ fontSize: '0.95rem', lineHeight: 1.5, margin: 0 }}>
                {callSummary.summary_text || callSummary.summary}
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
              <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', borderRadius: 6 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Calculated Lead Score</span>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
                  {callSummary.lead_score} / 100
                  <span className={`badge badge-${callSummary.lead_classification}`} style={{ marginLeft: '0.5rem', fontSize: '0.7rem', verticalAlign: 'middle' }}>
                    {callSummary.lead_classification}
                  </span>
                </div>
              </div>
              <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', borderRadius: 6 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>HubSpot CRM Sync</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--success)', textTransform: 'capitalize', marginTop: '0.15rem' }}>
                  {callSummary.crm_sync_status || 'Synced'}
                </div>
              </div>
            </div>

            <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Key Insights</h4>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-main)', marginBottom: '1rem' }}>
              {callSummary.key_insights?.map((item, idx) => (
                <li key={idx} style={{ marginBottom: '0.35rem' }}>{item}</li>
              ))}
            </ul>

            <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Action Items</h4>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-main)', marginBottom: '1.5rem' }}>
              {callSummary.action_items?.map((item, idx) => (
                <li key={idx} style={{ marginBottom: '0.35rem' }}>{item}</li>
              ))}
            </ul>

            <button className="btn btn-primary" onClick={() => setCallSummary(null)} style={{ width: '100%', padding: '0.75rem' }}>
              Close Summary
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
