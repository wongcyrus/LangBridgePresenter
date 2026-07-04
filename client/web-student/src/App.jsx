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
  AdminIndexPage,
  ClassSelectionPage,
  TeacherWorkspacePage,
  VoiceAdminPage,
  VoiceAssistantCard,
} from "./components/AppPages";
import Live2DTutor from "./components/Live2DTutor";
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

const SignOutIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M10 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4a1 1 0 1 0 0-2H6V5h4a1 1 0 1 0 0-2zm6.59 4.59L15.17 9l2.58 2.59H9a1 1 0 1 0 0 2h8.75l-2.58 2.59 1.42 1.41L21.59 12z"/>
    </svg>
);

const HomeIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M12 3.2 2.8 10.9a1 1 0 1 0 1.3 1.5L5 11.6V20a2 2 0 0 0 2 2h3.5a1 1 0 0 0 1-1v-5h1v5a1 1 0 0 0 1 1H17a2 2 0 0 0 2-2v-8.4l.9.8a1 1 0 0 0 1.3-1.5L12 3.2z"/>
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
            
            <div className={`fullscreen-content ${!isSubtitleVisible ? "subtitle-hidden" : ""}`.trim()}>
                <div className="fullscreen-media" onClick={(e) => { e.stopPropagation(); onTogglePlay(); }}>
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
                </div>

                <div
                    className={`fullscreen-subtitle ${!isSubtitleVisible ? 'hidden' : ''}`}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="fullscreen-subtitle-toolbar">
                        <button
                            className="fs-play-btn"
                            onClick={(e) => { e.stopPropagation(); onTogglePlay(); }}
                        >
                            {isPlaying ? <PauseIcon /> : <PlayIcon />}
                        </button>
                        <button
                            className="toggle-subtitle-btn"
                            onClick={(e) => { e.stopPropagation(); setIsSubtitleVisible(!isSubtitleVisible); }}
                        >
                            {isSubtitleVisible ? <HideSubtitleIcon /> : <ShowSubtitleIcon />}
                        </button>
                    </div>
                    <div className="fullscreen-subtitle-text">
                        <p>{text}</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

