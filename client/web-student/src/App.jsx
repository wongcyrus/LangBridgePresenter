import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { doc, onSnapshot, collection, getDocs } from "firebase/firestore";
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut
} from "firebase/auth";
import {
  AIError,
  getAI,
  getLiveGenerativeModel,
  ResponseModality,
  startAudioConversation,
  VertexAIBackend,
} from "firebase/ai";
import { app, auth, db, googleAuthProvider } from "./firebase";
import {
  formatBroadcastStatusLabel,
  normalizeBroadcastStatus,
  normalizeLanguageSelection,
  parseNumericIds,
} from "./utils/presentation";

// --- Icons ---
const PlayIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 5v14l11-7z" />
    </svg>
);

const PauseIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
    </svg>
);

const CloseIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
    </svg>
);

const ShowSubtitleIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 13c-3.13 0-6-2.03-7.8-5.5 1.8-3.47 4.67-5.5 7.8-5.5s6 2.03 7.8 5.5c-1.8 3.47-4.67 5.5-7.8 5.5zm0-8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm0 6c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
    </svg>
);

const HideSubtitleIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7L8.03 8.03C9.07 7.37 10.4 7 12 7zm0 10c-3.13 0-6-2.03-7.8-5.5 1.8-3.47 4.67-5.5 7.8-5.5.75 0 1.47.16 2.15.45l-1.63-1.63c-.5-.13-1.04-.22-1.52-.22-2.21 0-4 1.79-4 4s1.79 4 4 4c.48 0 .97-.09 1.4-.23l1.83 1.83c-.71.3-1.46.52-2.23.52zm4.3-5.74l3.15 3.15.01-.01L23.64 19l-1.41 1.41-3.28-3.28c-.89.23-1.8.36-2.75.36-3.13 0-6-2.03-7.8-5.5 1.15-1.92 2.76-3.37 4.67-4.38l1.79 1.79c-.07.03-.15.06-.22.09l-4.5-4.5L2.36 4.36 1 5.77l3.95 3.95c-1.45 1.62-2.58 3.49-3.43 5.55L1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.31 4.3-1.04zM12 11.5c.29 0 .56.03.82.09l-1.09-1.09c-.19.46-.3.97-.3 1.41 0 1.1.9 2 2 2 .44 0 .9-.1 1.3-.27l1.71 1.71c-.74.33-1.55.56-2.45.56-2.21 0-4-1.79-4-4 0-.91.3-1.75.79-2.44z"/>
    </svg>
);

const ChevronLeftIcon = () => (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="15 18 9 12 15 6"></polyline>
    </svg>
);

const ChevronRightIcon = () => (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="9 18 15 12 9 6"></polyline>
    </svg>
);

const LiveIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="8" />
    </svg>
);

const MicIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3zm5-3a1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V22h3a1 1 0 1 1 0 2H8a1 1 0 0 1 0-2h3v-3.07A7 7 0 0 1 5 12a1 1 0 1 1 2 0 5 5 0 1 0 10 0z"/>
    </svg>
);

const UserIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5zm0 2c-4.42 0-8 2.24-8 5a1 1 0 1 0 2 0c0-1.4 2.39-3 6-3s6 1.6 6 3a1 1 0 1 0 2 0c0-2.76-3.58-5-8-5z"/>
    </svg>
);

// --- FullScreen Slide Component ---
const FullScreenSlide = ({ slideUrl, text, onClose, onNext, onPrev, hasNext, hasPrev, isPlaying, onTogglePlay }) => {
    const [isSubtitleVisible, setIsSubtitleVisible] = useState(true);

    return (
        <div className="fullscreen-overlay">
            <button className="fullscreen-close-btn" onClick={(e) => { e.stopPropagation(); onClose(); }}>
                <CloseIcon />
            </button>
            
            {hasPrev && (
                <button className="nav-btn left" onClick={(e) => { e.stopPropagation(); onPrev(); }}>
                    <ChevronLeftIcon />
                </button>
            )}
            {hasNext && (
                <button className="nav-btn right" onClick={(e) => { e.stopPropagation(); onNext(); }}>
                    <ChevronRightIcon />
                </button>
            )}

            <div className="fullscreen-content" onClick={(e) => { e.stopPropagation(); onTogglePlay(); }}>
                {slideUrl ? (
                                                                    <img
                        src={slideUrl} 
                        alt="Presentation Slide"
                        className="fullscreen-image" 
                    />
                ) : (
                    <div className="fullscreen-placeholder">
                        <span>No Slide Image</span>
                    </div>
                )}
                
                <div 
                    className={`fullscreen-subtitle ${!isSubtitleVisible ? 'hidden' : ''}`}
                    onClick={(e) => e.stopPropagation()} // Prevent click through to image toggle
                >
                    <button 
                        className="fs-play-btn" 
                        onClick={(e) => { e.stopPropagation(); onTogglePlay(); }}
                    >
                        {isPlaying ? <PauseIcon /> : <PlayIcon />}
                    </button>
                    <p>{text}</p>
                    <button 
                        className="toggle-subtitle-btn" 
                        onClick={(e) => { e.stopPropagation(); setIsSubtitleVisible(!isSubtitleVisible); }}
                    >
                        {isSubtitleVisible ? <HideSubtitleIcon /> : <ShowSubtitleIcon />}
                    </button>
                </div>
            </div>
        </div>
    );
};

