import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { doc, onSnapshot, collection, query, orderBy, limitToLast } from "firebase/firestore";
import { db } from "./firebase";

// Icons
const PlayIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 3l14 9-14 9V3z" />
    </svg>
);

const PauseIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <rect x="6" y="4" width="4" height="16" rx="1" />
        <rect x="14" y="4" width="4" height="16" rx="1" />
    </svg>
);

function App() {
  const [searchParams] = useSearchParams();
  const courseId = searchParams.get('class') || searchParams.get('courseId') || 'current';
  
  const [status, setStatus] = useState({ text: "🟡 Connecting...", color: "orange" });
  const [currentLang, setCurrentLang] = useState('en');
  const [messages, setMessages] = useState([]);
  const [supportedLangs, setSupportedLangs] = useState([]);
  
  // Accessibility
  const [fontSize, setFontSize] = useState(1.1); // Default rem value

  // Audio State
  const [isPlaying, setIsPlaying] = useState(false);
  const [playingMsgId, setPlayingMsgId] = useState(null);
  const [playlist, setPlaylist] = useState([]); // Array of msg objects to play
  const [autoplay, setAutoplay] = useState(true);
  const [isReady, setIsReady] = useState(false); // User has clicked "Join"

  // Refs
  const audioRef = useRef(new Audio());
  const latestMsgIdRef = useRef(null); 

  const LANGUAGE_NAMES = {
    "en": "English",
    "en-US": "English (US)",
    "zh": "Chinese (中文)",
    "zh-CN": "Mandarin (简体中文)",
    "cmn-CN": "Mandarin (简体中文)",
    "zh-TW": "Mandarin (繁體中文)",
    "yue": "Cantonese (Gwong2 dung1 waa2)",
    "yue-HK": "Cantonese (香港)",
    "es": "Spanish (Español)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)"
  };

  const getLangName = (code) => LANGUAGE_NAMES[code] || code;

  // Font Size Handlers
  const increaseFont = () => setFontSize(prev => Math.min(prev + 0.2, 3.0));
  const decreaseFont = () => setFontSize(prev => Math.max(prev - 0.2, 0.8));

  // Helper to extract data for current language
  const getLangData = (data, lang) => {
    if (!data.languages) return null;
    let langData = data.languages[lang];
    if (!langData) {
        const match = Object.keys(data.languages).find(k => k.startsWith(lang) || lang.startsWith(k));
        if (match) langData = data.languages[match];
    }
    return langData;
  };

  // --- Audio Player Logic ---

  const playMessage = (msg, clearQueue = true) => {
    if (clearQueue) setPlaylist([]); 
    
    const langData = getLangData(msg, currentLang);
    if (langData && langData.audio_url) {
        setPlayingMsgId(msg.id);
        audioRef.current.src = langData.audio_url;
        audioRef.current.play()
            .then(() => setIsPlaying(true))
            .catch(e => {
                console.error("Playback failed", e);
                setIsPlaying(false);
                setPlayingMsgId(null);
            });
    }
  };

 

  // Audio Event Listeners
  useEffect(() => {
    const handleEnded = () => {
        setIsPlaying(false);
        setPlayingMsgId(null);
        
        if (playlist.length > 0) {
            const [next, ...rest] = playlist;
            setPlaylist(rest);
            playMessage(next, false);
        }
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    const audio = audioRef.current;
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);

    return () => {
        audio.removeEventListener('ended', handleEnded);
        audio.removeEventListener('play', handlePlay);
        audio.removeEventListener('pause', handlePause);
    };
  }, [playlist, currentLang]); // Depend on currentLang so next play uses correct language URL

  // --- Firestore Listeners ---

  // 1. Metadata
  useEffect(() => {
    if (!isReady) return;

    const unsubscribe = onSnapshot(doc(db, "presentation_broadcast", courseId), (docSnapshot) => {
      if (docSnapshot.exists()) {
        setStatus({ text: "🟢 Live", color: "green" });
        const data = docSnapshot.data();
        
        let langs = [];
        if (data.supported_languages && Array.isArray(data.supported_languages)) {
            langs = data.supported_languages;
        } else if (data.languages) {
            langs = Object.keys(data.languages);
        }
        if (langs.length > 0) setSupportedLangs(langs);
      } else {
          setStatus({ text: "🟡 Waiting...", color: "orange" });
      }
    });
    return () => unsubscribe();
  }, [courseId, isReady]);

  // 2. Messages
  useEffect(() => {
    if (!isReady) return;

    // Get messages sorted by time (Oldest -> Newest)
    const messagesRef = collection(db, "presentation_broadcast", courseId, "messages");
    const q = query(messagesRef, orderBy("updated_at", "asc"), limitToLast(100));

    const unsubscribe = onSnapshot(q, (snapshot) => {
      // Sort manually to be safe (though query should handle it)
      const msgs = snapshot.docs
        .map(doc => ({ id: doc.id, ...doc.data() }))
        .sort((a, b) => (a.updated_at?.seconds || 0) - (b.updated_at?.seconds || 0));

      setMessages(msgs);

      // Autoplay New Messages
      if (msgs.length > 0) {
          const lastMsg = msgs[msgs.length - 1];
          
          if (latestMsgIdRef.current !== lastMsg.id) {
              latestMsgIdRef.current = lastMsg.id;
              if (autoplay) {
                  playMessage(lastMsg, true);
              }
          }
      }
    });

    return () => unsubscribe();
  }, [courseId, currentLang, autoplay, isReady]); // Re-bind if params change

  // Display Order: Newest First
  const displayMessages = [...messages].reverse();

  if (!isReady) {
      return (
          <div className="splash-screen">
              <h1>LangBridge Student Client</h1>
              <button onClick={() => setIsReady(true)}>Join Class</button>
          </div>
      );
  }

  return (
    <div className="container">
      <header>
        <h1>🎓 LangBridge</h1>
        <div className="controls">
            <div className="status" style={{ color: status.color }}>{status.text}</div>
            <select value={currentLang} onChange={(e) => setCurrentLang(e.target.value)}>
                {supportedLangs.length > 0 ? (
                    supportedLangs.map(lang => <option key={lang} value={lang}>{getLangName(lang)}</option>)
                ) : (
                    <>
                        <option value="en">English</option>
                        <option value="zh">Chinese</option>
                    </>
                )}
            </select>
        </div>
      </header>
      
      <div className="sub-header">
        <label className="autoplay-toggle">
            <input 
            type="checkbox" 
            checked={autoplay} 
            onChange={(e) => setAutoplay(e.target.checked)} 
            /> 
            <span>Autoplay</span>
        </label>
        
        <div className="font-controls">
            <span className="font-label">Size:</span>
            <button className="font-btn" onClick={decreaseFont} title="Decrease Font">A-</button>
            <button className="font-btn" onClick={increaseFont} title="Increase Font">A+</button>
        </div>
      </div>

      <div className="chat-area">
        {displayMessages.length === 0 && (
           <div className="empty-state">Waiting for presentation...</div>
        )}
        {displayMessages.map((msg) => {
          const langData = getLangData(msg, currentLang);
          const hasAudio = langData && langData.audio_url;
          const isCurrentPlaying = playingMsgId === msg.id;

          return (
            <div key={msg.id} className="chat-message">
              <div 
                className={`message-bubble ${isCurrentPlaying ? 'playing' : ''}`}
                style={{ fontSize: `${fontSize}rem` }}
              >
                <div className="message-content">
                    {langData ? langData.text : <span className="missing-lang">(Translating...)</span>}
                </div>
                {hasAudio && (
                    <button 
                        className="msg-play-btn" 
                        onClick={() => {
                            if (isCurrentPlaying && isPlaying) {
                                audioRef.current.pause();
                            } else {
                                playMessage(msg);
                            }
                        }}
                    >
                        {isCurrentPlaying && isPlaying ? <PauseIcon /> : <PlayIcon />}
                    </button>
                )}
              </div>
              {msg.original_context && (
                 <div className="original-context">
                   {msg.original_context.substring(0, 80)}{msg.original_context.length > 80 ? "..." : ""}
                 </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default App;