import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

export default function WaitingRoomDisplay() {
  const [boardData, setBoardData] = useState({
    current_announcement: null,
    active_called_tokens: [],
    recent_call_history: [],
    total_waiting: 0,
    server_time: new Date().toISOString(),
  });
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [currentLanguage, setCurrentLanguage] = useState('both'); // 'en', 'te', 'both'
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());
  const [availableVoices, setAvailableVoices] = useState([]);
  const [isTeluguVoiceAvailable, setIsTeluguVoiceAvailable] = useState(false);

  // Refs for stable polling and deduplication
  const lastAnnouncedIdRef = useRef(null);
  const initialLoadRef = useRef(true);
  const isAudioEnabledRef = useRef(isAudioEnabled);
  const currentLanguageRef = useRef(currentLanguage);

  useEffect(() => {
    isAudioEnabledRef.current = isAudioEnabled;
  }, [isAudioEnabled]);

  useEffect(() => {
    currentLanguageRef.current = currentLanguage;
  }, [currentLanguage]);

  // Live Hospital Clock interval
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Web Speech API Voice Discovery & Telugu Detection
  useEffect(() => {
    const updateVoices = () => {
      if (!('speechSynthesis' in window)) return;
      const voices = window.speechSynthesis.getVoices() || [];
      setAvailableVoices(voices);
      const hasTelugu = voices.some(
        (v) => (v.lang && v.lang.toLowerCase().includes('te')) || (v.name && v.name.toLowerCase().includes('telugu'))
      );
      setIsTeluguVoiceAvailable(hasTelugu);
    };

    updateVoices();
    if ('speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, []);

  // Browser Speech Synthesis Engine
  const speakAnnouncement = useCallback((announcement) => {
    if (!('speechSynthesis' in window) || !announcement) return;

    window.speechSynthesis.cancel(); // Stop any overlapping utterance

    const voices = window.speechSynthesis.getVoices() || availableVoices;
    const enVoice =
      voices.find((v) => v.lang && (v.lang.startsWith('en-IN') || v.lang.startsWith('en_IN'))) ||
      voices.find((v) => v.lang && v.lang.startsWith('en-US')) ||
      voices.find((v) => v.lang && v.lang.startsWith('en'));

    const teVoice = voices.find(
      (v) => (v.lang && v.lang.toLowerCase().includes('te')) || (v.name && v.name.toLowerCase().includes('telugu'))
    );

    const langChoice = currentLanguageRef.current;
    const englishText = announcement.speech_text_en || `${announcement.token_display}. Patient ${announcement.patient_name}, please proceed to ${announcement.room_number}.`;
    const teluguText = announcement.speech_text_te || `టోకెన్ ${announcement.patient_code || announcement.token_number}. ${announcement.patient_name} గారు, దయచేసి ${announcement.room_number} కి వెళ్లండి.`;

    // 1. English Only Mode
    if (langChoice === 'en') {
      const utterEn = new SpeechSynthesisUtterance(englishText);
      if (enVoice) utterEn.voice = enVoice;
      utterEn.lang = enVoice?.lang || 'en-US';
      utterEn.rate = 0.88;
      utterEn.pitch = 1.0;
      window.speechSynthesis.speak(utterEn);
      return;
    }

    // 2. Telugu Only Mode
    if (langChoice === 'te') {
      if (teVoice) {
        const utterTe = new SpeechSynthesisUtterance(teluguText);
        utterTe.voice = teVoice;
        utterTe.lang = 'te-IN';
        utterTe.rate = 0.86;
        utterTe.pitch = 1.0;
        window.speechSynthesis.speak(utterTe);
      } else {
        // Fallback: If no Telugu TTS synthesizer is installed in OS/browser,
        // speak the English announcement with natural rate to avoid garbled pronunciation,
        // while displaying Telugu visual text prominently on the display screen.
        const fallbackUtter = new SpeechSynthesisUtterance(englishText);
        if (enVoice) fallbackUtter.voice = enVoice;
        fallbackUtter.lang = enVoice?.lang || 'en-US';
        fallbackUtter.rate = 0.88;
        window.speechSynthesis.speak(fallbackUtter);
      }
      return;
    }

    // 3. Bilingual Sequential Mode (English + Telugu)
    const utterEn = new SpeechSynthesisUtterance(englishText);
    if (enVoice) utterEn.voice = enVoice;
    utterEn.lang = enVoice?.lang || 'en-US';
    utterEn.rate = 0.88;

    if (teVoice) {
      utterEn.onend = () => {
        const utterTe = new SpeechSynthesisUtterance(teluguText);
        utterTe.voice = teVoice;
        utterTe.lang = 'te-IN';
        utterTe.rate = 0.86;
        window.speechSynthesis.speak(utterTe);
      };
    }
    window.speechSynthesis.speak(utterEn);
  }, [availableVoices]);

  // Handle Manual Replay (without advancing queue or creating new call event)
  const handleManualPlay = useCallback(() => {
    if (boardData.current_announcement) {
      speakAnnouncement(boardData.current_announcement);
    }
  }, [boardData.current_announcement, speakAnnouncement]);

  // Main Feed Fetch & Deduplication
  const fetchBoard = useCallback(async () => {
    try {
      const data = await api.getWaitingRoomBoard();
      let currentAnn = data?.current_announcement || null;
      let activeCalled = data?.active_called_tokens || [];
      let recentHistory = data?.recent_call_history || [];
      let totalWaiting = data?.total_waiting ?? 0;

      // Local storage fallback for hybrid / offline synchronization
      try {
        const localAnnRaw = localStorage.getItem('medqueue_current_announcement');
        if (localAnnRaw) {
          const localAnn = JSON.parse(localAnnRaw);
          if (localAnn && (!currentAnn || new Date(localAnn.timestamp) > new Date(currentAnn.timestamp || 0))) {
            currentAnn = localAnn;
          }
        }

        const localRecentRaw = localStorage.getItem('medqueue_recent_calls');
        if (localRecentRaw) {
          const localRecent = JSON.parse(localRecentRaw);
          if (Array.isArray(localRecent) && localRecent.length > recentHistory.length) {
            recentHistory = localRecent;
          }
        }

        if (totalWaiting === 0) {
          const localQ = JSON.parse(localStorage.getItem('medqueue_queue') || '[]');
          const localWaitingCount = localQ.filter(
            (q) => q.status === 'WAITING' || q.status === 'Waiting' || q.status === 'Escalated Emergency' || !q.status
          ).length;
          if (localWaitingCount > 0) {
            totalWaiting = localWaitingCount;
          }
        }
      } catch (_) {}

      // Format token display cleanly (e.g. Token P1005)
      if (currentAnn) {
        const pCode = currentAnn.patient_code || '';
        let tokDisp = currentAnn.token_display || '';
        if (!tokDisp || tokDisp.startsWith('T-')) {
          tokDisp = pCode.startsWith('P') ? `Token ${pCode}` : `Token ${tokDisp || pCode || 'P1001'}`;
        }
        currentAnn = {
          ...currentAnn,
          token_display: tokDisp,
        };
      }

      setBoardData({
        current_announcement: currentAnn,
        active_called_tokens: activeCalled,
        recent_call_history: recentHistory,
        total_waiting: totalWaiting,
        server_time: data?.server_time || new Date().toISOString(),
      });

      // Deduplicated Speech Announcement Trigger:
      // Only announce when a genuinely new call event ID is detected.
      if (currentAnn && currentAnn.event_id) {
        if (initialLoadRef.current) {
          // On first page load, register the current event ID without blasting audio unexpectedly
          lastAnnouncedIdRef.current = currentAnn.event_id;
          initialLoadRef.current = false;
        } else if (currentAnn.event_id !== lastAnnouncedIdRef.current) {
          lastAnnouncedIdRef.current = currentAnn.event_id;
          if (isAudioEnabledRef.current) {
            speakAnnouncement(currentAnn);
          }
        }
      }
    } catch (err) {
      console.warn('Waiting room board fetch notice:', err.message);
      // Resilient local storage state recovery
      try {
        const localAnnRaw = localStorage.getItem('medqueue_current_announcement');
        const localRecentRaw = localStorage.getItem('medqueue_recent_calls');
        const localQ = JSON.parse(localStorage.getItem('medqueue_queue') || '[]');
        const localWaitingCount = localQ.filter(
          (q) => q.status === 'WAITING' || q.status === 'Waiting' || q.status === 'Escalated Emergency' || !q.status
        ).length;

        const currentAnn = localAnnRaw ? JSON.parse(localAnnRaw) : null;
        const recentHistory = localRecentRaw ? JSON.parse(localRecentRaw) : [];

        setBoardData((prev) => ({
          ...prev,
          current_announcement: currentAnn || prev.current_announcement,
          recent_call_history: recentHistory.length > 0 ? recentHistory : prev.recent_call_history,
          total_waiting: localWaitingCount || prev.total_waiting,
        }));
      } catch (_) {}
    }
  }, [speakAnnouncement]);

  // Polling Interval & Instant Event Listeners
  useEffect(() => {
    fetchBoard();
    const interval = setInterval(fetchBoard, 3500);

    // Instant local custom broadcast listener (0-latency across same window)
    const handleDirectAnnouncement = (e) => {
      if (e?.detail) {
        fetchBoard();
      }
    };

    // Instant cross-tab storage change listener
    const handleStorageChange = (e) => {
      if (e.key === 'medqueue_current_announcement' || e.key === 'medqueue_queue' || !e.key) {
        fetchBoard();
      }
    };

    window.addEventListener('medqueue_announcement', handleDirectAnnouncement);
    window.addEventListener('storage', handleStorageChange);

    return () => {
      clearInterval(interval);
      window.removeEventListener('medqueue_announcement', handleDirectAnnouncement);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [fetchBoard]);

  // Toggle Mute / Audio ON
  const handleToggleAudio = () => {
    const nextState = !isAudioEnabled;
    setIsAudioEnabled(nextState);
    if (!nextState && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  };

  const curr = boardData.current_announcement;

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans p-6 flex flex-col justify-between">
      {/* Top Header Bar */}
      <header className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <span className="text-2xl font-black">🏥</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              MedQueue AI OPD Display
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase font-semibold">
                Live Broadcast
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Outpatient Department Patient Token Display & Bilingual Audio System
            </p>
          </div>
        </div>

        {/* Live Clock & Controls */}
        <div className="flex items-center gap-4">
          <div className="bg-slate-900 border border-slate-800 px-4 py-2 rounded-lg text-right">
            <div className="text-xl font-mono font-bold text-cyan-400">{currentTime}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Hospital Local Time</div>
          </div>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1.5 rounded-lg">
            <button
              onClick={handleToggleAudio}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                isAudioEnabled
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/30'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
              title="Toggle automatic speech announcement"
            >
              <span>{isAudioEnabled ? '🔊 Audio ON' : '🔇 Audio Muted'}</span>
            </button>

            <select
              value={currentLanguage}
              onChange={(e) => setCurrentLanguage(e.target.value)}
              className="bg-slate-800 text-xs text-slate-200 px-2 py-1.5 rounded border border-slate-700 focus:outline-none cursor-pointer"
            >
              <option value="both">EN + Telugu (ద్విభాష)</option>
              <option value="en">English Only</option>
              <option value="te">Telugu Only (తెలుగు)</option>
            </select>

            <button
              onClick={handleManualPlay}
              className="bg-slate-800 hover:bg-slate-700 text-xs px-2.5 py-1.5 rounded text-slate-300 hover:text-white transition-colors cursor-pointer"
              title="Re-play current announcement without creating a new call event"
            >
              ▶ Replay
            </button>
          </div>
        </div>
      </header>

      {/* Main Hero Section: Currently Called Token & Patient */}
      <main className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
        {/* Left 2 Columns: Big Prominent Token Calling Card */}
        <div className="lg:col-span-2 flex flex-col justify-center items-center bg-gradient-to-b from-slate-900 via-slate-900/80 to-slate-950 border-2 border-cyan-500/40 rounded-3xl p-8 relative overflow-hidden shadow-2xl shadow-cyan-950/40">
          <div className="absolute top-4 left-6 flex items-center gap-2">
            <span className="relative flex h-3.5 w-3.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs uppercase tracking-widest font-bold text-emerald-400">
              NOW CALLING / ప్రస్తుతం పిలుస్తున్నారు
            </span>
          </div>

          {curr ? (
            <div className="w-full text-center mt-6">
              {/* Token Pill */}
              <div className="inline-block bg-cyan-500/10 border border-cyan-500/30 rounded-2xl px-6 py-1.5 mb-2">
                <span className="text-cyan-400 text-xs font-bold uppercase tracking-wider">
                  Patient Token / రోగి టోకెన్
                </span>
              </div>

              {/* Huge Token Display */}
              <div className="text-6xl md:text-8xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-blue-400 to-indigo-400 tracking-tight font-mono py-1 drop-shadow-lg">
                {curr.token_display || `Token ${curr.patient_code || 'P1001'}`}
              </div>

              {/* Prominent Patient Name Display */}
              <div className="my-3">
                <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold block mb-0.5">
                  Patient Name / రోగి పేరు
                </span>
                <h2 className="text-3xl md:text-5xl font-black text-white tracking-tight drop-shadow-md">
                  {curr.patient_name || curr.patient_initials || 'Patient'}
                </h2>
              </div>

              {/* Visual Calling State Indicator */}
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold mb-5 shadow-xs animate-pulse">
                <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                <span>Active Call • Please Proceed to Consultation Room</span>
              </div>

              {/* Room & Doctor Card */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-xl mx-auto">
                <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-4 shadow-sm">
                  <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                    Proceed To / గది నంబర్
                  </div>
                  <div className="text-2xl md:text-3xl font-extrabold text-amber-300">
                    {curr.room_number || 'OPD Room 1'}
                  </div>
                </div>

                <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-4 shadow-sm">
                  <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                    Attending Physician / డాక్టర్
                  </div>
                  <div className="text-lg md:text-xl font-bold text-slate-100 truncate">
                    {curr.doctor_name || 'Consulting Physician'}
                  </div>
                </div>
              </div>

              {/* Bilingual Announcement Subtitle Banner for Hearing Impaired & Accessibility */}
              <div className="mt-6 bg-slate-950/80 border border-slate-800 rounded-2xl p-4 max-w-2xl mx-auto text-left shadow-inner">
                <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1 flex items-center justify-between">
                  <span>Visual Accessibility Subtitles (ద్విభాష సబ్-టైటిల్స్)</span>
                  {currentLanguage !== 'en' && !isTeluguVoiceAvailable && (
                    <span className="text-[10px] text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      Visual Telugu Mode Active
                    </span>
                  )}
                </div>
                <p className="text-sm text-cyan-200 font-medium">"{curr.speech_text_en}"</p>
                <p className="text-sm text-amber-200/90 font-medium mt-1 font-serif">"{curr.speech_text_te}"</p>
              </div>
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="text-5xl mb-4">⏳</div>
              <h3 className="text-xl font-semibold text-slate-300">Consultation Rooms Standing By</h3>
              <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
                Next patient will be called shortly. Please keep your OPD card and token ready.
              </p>
            </div>
          )}
        </div>

        {/* Right Column: Active Room Grid & Queue Stat */}
        <div className="flex flex-col gap-6">
          {/* Queue Depth Stat Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center justify-between shadow-lg">
            <div>
              <div className="text-xs text-slate-400 uppercase font-semibold tracking-wider">
                Waiting In OPD Queue
              </div>
              <div className="text-4xl font-extrabold text-white mt-1">
                {boardData.total_waiting}{' '}
                <span className="text-sm font-normal text-slate-400">patients</span>
              </div>
            </div>
            <div className="h-14 w-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-2xl text-blue-400">
              👥
            </div>
          </div>

          {/* Active Consultation Rooms List */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex-1 flex flex-col">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center justify-between">
              <span>Active Consultation Rooms</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                {boardData.active_called_tokens.length || (curr ? 1 : 0)} Active
              </span>
            </h3>

            <div className="space-y-3 overflow-y-auto flex-1 pr-1">
              {boardData.active_called_tokens.length > 0 ? (
                boardData.active_called_tokens.map((call, idx) => (
                  <div
                    key={call.event_id || idx}
                    className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between hover:border-slate-700 transition-colors"
                  >
                    <div>
                      <div className="text-base font-black text-cyan-400 font-mono">
                        {call.token_display}
                      </div>
                      <div className="text-xs text-white font-semibold mt-0.5">{call.patient_name}</div>
                      <div className="text-[11px] text-slate-400">{call.doctor_name}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-bold text-amber-400 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 inline-block">
                        {call.room_number}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-1">{call.department || 'General Medicine'}</div>
                    </div>
                  </div>
                ))
              ) : curr ? (
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between hover:border-slate-700 transition-colors">
                  <div>
                    <div className="text-base font-black text-cyan-400 font-mono">
                      {curr.token_display}
                    </div>
                    <div className="text-xs text-white font-semibold mt-0.5">{curr.patient_name}</div>
                    <div className="text-[11px] text-slate-400">{curr.doctor_name}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-bold text-amber-400 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 inline-block">
                      {curr.room_number || 'OPD Room 1'}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1">{curr.department || 'General Medicine'}</div>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-500 text-center py-8">
                  No consultation rooms currently calling patients.
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Bottom Footer Marquee: Recent Called Tokens History */}
      <footer className="mt-6 bg-slate-900 border border-slate-800 rounded-2xl p-3.5 flex items-center gap-4 overflow-hidden shadow-lg">
        <div className="shrink-0 flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider text-slate-300">
          <span>📢 Recent Calls:</span>
        </div>

        <div className="flex items-center gap-3 overflow-x-auto py-0.5 scrollbar-none flex-1">
          {boardData.recent_call_history.length > 0 ? (
            boardData.recent_call_history.map((hist, idx) => (
              <div
                key={hist.event_id || idx}
                className="shrink-0 flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-950 border border-slate-800 text-xs hover:border-slate-700 transition"
              >
                <span className="font-mono font-bold text-cyan-400">{hist.token_display || `Token ${hist.patient_code}`}</span>
                <span className="text-slate-500">→</span>
                <span className="text-slate-300 font-medium">{hist.room_number}</span>
                <span className="text-slate-200 font-bold">({hist.patient_name || hist.patient_initials})</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold uppercase">
                  CALLED
                </span>
              </div>
            ))
          ) : (
            <span className="text-xs text-slate-500">Awaiting initial token calls...</span>
          )}
        </div>
      </footer>
    </div>
  );
}