// --- Main App Component ---
function App() {
  const [searchParams] = useSearchParams();
  const hasClassParam = searchParams.has('class') || searchParams.has('courseId');
  const courseId = searchParams.get('class') || searchParams.get('courseId') || 'current';
  
  const [status, setStatus] = useState({ text: "🟡 Connecting...", color: "orange" });
  const [viewLang, setViewLang] = useState('en');
  const [listenLang, setListenLang] = useState('en');
  const [supportedLangs, setSupportedLangs] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [authStatus, setAuthStatus] = useState("Guest");
  
  // -- State for Live/Nav Logic --
  const [livePptId, setLivePptId] = useState(null);
  const [liveSlideId, setLiveSlideId] = useState(null);
  const [broadcastStatus, setBroadcastStatus] = useState(null);
  
  const [viewingPptId, setViewingPptId] = useState(null);
  const [viewingSlideId, setViewingSlideId] = useState(null);
  const [isLiveMode, setIsLiveMode] = useState(true); // Start in sync
  
  const [presentationList, setPresentationList] = useState([]); // List of presentation IDs
  const [slideList, setSlideList] = useState([]); // List of integers
  
  const [slideData, setSlideData] = useState(null); // Content of Viewing Slide
  const [liveData, setLiveData] = useState(null);   // Content of Live Broadcast (for audio)

  // Audio State
  const [isPlaying, setIsPlaying] = useState(false);
  const [autoplay, setAutoplay] = useState(true);
  const [isReady, setIsReady] = useState(false); 
  const [narrationStatus, setNarrationStatus] = useState("Idle");
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  
  // Full Screen State
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Sign in to use voice chat");
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [voiceAnswer, setVoiceAnswer] = useState("");
  const [voiceAccessGranted, setVoiceAccessGranted] = useState(false);
  const [voicePlatformBlockReason, setVoicePlatformBlockReason] = useState("");
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [adminEnabled, setAdminEnabled] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminStatus, setAdminStatus] = useState("");
  const [adminSummary, setAdminSummary] = useState(null);
  const [adminTopUsage, setAdminTopUsage] = useState([]);
  const [limitPerMinute, setLimitPerMinute] = useState(10);
  const [limitPerDay, setLimitPerDay] = useState(200);

  // Refs
  const audioRef = useRef(new Audio());
  const lastPlayedHash = useRef(null);
  const lastNarratedAudioUrl = useRef(null);
  const liveConversationRef = useRef(null);
  const liveContextKeyRef = useRef("");

  const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
  const LIVE_MODEL = "gemini-live-2.5-flash-native-audio";

  const AUDIO_LANGUAGE_NAMES = {
    "en-US": "English",
    "zh-CN": "普通話",
    "yue-HK": "廣東話"
  };

  const DISPLAY_LANGUAGE_NAMES = {
    "en-US": "English",
    "zh-CN": "中文简体",
    "yue-HK": "中文繁體"
  };

  const getTextLangName = (code) => DISPLAY_LANGUAGE_NAMES[code] || code;
  const getAudioLangName = (code) => AUDIO_LANGUAGE_NAMES[code] || code;
  const getUserLabel = (user) => {
    if (!user) return "Guest";
    const displayName = (user.displayName || "").trim();
    if (displayName) return displayName;
    const email = (user.email || "").trim();
    if (email.includes("@")) return email.split("@")[0];
    return user.uid || "User";
  };

  useEffect(() => {
    if (typeof navigator === "undefined") return;
    const userAgent = navigator.userAgent || "";
    const isIPadOS = navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
    const isIOSDevice = /iPad|iPhone|iPod/i.test(userAgent) || isIPadOS;
    const isIOSChrome = /CriOS/i.test(userAgent);
    if (isIOSDevice && isIOSChrome) {
      setVoicePlatformBlockReason("Voice chat is not supported on iPad/iPhone Chrome. Use Safari.");
      return;
    }
    setVoicePlatformBlockReason("");
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setCurrentUser(user);
      setAuthStatus(user ? `Signed in: ${getUserLabel(user)}` : "Guest");
      if (!user) {
        setVoiceStatus("Sign in to use voice chat");
      } else if (voicePlatformBlockReason) {
        setVoiceStatus(voicePlatformBlockReason);
      } else if (!API_BASE_URL) {
        setVoiceStatus("Voice chat unavailable: API base URL not configured");
      } else {
        setVoiceStatus("Checking voice access...");
      }
      if (!user) {
        setVoiceAccessGranted(false);
      }
    });
    return () => unsubscribe();
  }, [API_BASE_URL, voicePlatformBlockReason]);

  useEffect(() => {
    if (currentUser) {
      loadAdminDashboard(currentUser);
      loadVoiceAccess(currentUser);
    }
  }, [currentUser]);

  const handleSignIn = async () => {
    try {
      await signInWithPopup(auth, googleAuthProvider);
    } catch (error) {
      console.error("Sign-in failed:", error);
      setVoiceStatus(error?.message || "Sign-in failed");
    }
  };

  const handleSignOut = async () => {
    try {
      if (liveConversationRef.current) {
        await liveConversationRef.current.controller.stop();
        await liveConversationRef.current.session.close();
        liveConversationRef.current = null;
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      await signOut(auth);
      setVoiceTranscript("");
      setVoiceAnswer("");
      setVoiceAccessGranted(false);
      setAdminEnabled(false);
      setAdminStatus("");
      setAdminSummary(null);
      setAdminTopUsage([]);
    } catch (error) {
      console.error("Sign-out failed:", error);
    }
  };

  const loadAdminDashboard = async (user = currentUser) => {
    if (!user || !API_BASE_URL) return;
    setAdminLoading(true);
    try {
      const idToken = await user.getIdToken();
      const response = await fetch(`${API_BASE_URL}/api/voice-chat-admin`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${idToken}`,
        },
      });

      if (response.status === 401 || response.status === 403) {
        setAdminEnabled(false);
        setAdminStatus("");
        return;
      }
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Failed to load admin dashboard");
      }

      const data = await response.json();
      setAdminEnabled(true);
      setAdminStatus("");
      setAdminSummary(data.summary || null);
      setAdminTopUsage(Array.isArray(data.top_usage) ? data.top_usage : []);
      if (data.limits) {
        setLimitPerMinute(data.limits.requests_per_minute ?? 10);
        setLimitPerDay(data.limits.requests_per_day ?? 200);
      }
    } catch (error) {
      setAdminEnabled(false);
      setAdminStatus("");
    } finally {
      setAdminLoading(false);
    }
  };

  const loadVoiceAccess = async (user = currentUser) => {
    if (!user) return;
    if (voicePlatformBlockReason) {
      setVoiceAccessGranted(false);
      setVoiceStatus(voicePlatformBlockReason);
      return;
    }
    if (!API_BASE_URL) {
      setVoiceAccessGranted(false);
      setVoiceStatus("Voice chat unavailable: API base URL not configured");
      return;
    }
    try {
      const idToken = await user.getIdToken();
      const response = await fetch(`${API_BASE_URL}/api/voice-chat-access`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${idToken}`,
        },
      });
      if (response.status === 401) {
        setVoiceAccessGranted(false);
        setVoiceStatus("Session expired. Please sign in again");
        return;
      }
      if (response.status === 403) {
        setVoiceAccessGranted(false);
        setVoiceStatus("Voice chat access requires admin grant");
        return;
      }
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Failed to check voice access");
      }
      const granted = data.granted === true;
      setVoiceAccessGranted(granted);
      setVoiceStatus(granted ? "Ready for voice chat" : "Voice chat access requires admin grant");
    } catch (error) {
      console.error("Voice access check failed:", error);
      setVoiceAccessGranted(false);
      setVoiceStatus(error?.message || "Voice chat access check failed");
    }
  };

  const saveAdminLimits = async () => {
    if (!currentUser || !API_BASE_URL) return;
    setAdminLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(`${API_BASE_URL}/api/voice-chat-admin`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          requests_per_minute: Number(limitPerMinute),
          requests_per_day: Number(limitPerDay),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Failed to update limits");
      }
      setAdminStatus("Limits updated");
      await loadAdminDashboard();
    } catch (error) {
      console.error("Admin limits update failed:", error);
      setAdminStatus(error.message || "Failed to update limits");
    } finally {
      setAdminLoading(false);
    }
  };

  const buildVoiceContext = () => {
    const presentationId = viewingPptId || livePptId;
    const slideId = viewingSlideId || liveSlideId;
    if (!presentationId || !slideId) return null;

    const langMap = (slideData?.languages || liveData || {});
    const langEntry = langMap[listenLang] || langMap[Object.keys(langMap)[0]] || {};
    const slideText = (langEntry?.text || "").trim();
    const contextKey = `${courseId}:${presentationId}:${slideId}:${listenLang}:${slideText}`;

    const message = [
      "Context update for the ongoing classroom conversation.",
      "Do not answer this message.",
      `Course: ${courseId}`,
      `Presentation: ${presentationId}`,
      `Slide: ${slideId}`,
      `Language: ${listenLang || "en-US"}`,
      `Slide text: ${slideText || "(not available)"}`,
    ].join("\n");

    return { contextKey, message };
  };

  const sendVoiceContextUpdate = async (session, force = false) => {
    const context = buildVoiceContext();
    if (!context) return;
    if (!force && context.contextKey === liveContextKeyRef.current) return;
    await session.send(context.message, false);
    liveContextKeyRef.current = context.contextKey;
  };

  const startVoiceCapture = async () => {
    if (!currentUser) {
      setVoiceStatus("Sign in to use voice chat");
      return;
    }
    if (!voiceAccessGranted) {
      setVoiceStatus("Voice chat access requires admin grant");
      return;
    }
    if (voicePlatformBlockReason) {
      setVoiceStatus(voicePlatformBlockReason);
      return;
    }
    if (isListening || voiceBusy) return;

    const presentationId = viewingPptId || livePptId;
    const slideId = viewingSlideId || liveSlideId;
    if (!presentationId || !slideId) {
      setVoiceStatus("No active slide to discuss");
      return;
    }

    setVoiceBusy(true);
    setVoiceTranscript("");
    setVoiceAnswer("");
    stopNarration();
    setAutoplay(false);
    setVoiceStatus("Connecting Gemini Live...");
    try {
      const ai = getAI(app, {
        backend: new VertexAIBackend("us-east1"),
        useLimitedUseAppCheckTokens: true,
      });
      const model = getLiveGenerativeModel(ai, {
        model: LIVE_MODEL,
        generationConfig: {
          responseModalities: [ResponseModality.AUDIO],
        },
      });
      const session = await model.connect();
      await session.send(
        `You are a classroom voice assistant. Keep responses concise and use ${listenLang || "en-US"}.`,
        false
      );
      await sendVoiceContextUpdate(session, true);
      const controller = await startAudioConversation(session);
      liveConversationRef.current = { controller, session };
      setIsListening(true);
      setVoiceStatus("Gemini Live connected");
    } catch (error) {
      console.error("Gemini Live connection failed:", error);
      if (error instanceof AIError) {
        setVoiceStatus(`Live API error: ${error.message}`);
      } else {
        setVoiceStatus(error?.message || "Failed to connect Gemini Live");
      }
    } finally {
      setVoiceBusy(false);
    }
  };

  useEffect(() => {
    if (!isListening || !liveConversationRef.current?.session) return;
    sendVoiceContextUpdate(liveConversationRef.current.session).catch((error) => {
      console.error("Failed to update Gemini Live context:", error);
    });
  }, [isListening, courseId, viewingPptId, viewingSlideId, livePptId, liveSlideId, listenLang, slideData, liveData]);

  const stopVoiceCapture = async () => {
    if (!liveConversationRef.current) {
      setIsListening(false);
      setVoiceStatus("Live session not running");
      return;
    }
    setVoiceBusy(true);
    try {
      await liveConversationRef.current.controller.stop();
      await liveConversationRef.current.session.close();
      liveConversationRef.current = null;
      liveContextKeyRef.current = "";
      setIsListening(false);
      setVoiceStatus("Gemini Live stopped");
    } catch (error) {
      console.error("Failed to stop Gemini Live:", error);
      setVoiceStatus(error?.message || "Failed to stop Gemini Live");
    } finally {
      setVoiceBusy(false);
    }
  };

  useEffect(() => {
    if (hasClassParam) {
      setIsReady(true);
    }
  }, [hasClassParam]);

  // Helper to extract data for specific language
  const getLangContent = (languagesMap, langCode) => {
    if (!languagesMap) return null;
    let content = languagesMap[langCode];
    if (!content) {
        const match = Object.keys(languagesMap).find(k => k.startsWith(langCode) || langCode.startsWith(k));
        if (match) content = languagesMap[match];
    }
    return content;
  };

  const cycleLanguage = (currentLang, direction = 1) => {
    if (!supportedLangs.length) return currentLang;

    const currentIndex = supportedLangs.indexOf(currentLang);
    const fallbackIndex = currentIndex === -1 ? 0 : currentIndex;
    const nextIndex = (fallbackIndex + direction + supportedLangs.length) % supportedLangs.length;
    return supportedLangs[nextIndex];
  };

  const syncAudioState = () => {
    setAudioCurrentTime(audioRef.current.currentTime || 0);
    setAudioDuration(Number.isFinite(audioRef.current.duration) ? audioRef.current.duration : 0);
    setIsPlaying(!audioRef.current.paused && !audioRef.current.ended);
  };

  const startAudioPlayback = (audioUrl, { restart = true } = {}) => {
    if (!audioUrl) {
      setNarrationStatus("Narration audio unavailable");
      return;
    }

    if (audioRef.current.src !== audioUrl) {
      audioRef.current.src = audioUrl;
    }

    if (restart) {
      audioRef.current.currentTime = 0;
      setAudioCurrentTime(0);
    }

    lastNarratedAudioUrl.current = audioUrl;
    setNarrationStatus("Playing MP3 narration");
    audioRef.current.play()
      .then(() => {
        setIsPlaying(true);
        setNarrationStatus("Narrating");
      })
      .catch((error) => {
        console.error("Narration playback blocked:", error);
        setIsPlaying(false);
        setNarrationStatus("Narration playback blocked");
      });
  };

  const stopNarration = () => {
    audioRef.current.pause();
    audioRef.current.currentTime = 0;
    setAudioCurrentTime(0);
    setNarrationStatus("Stopped");
  };

  useEffect(() => {
    return () => {
      if (liveConversationRef.current) {
        liveConversationRef.current.controller.stop();
        liveConversationRef.current.session.close();
        liveConversationRef.current = null;
        liveContextKeyRef.current = "";
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const narrateCurrentSlide = () => {
    if (isListening || voiceBusy) {
      setNarrationStatus("Narration paused during voice chat");
      return;
    }

    const audioUrl = resolveActiveAudioUrl();
    if (!audioUrl) {
      setNarrationStatus("Narration audio unavailable");
      return;
    }

    startAudioPlayback(audioUrl, { restart: true });
  };

  // --- 1. Listen to Root Broadcast (Live State) ---
  useEffect(() => {
    if (!isReady) return;

    const unsubscribe = onSnapshot(doc(db, "presentation_broadcast", courseId), (docSnapshot) => {
      if (docSnapshot.exists()) {
        setStatus({ text: "🟢 Live", color: "green" });
        const data = docSnapshot.data();

        // Update Live Pointers
        if (data.current_presentation_id) setLivePptId(data.current_presentation_id);
        if (data.current_slide_id) setLiveSlideId(data.current_slide_id);
        setBroadcastStatus(normalizeBroadcastStatus(data.broadcast_status));
        
        // Update Live Content (Audio/Text)
        if (data.latest_languages) {
            setLiveData(data.latest_languages);
            
            // Update supported languages list and sync selection
            const langs = Object.keys(data.latest_languages);
            if (langs.length > 0) {
                setSupportedLangs(langs);
                
                setViewLang(prev => normalizeLanguageSelection(prev, langs));
                setListenLang(prev => normalizeLanguageSelection(prev, langs));
            }
        }
      } else {
          setStatus({ text: "🟡 Waiting for Class...", color: "orange" });
      }
    });
    return () => unsubscribe();
  }, [courseId, isReady]);

  // --- 1b. Fetch Presentation List ---
  useEffect(() => {
      if (!isReady) return;
      
      console.log("Fetching presentation list for course:", courseId);
      const pptCollection = collection(db, "presentation_broadcast", courseId, "presentations");
      const unsubscribe = onSnapshot(pptCollection, (snapshot) => {
          const ppts = snapshot.docs.map(doc => doc.id);
          console.log("Presentation list fetched:", ppts);
          setPresentationList(ppts);
      }, (error) => {
          console.error("Error fetching presentation list:", error);
      });
      return () => unsubscribe();
  }, [courseId, isReady]);

  // --- 1c. Auto-select first presentation if none selected ---
  useEffect(() => {
      if (!viewingPptId && presentationList.length > 0) {
          console.log("[DEBUG] Auto-selecting first presentation:", presentationList[0]);
          setViewingPptId(presentationList[0]);
      }
  }, [presentationList, viewingPptId]);

  // --- 2. Sync Logic: Keep viewing pointers in sync with live if isLiveMode ---
  useEffect(() => {
      if (isLiveMode) {
          if (livePptId) setViewingPptId(livePptId);
          if (liveSlideId) setViewingSlideId(liveSlideId);
      }
  }, [livePptId, liveSlideId, isLiveMode]);

  // --- 3. Fetch Slide List for Navigation ---
  useEffect(() => {
      if (!isReady || !viewingPptId) return;
      
      console.log(`[DEBUG] Fetching slide list. Course: "${courseId}", PPT: "${viewingPptId}" (len: ${viewingPptId.length})`);
      console.log(`[DEBUG] PPT ID Char Codes: ${viewingPptId.split('').map(c => c.charCodeAt(0)).join(',')}`);

      // Step-by-step reference construction for debugging/safety
      try {
          const rootRef = collection(db, "presentation_broadcast");
          const courseRef = doc(rootRef, courseId);
          const pptsRef = collection(courseRef, "presentations");
          const pptRef = doc(pptsRef, viewingPptId);
          const slidesCol = collection(pptRef, "slides");

          console.log(`[DEBUG] Resolved Path: ${slidesCol.path}`);

          const unsubscribe = onSnapshot(slidesCol, (snapshot) => {
              console.log(`[DEBUG] Slide list snapshot received. Size: ${snapshot.size}`);
              
              const rawIds = snapshot.docs.map(d => d.id);
              console.log("[DEBUG] Raw Slide IDs:", rawIds);
    
              const ids = parseNumericIds(rawIds);
              console.log("[DEBUG] Parsed Slide IDs:", ids);
              setSlideList(ids);
          }, (error) => {
              console.error("[DEBUG] Error fetching slide list:", error);
          });
    
          return () => unsubscribe();
      } catch (err) {
          console.error("[DEBUG] Error constructing refs:", err);
      }
  }, [courseId, viewingPptId, isReady, isLiveMode]);

  // --- 3b. Auto-select first slide when switching presentations ---
  useEffect(() => {
      if (slideList.length > 0) {
          // If viewingSlideId is null, or not in the new list, default to first
          const current = parseInt(viewingSlideId, 10);
          if (isNaN(current) || !slideList.includes(current)) {
              setViewingSlideId(String(slideList[0]));
          }
      }
  }, [slideList, viewingSlideId]);

  // --- 4. Listen/Fetch Viewing Slide Data ---
  useEffect(() => {
      if (!isReady || !viewingPptId || !viewingSlideId) {
          if (viewingSlideId === null) setSlideData(null);
          return;
      }

      console.log(`[DEBUG] Fetching single slide. PPT: "${viewingPptId}", Slide: "${viewingSlideId}"`);
      const basePath = `presentation_broadcast/${courseId}/presentations`;

      const slideRef = doc(db, basePath, viewingPptId, "slides", String(viewingSlideId));
      const unsubscribe = onSnapshot(slideRef, (docSnapshot) => {
          console.log(`[DEBUG] Single slide snapshot for #${viewingSlideId}: exists=${docSnapshot.exists()}`);
          if (docSnapshot.exists()) {
              const data = docSnapshot.data();
              setSlideData(data);

              // Update supported languages from the slide data if available
              if (data.languages) {
                  const langs = Object.keys(data.languages);
                  if (langs.length > 0) {
                      // Only update if significantly different to avoid loops, or just set it
                      // Ideally, we merge or prioritize. For now, if we are viewing this slide, 
                      // these are the langs we can see.
                      setSupportedLangs(langs);
                      
                      // Ensure current selection is valid
                      if (!langs.includes(viewLang)) setViewLang(langs[0]);
                      if (!langs.includes(listenLang)) setListenLang(langs[0]);
                  }
              }

          } else {
              // If doc missing (maybe audio only update?), try to fallback to liveData if we are live
              if (isLiveMode && String(viewingSlideId) === String(liveSlideId)) {
                  setSlideData({ languages: liveData }); 
              } else {
                  setSlideData(null);
              }
          }
      });
      return () => unsubscribe();
  }, [courseId, isReady, viewingPptId, viewingSlideId, liveSlideId, liveData, isLiveMode]);

  // --- Render Logic Pre-calculation ---
  // For Visuals/Text (View Language)
  const liveContentView = getLangContent(liveData, viewLang);
  const viewingContentView = getLangContent(slideData?.languages, viewLang);
  
  // For Audio (Listen Language)
  const liveContentAudio = getLangContent(liveData, listenLang);
  const viewingContentAudio = getLangContent(slideData?.languages, listenLang);
  
  const resolveActiveAudioUrl = () => {
    // Strictly use audio-language content path only.
    // No fallback to display-language content.
    const audioContent = isLiveMode ? liveContentAudio : viewingContentAudio;
    return audioContent?.audio_url || null;
  };

  // Audio Source Decision
  // If Sync is ON: Play LIVE audio (from listenLang)
  // If Sync is OFF: Play Viewing Slide audio (from listenLang)
  const activeAudioUrl = resolveActiveAudioUrl();

  // --- 5. Audio Player Logic ---
  useEffect(() => {
      if (!activeAudioUrl || !autoplay || isListening || voiceBusy) return;

      if (lastPlayedHash.current !== activeAudioUrl) {
          lastPlayedHash.current = activeAudioUrl;
          startAudioPlayback(activeAudioUrl, { restart: false });
      }
  }, [activeAudioUrl, autoplay, isListening, voiceBusy]);

  // Audio Events
  useEffect(() => {
      const audio = audioRef.current;
      const handlePlay = () => syncAudioState();
      const handlePause = () => syncAudioState();
      const handleEnded = () => {
        syncAudioState();
        setAudioCurrentTime(0);
      };
      const handleTimeUpdate = () => setAudioCurrentTime(audio.currentTime || 0);
      const handleLoadedMetadata = () => syncAudioState();
      const handleDurationChange = () => syncAudioState();

      audio.addEventListener('play', handlePlay);
      audio.addEventListener('pause', handlePause);
      audio.addEventListener('ended', handleEnded);
      audio.addEventListener('timeupdate', handleTimeUpdate);
      audio.addEventListener('loadedmetadata', handleLoadedMetadata);
      audio.addEventListener('durationchange', handleDurationChange);
      return () => {
          audio.removeEventListener('play', handlePlay);
          audio.removeEventListener('pause', handlePause);
          audio.removeEventListener('ended', handleEnded);
          audio.removeEventListener('timeupdate', handleTimeUpdate);
          audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
          audio.removeEventListener('durationchange', handleDurationChange);
      };
  }, []);

  useEffect(() => {
      return () => {
          audioRef.current.pause();
          audioRef.current.src = '';
      };
  }, []);

  const togglePlay = () => {
      if (isListening || voiceBusy) {
        setNarrationStatus("Narration paused during voice chat");
        return;
      }

      if (isPlaying) {
        audioRef.current.pause();
        return;
      }

      const audioUrl = resolveActiveAudioUrl();
      if (!audioRef.current.src || audioRef.current.src !== audioUrl) {
        if (!audioUrl) {
          setNarrationStatus("Narration audio unavailable");
          return;
        }
        startAudioPlayback(audioUrl, { restart: false });
        return;
      }

      if (audioRef.current.ended) {
        audioRef.current.currentTime = 0;
        setAudioCurrentTime(0);
      }

      audioRef.current.play()
        .then(() => setIsPlaying(true))
        .catch((error) => {
          console.error("Playback failed:", error);
          setNarrationStatus("Narration playback blocked");
        });
  };

  const seekAudio = (seconds) => {
    if (!audioRef.current.src) return;
    const duration = Number.isFinite(audioRef.current.duration) ? audioRef.current.duration : 0;
    const nextTime = Math.min(Math.max((audioRef.current.currentTime || 0) + seconds, 0), duration || Infinity);
    audioRef.current.currentTime = nextTime;
    setAudioCurrentTime(nextTime);
  };

  const jumpToAudioStart = () => {
    if (!audioRef.current.src) return;
    audioRef.current.currentTime = 0;
    setAudioCurrentTime(0);
  };

  const formatTime = (seconds) => {
    if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${String(secs).padStart(2, "0")}`;
  };

  // --- Handlers ---
  const handleNext = () => {
      if (!viewingSlideId || slideList.length === 0) return;
      const currentNum = parseInt(viewingSlideId, 10);
      const idx = slideList.indexOf(currentNum);
      if (idx !== -1 && idx < slideList.length - 1) {
          setViewingSlideId(String(slideList[idx + 1]));
          setIsLiveMode(false); // User manually navigated, break sync
      }
  };

  const handlePrev = () => {
      if (!viewingSlideId || slideList.length === 0) return;
      const currentNum = parseInt(viewingSlideId, 10);
      const idx = slideList.indexOf(currentNum);
      if (idx > 0) {
          setViewingSlideId(String(slideList[idx - 1]));
          setIsLiveMode(false); // User manually navigated, break sync
      }
  };

  const toggleLiveMode = () => {
      if (isLiveMode) {
          setIsLiveMode(false);
      } else {
          setViewingPptId(livePptId);
          setViewingSlideId(liveSlideId);
          setIsLiveMode(true);
      }
  };

  useEffect(() => {
      const onKeyDown = (event) => {
          const target = event.target;
          const tagName = target?.tagName?.toLowerCase();
          if (tagName === "input" || tagName === "textarea" || tagName === "select" || target?.isContentEditable) {
              return;
          }

          if (isListening || voiceBusy) {
              const blockedKeys = new Set([" ", "spacebar", "r", "s", "a", "d", "home"]);
              const normalized = (event.key || "").toLowerCase();
              if (blockedKeys.has(normalized) || event.code === "Space") {
                  event.preventDefault();
                  return;
              }
          }

          if (event.key === "Escape") {
              if (isFullScreen) {
                  setIsFullScreen(false);
              } else {
                  stopNarration();
                  setAutoplay(false);
              }
              return;
          }

          if (event.key === "ArrowLeft") {
              event.preventDefault();
              handlePrev();
          } else if (event.key === "ArrowRight") {
              event.preventDefault();
              handleNext();
          } else if (event.key === " " || event.key === "Spacebar" || event.code === "Space") {
              event.preventDefault();
              togglePlay();
          } else if (event.key.toLowerCase() === "l") {
              event.preventDefault();
              toggleLiveMode();
          } else if (event.key.toLowerCase() === "r") {
              event.preventDefault();
              narrateCurrentSlide();
          } else if (event.key.toLowerCase() === "s") {
              event.preventDefault();
              stopNarration();
          } else if (event.key.toLowerCase() === "a" && !event.altKey) {
              event.preventDefault();
              seekAudio(event.shiftKey ? -30 : -10);
          } else if (event.key.toLowerCase() === "d" && !event.altKey) {
              event.preventDefault();
              seekAudio(event.shiftKey ? 30 : 10);
          } else if (event.key === "Home") {
              event.preventDefault();
              jumpToAudioStart();
          }

          if (!event.altKey) return;

          if (event.key.toLowerCase() === "v") {
              event.preventDefault();
              setViewLang((prev) => cycleLanguage(prev, event.shiftKey ? -1 : 1));
          } else if (event.key.toLowerCase() === "a") {
              event.preventDefault();
              setListenLang((prev) => cycleLanguage(prev, event.shiftKey ? -1 : 1));
          }
      };

      window.addEventListener("keydown", onKeyDown);
      return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullScreen, livePptId, liveSlideId, viewLang, listenLang, isLiveMode, viewingSlideId, viewingPptId, slideData, liveData, slideList, togglePlay, narrateCurrentSlide, stopNarration, seekAudio, jumpToAudioStart, handlePrev, handleNext, toggleLiveMode, activeAudioUrl, isPlaying, isListening, voiceBusy]);

  if (!isReady) {
      return (
          <div className="splash-screen">
              <h1>LangBridge</h1>
              <button onClick={() => setIsReady(true)}>Join Class</button>
              <p className="attribution">Developed by Higher Diploma in Cloud and Data Centre Administration at HKIIT</p>
          </div>
      );
  }

  // Priority: Viewing Slide Registry > Live Data (fallback if visual matches)
  const visualUrl = viewingContentView?.slide_link || (isLiveMode && String(viewingSlideId) === String(liveSlideId) ? liveContentView?.slide_link : null);
  
  // Text priority: Viewing Slide text (if browsing) -> Live text (if live)
  // This ensures text matches the audio language
  const displayText = (isLiveMode ? liveContentAudio?.text : viewingContentAudio?.text) || "(Translating...)";

  const currentNum = parseInt(viewingSlideId, 10);
  const hasPrev = slideList.length > 0 && slideList.indexOf(currentNum) > 0;
  const hasNext = slideList.length > 0 && slideList.indexOf(currentNum) < slideList.length - 1;
  const readAloudLabel = autoplay ? "Read aloud: On" : "Read aloud: Off";
  const canUseVoiceChat = Boolean(currentUser && voiceAccessGranted && !voicePlatformBlockReason);

  return (
    <div className="container single-slide-view">
      {isFullScreen && (
          <FullScreenSlide 
              slideUrl={visualUrl} 
              text={displayText}
              onClose={() => setIsFullScreen(false)}
              onNext={handleNext}
              onPrev={handlePrev}
              hasNext={hasNext}
              hasPrev={hasPrev}
              isPlaying={isPlaying}
              onTogglePlay={togglePlay}
          />
      )}

      <header>
        <h1>🎓 LangBridge</h1>
        <div className="controls">
            <div className="status" style={{ color: status.color }}>{status.text}</div>
            <div className="lang-select" title="Display Language">
                <span className="lang-select-icon">🌐</span>
                <select 
                    value={viewLang} 
                    onChange={(e) => setViewLang(e.target.value)}
                >
                    {supportedLangs.map(lang => <option key={lang} value={lang}>{getTextLangName(lang)}</option>)}
                </select>
            </div>
            <div className="lang-select" title="Audio Language">
                <span className="lang-select-icon">🔊</span>
                    <select 
                        value={listenLang} 
                        onChange={(e) => setListenLang(e.target.value)}
                    >
                        {supportedLangs.map(lang => <option key={lang} value={lang}>{getAudioLangName(lang)}</option>)}
                    </select>
            </div>
            <button
              type="button"
              className="account-action-btn"
              onClick={currentUser ? handleSignOut : handleSignIn}
            >
              <UserIcon />
              <span>{currentUser ? "Sign out" : "Sign in"}</span>
            </button>
                            </div>
                        </header>      
      <div className="identity-status">
        {authStatus}
      </div>
      {canUseVoiceChat ? (
        <div className="voice-assistant-panel">
          <div className="voice-assistant-top">
            <span className="voice-assistant-label">Voice Assistant</span>
            <button
              type="button"
              className={`voice-action-btn ${isListening || voiceBusy ? "active" : ""}`}
              onClick={isListening || voiceBusy ? stopVoiceCapture : startVoiceCapture}
            >
              <MicIcon />
              <span>{isListening || voiceBusy ? "Stop" : "Start"}</span>
            </button>
          </div>
          <div className="voice-assistant-status">{voiceStatus}</div>
          {voiceTranscript && (
            <div className="voice-transcript">
              <strong>You said:</strong> {voiceTranscript}
            </div>
          )}
          {voiceAnswer && (
            <div className="voice-answer">
              <strong>Assistant:</strong> {voiceAnswer}
            </div>
          )}
        </div>
      ) : (
        <div className="voice-assistant-inline">
          <MicIcon />
          <span>{voiceStatus}</span>
        </div>
      )}
      {currentUser && adminEnabled && (
        <div style={{ marginBottom: "10px", border: "1px solid #e5e7eb", borderRadius: "8px", padding: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <strong>Voice Chat Admin</strong>
            <button
              type="button"
              onClick={() => loadAdminDashboard()}
              disabled={adminLoading}
              style={{ borderRadius: "14px", border: "1px solid #ddd", padding: "4px 10px", background: "#fff" }}
            >
              Refresh
            </button>
          </div>
          <>
              {adminSummary && (
                <div style={{ fontSize: "0.85rem", marginBottom: "8px" }}>
                  Tracked users: {adminSummary.tracked_users} · Today requests: {adminSummary.total_today_requests}
                </div>
              )}
              <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap", marginBottom: "8px" }}>
                <label style={{ fontSize: "0.85rem" }}>
                  Per minute
                  <input
                    type="number"
                    min="1"
                    value={limitPerMinute}
                    onChange={(e) => setLimitPerMinute(e.target.value)}
                    style={{ marginLeft: "6px", width: "80px" }}
                  />
                </label>
                <label style={{ fontSize: "0.85rem" }}>
                  Per day
                  <input
                    type="number"
                    min="1"
                    value={limitPerDay}
                    onChange={(e) => setLimitPerDay(e.target.value)}
                    style={{ marginLeft: "6px", width: "90px" }}
                  />
                </label>
                <button
                  type="button"
                  onClick={saveAdminLimits}
                  disabled={adminLoading}
                  style={{ borderRadius: "14px", border: "1px solid #ddd", padding: "4px 10px", background: "#fff" }}
                >
                  Save limits
                </button>
              </div>
              {adminStatus && <div style={{ fontSize: "0.82rem", color: "#4b5563", marginBottom: "6px" }}>{adminStatus}</div>}
              <div style={{ maxHeight: "160px", overflow: "auto", fontSize: "0.8rem", borderTop: "1px solid #f3f4f6", paddingTop: "6px" }}>
                {adminTopUsage.slice(0, 15).map((row) => (
                  <div key={row.uid} style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "2px 0" }}>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{row.uid}</span>
                    <span>{row.day_count} today</span>
                  </div>
                ))}
              </div>
          </>
        </div>
      )}
      <div className="sub-header">
        <div className="nav-controls">
            {/* Presentation Selector */}
            <select 
                value={viewingPptId || ''} 
                onChange={(e) => {
                    setViewingPptId(e.target.value);
                    setIsLiveMode(false);
                }}
                style={{
                    padding: '6px 10px',
                    borderRadius: '20px',
                    border: '1px solid #ddd',
                    fontSize: '0.9rem',
                    maxWidth: '160px',
                    backgroundColor: '#fff'
                }}
            >
                {presentationList.length === 0 && <option value="">No presentations found</option>}
                {presentationList.map(ppt => (
                    <option key={ppt} value={ppt}>{ppt}</option>
                ))}
            </select>

            <button disabled={!hasPrev} onClick={handlePrev} className="nav-btn-mini">
                <ChevronLeftIcon />
            </button>
            
            <select 
                value={viewingSlideId || ''} 
                onChange={(e) => {
                    const newVal = e.target.value;
                    setViewingSlideId(newVal);
                    // If user manually selects the LIVE slide, we could auto-sync, 
                    // but let's keep it manual unless they click the LIVE badge.
                    // Actually, if they pick the *current* live ID, might as well sync?
                    // Let's stick to standard behavior: manual nav breaks sync.
                    setIsLiveMode(false); 
                }}
                style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    fontSize: '0.9rem',
                    background: 'white',
                    maxWidth: '80px'
                }}
            >
                {slideList.map(id => (
                    <option key={id} value={id}>#{id}</option>
                ))}
            </select>

            <button 
                onClick={toggleLiveMode} 
                className={`live-badge ${isLiveMode ? 'active' : 'inactive'}`}
                style={{
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '5px',
                    border: isLiveMode ? '1px solid #4caf50' : '1px solid #ccc',
                    background: isLiveMode ? '#e8f5e9' : '#fff',
                    color: isLiveMode ? '#2e7d32' : '#666',
                    borderRadius: '20px',
                    padding: '4px 10px',
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                }}
            >
                <div style={{
                    width: '8px', 
                    height: '8px', 
                    borderRadius: '50%', 
                    background: isLiveMode ? '#4caf50' : '#ccc'
                }}></div>
                {isLiveMode ? 'LIVE' : 'Sync'}
            </button>

            <button disabled={!hasNext} onClick={handleNext} className="nav-btn-mini">
                <ChevronRightIcon />
            </button>

          <div className="narration-controls">
            <button
              className={`narration-btn ${autoplay ? 'active' : ''}`}
              title="Automatically play new MP3s"
              onClick={() => {
                setAutoplay((prev) => !prev);
              }}
            >
              {readAloudLabel}
            </button>
            <button className="narration-btn" title="Restart from beginning (R)" onClick={narrateCurrentSlide}>
              Restart
            </button>
            <button className="narration-btn secondary" title="Stop (S)" onClick={stopNarration}>
              Stop
            </button>
          </div>
          <div className="audio-seek-row">
            <button
              className="audio-play-btn"
              title={isPlaying ? "Pause (Space)" : "Play / pause from current position (Space)"}
              aria-label={isPlaying ? "Pause" : "Play / pause from current position"}
              onClick={(e) => { e.stopPropagation(); togglePlay(); }}
              disabled={!activeAudioUrl}
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </button>
            <span className="audio-time">{formatTime(audioCurrentTime)}</span>
            <input
              className="audio-seek"
              type="range"
              min="0"
              max={audioDuration || 0}
              step="0.1"
              value={Math.min(audioCurrentTime, audioDuration || audioCurrentTime || 0)}
              onChange={(e) => {
                const nextTime = Number(e.target.value);
                audioRef.current.currentTime = nextTime;
                setAudioCurrentTime(nextTime);
              }}
              aria-label="Audio progress"
              title="Seek audio"
              disabled={!audioDuration}
            />
            <span className="audio-time">{formatTime(audioDuration)}</span>
          </div>
          <div className="compact-meta">
            <span className="shortcut-hint">
              Language: Alt+V view · Alt+A audio
            </span>
            <span className="shortcut-hint">
              Navigation: ←/→ slide · L sync/live · Esc close/stop
            </span>
            <span className="shortcut-hint">
              Player: Space play/pause · R restart · A/D seek (Shift=30s) · S stop · Home start
            </span>
            <span className="shortcut-hint">
              Voice chat active: player shortcuts are blocked
            </span>
            <span className="compact-status-line">Narration: {narrationStatus}</span>
          </div>
        </div>
      </div>

      <div className="main-stage">
          <div className="slide-container" onClick={() => setIsFullScreen(true)}>
            {visualUrl ? (
                <img src={visualUrl} alt="Current Slide" className="main-slide-image" />
            ) : (
                <div className="slide-placeholder">
                    <p>No Slide Image Available</p>
                    <small>Slide #{viewingSlideId}</small>
                </div>
            )}
            <div className="slide-overlay-btn">Click to Expand</div>
          </div>

          <div className="caption-container">
             <div className="caption-text">
                 {displayText}
             </div>
          </div>
      </div>
    </div>
  );
}

export default App;