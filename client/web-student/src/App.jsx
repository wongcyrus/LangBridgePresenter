import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { doc, onSnapshot, collection, getDocs, getDoc } from "firebase/firestore";
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut
} from "firebase/auth";
import { auth, db, googleAuthProvider } from "./firebase";
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
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const hasClassParam = searchParams.has('class') || searchParams.has('courseId');
  const courseId = searchParams.get('class') || searchParams.get('courseId') || 'current';
  const isAdminPage = location.pathname === "/voice-admin";
  
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
  const [adminUsageLogs, setAdminUsageLogs] = useState([]);
  const [adminVoiceUsers, setAdminVoiceUsers] = useState([]);
  const [adminGrantEmail, setAdminGrantEmail] = useState("");
  const [limitMinutesPerDay, setLimitMinutesPerDay] = useState(120);

  // Refs
  const audioRef = useRef(new Audio());
  const lastPlayedHash = useRef(null);
  const lastNarratedAudioUrl = useRef(null);
  const liveConversationRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const voiceProxySocketRef = useRef(null);
  const voiceProxyAuthorizedRef = useRef(false);
  const voiceRecognitionStartedRef = useRef(false);
  const voicePlaybackCtxRef = useRef(null);
  const voicePlaybackNextRef = useRef(0);
  const voiceCaptureActiveRef = useRef(false);
  const voiceCommandPendingRef = useRef(false);
  const voiceLeaseRef = useRef(null);
  const voiceLeaseHeartbeatRef = useRef(null);
  const voiceLeaseExpiryTimeoutRef = useRef(null);
  const liveContextKeyRef = useRef("");
  const narrationCheckpointRef = useRef({ url: "", time: 0 });
  const pendingNarrationAfterVoiceRef = useRef(null);
  const activeAudioUrlRef = useRef(null);
  const voiceStateRef = useRef({
    slideList: [],
    viewingSlideId: null,
    livePptId: null,
    liveSlideId: null,
    isLiveMode: true,
    supportedLangs: [],
    listenLang: "en-US",
    liveData: null,
    slideData: null,
  });

  const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
  const VOICE_LEASE_ENDPOINT = `${API_BASE_URL}/api/voice-live-session`;
  const VOICE_PROXY_WS_URL = (import.meta.env.VITE_VOICE_LIVE_PROXY_WS_URL || "").trim();
  const GCP_PROJECT_ID = (import.meta.env.VITE_GCP_PROJECT_ID || "").trim();
  const LIVE_MODEL = "gemini-live-2.5-flash-native-audio";
  const LIVE_MODEL_LOCATION = (import.meta.env.VITE_VOICE_LIVE_MODEL_LOCATION || "us-central1").trim();
  const VOICE_NAME = (import.meta.env.VITE_VOICE_NAME || "Aoede").trim();
  const ENABLE_GROUNDING = true;

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
  const parseBooleanArg = (value) => {
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return value !== 0;
    if (typeof value === "string") {
      const normalized = value.trim().toLowerCase();
      if (["true", "1", "yes", "on", "enable", "enabled"].includes(normalized)) return true;
      if (["false", "0", "no", "off", "disable", "disabled"].includes(normalized)) return false;
    }
    return null;
  };
  const normalizeVoiceLanguageCode = (value) => {
    const raw = String(value || "").trim();
    if (!raw) return null;
    const normalized = raw.toLowerCase();
    const aliases = {
      "en": "en-US",
      "en-us": "en-US",
      "english": "en-US",
      "zh": "zh-CN",
      "zh-cn": "zh-CN",
      "mandarin": "zh-CN",
      "chinese": "zh-CN",
      "simplified chinese": "zh-CN",
      "yue": "yue-HK",
      "yue-hk": "yue-HK",
      "cantonese": "yue-HK",
      "traditional chinese": "yue-HK",
    };
    const candidate = aliases[normalized] || raw;
    const available = supportedLangs.length > 0 ? supportedLangs : Object.keys(AUDIO_LANGUAGE_NAMES);
    if (available.includes(candidate)) return candidate;
    const matched = available.find((code) => code.toLowerCase() === String(candidate).toLowerCase());
    return matched || null;
  };
  const getUserLabel = (user) => {
    if (!user) return "Guest";
    const displayName = (user.displayName || "").trim();
    if (displayName) return displayName;
    const email = (user.email || "").trim();
    if (email.includes("@")) return email.split("@")[0];
    return user.uid || "User";
  };

  useEffect(() => {
    voiceStateRef.current = {
      slideList,
      viewingSlideId,
      livePptId,
      liveSlideId,
      isLiveMode,
      supportedLangs,
      listenLang,
      liveData,
      slideData,
    };
  }, [slideList, viewingSlideId, livePptId, liveSlideId, isLiveMode, supportedLangs, listenLang, liveData, slideData]);

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
      if (liveConversationRef.current || voiceLeaseRef.current) {
        await stopVoiceCapture();
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      await signOut(auth);
      setVoiceTranscript("");
      setVoiceAnswer("");
      setVoiceAccessGranted(false);
      pendingNarrationAfterVoiceRef.current = null;
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
      setAdminUsageLogs(Array.isArray(data.usage_logs) ? data.usage_logs : []);
      setAdminVoiceUsers(Array.isArray(data.voice_users) ? data.voice_users : []);
      if (data.limits) {
        setLimitMinutesPerDay(data.limits.minutes_per_day ?? data.limits.requests_per_day ?? 120);
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
          action: "update_limits",
          minutes_per_day: Number(limitMinutesPerDay),
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

  const grantVoiceUser = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const email = String(adminGrantEmail || "").trim().toLowerCase();
    if (!email) {
      setAdminStatus("Email is required");
      return;
    }
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
          action: "grant_voice_user",
          email,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Failed to grant voice user");
      }
      setAdminGrantEmail("");
      setAdminStatus(data.message || "Voice user granted");
      await loadAdminDashboard(currentUser);
    } catch (error) {
      console.error("Grant voice user failed:", error);
      setAdminStatus(error?.message || "Failed to grant voice user");
    } finally {
      setAdminLoading(false);
    }
  };

  const revokeVoiceUser = async (email) => {
    if (!currentUser || !API_BASE_URL) return;
    const normalizedEmail = String(email || "").trim().toLowerCase();
    if (!normalizedEmail) return;
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
          action: "revoke_voice_user",
          email: normalizedEmail,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Failed to revoke voice user");
      }
      setAdminStatus(data.message || "Voice user revoked");
      await loadAdminDashboard(currentUser);
    } catch (error) {
      console.error("Revoke voice user failed:", error);
      setAdminStatus(error?.message || "Failed to revoke voice user");
    } finally {
      setAdminLoading(false);
    }
  };

  const pickLanguageContent = (languagesMap, preferredLanguage) => {
    if (!languagesMap) return null;
    if (preferredLanguage && languagesMap[preferredLanguage]) return languagesMap[preferredLanguage];
    if (listenLang && languagesMap[listenLang]) return languagesMap[listenLang];
    if (viewLang && languagesMap[viewLang]) return languagesMap[viewLang];
    const fallbackCode = Object.keys(languagesMap)[0];
    return fallbackCode ? languagesMap[fallbackCode] : null;
  };

  const getCurrentSlideSnapshot = () => {
    const state = voiceStateRef.current;
    const presentationId = state.viewingPptId || viewingPptId || state.livePptId || livePptId;
    const slideId = state.viewingSlideId || viewingSlideId || state.liveSlideId || liveSlideId;
    if (!presentationId || !slideId) return null;
    const sourceLanguages = (state.slideData?.languages || state.liveData || {});
    const langEntry = pickLanguageContent(sourceLanguages, state.listenLang || listenLang);
    const slideText = (langEntry?.text || "").trim();
    const imageUrl = langEntry?.image_url || "";
    return {
      courseId,
      presentationId: String(presentationId),
      slideId: String(slideId),
      isLiveMode: Boolean(state.isLiveMode),
      displayLanguage: viewLang,
      audioLanguage: state.listenLang || listenLang,
      slideText,
      imageUrl,
      supportedLanguages: state.supportedLangs || [],
      narrationPlaying: Boolean(!audioRef.current.paused && !audioRef.current.ended),
      narrationTime: Number.isFinite(audioRef.current.currentTime) ? audioRef.current.currentTime : 0,
    };
  };

  const buildVoiceTurnPayload = (userText) => {
    const snapshot = getCurrentSlideSnapshot();
    if (!snapshot || !snapshot.slideText) {
      return null;
    }
    return [
      "Classroom context:",
      `course_id=${snapshot.courseId}`,
      `presentation_id=${snapshot.presentationId}`,
      `slide_id=${snapshot.slideId}`,
      `live_sync=${snapshot.isLiveMode ? "on" : "off"}`,
      `display_language=${snapshot.displayLanguage}`,
      `audio_language=${snapshot.audioLanguage}`,
      `slide_text=${snapshot.slideText}`,
      "",
      `User request: ${userText}`,
    ].join("\n");
  };

  const isNarrationBlockedByVoice = () => false;

  const resolveAudioUrlFromVoiceState = () => {
    const state = voiceStateRef.current;
    const pickLang = (languagesMap, langCode) => {
      if (!languagesMap) return null;
      let content = languagesMap[langCode];
      if (!content) {
        const match = Object.keys(languagesMap).find((k) => k.startsWith(langCode) || langCode.startsWith(k));
        if (match) content = languagesMap[match];
      }
      return content;
    };
    const liveAudio = pickLang(state.liveData, state.listenLang);
    const viewingAudio = pickLang(state.slideData?.languages, state.listenLang);
    const activeContent = state.isLiveMode ? liveAudio : viewingAudio;
    return activeContent?.audio_url || null;
  };

  const snapshotNarrationForVoice = () => {
    const currentUrl = audioRef.current.src || resolveAudioUrlFromVoiceState() || "";
    narrationCheckpointRef.current = {
      url: currentUrl,
      time: Number.isFinite(audioRef.current.currentTime) ? audioRef.current.currentTime : 0,
    };
    audioRef.current.pause();
    setIsPlaying(false);
    setNarrationStatus("Paused for voice chat");
  };

  const clearVoiceLeaseTimers = () => {
    if (voiceLeaseHeartbeatRef.current) {
      clearInterval(voiceLeaseHeartbeatRef.current);
      voiceLeaseHeartbeatRef.current = null;
    }
    if (voiceLeaseExpiryTimeoutRef.current) {
      clearTimeout(voiceLeaseExpiryTimeoutRef.current);
      voiceLeaseExpiryTimeoutRef.current = null;
    }
  };

  const callVoiceLeaseApi = async (user, payload) => {
    if (!user) {
      throw new Error("Sign in to use voice chat");
    }
    if (!VOICE_LEASE_ENDPOINT || !API_BASE_URL) {
      throw new Error("Voice session service unavailable");
    }

    const idToken = await user.getIdToken();
    const response = await fetch(VOICE_LEASE_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${idToken}`,
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || "Voice session request failed");
    }
    return data;
  };

  const armVoiceLeaseExpiryTimeout = (lease) => {
    if (!lease?.expires_at) return;
    const expiresAt = Date.parse(lease.expires_at);
    if (!Number.isFinite(expiresAt)) return;
    const delayMs = Math.max(0, expiresAt - Date.now());
    voiceLeaseExpiryTimeoutRef.current = setTimeout(() => {
      setVoiceStatus("Voice session expired");
      stopVoiceCapture().catch((error) => {
        console.error("Failed to stop expired voice session:", error);
      });
    }, delayMs);
  };

  const closeVoiceLease = async ({ reason = "client_close" } = {}) => {
    const lease = voiceLeaseRef.current;
    clearVoiceLeaseTimers();
    voiceLeaseRef.current = null;
    if (!lease?.session_id || !currentUser) return;
    try {
      await callVoiceLeaseApi(currentUser, {
        action: "close",
        session_id: lease.session_id,
        reason,
      });
    } catch (error) {
      console.error("Failed to close voice lease:", error);
    }
  };

  const startVoiceLease = async ({ user, courseIdValue, presentationIdValue, slideIdValue }) => {
    const lease = await callVoiceLeaseApi(user, {
      action: "open",
      course_id: courseIdValue,
      presentation_id: presentationIdValue,
      slide_id: String(slideIdValue),
    });
    voiceLeaseRef.current = lease;
    clearVoiceLeaseTimers();
    armVoiceLeaseExpiryTimeout(lease);

    const heartbeatSeconds = Math.max(10, Number(lease.heartbeat_interval_seconds) || 30);
    voiceLeaseHeartbeatRef.current = setInterval(async () => {
      if (!voiceCaptureActiveRef.current || !voiceLeaseRef.current?.session_id || !currentUser) return;
      try {
        const heartbeat = await callVoiceLeaseApi(currentUser, {
          action: "heartbeat",
          session_id: voiceLeaseRef.current.session_id,
          course_id: courseId,
          presentation_id: viewingPptId || livePptId,
          slide_id: String(viewingSlideId || liveSlideId || ""),
        });
        voiceLeaseRef.current = { ...voiceLeaseRef.current, ...heartbeat };
        if (heartbeat.expires_at) {
          if (voiceLeaseExpiryTimeoutRef.current) {
            clearTimeout(voiceLeaseExpiryTimeoutRef.current);
            voiceLeaseExpiryTimeoutRef.current = null;
          }
          armVoiceLeaseExpiryTimeout({ expires_at: heartbeat.expires_at });
        }
      } catch (error) {
        setVoiceStatus(error?.message || "Voice session authorization expired");
        stopVoiceCapture().catch((stopError) => {
          console.error("Failed to stop voice after heartbeat rejection:", stopError);
        });
      }
    }, heartbeatSeconds * 1000);
  };

  const getSpeechRecognitionCtor = () => {
    if (typeof window === "undefined") return null;
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  };

  const buildVoiceToolDeclarations = () => ([
    {
      name: "get_current_state",
      description: "Get current classroom/player state including active presentation and slide.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "get_slide_content",
      description: "Get slide content for a specific or current slide.",
      parameters: {
        type: "object",
        properties: {
          presentation_id: { type: "string" },
          slide_id: { type: "string" },
          language: { type: "string" },
        },
      },
    },
    {
      name: "search_slides",
      description: "Search slide text in the current presentation.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string" },
          presentation_id: { type: "string" },
          language: { type: "string" },
          limit: { type: "number" },
        },
        required: ["query"],
      },
    },
    {
      name: "navigate_slide",
      description: "Move to the next or previous slide.",
      parameters: {
        type: "object",
        properties: {
          direction: {
            type: "string",
            enum: ["next", "previous"],
            description: "Slide navigation direction.",
          },
        },
        required: ["direction"],
      },
    },
    {
      name: "go_to_slide",
      description: "Jump directly to a specific slide/page number.",
      parameters: {
        type: "object",
        properties: {
          slide_number: {
            type: "number",
            description: "Target slide/page number (for example 5).",
          },
          page_number: {
            type: "number",
            description: "Alias of slide_number.",
          },
        },
      },
    },
    {
      name: "set_live_sync",
      description: "Enable or disable live sync mode.",
      parameters: {
        type: "object",
        properties: {
          enabled: {
            type: "boolean",
            description: "True to sync with live presenter slide.",
          },
        },
        required: ["enabled"],
      },
    },
    {
      name: "set_audio_language",
      description: "Set narration audio language. Supported: en-US, zh-CN, yue-HK.",
      parameters: {
        type: "object",
        properties: {
          language: {
            type: "string",
            description: "Target audio language code or name.",
          },
        },
        required: ["language"],
      },
    },
    {
      name: "set_display_language",
      description: "Set displayed subtitle language. Supported: en-US, zh-CN, yue-HK.",
      parameters: {
        type: "object",
        properties: {
          language: {
            type: "string",
            description: "Target display language code or name.",
          },
        },
        required: ["language"],
      },
    },
    {
      name: "narration_control",
      description: "Control narration playback.",
      parameters: {
        type: "object",
        properties: {
          action: {
            type: "string",
            enum: ["play", "pause", "restart", "stop", "resume"],
            description: "Narration control action.",
          },
        },
        required: ["action"],
      },
    },
    {
      name: "help_commands",
      description: "Get a short spoken list of available voice commands.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "cycle_language",
      description: "Cycle audio or display language to next/previous option.",
      parameters: {
        type: "object",
        properties: {
          target: { type: "string", enum: ["audio", "display"] },
          direction: { type: "string", enum: ["next", "previous"] },
        },
        required: ["target", "direction"],
      },
    },
    {
      name: "seek_narration",
      description: "Seek narration by seconds. Positive moves forward, negative moves backward.",
      parameters: {
        type: "object",
        properties: {
          seconds: { type: "number" },
        },
        required: ["seconds"],
      },
    },
    {
      name: "jump_narration_start",
      description: "Jump narration playback to the beginning.",
      parameters: { type: "object", properties: {} },
    },
  ]);

  const playProxyPcmAudio = async (base64Data, mimeType = "audio/pcm") => {
    if (!base64Data || !mimeType.includes("audio/pcm")) return;
    const binary = atob(base64Data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i += 1) {
      float32[i] = int16[i] / 32768;
    }

    if (!voicePlaybackCtxRef.current) {
      voicePlaybackCtxRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      voicePlaybackNextRef.current = voicePlaybackCtxRef.current.currentTime;
    }
    const ctx = voicePlaybackCtxRef.current;
    if (ctx.state === "suspended") {
      await ctx.resume();
    }
    const buffer = ctx.createBuffer(1, float32.length, 24000);
    buffer.copyToChannel(float32, 0);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    const when = Math.max(ctx.currentTime, voicePlaybackNextRef.current || 0);
    source.start(when);
    voicePlaybackNextRef.current = when + buffer.duration;
  };

  const sendVoiceTextTurn = (socket, text) => {
    if (!socket || socket.readyState !== WebSocket.OPEN || !text) return true;
    const enrichedText = buildVoiceTurnPayload(text);
    if (!enrichedText) {
      return false;
    }
    socket.send(JSON.stringify({
      client_content: {
        turns: [{ role: "user", parts: [{ text: enrichedText }] }],
        turn_complete: true,
      },
    }));
    return true;
  };

  const handleVoiceProxyMessage = async (event) => {
    let payload;
    try {
      let raw = event?.data;
      if (raw instanceof Blob) {
        raw = await raw.text();
      } else if (raw instanceof ArrayBuffer) {
        raw = new TextDecoder().decode(raw);
      } else if (ArrayBuffer.isView(raw)) {
        raw = new TextDecoder().decode(raw);
      }
      if (typeof raw !== "string") {
        return;
      }
      payload = JSON.parse(raw);
    } catch (error) {
      console.error("Invalid proxy message:", error);
      return;
    }

    if (payload.type === "proxy_ready") {
      voiceProxyAuthorizedRef.current = true;
      const setupTools = ENABLE_GROUNDING
        ? {
          function_declarations: buildVoiceToolDeclarations(),
          google_search: {},
        }
        : { function_declarations: buildVoiceToolDeclarations() };
      const setupMessage = {
        setup: {
          model: `projects/${GCP_PROJECT_ID}/locations/${LIVE_MODEL_LOCATION}/publishers/google/models/${LIVE_MODEL}`,
          generation_config: {
            response_modalities: ["AUDIO"],
            speech_config: {
              voice_config: {
                prebuilt_voice_config: {
                  voice_name: VOICE_NAME,
                },
              },
            },
          },
          system_instruction: {
            parts: [{
              text: `You are an accessibility-first classroom voice assistant for visually impaired students.
Use ${listenLang || "en-US"} for spoken responses.
Use tool calls whenever you need current app state or slide data.
Never invent slide content. If context is missing, call get_current_state or get_slide_content first.
When user intent matches an available function, call the function instead of describing steps.
Narration and voice are allowed to run at the same time.
For each actionable user command, issue exactly one function call whenever possible.
Do not bundle multiple function calls in one response unless absolutely required.
Keep replies short and explicit about the action completed.`,
            }],
          },
          tools: setupTools,
          input_audio_transcription: {},
          output_audio_transcription: {},
        },
      };
      voiceProxySocketRef.current?.send(JSON.stringify(setupMessage));
      setVoiceStatus("Proxy authorized. Initializing Gemini...");
      return;
    }

    if (payload.setupComplete || payload.setup_complete) {
      setVoiceStatus("Gemini Live connected");
      const recognition = speechRecognitionRef.current;
      if (recognition && !voiceRecognitionStartedRef.current) {
        try {
          recognition.start();
          voiceRecognitionStartedRef.current = true;
          setVoiceStatus("Listening...");
        } catch (error) {
          setVoiceStatus(error?.message || "Failed to start microphone capture");
          stopVoiceCapture().catch((stopError) => {
            console.error("Failed to stop voice after recognition start error:", stopError);
          });
        }
      }
      return;
    }

    if (payload?.error?.message) {
      setVoiceStatus(`Gemini error: ${payload.error.message}`);
      return;
    }

    const inputTranscript =
      payload?.serverContent?.inputTranscription?.text
      || payload?.server_content?.input_transcription?.text;
    if (inputTranscript) {
      setVoiceTranscript(inputTranscript);
    }
    const outputTranscript =
      payload?.serverContent?.outputTranscription?.text
      || payload?.server_content?.output_transcription?.text;
    if (outputTranscript) {
      setVoiceAnswer(outputTranscript);
    }

    const toolCalls =
      payload?.toolCall?.functionCalls
      || payload?.tool_call?.function_calls;
    if (Array.isArray(toolCalls) && toolCalls.length > 0) {
      for (const call of toolCalls) {
        const result = await executeVoiceCommand(call);
        if (voiceProxySocketRef.current?.readyState === WebSocket.OPEN) {
          voiceProxySocketRef.current.send(JSON.stringify({
            tool_response: {
              function_responses: [
                {
                  id: call.id,
                  name: call.name,
                  response: result,
                },
              ],
            },
          }));
        }
      }
      return;
    }

    const parts =
      payload?.serverContent?.modelTurn?.parts
      || payload?.server_content?.model_turn?.parts;
    if (Array.isArray(parts)) {
      for (const part of parts) {
        if (part?.text) {
          setVoiceAnswer(part.text);
        }
        const inlineData = part?.inlineData || part?.inline_data;
        if (inlineData?.data) {
          await playProxyPcmAudio(inlineData.data, inlineData.mimeType || inlineData.mime_type || "");
        }
      }
    }
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

    const SpeechRecognitionCtor = getSpeechRecognitionCtor();
    if (!SpeechRecognitionCtor) {
      setVoiceStatus("Browser speech recognition is not supported on this device");
      return;
    }
    if (!VOICE_PROXY_WS_URL) {
      setVoiceStatus("Voice proxy is not configured");
      return;
    }
    if (!GCP_PROJECT_ID) {
      setVoiceStatus("Voice proxy project config is missing");
      return;
    }

    setVoiceBusy(true);
    setVoiceTranscript("");
    setVoiceAnswer("");
    setAutoplay(true);
    setVoiceStatus("Authorizing voice session...");
    try {
      await startVoiceLease({
        user: currentUser,
        courseIdValue: courseId,
        presentationIdValue: presentationId,
        slideIdValue: slideId,
      });
      const leaseSessionId = voiceLeaseRef.current?.session_id;
      if (!leaseSessionId) {
        throw new Error("Voice lease session was not issued");
      }

      const ws = new WebSocket(VOICE_PROXY_WS_URL);
      voiceProxySocketRef.current = ws;
      voiceProxyAuthorizedRef.current = false;
      voiceRecognitionStartedRef.current = false;

      const recognition = new SpeechRecognitionCtor();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = listenLang || "en-US";
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i];
          if (!result?.isFinal) continue;
          const transcript = (result[0]?.transcript || "").trim();
          if (!transcript) continue;
          setVoiceTranscript(transcript);
          const sent = sendVoiceTextTurn(ws, transcript);
          if (!sent) {
            setVoiceStatus("Slide context unavailable for voice answer");
            stopVoiceCapture().catch((stopError) => {
              console.error("Failed to stop voice after missing context:", stopError);
            });
            return;
          }
        }
      };

      recognition.onerror = (event) => {
        const code = String(event?.error || "unknown");
        if (code === "not-allowed" || code === "service-not-allowed") {
          setVoiceStatus("Microphone permission denied");
        } else if (code !== "aborted") {
          setVoiceStatus(`Voice recognition error: ${code}`);
        }
      };

      recognition.onend = () => {
        voiceRecognitionStartedRef.current = false;
        if (!voiceCaptureActiveRef.current) return;
        try {
          recognition.start();
          voiceRecognitionStartedRef.current = true;
        } catch (_error) {
          // no-op: browser is still stopping/starting recognition
        }
      };

      ws.onopen = async () => {
        try {
          const idToken = await currentUser.getIdToken();
          ws.send(JSON.stringify({
            type: "auth",
            id_token: idToken,
            lease_session_id: leaseSessionId,
          }));
          setVoiceStatus("Authorizing proxy...");
        } catch (error) {
          setVoiceStatus(error?.message || "Proxy authentication failed");
          stopVoiceCapture().catch((stopError) => {
            console.error("Failed to stop voice after auth error:", stopError);
          });
        }
      };
      ws.onmessage = (event) => {
        handleVoiceProxyMessage(event).catch((error) => {
          console.error("Voice proxy message handling failed:", error);
        });
      };
      ws.onerror = () => {
        setVoiceStatus("Voice proxy connection error");
      };
      ws.onclose = () => {
        if (voiceCaptureActiveRef.current) {
          const authorized = voiceProxyAuthorizedRef.current;
          setVoiceStatus(authorized ? "Voice proxy disconnected" : "Voice chat access requires admin grant");
          stopVoiceCapture().catch((stopError) => {
            console.error("Failed to stop voice after proxy disconnect:", stopError);
          });
        }
      };

      speechRecognitionRef.current = recognition;
      voiceCaptureActiveRef.current = true;
      setIsListening(true);
      setVoiceStatus("Connecting voice proxy...");
    } catch (error) {
      console.error("Voice session start failed:", error);
      voiceCaptureActiveRef.current = false;
      speechRecognitionRef.current = null;
      if (voiceProxySocketRef.current) {
        try {
          voiceProxySocketRef.current.close();
        } catch (_error) {
          // no-op
        }
        voiceProxySocketRef.current = null;
      }
      await closeVoiceLease({ reason: "connect_failed" });
      setVoiceStatus(error?.message || "Failed to start voice session");
    } finally {
      setVoiceBusy(false);
    }
  };

  const stopVoiceCapture = async () => {
    setVoiceBusy(true);
    try {
      voiceCaptureActiveRef.current = false;
      voiceCommandPendingRef.current = false;
      voiceProxyAuthorizedRef.current = false;
      voiceRecognitionStartedRef.current = false;
      const recognition = speechRecognitionRef.current;
      speechRecognitionRef.current = null;
      if (recognition) {
        try {
          recognition.onend = null;
          recognition.stop();
        } catch (error) {
          console.warn("Voice recognition stop warning:", error);
        }
      }
      if (voiceProxySocketRef.current) {
        try {
          voiceProxySocketRef.current.close(1000, "client_stop");
        } catch (_error) {
          // no-op
        }
        voiceProxySocketRef.current = null;
      }
      if (voicePlaybackCtxRef.current) {
        try {
          await voicePlaybackCtxRef.current.close();
        } catch (_error) {
          // no-op
        }
        voicePlaybackCtxRef.current = null;
        voicePlaybackNextRef.current = 0;
      }
      setIsListening(false);
      setVoiceStatus("Voice assistant stopped");
      playNarrationAfterVoiceStop();
    } catch (error) {
      console.error("Failed to stop voice assistant:", error);
      setVoiceStatus(error?.message || "Failed to stop voice assistant");
    } finally {
      await closeVoiceLease({ reason: "client_stop" });
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

  const playAudioUrlNow = async ({ audioUrl, restart = false, startTime = null } = {}) => {
    if (!audioUrl) {
      setNarrationStatus("Narration audio unavailable");
      return { ok: false, message: "Narration audio unavailable." };
    }
    if (audioRef.current.src !== audioUrl) {
      audioRef.current.src = audioUrl;
    }
    if (restart) {
      audioRef.current.currentTime = 0;
      setAudioCurrentTime(0);
    } else if (Number.isFinite(startTime) && startTime >= 0) {
      audioRef.current.currentTime = startTime;
      setAudioCurrentTime(startTime);
    }
    setNarrationStatus("Playing MP3 narration");
    try {
      await audioRef.current.play();
      setIsPlaying(true);
      setNarrationStatus("Narrating");
      return { ok: true, message: "Narration started." };
    } catch (error) {
      console.error("Narration playback blocked:", error);
      setIsPlaying(false);
      setNarrationStatus("Narration playback blocked");
      return { ok: false, message: "Narration playback blocked." };
    }
  };

  const stopNarration = () => {
    audioRef.current.pause();
    audioRef.current.currentTime = 0;
    setAudioCurrentTime(0);
    setNarrationStatus("Stopped");
  };

  const playNarrationAfterVoiceStop = () => {
    const pending = pendingNarrationAfterVoiceRef.current;
    pendingNarrationAfterVoiceRef.current = null;
    if (!pending?.mode) return;

    const checkpoint = narrationCheckpointRef.current;
    const targetUrl = pending.url || resolveAudioUrlFromVoiceState() || activeAudioUrlRef.current || checkpoint.url;
    if (!targetUrl) {
      setNarrationStatus("Narration audio unavailable");
      return;
    }

    if (audioRef.current.src !== targetUrl) {
      audioRef.current.src = targetUrl;
    }

    if (pending.mode === "restart") {
      audioRef.current.currentTime = 0;
      setAudioCurrentTime(0);
    } else {
      const resumeTime = Number.isFinite(checkpoint.time) ? Math.max(0, checkpoint.time) : 0;
      audioRef.current.currentTime = (checkpoint.url && checkpoint.url === targetUrl) ? resumeTime : 0;
      setAudioCurrentTime(audioRef.current.currentTime);
    }

    audioRef.current.play()
      .then(() => {
        setIsPlaying(true);
        setNarrationStatus("Narrating");
      })
      .catch((error) => {
        console.error("Narration handoff playback blocked:", error);
        setNarrationStatus("Narration playback blocked");
      });
  };

  useEffect(() => {
    return () => {
      clearVoiceLeaseTimers();
      voiceCaptureActiveRef.current = false;
      voiceCommandPendingRef.current = false;
      if (speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.onend = null;
          speechRecognitionRef.current.stop();
        } catch (error) {
          console.warn("Failed to stop speech recognition on unmount:", error);
        }
        speechRecognitionRef.current = null;
      }
      if (voiceProxySocketRef.current) {
        try {
          voiceProxySocketRef.current.close(1000, "component_unmount");
        } catch (error) {
          console.warn("Failed to close proxy socket on unmount:", error);
        }
        voiceProxySocketRef.current = null;
      }
      if (voicePlaybackCtxRef.current) {
        voicePlaybackCtxRef.current.close().catch(() => {});
        voicePlaybackCtxRef.current = null;
        voicePlaybackNextRef.current = 0;
      }
      if (voiceLeaseRef.current) {
        closeVoiceLease({ reason: "component_unmount" }).catch((error) => {
          console.error("Failed to close voice lease on unmount:", error);
        });
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const narrateCurrentSlide = () => {
    const narrationBlockedByVoice = isNarrationBlockedByVoice();
    if (narrationBlockedByVoice) {
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
  useEffect(() => {
    activeAudioUrlRef.current = activeAudioUrl;
  }, [activeAudioUrl]);

  // --- 5. Audio Player Logic ---
  useEffect(() => {
      const narrationBlockedByVoice = isNarrationBlockedByVoice();
      const shouldFollowSlideAudio = Boolean(audioRef.current.src) || isPlaying || autoplay;
      if (!activeAudioUrl || !shouldFollowSlideAudio || narrationBlockedByVoice) return;

      if (lastPlayedHash.current !== activeAudioUrl) {
          lastPlayedHash.current = activeAudioUrl;
          startAudioPlayback(activeAudioUrl, { restart: false });
      }
  }, [activeAudioUrl, autoplay, isListening, voiceBusy, isPlaying]);

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
      const narrationBlockedByVoice = isNarrationBlockedByVoice();
      if (narrationBlockedByVoice) {
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

  const executeVoiceCommand = async (functionCall) => {
    const name = functionCall?.name;
    const args = (() => {
      if (functionCall?.args && typeof functionCall.args === "object") return functionCall.args;
      if (functionCall?.arguments && typeof functionCall.arguments === "object") return functionCall.arguments;
      if (typeof functionCall?.args === "string") {
        try {
          const parsed = JSON.parse(functionCall.args);
          return parsed && typeof parsed === "object" ? parsed : {};
        } catch (_error) {
          return {};
        }
      }
      if (typeof functionCall?.arguments === "string") {
        try {
          const parsed = JSON.parse(functionCall.arguments);
          return parsed && typeof parsed === "object" ? parsed : {};
        } catch (_error) {
          return {};
        }
      }
      return {};
    })();
    try {
      if (name === "get_current_state") {
        const snapshot = getCurrentSlideSnapshot();
        if (!snapshot) {
          return { ok: false, message: "No active slide context available." };
        }
        return {
          ok: true,
          message: `On slide ${snapshot.slideId} of ${snapshot.presentationId}.`,
          data: snapshot,
        };
      }

      if (name === "get_slide_content") {
        const state = voiceStateRef.current;
        const targetPresentationId = String(args.presentation_id || state.viewingPptId || state.livePptId || "");
        const targetSlideId = String(args.slide_id || state.viewingSlideId || state.liveSlideId || "");
        const targetLanguage = String(args.language || state.listenLang || listenLang || "").trim();
        if (!targetPresentationId || !targetSlideId) {
          return { ok: false, message: "Missing presentation or slide id." };
        }
        const slideRef = doc(
          db,
          "presentation_broadcast",
          courseId,
          "presentations",
          targetPresentationId,
          "slides",
          targetSlideId,
        );
        const snap = await getDoc(slideRef);
        if (!snap.exists()) {
          return { ok: false, message: "Slide not found." };
        }
        const slideDoc = snap.data() || {};
        const languages = slideDoc.languages || {};
        const langEntry = pickLanguageContent(languages, targetLanguage);
        const slideText = (langEntry?.text || "").trim();
        if (!slideText) {
          return { ok: false, message: "Slide text is unavailable for requested language." };
        }
        return {
          ok: true,
          message: `Fetched content for slide ${targetSlideId}.`,
          data: {
            course_id: courseId,
            presentation_id: targetPresentationId,
            slide_id: targetSlideId,
            language: targetLanguage || null,
            text: slideText,
            image_url: langEntry?.image_url || null,
          },
        };
      }

      if (name === "search_slides") {
        const query = String(args.query || "").trim();
        if (!query) {
          return { ok: false, message: "Query is required." };
        }
        const state = voiceStateRef.current;
        const targetPresentationId = String(args.presentation_id || state.viewingPptId || state.livePptId || "");
        if (!targetPresentationId) {
          return { ok: false, message: "Presentation id is required." };
        }
        const targetLanguage = String(args.language || state.listenLang || listenLang || "").trim();
        const maxResults = Math.min(10, Math.max(1, Number(args.limit) || 3));
        const slidesRef = collection(
          db,
          "presentation_broadcast",
          courseId,
          "presentations",
          targetPresentationId,
          "slides",
        );
        const snapshot = await getDocs(slidesRef);
        const lowered = query.toLowerCase();
        const matches = [];
        for (const slide of snapshot.docs) {
          const data = slide.data() || {};
          const langEntry = pickLanguageContent(data.languages || {}, targetLanguage);
          const text = (langEntry?.text || "").trim();
          if (!text) continue;
          if (!text.toLowerCase().includes(lowered)) continue;
          matches.push({
            slide_id: slide.id,
            snippet: text.slice(0, 220),
          });
          if (matches.length >= maxResults) break;
        }
        if (matches.length === 0) {
          return { ok: true, message: "No matching slides found.", data: { matches: [] } };
        }
        return {
          ok: true,
          message: `Found ${matches.length} matching slide(s).`,
          data: { query, matches },
        };
      }

      if (name === "navigate_slide") {
        const { slideList: latestSlideList, viewingSlideId: latestViewingSlideId } = voiceStateRef.current;
        const currentNum = parseInt(latestViewingSlideId, 10);
        if (!Number.isFinite(currentNum) || latestSlideList.length === 0) {
          return { ok: false, message: "No active slide to navigate." };
        }
        const direction = String(args.direction || "").toLowerCase();
        const idx = latestSlideList.indexOf(currentNum);
        if (idx === -1) {
          return { ok: false, message: "Current slide is outside slide list." };
        }
        if (direction === "next") {
          if (idx >= latestSlideList.length - 1) {
            return { ok: false, message: "Already at the last slide." };
          }
          setViewingSlideId(String(latestSlideList[idx + 1]));
          setIsLiveMode(false);
          return { ok: true, message: "Moved to next slide." };
        }
        if (direction === "previous") {
          if (idx <= 0) {
            return { ok: false, message: "Already at the first slide." };
          }
          setViewingSlideId(String(latestSlideList[idx - 1]));
          setIsLiveMode(false);
          return { ok: true, message: "Moved to previous slide." };
        }
        const directTarget = Number(args.slide_number ?? args.page_number);
        if (Number.isFinite(directTarget)) {
          const target = Math.trunc(directTarget);
          if (!latestSlideList.includes(target)) {
            return { ok: false, message: `Slide ${target} is not available.` };
          }
          setViewingSlideId(String(target));
          setIsLiveMode(false);
          return { ok: true, message: `Moved to slide ${target}.` };
        }
        return { ok: false, message: "Direction must be next or previous." };
      }

      if (name === "go_to_slide") {
        const { slideList: latestSlideList } = voiceStateRef.current;
        const directTarget = Number(args.slide_number ?? args.page_number ?? args.slide ?? args.page);
        if (!Number.isFinite(directTarget)) {
          return { ok: false, message: "slide_number is required." };
        }
        const target = Math.trunc(directTarget);
        if (!latestSlideList.includes(target)) {
          return { ok: false, message: `Slide ${target} is not available.` };
        }
        setViewingSlideId(String(target));
        setIsLiveMode(false);
        return { ok: true, message: `Moved to slide ${target}.` };
      }

      if (name === "set_live_sync") {
        const enabled = parseBooleanArg(args.enabled);
        if (enabled === null) {
          return { ok: false, message: "Enabled must be true or false." };
        }
        const { isLiveMode: latestIsLiveMode, livePptId: latestLivePptId, liveSlideId: latestLiveSlideId } = voiceStateRef.current;
        if (enabled && !latestIsLiveMode) {
          setViewingPptId(latestLivePptId);
          setViewingSlideId(latestLiveSlideId);
          setIsLiveMode(true);
        }
        if (!enabled && latestIsLiveMode) {
          setIsLiveMode(false);
        }
        return { ok: true, message: enabled ? "Live sync enabled." : "Live sync disabled." };
      }

      if (name === "set_audio_language") {
        const code = normalizeVoiceLanguageCode(args.language);
        const { supportedLangs: latestSupportedLangs } = voiceStateRef.current;
        if (latestSupportedLangs.length > 0 && !latestSupportedLangs.includes(code)) {
          return { ok: false, message: "Requested audio language is not available on current slide." };
        }
        if (!code) {
          return { ok: false, message: "Unsupported audio language." };
        }
        voiceStateRef.current.listenLang = code;
        setListenLang(code);
        return { ok: true, message: `Audio language set to ${getAudioLangName(code)}.` };
      }

      if (name === "set_display_language") {
        const code = normalizeVoiceLanguageCode(args.language);
        const { supportedLangs: latestSupportedLangs } = voiceStateRef.current;
        if (latestSupportedLangs.length > 0 && !latestSupportedLangs.includes(code)) {
          return { ok: false, message: "Requested display language is not available on current slide." };
        }
        if (!code) {
          return { ok: false, message: "Unsupported display language." };
        }
        setViewLang(code);
        return { ok: true, message: `Display language set to ${getTextLangName(code)}.` };
      }

      if (name === "narration_control") {
        const rawAction = String(args.action || "").toLowerCase().trim();
        const action = rawAction.includes("restart")
          ? "restart"
          : (rawAction.includes("resume") || rawAction.includes("play"))
            ? "resume"
            : rawAction.includes("pause")
              ? "pause"
              : rawAction.includes("stop")
                ? "stop"
                : rawAction;
        if (action === "pause" || action === "stop") {
          audioRef.current.pause();
          setIsPlaying(false);
          setNarrationStatus(action === "stop" ? "Stopped" : "Paused");
          return { ok: true, message: action === "stop" ? "Narration stopped." : "Narration paused." };
        }
        if (action === "restart") {
          const url = resolveAudioUrlFromVoiceState();
          setAutoplay(true);
          return await playAudioUrlNow({ audioUrl: url, restart: true });
        }
        if (action === "play" || action === "resume") {
          const url = resolveAudioUrlFromVoiceState();
          const checkpoint = narrationCheckpointRef.current;
          const sameUrl = Boolean(checkpoint.url && checkpoint.url === url);
          const startTime = sameUrl ? checkpoint.time : null;
          setAutoplay(true);
          return await playAudioUrlNow({ audioUrl: url, restart: false, startTime });
        }
        return { ok: false, message: "Unknown narration action." };
      }

      if (name === "help_commands") {
        return {
          ok: true,
          message: "Try: next slide, previous slide, go to slide 5, enable live sync, disable live sync, set audio language to Cantonese, set display language to English, next audio language, previous display language, seek forward 10 seconds, seek back 30 seconds, jump narration to start, pause narration, or resume narration.",
        };
      }

      if (name === "cycle_language") {
        const target = String(args.target || "").toLowerCase();
        const direction = String(args.direction || "").toLowerCase();
        const step = direction === "previous" ? -1 : direction === "next" ? 1 : 0;
        if (!step) {
          return { ok: false, message: "Direction must be next or previous." };
        }
        if (target === "audio") {
          const nextCode = cycleLanguage(voiceStateRef.current.listenLang || listenLang, step);
          if (!nextCode) return { ok: false, message: "No audio language available." };
          setListenLang(nextCode);
          voiceStateRef.current.listenLang = nextCode;
          return { ok: true, message: `Audio language switched to ${getAudioLangName(nextCode)}.` };
        }
        if (target === "display") {
          const nextCode = cycleLanguage(viewLang, step);
          if (!nextCode) return { ok: false, message: "No display language available." };
          setViewLang(nextCode);
          return { ok: true, message: `Display language switched to ${getTextLangName(nextCode)}.` };
        }
        return { ok: false, message: "Target must be audio or display." };
      }

      if (name === "seek_narration") {
        const seconds = Number(args.seconds);
        if (!Number.isFinite(seconds) || seconds === 0) {
          return { ok: false, message: "Seconds must be a non-zero number." };
        }
        if (!audioRef.current.src) {
          return { ok: false, message: "Narration is not loaded yet." };
        }
        seekAudio(seconds);
        return { ok: true, message: `Narration moved ${seconds > 0 ? "forward" : "backward"} ${Math.abs(seconds)} seconds.` };
      }

      if (name === "jump_narration_start") {
        if (!audioRef.current.src) {
          return { ok: false, message: "Narration is not loaded yet." };
        }
        jumpToAudioStart();
        return { ok: true, message: "Narration moved to start." };
      }

      return { ok: false, message: `Unsupported command: ${name}` };
    } catch (error) {
      return { ok: false, message: error?.message || "Voice command failed." };
    }
  };

  useEffect(() => {
      const onKeyDown = (event) => {
          const target = event.target;
          const tagName = target?.tagName?.toLowerCase();
          if (tagName === "input" || tagName === "textarea" || tagName === "select" || target?.isContentEditable) {
              return;
          }

          const narrationBlockedByVoice = isNarrationBlockedByVoice();
          if (narrationBlockedByVoice) {
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

          const normalizedKey = (event.key || "").toLowerCase();
          if (normalizedKey === "m" && !event.altKey && !event.ctrlKey && !event.metaKey) {
              event.preventDefault();
              if (isListening || voiceBusy) {
                  stopVoiceCapture();
              } else {
                  startVoiceCapture();
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

  if (!isReady && !isAdminPage) {
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
  const backToSlidesHref = searchParams.toString() ? `/?${searchParams.toString()}` : "/";

  if (isAdminPage) {
    return (
      <div className="container" style={{ padding: "18px", overflow: "auto" }}>
        <header style={{ padding: 0, borderBottom: "none", marginBottom: "12px" }}>
          <h1>🎛️ Voice Chat Admin</h1>
          <div className="controls">
            <button
              type="button"
              className="account-action-btn"
              onClick={() => { window.location.href = backToSlidesHref; }}
            >
              Back to Slides
            </button>
            <button
              type="button"
              className="account-action-btn"
              onClick={currentUser ? handleSignOut : handleSignIn}
            >
              <UserIcon />
              <span>{currentUser ? "Sign out" : "Sign in"}</span>
            </button>
            {currentUser && adminEnabled && (
              <button
                type="button"
                className="account-action-btn"
                onClick={() => { window.location.href = "/voice-admin"; }}
              >
                Voice Admin
              </button>
            )}
          </div>
        </header>      
        <div className="identity-status" style={{ margin: "0 0 12px" }}>{authStatus}</div>
        {!currentUser && (
          <div style={{ color: "#4b5563" }}>Sign in with an admin account to manage voice-chat users and limits.</div>
        )}
        {currentUser && !adminEnabled && (
          <div style={{ color: "#b91c1c" }}>This account does not have voice admin access.</div>
        )}
        {currentUser && adminEnabled && (
          <div style={{ border: "1px solid #e5e7eb", borderRadius: "8px", padding: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <strong>Voice Chat Controls</strong>
              <button
                type="button"
                onClick={() => loadAdminDashboard()}
                disabled={adminLoading}
                style={{ borderRadius: "14px", border: "1px solid #ddd", padding: "4px 10px", background: "#fff" }}
              >
                Refresh
              </button>
            </div>
            {adminSummary && (
              <div style={{ fontSize: "0.9rem", marginBottom: "10px" }}>
                Tracked users: {adminSummary.tracked_users} · Today used: {adminSummary.total_today_minutes} minutes
              </div>
            )}
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap", marginBottom: "10px" }}>
              <label style={{ fontSize: "0.9rem" }}>
                Minutes per day
                <input
                  type="number"
                  min="1"
                  value={limitMinutesPerDay}
                  onChange={(e) => setLimitMinutesPerDay(e.target.value)}
                  style={{ marginLeft: "6px", width: "110px" }}
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
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap", marginBottom: "10px" }}>
              <label style={{ fontSize: "0.9rem" }}>
                Grant voice access (email)
                <input
                  type="email"
                  value={adminGrantEmail}
                  onChange={(e) => setAdminGrantEmail(e.target.value)}
                  placeholder="student@example.com"
                  style={{ marginLeft: "6px", width: "240px" }}
                />
              </label>
              <button
                type="button"
                onClick={grantVoiceUser}
                disabled={adminLoading}
                style={{ borderRadius: "14px", border: "1px solid #ddd", padding: "4px 10px", background: "#fff" }}
              >
                Grant user
              </button>
            </div>
            {adminStatus && <div style={{ fontSize: "0.9rem", color: "#4b5563", marginBottom: "8px" }}>{adminStatus}</div>}
            <div style={{ maxHeight: "220px", overflow: "auto", fontSize: "0.85rem", borderTop: "1px solid #f3f4f6", paddingTop: "8px", marginBottom: "8px" }}>
              <div style={{ fontWeight: 600, marginBottom: "4px" }}>Voice chat users</div>
              {adminVoiceUsers.length === 0 && (
                <div style={{ color: "#6b7280" }}>No voice users configured</div>
              )}
              {adminVoiceUsers.map((user) => (
                <div key={user.key} style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "3px 0", alignItems: "center" }}>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                    {user.value} {user.active ? "" : "(inactive)"}
                  </span>
                  {user.type === "email" && user.active && (
                    <button
                      type="button"
                      onClick={() => revokeVoiceUser(user.value)}
                      disabled={adminLoading}
                      style={{ borderRadius: "12px", border: "1px solid #ddd", padding: "2px 8px", background: "#fff" }}
                    >
                      Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
            <div style={{ maxHeight: "170px", overflow: "auto", fontSize: "0.85rem", borderTop: "1px solid #f3f4f6", paddingTop: "8px" }}>
              <div style={{ fontWeight: 600, marginBottom: "4px" }}>Top usage today</div>
              {adminTopUsage.slice(0, 20).map((row) => (
                <div key={row.uid} style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "2px 0" }}>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{row.email || row.uid}</span>
                  <span>{row.used_minutes} min</span>
                </div>
              ))}
            </div>
            <div style={{ maxHeight: "190px", overflow: "auto", fontSize: "0.85rem", borderTop: "1px solid #f3f4f6", paddingTop: "8px", marginTop: "8px" }}>
              <div style={{ fontWeight: 600, marginBottom: "4px" }}>Recent session logs</div>
              {adminUsageLogs.length === 0 && <div style={{ color: "#6b7280" }}>No usage logs yet</div>}
              {adminUsageLogs.slice(0, 30).map((log) => (
                <div key={log.id} style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "2px 0" }}>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{log.email || log.uid}</span>
                  <span>{Math.round((log.duration_seconds || 0) / 60)} min · {log.ended_reason || "ended"}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

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
            <div className="voice-assistant-actions">
              <button
                type="button"
                className={`voice-action-btn ${isListening || voiceBusy ? "active" : ""}`}
                onClick={isListening || voiceBusy ? stopVoiceCapture : startVoiceCapture}
              >
                <MicIcon />
                <span>{isListening || voiceBusy ? "Stop" : "Start"}</span>
              </button>
            </div>
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
            <span className="shortcut-hint">
              Voice: M start/stop
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