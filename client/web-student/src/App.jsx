import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { doc, onSnapshot, collection, query, orderBy, limitToLast } from "firebase/firestore";
import { db } from "./firebase";

// Icons
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

const FullScreenSlide = ({ msg, langData, onClose, onTogglePlay, isPlaying, isCurrentPlaying, onNext, onPrev, hasNext, hasPrev }) => {
    const [isSubtitleHidden, setIsSubtitleHidden] = useState(false);

    if (!msg || !langData) return null;

    const toggleSubtitle = (e) => {
        e.stopPropagation(); // Prevent toggling play/pause when clicking the subtitle button
        setIsSubtitleHidden(prev => !prev);
    };

    return (
        <div className="fullscreen-overlay" onClick={onTogglePlay}>
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

            <div className="fullscreen-content">
                {langData.slide_link ? (
                    <img 
                        src={langData.slide_link} 
                        alt={`Slide ${msg.page_number}`} 
                        className="fullscreen-image" 
                    />
                ) : (
                    <div className="fullscreen-placeholder">
                        <span>No Slide Image</span>
                    </div>
                )}
                
                <div className="fullscreen-controls">
                    {isCurrentPlaying && isPlaying ? (
                        <div className="play-indicator"><PauseIcon /></div>
                    ) : (
                        <div className="play-indicator"><PlayIcon /></div>
                    )}
                </div>

                <div className={`fullscreen-subtitle ${isSubtitleHidden ? 'hidden' : ''}`}>
                    <p>{langData.text}</p>
                    <button className="toggle-subtitle-btn" onClick={toggleSubtitle}>
                        {isSubtitleHidden ? <ShowSubtitleIcon /> : <HideSubtitleIcon />}
                    </button>
                </div>
            </div>
        </div>
    );
};