// --- Main App Component ---
function App() {
  const DISPLAY_LANG_STORAGE_KEY = "student.displayLanguage";
  const SPEAK_LANG_STORAGE_KEY = "student.speakLanguage";
  const AUTOPLAY_STORAGE_KEY = "student.autoplay";
  const SLIDE_STATE_STORAGE_KEY = "student.slideState";
  const FONT_SIZE_STORAGE_KEY = "student.readerFontSize";
  const readLocalStorage = (key) => {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  };
  const loadStoredSlideState = () => {
    const raw = readLocalStorage(SLIDE_STATE_STORAGE_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return null;
      return parsed;
    } catch (_error) {
      return null;
    }
  };
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const hasClassParam = searchParams.has('class') || searchParams.has('courseId');
  const courseId = searchParams.get('class') || searchParams.get('courseId') || 'current';
  const isAdminIndexPage = location.pathname === "/admin";
  const isAdminPage = location.pathname === "/voice-admin";
  const isTeacherPage = location.pathname === "/teacher-courses";
  
  const [status, setStatus] = useState({ text: "🟡 Connecting...", color: "orange" });
  const [viewLang, setViewLang] = useState(() => readLocalStorage(DISPLAY_LANG_STORAGE_KEY) || "en");
  const [listenLang, setListenLang] = useState(() => readLocalStorage(SPEAK_LANG_STORAGE_KEY) || "en-US");
  const [supportedLangs, setSupportedLangs] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [authStatus, setAuthStatus] = useState("Guest");
  
  // -- State for Live/Nav Logic --
  const [livePptId, setLivePptId] = useState(null);
  const [liveSlideId, setLiveSlideId] = useState(null);
  const [broadcastStatus, setBroadcastStatus] = useState(null);
  
  const [viewingPptId, setViewingPptId] = useState(() => {
    const stored = loadStoredSlideState();
    if (!stored || stored.isLiveMode !== false) return null;
    const pptId = String(stored.pptId || "").trim();
    return pptId || null;
  });
  const [viewingSlideId, setViewingSlideId] = useState(() => {
    const stored = loadStoredSlideState();
    if (!stored || stored.isLiveMode !== false) return null;
    const slideId = String(stored.slideId || "").trim();
    return slideId || null;
  });
  const [isLiveMode, setIsLiveMode] = useState(() => {
    const stored = loadStoredSlideState();
    return typeof stored?.isLiveMode === "boolean" ? stored.isLiveMode : true;
  }); // Start in sync
  
  const [presentationList, setPresentationList] = useState([]); // List of presentation IDs
  const [slideList, setSlideList] = useState([]); // List of integers
  
  const [slideData, setSlideData] = useState(null); // Content of Viewing Slide
  const [liveData, setLiveData] = useState(null);   // Content of Live Broadcast (for audio)

  // Audio State
  const [isPlaying, setIsPlaying] = useState(false);
  const [autoplay, setAutoplay] = useState(() => {
    const raw = readLocalStorage(AUTOPLAY_STORAGE_KEY);
    if (raw === "true") return true;
    if (raw === "false") return false;
    return true;
  });
  const [isReady, setIsReady] = useState(false); 
  const [readerFontSize, setReaderFontSize] = useState(() => {
    const raw = readLocalStorage(FONT_SIZE_STORAGE_KEY);
    const parsed = Number.parseInt(raw || "18", 10);
    if (!Number.isFinite(parsed)) return 18;
    return Math.max(16, Math.min(26, parsed));
  });
  const [narrationStatus, setNarrationStatus] = useState("Idle");
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [isTutorVisible, setIsTutorVisible] = useState(true);
  
  // Full Screen State
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Sign in to use voice chat");
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [voiceAnswer, setVoiceAnswer] = useState("");
  const [voiceAccessGranted, setVoiceAccessGranted] = useState(false);
  const [voiceAccessLoading, setVoiceAccessLoading] = useState(false);
  const [textChatAccessGranted, setTextChatAccessGranted] = useState(false);
  const [textChatAccessLoading, setTextChatAccessLoading] = useState(false);
  const [tutorStatus, setTutorStatus] = useState("");
  const [tutorBusy, setTutorBusy] = useState(false);
  const [tutorAnswerText, setTutorAnswerText] = useState("");
  const [tutorAudioUrl, setTutorAudioUrl] = useState("");
  const [tutorChatHistory, setTutorChatHistory] = useState([]);
  const [voicePlatformBlockReason, setVoicePlatformBlockReason] = useState("");
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [assistantSpeaking, setAssistantSpeaking] = useState(false);
  const [adminEnabled, setAdminEnabled] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminStatus, setAdminStatus] = useState("");
  const [adminSummary, setAdminSummary] = useState(null);
  const [adminTopUsage, setAdminTopUsage] = useState([]);
  const [adminUsageLogs, setAdminUsageLogs] = useState([]);
  const [adminVoiceUsers, setAdminVoiceUsers] = useState([]);
  const [adminTextUsers, setAdminTextUsers] = useState([]);
  const [adminTeachers, setAdminTeachers] = useState([]);
  const [adminUserSettings, setAdminUserSettings] = useState([]);
  const [adminGrantEmail, setAdminGrantEmail] = useState("");
  const [adminTextGrantEmail, setAdminTextGrantEmail] = useState("");
  const [adminTeacherEmail, setAdminTeacherEmail] = useState("");
  const [limitMinutesPerDay, setLimitMinutesPerDay] = useState(120);
  const [textWeeklyBudgetUsd, setTextWeeklyBudgetUsd] = useState(5);
  const [adminUserQuery, setAdminUserQuery] = useState("");
  const [adminSettingsQuery, setAdminSettingsQuery] = useState("");
  const [adminLogQuery, setAdminLogQuery] = useState("");
  const [adminUsersPage, setAdminUsersPage] = useState(1);
  const [adminSettingsPage, setAdminSettingsPage] = useState(1);
  const [adminUsagePage, setAdminUsagePage] = useState(1);
  const [adminLogsPage, setAdminLogsPage] = useState(1);
  const [teacherEnabled, setTeacherEnabled] = useState(false);
  const [teacherStatus, setTeacherStatus] = useState("");
  const [teacherLoading, setTeacherLoading] = useState(false);
  const [teacherCourses, setTeacherCourses] = useState([]);
  const [teacherClasses, setTeacherClasses] = useState([]);
  const [teacherCourseTitle, setTeacherCourseTitle] = useState("");
  const [teacherCourseLanguages, setTeacherCourseLanguages] = useState("en-US,zh-CN,yue-HK");
  const [teacherCloneCourseId, setTeacherCloneCourseId] = useState("");
  const [teacherCloneClassTitle, setTeacherCloneClassTitle] = useState("");
  const [teacherClassIsPublic, setTeacherClassIsPublic] = useState(false);
  const [teacherPackageBucket, setTeacherPackageBucket] = useState("");
  const [teacherPackagePrefix, setTeacherPackagePrefix] = useState("");
  const [teacherPackageManifestUrl, setTeacherPackageManifestUrl] = useState("");
  const [teacherUploadFilePaths, setTeacherUploadFilePaths] = useState("");
  const [teacherUploadUrls, setTeacherUploadUrls] = useState([]);
  const [studentClasses, setStudentClasses] = useState([]);
  const [studentLoading, setStudentLoading] = useState(false);
  const [studentStatus, setStudentStatus] = useState("");
  const [classAccessLoading, setClassAccessLoading] = useState(false);
  const [classAccessDeniedMessage, setClassAccessDeniedMessage] = useState("");

  // Refs
  const audioRef = useRef(new Audio());
  const lastPlayedHash = useRef(null);
  const lastNarratedAudioUrl = useRef(null);
  const liveConversationRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const voiceProxySocketRef = useRef(null);
  const voiceProxyAuthorizedRef = useRef(false);
  const voiceRecognitionStartedRef = useRef(false);
  const voiceCaptureStreamRef = useRef(null);
  const voiceCaptureAudioContextRef = useRef(null);
  const voiceCaptureSourceRef = useRef(null);
  const voiceCaptureProcessorRef = useRef(null);
  const voicePlaybackCtxRef = useRef(null);
  const voicePlaybackNextRef = useRef(0);
  const assistantSpeechTimeoutRef = useRef(null);
  const voiceCaptureActiveRef = useRef(false);
  const voiceCommandPendingRef = useRef(false);
  const voiceLeaseRef = useRef(null);
  const voiceLeaseHeartbeatRef = useRef(null);
  const voiceLeaseExpiryTimeoutRef = useRef(null);
  const voiceSuppressNextCloseRef = useRef(false);
  const liveContextKeyRef = useRef("");
  const narrationCheckpointRef = useRef({ url: "", time: 0 });
  const pendingNarrationAfterVoiceRef = useRef(null);
  const activeAudioUrlRef = useRef(null);
  const audioUnlockedRef = useRef(false);
  const pendingNarrationRetryRef = useRef(false);
  const userPausedNarrationRef = useRef(false);
  const slideSwipeRef = useRef({ tracking: false, startX: 0, startY: 0 });
  const suppressSlideClickRef = useRef(false);
  const activeVoiceModeRef = useRef("disabled");
  const recentVoiceTranscriptRef = useRef({ text: "", time: 0 });
  const recentVoiceToolCallRef = useRef({ signature: "", time: 0, result: null });
  const tutorAskStateRef = useRef({ inFlight: false, lastQuestion: "", lastAt: 0 });
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
    studentClasses: [],
    presentationList: [],
    pageMode: "disabled",
  });

  const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
  const ADMIN_TEACHERS_ENDPOINT = `${API_BASE_URL}/api/admin-teachers`;
  const TEACHER_COURSES_ENDPOINT = `${API_BASE_URL}/api/teacher-courses`;
  const STUDENT_COURSES_ENDPOINT = `${API_BASE_URL}/api/student-courses`;
  const TEACHER_RECORDS_ENDPOINT = `${API_BASE_URL}/api/teacher-student-records`;
  const VOICE_LEASE_ENDPOINT = `${API_BASE_URL}/api/voice-live-session`;
  const TEXT_CHAT_ACCESS_ENDPOINT = `${API_BASE_URL}/api/text-chat-access`;
  const TUTOR_ASK_ENDPOINT = `${API_BASE_URL}/api/tutor-ask`;
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
  const getTutorChatStorageKey = (userUid, activeCourseId, presentationId, slideId, lang) => (
    `student.tutor.chat:${String(userUid || "guest")}:${String(activeCourseId || "current")}:${String(presentationId || "none")}:${String(slideId || "none")}:${String(lang || "en-US")}`
  );
  const availableVoiceLanguages = supportedLangs.length > 0 ? supportedLangs : Object.keys(AUDIO_LANGUAGE_NAMES);
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
  const normalizeLanguageAliasKey = (value) => String(value || "").trim().toLowerCase().replace(/[\s_-]+/g, "");
  const normalizeVoiceLanguageCode = (value) => {
    const raw = String(value || "").trim();
    if (!raw) return null;
    const normalized = raw.toLowerCase();
    const compactNormalized = normalizeLanguageAliasKey(raw);
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
      "中文": "zh-CN",
      "简体中文": "zh-CN",
      "簡體中文": "zh-CN",
      "中文简体": "zh-CN",
      "中文簡體": "zh-CN",
      "普通话": "zh-CN",
      "普通話": "zh-CN",
      "国语": "zh-CN",
      "國語": "zh-CN",
      "繁体中文": "yue-HK",
      "繁體中文": "yue-HK",
      "中文繁体": "yue-HK",
      "中文繁體": "yue-HK",
      "粤语": "yue-HK",
      "粵語": "yue-HK",
      "广东话": "yue-HK",
      "廣東話": "yue-HK",
    };
    const compactAliases = Object.entries(aliases).reduce((acc, [key, code]) => {
      acc[normalizeLanguageAliasKey(key)] = code;
      return acc;
    }, {});
    const candidate = aliases[normalized] || compactAliases[compactNormalized] || raw;
    const available = supportedLangs.length > 0 ? supportedLangs : Object.keys(AUDIO_LANGUAGE_NAMES);
    if (available.includes(candidate)) return candidate;
    const matched = available.find((code) => code.toLowerCase() === String(candidate).toLowerCase());
    return matched || null;
  };
  const resolveSpeechRecognitionLang = () => {
    const preferred = normalizeVoiceLanguageCode(listenLang)
      || normalizeDisplayLanguageCode(viewLang)
      || "en-US";
    const recognitionLangMap = {
      "en-US": "en-US",
      "zh-CN": "cmn-Hans-CN",
      "yue-HK": "yue-Hant-HK",
    };
    return recognitionLangMap[preferred] || preferred;
  };
  const normalizeDisplayLanguageCode = (value) => {
    const raw = String(value || "").trim();
    if (!raw) return null;
    const normalized = raw.toLowerCase();
    const compactNormalized = normalizeLanguageAliasKey(raw);
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
      "中文": "zh-CN",
      "简体中文": "zh-CN",
      "簡體中文": "zh-CN",
      "中文简体": "zh-CN",
      "中文簡體": "zh-CN",
      "普通话": "zh-CN",
      "普通話": "zh-CN",
      "国语": "zh-CN",
      "國語": "zh-CN",
      "繁体中文": "yue-HK",
      "繁體中文": "yue-HK",
      "中文繁体": "yue-HK",
      "中文繁體": "yue-HK",
      "粤语": "yue-HK",
      "粵語": "yue-HK",
      "广东话": "yue-HK",
      "廣東話": "yue-HK",
    };
    const compactAliases = Object.entries(aliases).reduce((acc, [key, code]) => {
      acc[normalizeLanguageAliasKey(key)] = code;
      return acc;
    }, {});
    const candidate = aliases[normalized] || compactAliases[compactNormalized] || raw;
    const available = Array.from(new Set([
      ...supportedLangs,
      ...Object.keys(liveData || {}),
      ...Object.keys(slideData?.languages || {}),
      ...Object.keys(DISPLAY_LANGUAGE_NAMES),
    ]));
    if (available.includes(candidate)) return candidate;
    const matched = available.find((code) => code.toLowerCase() === String(candidate).toLowerCase());
    return matched || null;
  };
  const getDisplayLanguageOptions = () => Array.from(new Set([
    ...supportedLangs,
    ...Object.keys(liveData || {}),
    ...Object.keys(slideData?.languages || {}),
    ...Object.keys(DISPLAY_LANGUAGE_NAMES),
  ]));
  const getUserLabel = (user) => {
    if (!user) return "Guest";
    const displayName = (user.displayName || "").trim();
    if (displayName) return displayName;
    const email = (user.email || "").trim();
    if (email.includes("@")) return email.split("@")[0];
    return user.uid || "User";
  };
  const canRenderVoiceAssistant = (user, granted, blockReason, statusText) => Boolean(
    user
    && granted
    && !blockReason
    && !String(statusText || "").toLowerCase().includes("requires admin grant")
  );
  const convertToCorsAudioUrl = (inputUrl) => {
    const raw = String(inputUrl || "").trim();
    if (!raw) return "";
    try {
      const parsed = new URL(raw, window.location.href);
      if (parsed.hostname !== "storage.googleapis.com") return parsed.toString();
      if (parsed.pathname.startsWith("/download/storage/v1/b/")) {
        parsed.searchParams.set("alt", "media");
        return parsed.toString();
      }
      const segments = parsed.pathname.split("/").filter(Boolean);
      if (segments.length < 2) return parsed.toString();
      const bucket = segments.shift();
      const objectPath = segments.join("/");
      return `https://storage.googleapis.com/download/storage/v1/b/${encodeURIComponent(bucket)}/o/${encodeURIComponent(objectPath)}?alt=media`;
    } catch (_error) {
      return raw;
    }
  };
  const prepareAudioSource = (inputUrl) => {
    const nextUrl = convertToCorsAudioUrl(inputUrl);
    const audio = audioRef.current;
    if (nextUrl.includes("/download/storage/v1/b/")) {
      audio.crossOrigin = "anonymous";
    } else {
      audio.removeAttribute("crossorigin");
      audio.crossOrigin = null;
    }
    return nextUrl;
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(DISPLAY_LANG_STORAGE_KEY, String(viewLang || "en"));
  }, [viewLang]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(SPEAK_LANG_STORAGE_KEY, String(listenLang || "en-US"));
  }, [listenLang]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(AUTOPLAY_STORAGE_KEY, String(Boolean(autoplay)));
  }, [autoplay]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(FONT_SIZE_STORAGE_KEY, String(readerFontSize));
  }, [readerFontSize]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const payload = {
      isLiveMode: Boolean(isLiveMode),
      pptId: viewingPptId ? String(viewingPptId) : null,
      slideId: viewingSlideId ? String(viewingSlideId) : null,
    };
    window.localStorage.setItem(SLIDE_STATE_STORAGE_KEY, JSON.stringify(payload));
  }, [isLiveMode, viewingPptId, viewingSlideId]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const presentationId = viewingPptId || livePptId;
    const slideId = viewingSlideId || liveSlideId;
    const key = getTutorChatStorageKey(currentUser?.uid, courseId, presentationId, slideId, listenLang);
    const raw = readLocalStorage(key);
    if (!raw) {
      setTutorChatHistory([]);
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        setTutorChatHistory([]);
        return;
      }
      const cleaned = parsed
        .filter((row) => row && typeof row === "object")
        .map((row) => ({
          role: row.role === "assistant" ? "assistant" : "user",
          text: String(row.text || "").trim(),
          usage: row.usage && typeof row.usage === "object" ? row.usage : null,
          spend: row.spend && typeof row.spend === "object" ? row.spend : null,
          citations: Array.isArray(row.citations) ? row.citations.filter((x) => typeof x === "string") : [],
        }))
        .filter((row) => row.text)
        .slice(-30);
      setTutorChatHistory(cleaned);
    } catch (_error) {
      setTutorChatHistory([]);
    }
  }, [currentUser?.uid, courseId, viewingPptId, viewingSlideId, livePptId, liveSlideId, listenLang]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const presentationId = viewingPptId || livePptId;
    const slideId = viewingSlideId || liveSlideId;
    const key = getTutorChatStorageKey(currentUser?.uid, courseId, presentationId, slideId, listenLang);
    window.localStorage.setItem(key, JSON.stringify(tutorChatHistory.slice(-30)));
  }, [tutorChatHistory, currentUser?.uid, courseId, viewingPptId, viewingSlideId, livePptId, liveSlideId, listenLang]);

  const getStudentVoiceMode = () => {
    if (isAdminIndexPage || isAdminPage || isTeacherPage) return "disabled";
    if (!hasClassParam) return "class_selection";
    if (hasClassParam && isReady && !classAccessLoading && !classAccessDeniedMessage) return "presentation";
    return "disabled";
  };
  const studentVoiceMode = getStudentVoiceMode();

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
      studentClasses,
      presentationList,
      pageMode: studentVoiceMode,
    };
  }, [slideList, viewingSlideId, livePptId, liveSlideId, isLiveMode, supportedLangs, listenLang, liveData, slideData, studentClasses, presentationList, studentVoiceMode]);

  useEffect(() => {
    if (!isListening) {
      activeVoiceModeRef.current = studentVoiceMode;
      return;
    }
    if (activeVoiceModeRef.current && activeVoiceModeRef.current !== studentVoiceMode) {
      setVoiceStatus("Page changed. Voice session stopped; start again to load correct tools.");
      stopVoiceCapture().catch((error) => {
        console.error("Failed to stop voice after page mode change:", error);
      });
    }
  }, [studentVoiceMode, isListening]);

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
    if (typeof window === "undefined") return;
    const handlePageShow = (event) => {
      if (!event.persisted) return;
      // Safari iOS can restore a stale JS runtime/session from bfcache.
      window.location.reload();
    };
    window.addEventListener("pageshow", handlePageShow);
    return () => window.removeEventListener("pageshow", handlePageShow);
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setCurrentUser(user);
      setAuthStatus(user ? `Signed in: ${getUserLabel(user)}` : "Guest");
      if (!user) {
        setVoiceStatus("Sign in to use voice chat");
        setVoiceAccessLoading(false);
        setTextChatAccessLoading(false);
        setTutorStatus("");
      } else if (voicePlatformBlockReason) {
        setVoiceStatus(voicePlatformBlockReason);
        setVoiceAccessLoading(false);
      } else if (!API_BASE_URL) {
        setVoiceStatus("Voice chat unavailable: API base URL not configured");
        setVoiceAccessLoading(false);
        setTextChatAccessLoading(false);
      } else {
        setVoiceStatus("Checking voice access...");
        setVoiceAccessLoading(true);
        setTextChatAccessLoading(true);
      }
      if (!user) {
        setVoiceAccessGranted(false);
        setTextChatAccessGranted(false);
      }
    });
    return () => unsubscribe();
  }, [API_BASE_URL, voicePlatformBlockReason]);

  useEffect(() => {
    if (currentUser) {
      loadAdminDashboard(currentUser);
      loadAdminTeachers(currentUser);
      loadTeacherRecords(currentUser);
      loadTeacherWorkspace(currentUser);
      loadStudentClasses(currentUser);
      loadVoiceAccess(currentUser);
      loadTextChatAccess(currentUser);
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
      setTextChatAccessGranted(false);
      setTutorStatus("");
      setTutorAnswerText("");
      setTutorAudioUrl("");
      setTutorChatHistory([]);
      pendingNarrationAfterVoiceRef.current = null;
      setAdminEnabled(false);
      setAdminStatus("");
      setAdminSummary(null);
      setAdminTopUsage([]);
      setAdminUsageLogs([]);
      setAdminVoiceUsers([]);
      setAdminTextUsers([]);
      setAdminTeachers([]);
      setAdminUserSettings([]);
      setAdminGrantEmail("");
      setAdminTextGrantEmail("");
      setTeacherEnabled(false);
      setTeacherStatus("");
      setTeacherCourses([]);
      setTeacherClasses([]);
      setStudentClasses([]);
      setStudentStatus("");
      setClassAccessDeniedMessage("");
      setIsReady(false);
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
        const rawBody = await response.text();
        let data = {};
        try {
          data = rawBody ? JSON.parse(rawBody) : {};
        } catch (_error) {
          data = {};
        }
        throw new Error(data.error || "Failed to load admin dashboard");
      }

      const data = await response.json();
      setAdminEnabled(true);
      setAdminStatus("");
      setAdminSummary(data.summary || null);
      setAdminVoiceUsers(Array.isArray(data.voice_users) ? data.voice_users : []);
      setAdminTextUsers(Array.isArray(data.text_users) ? data.text_users : []);
      setAdminUsersPage(1);
      if (data.limits) {
        setLimitMinutesPerDay(data.limits.minutes_per_day ?? data.limits.requests_per_day ?? 120);
      }
      if (data.text_chat) {
        setTextWeeklyBudgetUsd(Number(data.text_chat.weekly_budget_usd ?? 5));
      }
    } catch (error) {
      setAdminEnabled(false);
      setAdminStatus("");
      setAdminTextUsers([]);
    } finally {
      setAdminLoading(false);
    }
  };

  const loadAdminTeachers = async (user = currentUser) => {
    if (!user || !API_BASE_URL) return;
    try {
      const idToken = await user.getIdToken();
      const response = await fetch(ADMIN_TEACHERS_ENDPOINT, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${idToken}`,
        },
      });
      if (response.status === 401 || response.status === 403) {
        setAdminTeachers([]);
        return;
      }
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Failed to load teachers");
      }
      const data = await response.json();
      const rawTeachers = Array.isArray(data.teachers) ? data.teachers : [];
      const dedupedTeachers = Array.from(
        rawTeachers.reduce((map, teacher) => {
          const key = String(teacher?.email || teacher?.uid || teacher?.principal_value || "").trim().toLowerCase();
          if (!key) return map;
          const existing = map.get(key);
          if (!existing) {
            map.set(key, teacher);
            return map;
          }
          const existingRank = [
            existing?.active === true ? 1 : 0,
            existing?.principal_type === "uid" ? 1 : 0,
            String(existing?.updated_at || ""),
          ];
          const nextRank = [
            teacher?.active === true ? 1 : 0,
            teacher?.principal_type === "uid" ? 1 : 0,
            String(teacher?.updated_at || ""),
          ];
          if (nextRank[0] > existingRank[0]
            || (nextRank[0] === existingRank[0] && nextRank[1] > existingRank[1])
            || (nextRank[0] === existingRank[0] && nextRank[1] === existingRank[1] && nextRank[2] > existingRank[2])) {
            map.set(key, teacher);
          }
          return map;
        }, new Map())
      );
      setAdminTeachers(dedupedTeachers);
    } catch (_error) {
      setAdminTeachers([]);
    }
  };

  const loadTeacherRecords = async (user = currentUser) => {
    if (!user || !API_BASE_URL) return;
    setAdminLoading(true);
    try {
      const idToken = await user.getIdToken();
      const response = await fetch(TEACHER_RECORDS_ENDPOINT, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${idToken}`,
        },
      });

      if (response.status === 401 || response.status === 403) {
        setAdminTopUsage([]);
        setAdminUsageLogs([]);
        setAdminUserSettings([]);
        return;
      }
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Failed to load teacher records");
      }

      const data = await response.json();
      setAdminTopUsage(Array.isArray(data.top_usage) ? data.top_usage : []);
      setAdminUsageLogs(Array.isArray(data.usage_logs) ? data.usage_logs : []);
      setAdminUserSettings(Array.isArray(data.user_settings) ? data.user_settings : []);
      setAdminUsagePage(1);
      setAdminSettingsPage(1);
      setAdminLogsPage(1);
    } catch (_error) {
      setAdminTopUsage([]);
      setAdminUsageLogs([]);
      setAdminUserSettings([]);
    } finally {
      setAdminLoading(false);
    }
  };

  const loadTeacherWorkspace = async (user = currentUser) => {
    if (!user || !API_BASE_URL) return;
    setTeacherLoading(true);
    try {
      const idToken = await user.getIdToken();
      const response = await fetch(TEACHER_COURSES_ENDPOINT, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${idToken}`,
        },
      });
      if (response.status === 401 || response.status === 403) {
        setTeacherEnabled(false);
        setTeacherCourses([]);
        setTeacherClasses([]);
        return;
      }
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Failed to load teacher workspace");
      }
      const data = await response.json();
      setTeacherEnabled(Boolean(data.is_teacher || data.is_admin));
      setTeacherCourses(Array.isArray(data.courses) ? data.courses : []);
      setTeacherClasses(Array.isArray(data.classes) ? data.classes : []);
    } catch (_error) {
      setTeacherEnabled(false);
      setTeacherCourses([]);
      setTeacherClasses([]);
    } finally {
      setTeacherLoading(false);
    }
  };

  const loadStudentClasses = async (user = currentUser) => {
    if (!user || !API_BASE_URL) {
      setStudentClasses([]);
      return;
    }
    setStudentLoading(true);
    try {
      const idToken = await user.getIdToken();
      const response = await fetch(STUDENT_COURSES_ENDPOINT, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${idToken}`,
        },
      });
      if (response.status === 401 || response.status === 403) {
        setStudentClasses([]);
        setTeacherEnabled(false);
        return;
      }
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Failed to load classes");
      }
      const data = await response.json();
      setStudentClasses(Array.isArray(data.classes) ? data.classes : []);
      if (data?.user && (data.user.is_teacher || data.user.is_admin)) {
        setTeacherEnabled(true);
      }
    } catch (error) {
      setStudentClasses([]);
      setStudentStatus(error?.message || "Failed to load classes");
    } finally {
      setStudentLoading(false);
    }
  };

  const verifyClassAccess = async (user = currentUser, classIdValue = courseId) => {
    if (!user || !API_BASE_URL || !classIdValue) return false;
    setClassAccessLoading(true);
    setClassAccessDeniedMessage("");
    try {
      const idToken = await user.getIdToken();
      const response = await fetch(STUDENT_COURSES_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "access_check",
          class_id: classIdValue,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Class access denied");
      }
      return true;
    } catch (error) {
      setClassAccessDeniedMessage(error?.message || "Class access denied");
      return false;
    } finally {
      setClassAccessLoading(false);
    }
  };

  const createTeacherCourse = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const title = String(teacherCourseTitle || "").trim();
    if (!title) {
      setTeacherStatus("Course title is required");
      return;
    }
    setTeacherLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(TEACHER_COURSES_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "create_course",
          title,
          languages: teacherCourseLanguages,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Failed to create course");
      setTeacherStatus(`Created course: ${data.course_id}`);
      setTeacherCourseTitle("");
      await loadTeacherWorkspace(currentUser);
    } catch (error) {
      setTeacherStatus(error?.message || "Failed to create course");
    } finally {
      setTeacherLoading(false);
    }
  };

  const updateTeacherCourseTitle = async (course) => {
    if (!currentUser || !API_BASE_URL || !course?.course_id) return;
    const nextTitle = window.prompt("New course title", course.title || "");
    if (nextTitle === null) return;
    const title = String(nextTitle || "").trim();
    if (!title) {
      setTeacherStatus("Course title cannot be empty");
      return;
    }
    setTeacherLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(TEACHER_COURSES_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "update_course",
          course_id: course.course_id,
          title,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Failed to update course");
      setTeacherStatus(`Updated course: ${course.course_id}`);
      await loadTeacherWorkspace(currentUser);
    } catch (error) {
      setTeacherStatus(error?.message || "Failed to update course");
    } finally {
      setTeacherLoading(false);
    }
  };

  const cloneTeacherClass = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const courseIdValue = String(teacherCloneCourseId || "").trim();
    const classTitleValue = String(teacherCloneClassTitle || "").trim();
    if (!courseIdValue) {
      setTeacherStatus("Select a course to clone");
      return;
    }
    setTeacherLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(TEACHER_COURSES_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "clone_class",
          course_id: courseIdValue,
          class_title: classTitleValue || undefined,
          is_public: teacherClassIsPublic,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Failed to clone class");
      setTeacherStatus(`Created class: ${data.class_id}`);
      setTeacherCloneClassTitle("");
      await loadTeacherWorkspace(currentUser);
      await loadStudentClasses(currentUser);
    } catch (error) {
      setTeacherStatus(error?.message || "Failed to clone class");
    } finally {
      setTeacherLoading(false);
    }
  };

  const parseLines = (rawText) => String(rawText || "")
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);

  const linkTeacherCoursePackage = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const courseIdValue = String(teacherCloneCourseId || "").trim();
    const manifestUrl = String(teacherPackageManifestUrl || "").trim();
    if (!courseIdValue) {
      setTeacherStatus("Select a course first");
      return;
    }
    if (!manifestUrl) {
      setTeacherStatus("Manifest URL is required");
      return;
    }
    setTeacherLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(TEACHER_COURSES_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "link_course_package",
          course_id: courseIdValue,
          package_bucket: String(teacherPackageBucket || "").trim() || undefined,
          package_prefix: String(teacherPackagePrefix || "").trim() || undefined,
          manifest_url: manifestUrl || undefined,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Failed to link course package");
      setTeacherStatus(`Package linked and validated (${data.validation?.slides || 0} slides)`);
      await loadTeacherWorkspace(currentUser);
    } catch (error) {
      setTeacherStatus(error?.message || "Failed to link package");
    } finally {
      setTeacherLoading(false);
    }
  };

  const createClassFromPackage = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const courseIdValue = String(teacherCloneCourseId || "").trim();
    if (!courseIdValue) {
      setTeacherStatus("Select a course first");
      return;
    }
    setTeacherLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(TEACHER_COURSES_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "clone_class_from_package",
          course_id: courseIdValue,
          class_title: String(teacherCloneClassTitle || "").trim() || undefined,
          is_public: teacherClassIsPublic,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Failed to create class from package");
      setTeacherStatus(`Created class from package: ${data.class_id}`);
      setTeacherCloneClassTitle("");
      await loadTeacherWorkspace(currentUser);
      await loadStudentClasses(currentUser);
    } catch (error) {
      setTeacherStatus(error?.message || "Failed to create class from package");
    } finally {
      setTeacherLoading(false);
    }
  };

  const createTeacherUploadSession = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const courseIdValue = String(teacherCloneCourseId || "").trim();
    if (!courseIdValue) {
      setTeacherStatus("Select a course first");
      return;
    }
    const filePaths = parseLines(teacherUploadFilePaths);
    if (filePaths.length === 0) {
      setTeacherStatus("Provide file paths (one per line)");
      return;
    }
    setTeacherLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(TEACHER_COURSES_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "create_upload_session",
          course_id: courseIdValue,
          package_bucket: String(teacherPackageBucket || "").trim() || undefined,
          package_prefix: String(teacherPackagePrefix || "").trim() || undefined,
          file_paths: filePaths,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Failed to create upload session");
      setTeacherUploadUrls(Array.isArray(data.upload_urls) ? data.upload_urls : []);
      setTeacherStatus(`Upload session ready (${(data.upload_urls || []).length} file URLs)`);
    } catch (error) {
      setTeacherUploadUrls([]);
      setTeacherStatus(error?.message || "Failed to create upload session");
    } finally {
      setTeacherLoading(false);
    }
  };

  const enrollAndOpenClass = async (classIdValue) => {
    if (!currentUser || !API_BASE_URL || !classIdValue) return;
    setStudentLoading(true);
    setStudentStatus("");
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(STUDENT_COURSES_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "enroll",
          class_id: classIdValue,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Failed to enroll class");
      window.location.href = `/?class=${encodeURIComponent(classIdValue)}`;
    } catch (error) {
      setStudentStatus(error?.message || "Failed to open class");
    } finally {
      setStudentLoading(false);
    }
  };

  const loadVoiceAccess = async (user = currentUser) => {
    if (!user) return;
    setVoiceAccessLoading(true);
    if (voicePlatformBlockReason) {
      setVoiceAccessGranted(false);
      setVoiceStatus(voicePlatformBlockReason);
      setVoiceAccessLoading(false);
      return;
    }
    if (!API_BASE_URL) {
      setVoiceAccessGranted(false);
      setVoiceStatus("Voice chat unavailable: API base URL not configured");
      setVoiceAccessLoading(false);
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
    } finally {
      setVoiceAccessLoading(false);
    }
  };

  const loadTextChatAccess = async (user = currentUser) => {
    if (!user) return;
    setTextChatAccessLoading(true);
    if (!API_BASE_URL) {
      setTextChatAccessGranted(false);
      setTutorStatus("Text chat unavailable: API base URL not configured");
      setTextChatAccessLoading(false);
      return;
    }
    try {
      const idToken = await user.getIdToken();
      const response = await fetch(TEXT_CHAT_ACCESS_ENDPOINT, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${idToken}`,
        },
      });
      if (response.status === 401) {
        setTextChatAccessGranted(false);
        setTutorStatus("Session expired. Please sign in again");
        return;
      }
      if (response.status === 403) {
        setTextChatAccessGranted(false);
        setTutorStatus("Text chat access requires admin grant");
        return;
      }
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Failed to check text chat access");
      }
      const granted = data.granted === true;
      setTextChatAccessGranted(granted);
      setTutorStatus(granted ? "Text tutor ready" : "Text chat access requires admin grant");
    } catch (error) {
      setTextChatAccessGranted(false);
      setTutorStatus(error?.message || "Text chat access check failed");
    } finally {
      setTextChatAccessLoading(false);
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

  const saveTextBudget = async () => {
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
          action: "update_text_budget",
          weekly_budget_usd: Number(textWeeklyBudgetUsd),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Failed to update text budget");
      }
      setAdminStatus("Text chat budget updated");
      await loadAdminDashboard();
    } catch (error) {
      setAdminStatus(error.message || "Failed to update text budget");
    } finally {
      setAdminLoading(false);
    }
  };

  const parseGrantEmails = (rawText) => {
    const values = String(rawText || "")
      .split(/[\n,;]+/)
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);
    const deduped = Array.from(new Set(values));
    const valid = deduped.filter((email) => email.includes("@"));
    const invalid = deduped.filter((email) => !email.includes("@"));
    return { valid, invalid };
  };

  const grantVoiceUser = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const { valid: emails, invalid } = parseGrantEmails(adminGrantEmail);
    if (emails.length === 0) {
      setAdminStatus("At least one valid email is required");
      return;
    }
    setAdminLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const failed = [];
      for (const email of emails) {
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
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          failed.push(`${email} (${data.error || "request failed"})`);
        }
      }
      if (failed.length > 0 || invalid.length > 0) {
        const failedText = [...failed, ...invalid.map((email) => `${email} (invalid email)`)];
        setAdminGrantEmail(failed.map((item) => item.split(" (")[0]).join("\n"));
        setAdminStatus(`Granted ${emails.length - failed.length}/${emails.length}. Failed: ${failedText.join(", ")}`);
      } else {
        setAdminGrantEmail("");
        setAdminTextGrantEmail("");
        setAdminStatus(`Granted ${emails.length} student access user(s)`);
      }
      await loadAdminDashboard(currentUser);
    } catch (error) {
      console.error("Grant voice user failed:", error);
      setAdminStatus(error?.message || "Failed to grant voice user");
    } finally {
      setAdminLoading(false);
    }
  };

  const grantTextUser = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const { valid: emails, invalid } = parseGrantEmails(adminTextGrantEmail);
    if (emails.length === 0) {
      setAdminStatus("At least one valid text-chat email is required");
      return;
    }
    setAdminLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const failed = [];
      for (const email of emails) {
        const response = await fetch(`${API_BASE_URL}/api/voice-chat-admin`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${idToken}`,
          },
          body: JSON.stringify({
            action: "grant_text_user",
            email,
          }),
        });
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          failed.push(`${email} (${data.error || "request failed"})`);
        }
      }
      if (failed.length > 0 || invalid.length > 0) {
        const failedText = [...failed, ...invalid.map((email) => `${email} (invalid email)`)];
        setAdminTextGrantEmail(failed.map((item) => item.split(" (")[0]).join("\n"));
        setAdminStatus(`Granted ${emails.length - failed.length}/${emails.length} text users. Failed: ${failedText.join(", ")}`);
      } else {
        setAdminTextGrantEmail("");
        setAdminStatus(`Granted ${emails.length} text chat user(s)`);
      }
      await loadAdminDashboard(currentUser);
    } catch (error) {
      setAdminStatus(error?.message || "Failed to grant text chat user");
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

  const revokeTextUser = async (email) => {
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
          action: "revoke_text_user",
          email: normalizedEmail,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Failed to revoke text chat user");
      }
      setAdminStatus(data.message || "Text chat user revoked");
      await loadAdminDashboard(currentUser);
    } catch (error) {
      setAdminStatus(error?.message || "Failed to revoke text chat user");
    } finally {
      setAdminLoading(false);
    }
  };

  const grantTeacherUser = async () => {
    if (!currentUser || !API_BASE_URL) return;
    const { valid: emails, invalid } = parseGrantEmails(adminTeacherEmail);
    if (emails.length === 0) {
      setAdminStatus("At least one valid teacher email is required");
      return;
    }
    setAdminLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const failed = [];
      for (const email of emails) {
        const response = await fetch(ADMIN_TEACHERS_ENDPOINT, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${idToken}`,
          },
          body: JSON.stringify({
            action: "grant_teacher",
            email,
          }),
        });
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          failed.push(`${email} (${data.error || "request failed"})`);
        }
      }
      if (failed.length > 0 || invalid.length > 0) {
        const failedText = [...failed, ...invalid.map((email) => `${email} (invalid email)`)];
        setAdminTeacherEmail(failed.map((item) => item.split(" (")[0]).join("\n"));
        setAdminStatus(`Granted ${emails.length - failed.length}/${emails.length} teacher(s). Failed: ${failedText.join(", ")}`);
      } else {
        setAdminTeacherEmail("");
        setAdminStatus(`Granted ${emails.length} teacher(s)`);
      }
      await loadAdminTeachers(currentUser);
    } catch (error) {
      setAdminStatus(error?.message || "Failed to grant teacher");
    } finally {
      setAdminLoading(false);
    }
  };

  const revokeTeacherUser = async (email) => {
    if (!currentUser || !API_BASE_URL) return;
    const normalizedEmail = String(email || "").trim().toLowerCase();
    if (!normalizedEmail) return;
    setAdminLoading(true);
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(ADMIN_TEACHERS_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          action: "revoke_teacher",
          email: normalizedEmail,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Failed to revoke teacher");
      }
      setAdminStatus(data.message || "Teacher revoked");
      await loadAdminTeachers(currentUser);
    } catch (error) {
      setAdminStatus(error?.message || "Failed to revoke teacher");
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
    const mode = studentVoiceMode;
    if (mode === "class_selection") {
      const classSummary = studentClasses
        .slice(0, 20)
        .map((row) => `${row.class_id}:${row.title || row.class_id}`)
        .join(", ");
      return [
        "Student class selection context:",
        `available_classes=${classSummary || "none"}`,
        "",
        `User request: ${userText}`,
      ].join("\n");
    }

    const snapshot = getCurrentSlideSnapshot();
    if (mode === "presentation" && snapshot && snapshot.slideText) {
      return [
        "Student presentation context:",
        `class_id=${courseId}`,
        `presentation_id=${snapshot.presentationId}`,
        `slide_id=${snapshot.slideId}`,
        `slide_text=${snapshot.slideText}`,
        "",
        `User request: ${userText}`,
      ].join("\n");
    }

    return null;
  };

  const askTutorByText = async (question, options = {}) => {
    const text = String(question || "").trim();
    if (!text) return false;
    const forceSubmit = Boolean(options.force);
    const avatarName = String(options.avatarName || "").trim();
    const now = Date.now();
    const state = tutorAskStateRef.current;
    if (state.inFlight) {
      setTutorStatus("Tutor is processing your previous question...");
      return false;
    }
    const normalized = text.toLowerCase();
    if (!forceSubmit && state.lastQuestion === normalized && now - state.lastAt < 1500) {
      setTutorStatus("Duplicate question ignored");
      return false;
    }
    if (!currentUser) {
      setTutorStatus("Sign in to ask tutor");
      return false;
    }
    if (!textChatAccessGranted) {
      setTutorStatus("Text chat access requires admin grant");
      return false;
    }
    const presentationId = viewingPptId || livePptId;
    const slideId = viewingSlideId || liveSlideId;
    if (!presentationId || !slideId) {
      setTutorStatus("No active slide to discuss");
      return false;
    }
    tutorAskStateRef.current = { ...state, inFlight: true, lastQuestion: normalized, lastAt: now };
    const historyForRequest = tutorChatHistory.slice(-12).map((row) => ({
      role: row.role,
      text: String(row.text || "").trim(),
    })).filter((row) => row.text);
    setTutorChatHistory((prev) => [...prev, { role: "user", text }].slice(-30));
    setTutorBusy(true);
    setTutorStatus("Asking tutor...");
    try {
      const idToken = await currentUser.getIdToken();
      const response = await fetch(TUTOR_ASK_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          question: text,
          courseId,
          presentationId: String(presentationId),
          slideId: String(slideId),
          languageCode: listenLang,
          avatarName,
          chatHistory: historyForRequest,
        }),
      });
      const rawBody = await response.text();
      let data = {};
      try {
        data = rawBody ? JSON.parse(rawBody) : {};
      } catch (_error) {
        data = {};
      }
      if (response.status === 401) {
        setTextChatAccessGranted(false);
        setTutorStatus("Session expired. Please sign in again");
        return false;
      }
      if (response.status === 403) {
        setTextChatAccessGranted(false);
        setTutorStatus("Text chat access requires admin grant");
        return false;
      }
      if (response.status === 429) {
        setTutorStatus(data.error || "Weekly text chat budget exceeded");
        return false;
      }
      if (!response.ok) {
        const detail = String(data.error || rawBody || "").trim();
        throw new Error(detail ? `Tutor request failed (${response.status}): ${detail}` : `Tutor request failed (${response.status})`);
      }
      const answer = String(data.answer || "").trim();
      const audioUrl = String(data.audioUrl || "").trim();
      setTutorAnswerText(answer);
      setTutorAudioUrl(audioUrl);
      if (answer) {
        setTutorChatHistory((prev) => [...prev, {
          role: "assistant",
          text: answer,
          usage: data?.usage || null,
          spend: data?.spend || null,
          citations: Array.isArray(data?.citations) ? data.citations : [],
        }].slice(-30));
      }
      const remaining = Number(data?.spend?.weekly_remaining_usd);
      if (Number.isFinite(remaining)) {
        setTutorStatus(`Tutor replied · Weekly budget left: $${Math.max(0, remaining).toFixed(2)}`);
      } else {
        setTutorStatus("Tutor replied");
      }
      if (audioUrl) {
        await playAudioUrlNow({ audioUrl, restart: true });
      }
      return true;
    } catch (error) {
      const message = String(error?.message || "").trim();
      if (!message) {
        setTutorStatus("Tutor request failed: network or gateway error");
      } else {
        setTutorStatus(message);
      }
      return false;
    } finally {
      tutorAskStateRef.current = { ...tutorAskStateRef.current, inFlight: false };
      setTutorBusy(false);
    }
  };

  const replayTutorTts = async () => {
    const audioUrl = String(tutorAudioUrl || "").trim();
    if (!audioUrl) {
      setTutorStatus("No tutor speech to replay");
      return;
    }
    await playAudioUrlNow({ audioUrl, restart: true });
  };

  useEffect(() => {
    setTutorAnswerText("");
    setTutorAudioUrl("");
  }, [viewingPptId, viewingSlideId, isLiveMode, viewLang, listenLang]);

  const isNarrationBlockedByVoice = () => false;

  const clearTutorChatHistory = () => {
    setTutorChatHistory([]);
    const presentationId = viewingPptId || livePptId;
    const slideId = viewingSlideId || liveSlideId;
    const key = getTutorChatStorageKey(currentUser?.uid, courseId, presentationId, slideId, listenLang);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(key);
    }
    setTutorStatus("Tutor chat cleared");
  };

  const regenerateTutorAnswer = async (avatarName) => {
    const lastUser = [...tutorChatHistory].reverse().find((row) => row.role === "user" && String(row.text || "").trim());
    if (!lastUser) {
      setTutorStatus("No previous question to regenerate");
      return;
    }
    await askTutorByText(lastUser.text, { force: true, avatarName: String(avatarName || "").trim() });
  };

  const stopTutorSpeech = () => {
    audioRef.current.pause();
    setIsPlaying(false);
    setTutorStatus("Tutor speech stopped");
  };

  const exportTutorChat = async () => {
    if (!tutorChatHistory.length) {
      setTutorStatus("No tutor chat to export");
      return;
    }
    const transcript = tutorChatHistory.map((row) => {
      const role = row.role === "assistant" ? "Tutor" : "You";
      return `${role}: ${String(row.text || "").trim()}`;
    }).join("\n\n");
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(transcript);
        setTutorStatus("Tutor chat copied to clipboard");
        return;
      }
      throw new Error("clipboard unavailable");
    } catch (_error) {
      const blob = new Blob([transcript], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "tutor-chat.txt";
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      setTutorStatus("Tutor chat exported");
    }
  };

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
    const rawAudioUrl = activeContent?.audio_url || null;
    return rawAudioUrl ? convertToCorsAudioUrl(rawAudioUrl) : null;
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
      display_language: viewLang,
      audio_language: listenLang,
      autoplay,
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
          display_language: viewLang,
          audio_language: listenLang,
          autoplay,
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

  const buildVoiceToolDeclarations = (mode = getStudentVoiceMode()) => {
    const declarations = [
    {
      name: "get_student_state",
      description: "Get current student page state, classes, and presentation context.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "list_available_classes",
      description: "List available student course access entries.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "open_class",
      description: "Open the student's course by class_id/title/course_id.",
      parameters: {
        type: "object",
        properties: {
          class_id: { type: "string" },
          class_title: { type: "string" },
          course_id: { type: "string" },
        },
      },
    },
    {
      name: "back_to_class_selection",
      description: "Navigate back to the student course home page.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "select_presentation",
      description: "Select a presentation by presentation_id on the student slide page.",
      parameters: {
        type: "object",
        properties: {
          presentation_id: { type: "string" },
        },
        required: ["presentation_id"],
      },
    },
    {
      name: "navigate_slide",
      description: "Move to the next or previous slide on the student slide page.",
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
      description: "Jump directly to a specific slide/page number on the student slide page.",
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
      name: "select_slide",
      description: "Select a specific slide/page number on the student slide page.",
      parameters: {
        type: "object",
        properties: {
          slide_number: { type: "number", description: "Target slide/page number (for example 5)." },
          page_number: { type: "number", description: "Alias of slide_number." },
          slide: { type: "number", description: "Alias of slide_number." },
          page: { type: "number", description: "Alias of slide_number." },
        },
      },
    },
    {
      name: "list_presentations",
      description: "List available topic slide sets and the currently selected set.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "get_slide_range",
      description: "Get current slide page range (first page, last page, total pages).",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "list_slide_pages",
      description: "List available slide page numbers and the current page.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "get_current_slide_content",
      description: "Get current slide content (text/image/audio URLs) for active languages.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "jump_to_slide_boundary",
      description: "Jump directly to the first or last slide page.",
      parameters: {
        type: "object",
        properties: {
          boundary: {
            type: "string",
            enum: ["first", "last"],
            description: "Which edge of the current slide range to jump to.",
          },
        },
        required: ["boundary"],
      },
    },
    {
      name: "list_slide_languages",
      description: "Show available slide display and narration languages.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "toggle_live_mode",
      description: "Switch between LIVE sync mode and manual slide mode.",
      parameters: {
        type: "object",
        properties: {
          mode: {
            type: "string",
            enum: ["toggle", "live", "manual"],
            description: "Set mode explicitly or toggle current mode.",
          },
        },
      },
    },
    {
      name: "playback_control",
      description: "Control narration playback (start, pause, play/pause toggle, restart, seek, jump start).",
      parameters: {
        type: "object",
        properties: {
          action: {
            type: "string",
            enum: ["start", "pause", "play_pause", "restart", "seek", "seek_to", "jump_start"],
          },
          seconds: {
            type: "number",
            description: "For seek action: positive or negative seconds.",
          },
          position_seconds: {
            type: "number",
            description: "For seek_to action: absolute playback position in seconds.",
          },
        },
      },
    },
    {
      name: "set_read_aloud",
      description: "Set or toggle read-aloud autoplay for narration.",
      parameters: {
        type: "object",
        properties: {
          enabled: { type: "boolean" },
          mode: { type: "string", enum: ["on", "off", "toggle"] },
        },
      },
    },
    {
      name: "set_fullscreen_mode",
      description: "Open or close full-screen slide view.",
      parameters: {
        type: "object",
        properties: {
          mode: { type: "string", enum: ["open", "close", "toggle"] },
        },
      },
    },
    {
      name: "change_display_language",
      description: "Change display language (same as Alt+V shortcut).",
      parameters: {
        type: "object",
        properties: {
          direction: { type: "string", enum: ["next", "previous"] },
          language: { type: "string", description: "Target display language code/name." },
        },
      },
    },
    {
      name: "change_narration_language",
      description: "Change narration language (same as Alt+A shortcut).",
      parameters: {
        type: "object",
        properties: {
          direction: { type: "string", enum: ["next", "previous"] },
          language: { type: "string", description: "Target narration language code/name." },
        },
      },
    },
    {
      name: "list_shortcuts",
      description: "List available keyboard shortcuts for this page mode.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "help_commands",
      description: "Get a short spoken list of available voice commands.",
      parameters: { type: "object", properties: {} },
    },
    ];
    const declarationsByName = new Map(declarations.map((item) => [item.name, item]));
    const commonToolNames = [
      "get_student_state",
      "back_to_class_selection",
      "list_slide_languages",
      "list_shortcuts",
      "help_commands",
    ];
    const classSelectionToolNames = [
      "list_available_classes",
      "open_class",
    ];
    const presentationToolNames = [
      "list_presentations",
      "select_presentation",
      "get_slide_range",
      "list_slide_pages",
      "get_current_slide_content",
      "jump_to_slide_boundary",
      "navigate_slide",
      "go_to_slide",
      "select_slide",
      "toggle_live_mode",
      "playback_control",
      "set_read_aloud",
      "set_fullscreen_mode",
      "change_display_language",
      "change_narration_language",
    ];
    const modeToolNames = mode === "class_selection"
      ? [...commonToolNames, ...classSelectionToolNames]
      : mode === "presentation"
        ? [...commonToolNames, ...presentationToolNames]
        : commonToolNames;
    return modeToolNames
      .map((name) => declarationsByName.get(name))
      .filter(Boolean);
  };

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
    const remainingMs = Math.max(180, ((voicePlaybackNextRef.current - ctx.currentTime) * 1000) + 120);
    setAssistantSpeaking(true);
    if (assistantSpeechTimeoutRef.current) {
      clearTimeout(assistantSpeechTimeoutRef.current);
    }
    assistantSpeechTimeoutRef.current = setTimeout(() => {
      setAssistantSpeaking(false);
      assistantSpeechTimeoutRef.current = null;
    }, remainingMs);
  };

  const unlockAudioPlayback = async () => {
    audioUnlockedRef.current = true;
    if (voicePlaybackCtxRef.current && voicePlaybackCtxRef.current.state === "suspended") {
      try {
        await voicePlaybackCtxRef.current.resume();
      } catch (_error) {
        // no-op
      }
    }
    if (voiceCaptureAudioContextRef.current && voiceCaptureAudioContextRef.current.state === "suspended") {
      try {
        await voiceCaptureAudioContextRef.current.resume();
      } catch (_error) {
        // no-op
      }
    }
    if (pendingNarrationRetryRef.current) {
      pendingNarrationRetryRef.current = false;
      const retryUrl = activeAudioUrlRef.current || resolveActiveAudioUrl();
      if (retryUrl) {
        setTimeout(() => {
          startAudioPlayback(retryUrl, { restart: false });
        }, 0);
      }
    }
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

  const pcm16ToBase64 = (float32Array) => {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < float32Array.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    }
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  const stopRawVoiceInputCapture = async () => {
    if (voiceCaptureProcessorRef.current) {
      try {
        voiceCaptureProcessorRef.current.disconnect();
      } catch (_error) {
        // no-op
      }
      voiceCaptureProcessorRef.current.onaudioprocess = null;
      voiceCaptureProcessorRef.current = null;
    }
    if (voiceCaptureSourceRef.current) {
      try {
        voiceCaptureSourceRef.current.disconnect();
      } catch (_error) {
        // no-op
      }
      voiceCaptureSourceRef.current = null;
    }
    if (voiceCaptureAudioContextRef.current) {
      try {
        await voiceCaptureAudioContextRef.current.close();
      } catch (_error) {
        // no-op
      }
      voiceCaptureAudioContextRef.current = null;
    }
    if (voiceCaptureStreamRef.current) {
      voiceCaptureStreamRef.current.getTracks().forEach((track) => track.stop());
      voiceCaptureStreamRef.current = null;
    }
  };

  const startRawVoiceInputCapture = async (socket) => {
    if (!navigator?.mediaDevices?.getUserMedia) {
      throw new Error("Microphone capture is not supported on this device");
    }
    await stopRawVoiceInputCapture();
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioContextCtor({ sampleRate: 16000 });
    const source = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(4096, 1, 1);

    processor.onaudioprocess = (event) => {
      if (!voiceCaptureActiveRef.current) return;
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      const input = event.inputBuffer.getChannelData(0);
      const base64Audio = pcm16ToBase64(input);
      socket.send(JSON.stringify({
        realtime_input: {
          media_chunks: [
            {
              mime_type: "audio/pcm",
              data: base64Audio,
            },
          ],
        },
      }));
    };

    source.connect(processor);
    processor.connect(ctx.destination);

    voiceCaptureStreamRef.current = stream;
    voiceCaptureAudioContextRef.current = ctx;
    voiceCaptureSourceRef.current = source;
    voiceCaptureProcessorRef.current = processor;
  };

  const parseToolArgs = (call) => {
    if (call?.args && typeof call.args === "object") return call.args;
    if (call?.arguments && typeof call.arguments === "object") return call.arguments;
    if (typeof call?.args === "string") {
      try {
        const parsed = JSON.parse(call.args);
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch (_error) {
        return {};
      }
    }
    if (typeof call?.arguments === "string") {
      try {
        const parsed = JSON.parse(call.arguments);
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch (_error) {
        return {};
      }
    }
    return {};
  };

  const buildToolCallSignature = (call) => {
    const args = parseToolArgs(call);
    const keys = Object.keys(args).sort();
    const stableArgs = {};
    for (const key of keys) stableArgs[key] = args[key];
    return `${String(call?.name || "").trim()}:${JSON.stringify(stableArgs)}`;
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
      const mode = studentVoiceMode;
      const setupTools = ENABLE_GROUNDING
        ? {
          function_declarations: buildVoiceToolDeclarations(mode),
          google_search: {},
        }
        : { function_declarations: buildVoiceToolDeclarations(mode) };
      const modeScopeInstruction = mode === "class_selection"
        ? "This session is on course home. Only use course-home tools."
        : mode === "presentation"
          ? "This session is on presentation page. Use presentation/slide, playback, language, and back-to-home tools only."
          : "Tools are limited to safe student commands.";
      const currentStudentName = getUserLabel(currentUser);
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
              text: `You are an accessibility-first student voice assistant for visually impaired students.
Detect the user's spoken language each turn and reply in that language. You may switch languages naturally across turns.
The signed-in student name is ${currentStudentName}. Use this name naturally in greetings when appropriate.
Use tool calls for navigation, playback, and language actions.
Never invent class IDs, presentation IDs, or slide IDs.
When user intent matches an available function, call the function instead of describing steps.
Allowed scope only: tools declared in this session.
${modeScopeInstruction}
When the user asks about current slide content, first call get_current_slide_content.
For each actionable user command, issue exactly one function call whenever possible.
Do not call tools outside this scope.
Keep replies short and explicit about the action completed.`,
            }],
          },
          tools: setupTools,
          realtime_input_config: {
            automatic_activity_detection: {
              disabled: false,
              silence_duration_ms: 900,
              prefix_padding_ms: 250,
            },
          },
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
      if (!voiceRecognitionStartedRef.current) {
        try {
          await startRawVoiceInputCapture(voiceProxySocketRef.current);
          voiceRecognitionStartedRef.current = true;
          setVoiceStatus("Listening...");
        } catch (error) {
          setVoiceStatus(error?.message || "Failed to start microphone capture");
          stopVoiceCapture().catch((stopError) => {
            console.error("Failed to stop voice after microphone start error:", stopError);
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
      try {
        voiceCommandPendingRef.current = true;
        for (const call of toolCalls) {
          const signature = buildToolCallSignature(call);
          const now = Date.now();
          let result;
          if (
            recentVoiceToolCallRef.current.signature === signature
            && now - recentVoiceToolCallRef.current.time < 2500
          ) {
            result = recentVoiceToolCallRef.current.result || { ok: true, message: "Command already applied." };
          } else {
            result = await executeVoiceCommand(call);
            recentVoiceToolCallRef.current = { signature, time: now, result };
          }
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
      } finally {
        voiceCommandPendingRef.current = false;
      }
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
          await playProxyPcmAudio(inlineData.data, inlineData.mimeType || inlineData.mime_type || "audio/pcm");
        }
      }
    }
  };

  const startVoiceCapture = async () => {
    unlockAudioPlayback().catch(() => {});
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
    const mode = getStudentVoiceMode();
    const presentationId = viewingPptId || livePptId;
    const slideId = viewingSlideId || liveSlideId;
    if (mode === "disabled") {
      setVoiceStatus("Voice tools are unavailable on this page");
      return;
    }
    if (mode === "presentation" && (!presentationId || !slideId)) {
      setVoiceStatus("No active slide to discuss");
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
    recentVoiceTranscriptRef.current = { text: "", time: 0 };
    recentVoiceToolCallRef.current = { signature: "", time: 0, result: null };
    setAutoplay(true);
    setVoiceStatus("Authorizing voice session...");
    try {
      await startVoiceLease({
        user: currentUser,
        courseIdValue: mode === "presentation" ? courseId : "",
        presentationIdValue: mode === "presentation" ? presentationId : "",
        slideIdValue: mode === "presentation" ? slideId : "",
      });
      const leaseSessionId = voiceLeaseRef.current?.session_id;
      if (!leaseSessionId) {
        throw new Error("Voice lease session was not issued");
      }

      const ws = new WebSocket(VOICE_PROXY_WS_URL);
      voiceProxySocketRef.current = ws;
      voiceProxyAuthorizedRef.current = false;
      voiceRecognitionStartedRef.current = false;

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
        if (voiceSuppressNextCloseRef.current) {
          voiceSuppressNextCloseRef.current = false;
          return;
        }
        if (voiceCaptureActiveRef.current) {
          const authorized = voiceProxyAuthorizedRef.current;
          if (!authorized) {
            setVoiceAccessGranted(false);
          }
          setVoiceStatus(authorized ? "Voice proxy disconnected" : "Voice chat access requires admin grant");
          stopVoiceCapture().catch((stopError) => {
            console.error("Failed to stop voice after proxy disconnect:", stopError);
          });
        }
      };

      voiceCaptureActiveRef.current = true;
      activeVoiceModeRef.current = mode;
      setIsListening(true);
      setVoiceStatus("Connecting voice proxy...");
    } catch (error) {
      console.error("Voice session start failed:", error);
      voiceCaptureActiveRef.current = false;
      speechRecognitionRef.current = null;
      await stopRawVoiceInputCapture();
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
      activeVoiceModeRef.current = "disabled";
      recentVoiceTranscriptRef.current = { text: "", time: 0 };
      recentVoiceToolCallRef.current = { signature: "", time: 0, result: null };
      voiceProxyAuthorizedRef.current = false;
      voiceRecognitionStartedRef.current = false;
      await stopRawVoiceInputCapture();
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
      if (assistantSpeechTimeoutRef.current) {
        clearTimeout(assistantSpeechTimeoutRef.current);
        assistantSpeechTimeoutRef.current = null;
      }
      setAssistantSpeaking(false);
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

  const applyMp3LanguageChange = (requestedLanguage) => {
    const normalized = normalizeVoiceLanguageCode(requestedLanguage);
    if (!normalized) {
      const raw = String(requestedLanguage || "").trim();
      setVoiceStatus(`Unsupported narration language: ${raw || "unknown"}`);
      return;
    }
    setListenLang(normalized);
  };

  useEffect(() => {
    if (isAdminIndexPage || isAdminPage || isTeacherPage) return;
    if (!hasClassParam) {
      setClassAccessDeniedMessage("");
      setIsReady(false);
      return;
    }
    if (!currentUser) {
      setClassAccessDeniedMessage("Sign in required to open this class");
      setIsReady(false);
      return;
    }
    verifyClassAccess(currentUser, courseId).then((allowed) => {
      setIsReady(allowed);
    });
  }, [hasClassParam, currentUser, courseId, isAdminIndexPage, isAdminPage, isTeacherPage]);

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

    const playbackUrl = prepareAudioSource(audioUrl);
    if (audioRef.current.src !== playbackUrl) {
      audioRef.current.src = playbackUrl;
    }

    if (restart) {
      audioRef.current.currentTime = 0;
      setAudioCurrentTime(0);
    }

    lastNarratedAudioUrl.current = playbackUrl;
    setNarrationStatus("Playing narration");
    audioRef.current.play()
      .then(() => {
        userPausedNarrationRef.current = false;
        setIsPlaying(true);
        setNarrationStatus("Narrating");
      })
      .catch((error) => {
        console.error("Narration playback blocked:", error);
        setIsPlaying(false);
        pendingNarrationRetryRef.current = true;
        setNarrationStatus("Tap screen once to enable narration audio");
      });
  };

  const playAudioUrlNow = async ({ audioUrl, restart = false, startTime = null } = {}) => {
    if (!audioUrl) {
      setNarrationStatus("Narration audio unavailable");
      return { ok: false, message: "Narration audio unavailable." };
    }
    const playbackUrl = prepareAudioSource(audioUrl);
    if (audioRef.current.src !== playbackUrl) {
      audioRef.current.src = playbackUrl;
    }
    if (restart) {
      audioRef.current.currentTime = 0;
      setAudioCurrentTime(0);
    } else if (Number.isFinite(startTime) && startTime >= 0) {
      audioRef.current.currentTime = startTime;
      setAudioCurrentTime(startTime);
    }
    setNarrationStatus("Playing narration");
    try {
      await audioRef.current.play();
      userPausedNarrationRef.current = false;
      setIsPlaying(true);
      setNarrationStatus("Narrating");
      return { ok: true, message: "Narration started." };
    } catch (error) {
      console.error("Narration playback blocked:", error);
      setIsPlaying(false);
      pendingNarrationRetryRef.current = true;
      setNarrationStatus("Tap screen once to enable narration audio");
      return { ok: false, message: "Narration playback blocked." };
    }
  };

  const stopNarration = () => {
    userPausedNarrationRef.current = true;
    audioRef.current.pause();
    audioRef.current.currentTime = 0;
    setAudioCurrentTime(0);
    setIsPlaying(false);
    setNarrationStatus("Stopped");
  };

  const pauseNarration = () => {
    userPausedNarrationRef.current = true;
    audioRef.current.pause();
    setIsPlaying(false);
    setNarrationStatus("Paused");
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
    const playbackUrl = prepareAudioSource(targetUrl);

    if (audioRef.current.src !== playbackUrl) {
      audioRef.current.src = playbackUrl;
    }

    if (pending.mode === "restart") {
      audioRef.current.currentTime = 0;
      setAudioCurrentTime(0);
    } else {
      const resumeTime = Number.isFinite(checkpoint.time) ? Math.max(0, checkpoint.time) : 0;
      audioRef.current.currentTime = (checkpoint.url && checkpoint.url === playbackUrl) ? resumeTime : 0;
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
    const onUserActivation = () => {
      unlockAudioPlayback().catch(() => {});
    };
    window.addEventListener("pointerdown", onUserActivation, { passive: true });
    window.addEventListener("touchstart", onUserActivation, { passive: true });
    window.addEventListener("keydown", onUserActivation);
    return () => {
      window.removeEventListener("pointerdown", onUserActivation);
      window.removeEventListener("touchstart", onUserActivation);
      window.removeEventListener("keydown", onUserActivation);
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
      stopRawVoiceInputCapture().catch(() => {});
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
      if (assistantSpeechTimeoutRef.current) {
        clearTimeout(assistantSpeechTimeoutRef.current);
        assistantSpeechTimeoutRef.current = null;
      }
      setAssistantSpeaking(false);
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

  useEffect(() => {
    if (isListening) return;
    if (assistantSpeechTimeoutRef.current) {
      clearTimeout(assistantSpeechTimeoutRef.current);
      assistantSpeechTimeoutRef.current = null;
    }
    setAssistantSpeaking(false);
  }, [isListening]);

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

  const startNarration = ({ restart = false } = {}) => {
    const audioUrl = resolveActiveAudioUrl();
    if (!audioUrl) {
      setNarrationStatus("Narration audio unavailable");
      return;
    }
    const currentSrc = String(audioRef.current.src || "");
    const playbackUrl = prepareAudioSource(audioUrl);
    const sameSource = currentSrc === playbackUrl || currentSrc.endsWith(playbackUrl);
    userPausedNarrationRef.current = false;
    if (restart || !audioRef.current.src || !sameSource) {
      startAudioPlayback(playbackUrl, { restart });
      return;
    }
    if (audioRef.current.ended) {
      audioRef.current.currentTime = 0;
      setAudioCurrentTime(0);
    }
    audioRef.current.play()
      .then(() => {
        setIsPlaying(true);
        setNarrationStatus("Narrating");
      })
      .catch((error) => {
        console.error("Playback failed:", error);
        pendingNarrationRetryRef.current = true;
        setNarrationStatus("Tap screen once to enable narration audio");
      });
  };

  // --- 1. Listen to Root Broadcast (Live State) ---
  useEffect(() => {
    if (!isReady) return;

    const unsubscribe = onSnapshot(
      doc(db, "presentation_broadcast", courseId),
      (docSnapshot) => {
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
      },
      (error) => {
        console.error("Error reading class broadcast:", error);
        setStatus({ text: "🔴 Class access denied", color: "red" });
        setClassAccessDeniedMessage("Class access denied");
      },
    );
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
      const unsubscribe = onSnapshot(
        slideRef,
        (docSnapshot) => {
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
        },
        (error) => {
          console.error("Error reading slide data:", error);
          setClassAccessDeniedMessage("Class access denied");
        },
      );
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
    const rawAudioUrl = audioContent?.audio_url || null;
    return rawAudioUrl ? convertToCorsAudioUrl(rawAudioUrl) : null;
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
      if (!activeAudioUrl || !autoplay || narrationBlockedByVoice || userPausedNarrationRef.current) return;

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
      const narrationBlockedByVoice = isNarrationBlockedByVoice();
      if (narrationBlockedByVoice) {
        setNarrationStatus("Narration paused during voice chat");
        return;
      }

      const isCurrentlyPlaying = !audioRef.current.paused && !audioRef.current.ended;
      if (isCurrentlyPlaying) {
        pauseNarration();
        return;
      }
      startNarration({ restart: false });
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

  const handleSlidePointerDown = (event) => {
    if ((window.innerWidth || 0) > 900) return;
    if (event.pointerType !== "touch" && event.pointerType !== "pen") return;
    slideSwipeRef.current = {
      tracking: true,
      startX: event.clientX,
      startY: event.clientY,
    };
  };

  const handleSlidePointerUp = (event) => {
    const state = slideSwipeRef.current;
    if (!state.tracking) return;
    slideSwipeRef.current.tracking = false;
    const deltaX = event.clientX - state.startX;
    const deltaY = event.clientY - state.startY;
    const horizontalThreshold = 56;
    const verticalTolerance = 72;
    if (Math.abs(deltaX) < horizontalThreshold || Math.abs(deltaY) > verticalTolerance) return;
    suppressSlideClickRef.current = true;
    if (deltaX < 0) {
      handleNext();
    } else {
      handlePrev();
    }
  };

  const handleSlidePointerCancel = () => {
    slideSwipeRef.current.tracking = false;
  };

  const handleSlideOpenFullScreen = () => {
    if (suppressSlideClickRef.current) {
      suppressSlideClickRef.current = false;
      return;
    }
    setIsFullScreen(true);
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
      const mode = getStudentVoiceMode();
      const allowedTools = new Set(buildVoiceToolDeclarations(mode).map((item) => item.name));
      if (mode === "disabled") {
        return { ok: false, message: "Student voice tools are unavailable on this page." };
      }
      if (!allowedTools.has(name)) {
        return { ok: false, message: `Unsupported command: ${name}` };
      }

      if (name === "get_student_state") {
        const state = voiceStateRef.current;
        const classes = (state.studentClasses || []).map((row) => ({
          class_id: row.class_id,
          title: row.title || "",
          course_id: row.course_id || "",
          course_title: row.course_title || "",
          is_public: row.is_public === true,
        }));
        const courses = Array.from(
          new Map(
            classes
              .filter((row) => row.course_id)
              .map((row) => [row.course_id, { course_id: row.course_id, course_title: row.course_title || row.course_id }]),
          ).values(),
        );
        return {
          ok: true,
          message: mode === "class_selection"
            ? `On student course home with ${classes.length} available course access entr${classes.length === 1 ? "y" : "ies"}.`
            : `On presentation ${state.viewingPptId || state.livePptId || ""}, slide ${state.viewingSlideId || state.liveSlideId || ""}.`,
          data: {
            mode,
            class_id: hasClassParam ? courseId : null,
            classes,
            courses,
            presentation_id: state.viewingPptId || state.livePptId || null,
            slide_id: state.viewingSlideId || state.liveSlideId || null,
            available_presentations: state.presentationList || [],
            slide_first_page: state.slideList?.[0] ?? null,
            slide_last_page: state.slideList?.[state.slideList.length - 1] ?? null,
            slide_total_pages: state.slideList?.length ?? 0,
            available_slide_pages: state.slideList || [],
            read_aloud_enabled: autoplay,
            fullscreen_open: isFullScreen,
            narration_playing: isPlaying,
          },
        };
      }

      if (name === "list_available_classes") {
        const state = voiceStateRef.current;
        const classes = (state.studentClasses || []).map((row) => ({
          class_id: row.class_id,
          class_title: row.title || row.class_id,
          course_id: row.course_id || "",
          course_title: row.course_title || row.course_id || "",
          is_public: row.is_public === true,
        }));
        const courses = Array.from(
          new Map(
            classes
              .filter((row) => row.course_id)
              .map((row) => [row.course_id, { course_id: row.course_id, course_title: row.course_title || row.course_id }]),
          ).values(),
        );
        return {
          ok: true,
          message: classes.length === 1
            ? "This student account has one course access entry."
            : `This student account has ${classes.length} course access entries.`,
          data: {
            courses,
            classes,
          },
        };
      }

      if (name === "open_class") {
        if (mode !== "class_selection") {
          return { ok: false, message: "open_class is only available on student course home." };
        }
        const requestedClassId = String(args.class_id || args.classId || "").trim();
        const requestedClassTitle = String(args.class_title || args.title || "").trim().toLowerCase();
        const requestedCourseId = String(args.course_id || args.courseId || "").trim();
        let candidate = null;
        if (requestedClassId) {
          candidate = studentClasses.find((row) => String(row.class_id || "") === requestedClassId) || null;
        }
        if (!candidate && requestedClassTitle) {
          candidate = studentClasses.find((row) => String(row.title || "").trim().toLowerCase() === requestedClassTitle) || null;
        }
        if (!candidate && requestedCourseId) {
          candidate = studentClasses.find((row) => String(row.course_id || "") === requestedCourseId) || null;
        }
        if (!candidate) {
          if (studentClasses.length === 1) {
            candidate = studentClasses[0];
          } else {
            return { ok: false, message: "Course entry not found. Provide class_id." };
          }
        }
        await enrollAndOpenClass(candidate.class_id);
        return { ok: true, message: `Opening course ${(candidate.course_title || candidate.course_id || candidate.class_id)}.` };
      }

      if (name === "back_to_class_selection") {
        window.location.href = "/";
        return { ok: true, message: "Returning to course home." };
      }

      if (name === "select_presentation") {
        if (mode !== "presentation") {
          return { ok: false, message: "select_presentation is only available on presentation page." };
        }
        const targetPresentationId = String(args.presentation_id || args.presentationId || "").trim();
        if (!targetPresentationId) {
          return { ok: false, message: "presentation_id is required." };
        }
        if (!presentationList.includes(targetPresentationId)) {
          return { ok: false, message: `Presentation ${targetPresentationId} is not available.` };
        }
        setViewingPptId(targetPresentationId);
        setIsLiveMode(false);
        return { ok: true, message: `Presentation switched to ${targetPresentationId}.` };
      }

      if (name === "list_presentations") {
        if (mode !== "presentation") {
          return { ok: false, message: "list_presentations is only available on presentation page." };
        }
        const state = voiceStateRef.current;
        const latestPresentations = Array.isArray(state.presentationList) ? state.presentationList : [];
        const currentPresentationId = state.viewingPptId || state.livePptId || null;
        return {
          ok: true,
          message: latestPresentations.length === 0
            ? "No topic slide sets are available."
            : `There are ${latestPresentations.length} topic slide sets available.`,
          data: {
            current_presentation_id: currentPresentationId,
            available_presentations: latestPresentations,
          },
        };
      }

      if (name === "get_slide_range") {
        if (mode !== "presentation") {
          return { ok: false, message: "get_slide_range is only available on presentation page." };
        }
        const { slideList: latestSlideList, viewingSlideId: latestViewingSlideId, viewingPptId: latestViewingPptId, livePptId: latestLivePptId } = voiceStateRef.current;
        if (!Array.isArray(latestSlideList) || latestSlideList.length === 0) {
          return { ok: false, message: "No slide pages are available for the current topic." };
        }
        const firstPage = latestSlideList[0];
        const lastPage = latestSlideList[latestSlideList.length - 1];
        return {
          ok: true,
          message: `Current page range is ${firstPage} to ${lastPage}.`,
          data: {
            presentation_id: latestViewingPptId || latestLivePptId || null,
            current_page: Number.parseInt(latestViewingSlideId, 10) || null,
            first_page: firstPage,
            last_page: lastPage,
            total_pages: latestSlideList.length,
            available_pages: latestSlideList,
          },
        };
      }

      if (name === "list_slide_pages") {
        if (mode !== "presentation") {
          return { ok: false, message: "list_slide_pages is only available on presentation page." };
        }
        const { slideList: latestSlideList, viewingSlideId: latestViewingSlideId, viewingPptId: latestViewingPptId, livePptId: latestLivePptId } = voiceStateRef.current;
        if (!Array.isArray(latestSlideList) || latestSlideList.length === 0) {
          return { ok: false, message: "No slide pages are available for the current topic." };
        }
        return {
          ok: true,
          message: `Current topic has ${latestSlideList.length} slide pages.`,
          data: {
            presentation_id: latestViewingPptId || latestLivePptId || null,
            current_page: Number.parseInt(latestViewingSlideId, 10) || null,
            available_pages: latestSlideList,
          },
        };
      }

      if (name === "get_current_slide_content") {
        if (mode !== "presentation") {
          return { ok: false, message: "get_current_slide_content is only available on presentation page." };
        }
        const state = voiceStateRef.current;
        const presentationId = state.viewingPptId || state.livePptId || null;
        const slideId = state.viewingSlideId || state.liveSlideId || null;
        if (!presentationId || !slideId) {
          return { ok: false, message: "No active presentation slide is available." };
        }
        const sourceLanguages = state.isLiveMode
          ? (state.liveData || state.slideData?.languages || {})
          : (state.slideData?.languages || state.liveData || {});
        const availableLanguageCodes = Object.keys(sourceLanguages || {});
        if (availableLanguageCodes.length === 0) {
          return { ok: false, message: "Current slide content is unavailable." };
        }

        const activeDisplayLanguage = normalizeDisplayLanguageCode(viewLang) || viewLang;
        const activeNarrationLanguage = normalizeVoiceLanguageCode(listenLang) || listenLang;
        const displayContent = getLangContent(sourceLanguages, activeDisplayLanguage);
        const narrationContent = getLangContent(sourceLanguages, activeNarrationLanguage);

        const languages = availableLanguageCodes.map((code) => {
          const content = sourceLanguages[code] || {};
          return {
            code,
            text: String(content.text || "").trim(),
            image_url: content.image_url || null,
            audio_url: content.audio_url || null,
          };
        });

        return {
          ok: true,
          message: `Loaded current slide content for slide ${slideId}.`,
          data: {
            mode: state.isLiveMode ? "live" : "manual",
            presentation_id: String(presentationId),
            slide_id: String(slideId),
            display_language: activeDisplayLanguage,
            narration_language: activeNarrationLanguage,
            display_content: {
              text: String(displayContent?.text || "").trim(),
              image_url: displayContent?.image_url || null,
              audio_url: displayContent?.audio_url || null,
            },
            narration_content: {
              text: String(narrationContent?.text || "").trim(),
              image_url: narrationContent?.image_url || null,
              audio_url: narrationContent?.audio_url || null,
            },
            available_languages: languages,
          },
        };
      }

      if (name === "jump_to_slide_boundary") {
        if (mode !== "presentation") {
          return { ok: false, message: "jump_to_slide_boundary is only available on presentation page." };
        }
        const { slideList: latestSlideList } = voiceStateRef.current;
        if (!Array.isArray(latestSlideList) || latestSlideList.length === 0) {
          return { ok: false, message: "No slide pages are available for the current topic." };
        }
        const boundary = String(args.boundary || "").toLowerCase();
        if (boundary !== "first" && boundary !== "last") {
          return { ok: false, message: "boundary must be first or last." };
        }
        const target = boundary === "first" ? latestSlideList[0] : latestSlideList[latestSlideList.length - 1];
        setViewingSlideId(String(target));
        setIsLiveMode(false);
        return { ok: true, message: `Moved to ${boundary} slide ${target}.` };
      }

      if (name === "navigate_slide") {
        if (mode !== "presentation") {
          return { ok: false, message: "navigate_slide is only available on presentation page." };
        }
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
        if (mode !== "presentation") {
          return { ok: false, message: "go_to_slide is only available on presentation page." };
        }
        const { slideList: latestSlideList } = voiceStateRef.current;
        if (!Array.isArray(latestSlideList) || latestSlideList.length === 0) {
          return { ok: false, message: "No slide pages are available for the current topic." };
        }
        const rawTarget = args.slide_number ?? args.page_number ?? args.slide ?? args.page ?? args.position;
        const rawLabel = String(rawTarget ?? "").trim().toLowerCase();
        let target;
        if (rawLabel === "first") {
          target = latestSlideList[0];
        } else if (rawLabel === "last") {
          target = latestSlideList[latestSlideList.length - 1];
        } else {
          const directTarget = Number(rawTarget);
          if (!Number.isFinite(directTarget)) {
            return { ok: false, message: "slide_number is required (or use first/last)." };
          }
          target = Math.trunc(directTarget);
        }
        if (!latestSlideList.includes(target)) {
          return { ok: false, message: `Slide ${target} is not available.` };
        }
        setViewingSlideId(String(target));
        setIsLiveMode(false);
        return { ok: true, message: `Moved to slide ${target}.` };
      }

      if (name === "select_slide") {
        if (mode !== "presentation") {
          return { ok: false, message: "select_slide is only available on presentation page." };
        }
        const { slideList: latestSlideList } = voiceStateRef.current;
        if (!Array.isArray(latestSlideList) || latestSlideList.length === 0) {
          return { ok: false, message: "No slide pages are available for the current topic." };
        }
        const rawTarget = args.slide_number ?? args.page_number ?? args.slide ?? args.page ?? args.position;
        const rawLabel = String(rawTarget ?? "").trim().toLowerCase();
        let target;
        if (rawLabel === "first") {
          target = latestSlideList[0];
        } else if (rawLabel === "last") {
          target = latestSlideList[latestSlideList.length - 1];
        } else {
          const directTarget = Number(rawTarget);
          if (!Number.isFinite(directTarget)) {
            return { ok: false, message: "slide_number is required (or use first/last)." };
          }
          target = Math.trunc(directTarget);
        }
        if (!latestSlideList.includes(target)) {
          return { ok: false, message: `Slide ${target} is not available.` };
        }
        setViewingSlideId(String(target));
        setIsLiveMode(false);
        return { ok: true, message: `Moved to slide ${target}.` };
      }

      if (name === "list_slide_languages") {
        const displayOptions = getDisplayLanguageOptions();
        return {
          ok: true,
          message: "Slide display and narration languages can be changed.",
          data: {
            narration_current_language: listenLang,
            display_current_language: viewLang,
            narration_available_languages: availableVoiceLanguages.map((code) => ({ code, name: getAudioLangName(code) })),
            display_available_languages: displayOptions.map((code) => ({ code, name: getTextLangName(code) })),
          },
        };
      }

      if (name === "toggle_live_mode") {
        if (mode !== "presentation") {
          return { ok: false, message: "toggle_live_mode is only available on presentation page." };
        }
        const targetMode = String(args.mode || "toggle").toLowerCase();
        if (targetMode === "live" && !isLiveMode) {
          setViewingPptId(livePptId);
          setViewingSlideId(liveSlideId);
          setIsLiveMode(true);
        } else if (targetMode === "manual" && isLiveMode) {
          setIsLiveMode(false);
        } else if (targetMode === "toggle") {
          toggleLiveMode();
        }
        const nextMode = targetMode === "toggle" ? !isLiveMode : targetMode === "manual" ? false : true;
        return { ok: true, message: nextMode ? "Switched to LIVE mode." : "Switched to manual mode." };
      }

      if (name === "playback_control") {
        if (mode !== "presentation") {
          return { ok: false, message: "playback_control is only available on presentation page." };
        }
        const action = String(args.action || "play_pause").toLowerCase();
        if (action === "start") {
          startNarration({ restart: false });
          return { ok: true, message: "Started narration." };
        }
        if (action === "pause") {
          pauseNarration();
          return { ok: true, message: "Paused narration." };
        }
        if (action === "play_pause") {
          togglePlay();
          return { ok: true, message: "Toggled narration playback." };
        }
        if (action === "restart") {
          narrateCurrentSlide();
          return { ok: true, message: "Restarted narration from the current slide." };
        }
        if (action === "seek") {
          const seconds = Number(args.seconds);
          if (!Number.isFinite(seconds) || seconds === 0) {
            return { ok: false, message: "For seek, provide a non-zero seconds value." };
          }
          seekAudio(seconds);
          return { ok: true, message: `Seeked narration by ${Math.trunc(seconds)} seconds.` };
        }
        if (action === "seek_to") {
          const targetTime = Number(args.position_seconds ?? args.seconds);
          if (!Number.isFinite(targetTime) || targetTime < 0) {
            return { ok: false, message: "For seek_to, provide position_seconds >= 0." };
          }
          if (!Number.isFinite(audioDuration) || audioDuration <= 0) {
            return { ok: false, message: "Cannot seek to position because narration duration is unavailable." };
          }
          const clamped = Math.min(targetTime, audioDuration);
          audioRef.current.currentTime = clamped;
          setAudioCurrentTime(clamped);
          return { ok: true, message: `Moved narration position to ${Math.round(clamped)} seconds.` };
        }
        if (action === "jump_start") {
          jumpToAudioStart();
          return { ok: true, message: "Jumped narration to start." };
        }
        return { ok: false, message: "Unsupported playback action." };
      }

      if (name === "set_read_aloud") {
        if (mode !== "presentation") {
          return { ok: false, message: "set_read_aloud is only available on presentation page." };
        }
        const modeArg = String(args.mode || "").toLowerCase();
        let nextValue = autoplay;
        if (modeArg === "toggle") {
          nextValue = !autoplay;
        } else if (modeArg === "on") {
          nextValue = true;
        } else if (modeArg === "off") {
          nextValue = false;
        } else {
          const parsed = parseBooleanArg(args.enabled);
          if (parsed === null) {
            return { ok: false, message: "Provide mode (on/off/toggle) or enabled boolean." };
          }
          nextValue = parsed;
        }
        setAutoplay(nextValue);
        return { ok: true, message: `Autoplay is now ${nextValue ? "on" : "off"}.` };
      }

      if (name === "set_fullscreen_mode") {
        if (mode !== "presentation") {
          return { ok: false, message: "set_fullscreen_mode is only available on presentation page." };
        }
        const modeArg = String(args.mode || "toggle").toLowerCase();
        if (modeArg !== "open" && modeArg !== "close" && modeArg !== "toggle") {
          return { ok: false, message: "mode must be open, close, or toggle." };
        }
        const nextValue = modeArg === "toggle" ? !isFullScreen : modeArg === "open";
        setIsFullScreen(nextValue);
        return { ok: true, message: nextValue ? "Opened full-screen slide view." : "Closed full-screen slide view." };
      }

      if (name === "change_display_language") {
        if (mode !== "presentation") {
          return { ok: false, message: "change_display_language is only available on presentation page." };
        }
        const requestedLanguage = String(args.language || "").trim();
        if (requestedLanguage) {
          const normalized = normalizeDisplayLanguageCode(requestedLanguage);
          if (!normalized) {
            return { ok: false, message: `Unsupported display language: ${requestedLanguage}` };
          }
          setViewLang(normalized);
          return { ok: true, message: `Display language changed to ${getTextLangName(normalized)}.` };
        }
        const direction = String(args.direction || "next").toLowerCase();
        const step = direction === "previous" ? -1 : 1;
        const displayOptions = getDisplayLanguageOptions();
        const currentIndex = displayOptions.indexOf(viewLang);
        const baseIndex = currentIndex === -1 ? 0 : currentIndex;
        const nextLanguage = displayOptions[(baseIndex + step + displayOptions.length) % displayOptions.length] || viewLang;
        setViewLang(nextLanguage);
        return { ok: true, message: `Display language changed to ${getTextLangName(nextLanguage)}.` };
      }

      if (name === "change_narration_language") {
        if (mode !== "presentation") {
          return { ok: false, message: "Narration language change is only available on presentation page." };
        }
        const requestedLanguage = String(args.language || "").trim();
        if (requestedLanguage) {
          const normalized = normalizeVoiceLanguageCode(requestedLanguage);
          if (!normalized) {
            return { ok: false, message: `Unsupported narration language: ${requestedLanguage}` };
          }
          applyMp3LanguageChange(normalized);
          return { ok: true, message: `Narration language changed to ${getAudioLangName(normalized)}.` };
        }
        const direction = String(args.direction || "next").toLowerCase();
        const step = direction === "previous" ? -1 : 1;
        const current = normalizeVoiceLanguageCode(listenLang) || "en-US";
        const nextLanguage = cycleLanguage(current, step);
        applyMp3LanguageChange(nextLanguage);
        return { ok: true, message: `Narration language changed to ${getAudioLangName(nextLanguage)}.` };
      }

      if (name === "list_shortcuts") {
        return {
          ok: true,
          message: mode === "class_selection"
            ? "Shortcut: M to start/stop voice."
            : "Shortcuts: Left/Right slide, Space play/pause, L live/manual, R restart narration, A/D seek, Home jump start, Alt+V display language, Alt+A narration language, M voice start/stop, click slide to open full-screen.",
        };
      }

      if (name === "help_commands") {
        return {
          ok: true,
          message: mode === "class_selection"
            ? "Try: list available courses, open class by class id, list slide languages, or list shortcuts."
            : "Try: list slide pages, get current slide content, list presentations, get slide range, jump to last slide, set read aloud off, playback control seek_to position 90, set fullscreen mode open, or list shortcuts.",
        };
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
              const blockedKeys = new Set([" ", "spacebar", "r", "a", "d", "home"]);
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
              const nextLanguage = cycleLanguage(normalizeVoiceLanguageCode(listenLang) || "en-US", event.shiftKey ? -1 : 1);
              applyMp3LanguageChange(nextLanguage);
          }
      };

      window.addEventListener("keydown", onKeyDown);
      return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullScreen, livePptId, liveSlideId, viewLang, listenLang, isLiveMode, viewingSlideId, viewingPptId, slideData, liveData, slideList, togglePlay, narrateCurrentSlide, stopNarration, seekAudio, jumpToAudioStart, handlePrev, handleNext, toggleLiveMode, activeAudioUrl, isPlaying, isListening, voiceBusy]);

  if (!hasClassParam && !isAdminIndexPage && !isAdminPage && !isTeacherPage) {
    return (
      <ClassSelectionPage
        currentUser={currentUser}
        teacherEnabled={teacherEnabled}
        adminEnabled={adminEnabled}
        handleSignOut={handleSignOut}
        handleSignIn={handleSignIn}
        UserIcon={UserIcon}
        authStatus={authStatus}
        studentStatus={studentStatus}
        studentLoading={studentLoading}
        studentClasses={studentClasses}
        loadStudentClasses={loadStudentClasses}
        enrollAndOpenClass={enrollAndOpenClass}
        canUseVoiceChat={canRenderVoiceAssistant(currentUser, voiceAccessGranted, voicePlatformBlockReason, voiceStatus)}
        voiceStatus={voiceStatus}
        voiceAccessLoading={voiceAccessLoading}
        isListening={isListening}
        voiceBusy={voiceBusy}
        voiceTranscript={voiceTranscript}
        voiceAnswer={voiceAnswer}
        startVoiceCapture={startVoiceCapture}
        stopVoiceCapture={stopVoiceCapture}
        MicIcon={MicIcon}
      />
    );
  }

  if (hasClassParam && !isAdminIndexPage && !isAdminPage && !isTeacherPage && !currentUser) {
    return (
      <div className="container" style={{ padding: "24px" }}>
        <h2 style={{ marginBottom: "10px" }}>Sign in required</h2>
        <p style={{ color: "#4b5563", marginBottom: "12px" }}>Only public classes, enrolled students, class teacher, and admins can open this class.</p>
        <div className="controls">
          <button type="button" className="account-action-btn" onClick={handleSignIn}>
            <UserIcon />
            <span>Sign in</span>
          </button>
          <button
            type="button"
            className="account-action-btn account-action-icon-btn header-home-btn"
            onClick={() => { window.location.href = "/"; }}
            aria-label="Go to home page"
            title="Home"
          >
            <HomeIcon />
          </button>
        </div>
      </div>
    );
  }

  if (hasClassParam && !isAdminIndexPage && !isAdminPage && !isTeacherPage && classAccessLoading) {
    return (
      <div className="splash-screen">
        <h1>LangBridge</h1>
        <p>Checking class access...</p>
      </div>
    );
  }

  if (hasClassParam && !isAdminIndexPage && !isAdminPage && !isTeacherPage && classAccessDeniedMessage) {
    return (
      <div className="container" style={{ padding: "24px" }}>
        <h2 style={{ marginBottom: "10px" }}>Class access denied</h2>
        <p style={{ color: "#b91c1c", marginBottom: "12px" }}>{classAccessDeniedMessage}</p>
        <p style={{ color: "#4b5563", marginBottom: "12px" }}>Only public classes, enrolled students, class teacher, and admins can open this class.</p>
        <div className="controls">
          <button
            type="button"
            className="account-action-btn account-action-icon-btn"
            onClick={() => { window.location.href = "/"; }}
            aria-label="Go to home page"
            title="Home"
          >
            <HomeIcon />
          </button>
        </div>
      </div>
    );
  }

  if (!isReady && !isAdminIndexPage && !isAdminPage && !isTeacherPage) {
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
  const narrativeText = tutorAnswerText || displayText;

  const currentNum = parseInt(viewingSlideId, 10);
  const hasPrev = slideList.length > 0 && slideList.indexOf(currentNum) > 0;
  const hasNext = slideList.length > 0 && slideList.indexOf(currentNum) < slideList.length - 1;
  const readAloudLabel = autoplay ? "Autoplay: On" : "Autoplay: Off";
  const canUseVoiceChat = canRenderVoiceAssistant(currentUser, voiceAccessGranted, voicePlatformBlockReason, voiceStatus);
  const activeClass = studentClasses.find((row) => String(row.class_id || "") === String(courseId)) || null;
  const activeCourseLabel = activeClass?.course_title || activeClass?.course_id || "-";
  const backToSlidesHref = searchParams.toString() ? `/?${searchParams.toString()}` : "/";
  const ADMIN_PAGE_SIZE = 20;
  const userQuery = adminUserQuery.trim().toLowerCase();
  const settingsQuery = adminSettingsQuery.trim().toLowerCase();
  const logQuery = adminLogQuery.trim().toLowerCase();
  const filteredVoiceUsers = adminVoiceUsers.filter((user) => {
    const haystack = `${user.value || ""} ${user.type || ""} ${user.note || ""}`.toLowerCase();
    return !userQuery || haystack.includes(userQuery);
  });
  const filteredTextUsers = adminTextUsers.filter((user) => {
    const haystack = `${user.value || ""} ${user.type || ""} ${user.note || ""}`.toLowerCase();
    return !userQuery || haystack.includes(userQuery);
  });
  const filteredTopUsage = adminTopUsage.filter((row) => {
    const haystack = `${row.email || ""} ${row.uid || ""}`.toLowerCase();
    return !userQuery || haystack.includes(userQuery);
  });
  const filteredUserSettings = adminUserSettings.filter((row) => {
    const haystack = `${row.email || ""} ${row.uid || ""} ${row.display_language || ""} ${row.audio_language || ""} ${row.course_id || ""} ${row.presentation_id || ""}`.toLowerCase();
    return !settingsQuery || haystack.includes(settingsQuery);
  });
  const filteredUsageLogs = adminUsageLogs.filter((log) => {
    const haystack = `${log.email || ""} ${log.uid || ""} ${log.session_id || ""} ${log.ended_reason || ""}`.toLowerCase();
    return !logQuery || haystack.includes(logQuery);
  });
  const userPageCount = Math.max(1, Math.ceil(filteredVoiceUsers.length / ADMIN_PAGE_SIZE));
  const settingsPageCount = Math.max(1, Math.ceil(filteredUserSettings.length / ADMIN_PAGE_SIZE));
  const usagePageCount = Math.max(1, Math.ceil(filteredTopUsage.length / ADMIN_PAGE_SIZE));
  const logsPageCount = Math.max(1, Math.ceil(filteredUsageLogs.length / ADMIN_PAGE_SIZE));
  const userStart = (Math.min(adminUsersPage, userPageCount) - 1) * ADMIN_PAGE_SIZE;
  const settingsStart = (Math.min(adminSettingsPage, settingsPageCount) - 1) * ADMIN_PAGE_SIZE;
  const usageStart = (Math.min(adminUsagePage, usagePageCount) - 1) * ADMIN_PAGE_SIZE;
  const logsStart = (Math.min(adminLogsPage, logsPageCount) - 1) * ADMIN_PAGE_SIZE;
  const pagedVoiceUsers = filteredVoiceUsers.slice(userStart, userStart + ADMIN_PAGE_SIZE);
  const pagedUserSettings = filteredUserSettings.slice(settingsStart, settingsStart + ADMIN_PAGE_SIZE);
  const pagedTopUsage = filteredTopUsage.slice(usageStart, usageStart + ADMIN_PAGE_SIZE);
  const pagedUsageLogs = filteredUsageLogs.slice(logsStart, logsStart + ADMIN_PAGE_SIZE);

  if (isTeacherPage) {
    return (
      <TeacherWorkspacePage
        currentUser={currentUser}
        teacherEnabled={teacherEnabled}
        teacherLoading={teacherLoading}
        teacherStatus={teacherStatus}
        teacherCourses={teacherCourses}
        teacherClasses={teacherClasses}
        teacherCourseTitle={teacherCourseTitle}
        setTeacherCourseTitle={setTeacherCourseTitle}
        teacherCourseLanguages={teacherCourseLanguages}
        setTeacherCourseLanguages={setTeacherCourseLanguages}
        teacherCloneCourseId={teacherCloneCourseId}
        setTeacherCloneCourseId={setTeacherCloneCourseId}
        teacherCloneClassTitle={teacherCloneClassTitle}
        setTeacherCloneClassTitle={setTeacherCloneClassTitle}
        teacherClassIsPublic={teacherClassIsPublic}
        setTeacherClassIsPublic={setTeacherClassIsPublic}
        teacherPackageBucket={teacherPackageBucket}
        setTeacherPackageBucket={setTeacherPackageBucket}
        teacherPackagePrefix={teacherPackagePrefix}
        setTeacherPackagePrefix={setTeacherPackagePrefix}
        teacherPackageManifestUrl={teacherPackageManifestUrl}
        setTeacherPackageManifestUrl={setTeacherPackageManifestUrl}
        teacherUploadFilePaths={teacherUploadFilePaths}
        setTeacherUploadFilePaths={setTeacherUploadFilePaths}
        teacherUploadUrls={teacherUploadUrls}
        createTeacherCourse={createTeacherCourse}
        cloneTeacherClass={cloneTeacherClass}
        linkTeacherCoursePackage={linkTeacherCoursePackage}
        createClassFromPackage={createClassFromPackage}
        createTeacherUploadSession={createTeacherUploadSession}
        updateTeacherCourseTitle={updateTeacherCourseTitle}
        loadTeacherWorkspace={loadTeacherWorkspace}
        handleSignOut={handleSignOut}
        handleSignIn={handleSignIn}
        UserIcon={UserIcon}
        authStatus={authStatus}
      />
    );
  }

  if (isAdminIndexPage) {
    return (
      <AdminIndexPage
        currentUser={currentUser}
        adminEnabled={adminEnabled}
        handleSignOut={handleSignOut}
        handleSignIn={handleSignIn}
        UserIcon={UserIcon}
        authStatus={authStatus}
      />
    );
  }

  if (isAdminPage) {
    return (
      <VoiceAdminPage
        currentUser={currentUser}
        adminEnabled={adminEnabled}
        handleSignOut={handleSignOut}
        handleSignIn={handleSignIn}
        UserIcon={UserIcon}
        authStatus={authStatus}
        backToSlidesHref={backToSlidesHref}
        adminLoading={adminLoading}
        adminStatus={adminStatus}
        adminSummary={adminSummary}
        loadAllAdminData={() => { loadAdminDashboard(); loadAdminTeachers(); loadTeacherRecords(); }}
        adminTeacherEmail={adminTeacherEmail}
        setAdminTeacherEmail={setAdminTeacherEmail}
        grantTeacherUser={grantTeacherUser}
        adminTeachers={adminTeachers}
        revokeTeacherUser={revokeTeacherUser}
        adminGrantEmail={adminGrantEmail}
        setAdminGrantEmail={setAdminGrantEmail}
        adminTextGrantEmail={adminTextGrantEmail}
        setAdminTextGrantEmail={setAdminTextGrantEmail}
        grantVoiceUser={grantVoiceUser}
        grantTextUser={grantTextUser}
        textWeeklyBudgetUsd={textWeeklyBudgetUsd}
        setTextWeeklyBudgetUsd={setTextWeeklyBudgetUsd}
        saveTextBudget={saveTextBudget}
        adminUserQuery={adminUserQuery}
        setAdminUserQuery={(value) => { setAdminUserQuery(value); setAdminUsersPage(1); setAdminUsagePage(1); }}
        adminUsersPage={adminUsersPage}
        setAdminUsersPage={setAdminUsersPage}
        userPageCount={userPageCount}
        filteredVoiceUsers={filteredVoiceUsers}
        pagedVoiceUsers={pagedVoiceUsers}
        revokeVoiceUser={revokeVoiceUser}
        filteredTextUsers={filteredTextUsers}
        revokeTextUser={revokeTextUser}
        pagedTopUsage={pagedTopUsage}
        adminUsagePage={adminUsagePage}
        setAdminUsagePage={setAdminUsagePage}
        usagePageCount={usagePageCount}
        adminSettingsQuery={adminSettingsQuery}
        setAdminSettingsQuery={setAdminSettingsQuery}
        filteredUserSettings={filteredUserSettings}
        pagedUserSettings={pagedUserSettings}
        adminSettingsPage={adminSettingsPage}
        setAdminSettingsPage={setAdminSettingsPage}
        settingsPageCount={settingsPageCount}
        adminLogQuery={adminLogQuery}
        setAdminLogQuery={setAdminLogQuery}
        filteredUsageLogs={filteredUsageLogs}
        pagedUsageLogs={pagedUsageLogs}
        adminLogsPage={adminLogsPage}
        setAdminLogsPage={setAdminLogsPage}
        logsPageCount={logsPageCount}
      />
    );
  }

  return (
    <div className="container single-slide-view" style={{ "--reader-font-size": `${readerFontSize}px` }}>
      {isFullScreen && (
          <FullScreenSlide 
              slideUrl={visualUrl} 
              text={narrativeText}
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
            <div className="status header-live-status" style={{ color: status.color }}>{status.text}</div>
            <div className="lang-select header-display-lang" title="Display Language">
                <span className="lang-select-icon">🌐</span>
                <select 
                    value={viewLang} 
                    onChange={(e) => setViewLang(e.target.value)}
                >
                    {supportedLangs.map(lang => <option key={lang} value={lang}>{getTextLangName(lang)}</option>)}
                </select>
            </div>
            <div className="lang-select header-audio-lang" title="Narration Language">
                <span className="lang-select-icon">🔊</span>
                <select
                    value={normalizeVoiceLanguageCode(listenLang) || "en-US"}
                    onChange={(e) => applyMp3LanguageChange(e.target.value)}
                >
                    {availableVoiceLanguages.map(lang => <option key={lang} value={lang}>{getAudioLangName(lang)}</option>)}
                </select>
            </div>
            <button
              type="button"
              className="account-action-btn header-font-dec header-font-btn"
              onClick={() => setReaderFontSize((prev) => Math.max(16, prev - 2))}
              aria-label="Decrease text size"
              title="Text size down"
            >
              A-
            </button>
            <button
              type="button"
              className="account-action-btn header-font-inc header-font-btn"
              onClick={() => setReaderFontSize((prev) => Math.min(26, prev + 2))}
              aria-label="Increase text size"
              title="Text size up"
            >
              A+
            </button>
            <button
              type="button"
              className="account-action-btn account-action-icon-btn header-home-btn"
              onClick={() => { window.location.href = "/"; }}
              aria-label="Go to home page"
              title="Home"
            >
              <HomeIcon />
            </button>
            <button
              type="button"
              className={`account-action-btn header-auth-btn ${currentUser ? "account-action-icon-btn" : ""}`.trim()}
              onClick={currentUser ? handleSignOut : handleSignIn}
              aria-label={currentUser ? "Sign out" : "Sign in"}
              title={currentUser ? "Sign out" : "Sign in"}
            >
              {currentUser ? <SignOutIcon /> : <UserIcon />}
              {!currentUser && <span>Sign in</span>}
            </button>
                            </div>
                        </header>      
      <div className="main-stage">
          <div
            className="slide-container"
            onClick={handleSlideOpenFullScreen}
            onPointerDown={handleSlidePointerDown}
            onPointerUp={handleSlidePointerUp}
            onPointerCancel={handleSlidePointerCancel}
          >
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
                 {narrativeText}
             </div>
          </div>
      </div>
      <div className="sub-header">
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
          <span className="compact-status-line">Narration: {narrationStatus}</span>
        </div>
        <div className="nav-controls">
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
        </div>
      </div>
      <div className="identity-course-row" aria-label="Current account and course">
        <div className="identity-course-main">
          <span><strong>Course:</strong> {activeCourseLabel}</span>
          <div className="narration-controls">
            <button
             className={`narration-btn ${autoplay ? 'active' : ''}`}
             title="Automatically play new narration"
             onClick={() => {
               setAutoplay((prev) => !prev);
             }}
            >
             {readAloudLabel}
            </button>
            <button className="narration-btn" title="Restart from beginning (R)" onClick={narrateCurrentSlide}>
             Restart
            </button>
          </div>
        </div>
        <div className="identity-quick-actions">
          <button
           type="button"
           className="identity-tutor-toggle"
           onClick={() => setIsTutorVisible((prev) => !prev)}
           aria-label={isTutorVisible ? "Hide tutor panel" : "Show tutor panel"}
          >
           {isTutorVisible ? "Hide Tutor" : "Show Tutor"}
          </button>
          <details className="identity-shortcuts">
           <summary>Shortcuts</summary>
           <div className="identity-shortcuts-body">
             <div>Keys: Alt+V/A language · ←/→ slides · L live/manual · Space play/pause · R restart · A/D seek (Shift=30s) · Home start · Esc close</div>
             <div>{isListening ? "Voice chat active: player shortcuts are blocked." : "Voice: M start/stop · open class · select presentation · next/previous slide."}</div>
           </div>
          </details>
        </div>
      </div>
      <VoiceAssistantCard
        canUseVoiceChat={canUseVoiceChat}
        voiceStatus={voiceStatus}
        voiceAccessLoading={voiceAccessLoading}
        isListening={isListening}
        voiceBusy={voiceBusy}
        startVoiceCapture={startVoiceCapture}
        stopVoiceCapture={stopVoiceCapture}
        MicIcon={MicIcon}
        voiceTranscript={voiceTranscript}
        voiceAnswer={voiceAnswer}
      />
      <Live2DTutor
        audioElement={audioRef.current}
        isVisible={isTutorVisible}
        assistantMode={isListening}
        assistantSpeaking={assistantSpeaking}
        questionEnabled={Boolean(textChatAccessGranted && !textChatAccessLoading)}
        questionBusy={tutorBusy}
        questionStatus={tutorStatus}
        chatHistory={tutorChatHistory}
        canReplayTts={Boolean(tutorAudioUrl)}
        onReplayTts={replayTutorTts}
        onClearChat={clearTutorChatHistory}
        onRegenerate={regenerateTutorAnswer}
        onStopSpeech={stopTutorSpeech}
        onExportChat={exportTutorChat}
        questionLanguage={listenLang}
        onSubmitQuestion={askTutorByText}
      />
    </div>
  );
}

export default App;