function App() {
  const [searchParams] = useSearchParams();
  const courseId = searchParams.get('class') || searchParams.get('courseId') || 'current';
  
  const [status, setStatus] = useState({ text: "🟡 Connecting...", color: "orange" });
  const [currentLang, setCurrentLang] = useState('en');
  const [messages, setMessages] = useState([]);
  const [supportedLangs, setSupportedLangs] = useState([]);
  const [pptFilter, setPptFilter] = useState('');
  const [currentPptFile, setCurrentPptFile] = useState('');
  const [currentSlideNumber, setCurrentSlideNumber] = useState('');
  const [isAutoFilter, setIsAutoFilter] = useState(true);
  
  // Accessibility
  const [fontSize, setFontSize] = useState(1.1); // Default rem value

  // Audio State
  const [isPlaying, setIsPlaying] = useState(false);
  const [playingMsgId, setPlayingMsgId] = useState(null);
  const [playlist, setPlaylist] = useState([]); // Array of msg objects to play
  const [autoplay, setAutoplay] = useState(true);
  const [isReady, setIsReady] = useState(false); // User has clicked "Join"
  
  // Full Screen State
  const [fullScreenMsg, setFullScreenMsg] = useState(null);

  // Refs
  const audioRef = useRef(new Audio());
  const latestMsgIdRef = useRef(null); 
    const parentLastMsgIdRef = useRef(null);

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

  const togglePlay = (msg) => {
      const isCurrent = playingMsgId === msg.id;
      if (isCurrent && isPlaying) {
          audioRef.current.pause();
      } else {
          playMessage(msg);
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

    // 1b. React to parent doc's `last_message_id` changes and move that message to top
    useEffect(() => {
        if (!isReady) return;

        const unsub = onSnapshot(doc(db, "presentation_broadcast", courseId), (docSnapshot) => {
            if (!docSnapshot.exists()) return;
            const data = docSnapshot.data();
            const lastId = data && data.last_message_id;
            if (!lastId) return;

            // If last_message_id changed, reorder local messages so that the referenced
            // message appears as the most recent (end of the chronological array).
            if (parentLastMsgIdRef.current !== lastId) {
                parentLastMsgIdRef.current = lastId;
                setMessages(prev => {
                    const idx = prev.findIndex(m => m.id === lastId);
                    if (idx === -1) return prev; // message not yet in local cache
                    // Move the message to the end of the array (newest)
                    const item = prev[idx];
                    const rest = [...prev.slice(0, idx), ...prev.slice(idx + 1)];
                    return [...rest, item];
                });
            }
        });

        return () => unsub();
    }, [courseId, isReady]);

  // 2. Messages
  useEffect(() => {
    if (!isReady) return;

    // Get messages sorted by time (Oldest -> Newest)
    const messagesRef = collection(db, "presentation_broadcast", courseId, "messages");
    const q = query(messagesRef, orderBy("updated_at", "asc"), limitToLast(100));

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const msgs = snapshot.docs
        .map(doc => ({ id: doc.id, ...doc.data() }))
        .sort((a, b) => (a.updated_at?.seconds || 0) - (b.updated_at?.seconds || 0));

      setMessages(msgs);
    });

    return () => unsubscribe();
  }, [courseId, isReady]);

  // 3. React to New Messages (Autoplay & Follow Presenter)
  useEffect(() => {
      if (messages.length > 0) {
          const lastMsg = messages[messages.length - 1];
          
          // Always update current tracking info
          setCurrentPptFile(lastMsg.ppt_filename || '');
          setCurrentSlideNumber(lastMsg.page_number || '');

          // Auto-follow presenter: Update filter if it differs AND auto-follow is enabled
          if (isAutoFilter) {
             if (lastMsg.ppt_filename && pptFilter !== lastMsg.ppt_filename) {
                 setPptFilter(lastMsg.ppt_filename);
             } else if (!pptFilter && lastMsg.ppt_filename) {
                 setPptFilter(lastMsg.ppt_filename);
             }
          }
          
          // Handle New Message Arrival
          if (latestMsgIdRef.current !== lastMsg.id) {
              latestMsgIdRef.current = lastMsg.id;
              if (autoplay) {
                  playMessage(lastMsg, true);
                  
                  // If user is in fullscreen, we want to ensure the view updates 
                  // (Handled by the sync effect below, but explicitly setting here reduces latency)
                  if (fullScreenMsg) {
                      setFullScreenMsg(lastMsg);
                  }
              }
          }
      }
  }, [messages, autoplay, pptFilter, fullScreenMsg, isAutoFilter]); // Dependencies allow access to fresh state

  // 4. Sync FullScreen view with Audio Player
  useEffect(() => {
    if (fullScreenMsg && playingMsgId) {
        const msgPlaying = messages.find(m => m.id === playingMsgId);
        // If the audio playing is different from what we show, update the show
        if (msgPlaying && msgPlaying.id !== fullScreenMsg.id) {
            setFullScreenMsg(msgPlaying);
        }
    }
  }, [playingMsgId, messages, fullScreenMsg]);

  // Filter messages for slideshow navigation (Chronological order)
  const slideshowMessages = messages.filter(msg => {
      if (pptFilter) {
          const pptName = (msg.ppt_filename || "");
          if (pptName !== pptFilter) return false;
      }
      const langData = getLangData(msg, currentLang);
      return langData && langData.slide_link;
  });

  const currentIndex = fullScreenMsg ? slideshowMessages.findIndex(m => m.id === fullScreenMsg.id) : -1;
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex !== -1 && currentIndex < slideshowMessages.length - 1;

  const handlePrevSlide = () => {
      if (hasPrev) {
          // Stop current audio and clear tracking to prevent auto-revert
          audioRef.current.pause();
          setIsPlaying(false);
          setPlayingMsgId(null);

          const prevMsg = slideshowMessages[currentIndex - 1];
          setFullScreenMsg(prevMsg);
          playMessage(prevMsg);
      }
  };

  const handleNextSlide = () => {
      if (hasNext) {
          // Stop current audio and clear tracking to prevent auto-revert
          audioRef.current.pause();
          setIsPlaying(false);
          setPlayingMsgId(null);

          const nextMsg = slideshowMessages[currentIndex + 1];
          setFullScreenMsg(nextMsg);
          playMessage(nextMsg);
      }
  };

  // Display Order: Newest First
  const displayMessages = [...messages].reverse().filter(msg => {
    if (!pptFilter) return true;
    const pptName = (msg.ppt_filename || "");
    return pptName === pptFilter;
  });

  // Get unique PPT filenames for dropdown
  const uniquePptFiles = [...new Set(messages.map(m => m.ppt_filename).filter(Boolean))];

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
      {fullScreenMsg && (
          <FullScreenSlide 
              msg={fullScreenMsg} 
              langData={getLangData(fullScreenMsg, currentLang)}
              onClose={() => setFullScreenMsg(null)}
              onTogglePlay={() => togglePlay(fullScreenMsg)}
              isPlaying={isPlaying}
              isCurrentPlaying={playingMsgId === fullScreenMsg.id}
              onNext={handleNextSlide}
              onPrev={handlePrevSlide}
              hasNext={hasNext}
              hasPrev={hasPrev}
          />
      )}

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
        <div className="filter-controls">
            <label className="auto-follow-toggle">
                <input 
                    type="checkbox" 
                    checked={isAutoFilter} 
                    onChange={(e) => {
                        const checked = e.target.checked;
                        setIsAutoFilter(checked);
                        if (checked) {
                            setPptFilter(currentPptFile);
                        }
                    }} 
                />
                <span>Auto-follow</span>
            </label>
            <select 
                value={pptFilter}
                onChange={(e) => {
                    setPptFilter(e.target.value);
                    setIsAutoFilter(false);
                }}
                className="ppt-filter-select"
                disabled={isAutoFilter}
            >
                {uniquePptFiles.map(file => (
                    <option key={file} value={file}>{file}</option>
                ))}
            </select>
        </div>
        
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
          const hasSlideLink = langData && langData.slide_link;
          const isCurrentPlaying = playingMsgId === msg.id;

          return (
            <div key={msg.id} className="chat-message">
              {hasSlideLink && (
                <div className="slide-image-wrapper" onClick={() => {
                    setFullScreenMsg(msg);
                    playMessage(msg);
                }}>
                  <img src={langData.slide_link} alt={`Slide ${msg.page_number}`} className="slide-image" />
                </div>
              )}
              <div 
                className={`message-bubble ${isCurrentPlaying ? 'playing' : ''} ${hasAudio ? 'has-audio' : ''} ${hasSlideLink ? 'has-slide' : ''}`}
                style={{ fontSize: `${fontSize}rem` }}
                onClick={() => {
                    setFullScreenMsg(msg);
                    playMessage(msg);
                }}
              >
                <div className="message-content-wrapper">
                    <div className="message-content">
                        {langData ? langData.text : <span className="missing-lang">(Translating...)</span>}
                    </div>
                    {msg.page_number && (
                        <div className="msg-footer">
                            Slide {msg.page_number}
                        </div>
                    )}
                </div>
                {hasAudio && isCurrentPlaying && isPlaying && (
                    <div className="msg-status-icon"><PauseIcon /></div>
                )}
                {hasAudio && (!isCurrentPlaying || !isPlaying) && (
                    <div className="msg-status-icon"><PlayIcon /></div>
                )}
              </div>

            </div>
          );
        })}
      </div>
    </div>
  );
}

export default App;