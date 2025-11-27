import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { doc, onSnapshot, collection, getDocs } from "firebase/firestore";
import { db } from "./firebase";

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
  const courseId = searchParams.get('class') || searchParams.get('courseId') || 'current';
  
  const [status, setStatus] = useState({ text: "🟡 Connecting...", color: "orange" });
  const [viewLang, setViewLang] = useState('en');
  const [listenLang, setListenLang] = useState('en');
  const [supportedLangs, setSupportedLangs] = useState([]);
  
  // -- State for Live/Nav Logic --
  const [livePptId, setLivePptId] = useState(null);
  const [liveSlideId, setLiveSlideId] = useState(null);
  
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
  
  // Full Screen State
  const [isFullScreen, setIsFullScreen] = useState(false);

  // Refs
  const audioRef = useRef(new Audio());
  const lastPlayedHash = useRef(null);

  const LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Chinese (中文)",
    "yue-HK": "Cantonese (香港)",
    "es": "Spanish (Español)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)"
  };

  const getLangName = (code) => LANGUAGE_NAMES[code] || code;

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
        
        // Update Live Content (Audio/Text)
        if (data.latest_languages) {
            setLiveData(data.latest_languages);
            
            // Update supported languages list and sync selection
            const langs = Object.keys(data.latest_languages);
            if (langs.length > 0) {
                setSupportedLangs(langs);
                
                // Auto-select valid language helper
                const initLang = (current, available) => {
                    if (available.includes(current)) return current;
                    const match = available.find(l => l.startsWith(current) || current.startsWith(l));
                    if (match) return match;
                    return available[0];
                };

                setViewLang(prev => initLang(prev, langs));
                setListenLang(prev => initLang(prev, langs));
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
      
      const pptCollection = collection(db, "presentation_broadcast", courseId, "presentations");
      const unsubscribe = onSnapshot(pptCollection, (snapshot) => {
          const ppts = snapshot.docs.map(doc => doc.id);
          setPresentationList(ppts);
      });
      return () => unsubscribe();
  }, [courseId, isReady]);

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
      
      const basePath = `presentation_broadcast/${courseId}/presentations`;
      console.log("Fetching slide list from:", basePath, viewingPptId);
          
      const slidesCol = collection(db, basePath, viewingPptId, "slides");
      
      const unsubscribe = onSnapshot(slidesCol, (snapshot) => {
          console.log("Slide list snapshot size:", snapshot.size);
          // Assuming ids are numeric strings "1", "2", etc.
          const ids = snapshot.docs
              .map(d => parseInt(d.id, 10))
              .filter(n => !isNaN(n))
              .sort((a, b) => a - b);
          setSlideList(ids);
      }, (error) => {
          console.error("Error fetching slide list:", error);
      });

      return () => unsubscribe();
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

      console.log("Fetching slide:", viewingPptId, viewingSlideId);
      const basePath = `presentation_broadcast/${courseId}/presentations`;

      const slideRef = doc(db, basePath, viewingPptId, "slides", String(viewingSlideId));
      const unsubscribe = onSnapshot(slideRef, (docSnapshot) => {
          console.log("Slide snapshot:", docSnapshot.exists(), docSnapshot.data());
          if (docSnapshot.exists()) {
              setSlideData(docSnapshot.data());
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
  
  // Audio Source Decision
  // If Sync is ON: Play LIVE audio (from listenLang)
  // If Sync is OFF: Play Viewing Slide audio (from listenLang)
  const activeAudioContent = isLiveMode ? liveContentAudio : viewingContentAudio;
  const activeAudioUrl = activeAudioContent?.audio_url;

  // --- 5. Audio Player Logic ---
  useEffect(() => {
      if (!activeAudioUrl || !autoplay) return;

      if (lastPlayedHash.current !== activeAudioUrl) {
          lastPlayedHash.current = activeAudioUrl;
          
          audioRef.current.src = activeAudioUrl;
          audioRef.current.play()
              .then(() => setIsPlaying(true))
              .catch(e => console.error("Autoplay blocked:", e));
      }
  }, [activeAudioUrl, autoplay]);

  // Audio Events
  useEffect(() => {
      const audio = audioRef.current;
      const handlePlay = () => setIsPlaying(true);
      const handlePause = () => setIsPlaying(false);
      const handleEnded = () => setIsPlaying(false);

      audio.addEventListener('play', handlePlay);
      audio.addEventListener('pause', handlePause);
      audio.addEventListener('ended', handleEnded);
      return () => {
          audio.removeEventListener('play', handlePlay);
          audio.removeEventListener('pause', handlePause);
          audio.removeEventListener('ended', handleEnded);
      };
  }, []);

  const togglePlay = () => {
      if (isPlaying) audioRef.current.pause();
      else audioRef.current.play();
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

  if (!isReady) {
      return (
          <div className="splash-screen">
              <h1>LangBride</h1>
              <button onClick={() => setIsReady(true)}>Join Class</button>
              <p className="attribution">Developed by Higher Diploma in Cloud and Data Centre Administration at HKIIT</p>
          </div>
      );
  }

  // Priority: Viewing Slide Registry > Live Data (fallback if visual matches)
  const visualUrl = viewingContentView?.slide_link || (isLiveMode && String(viewingSlideId) === String(liveSlideId) ? liveContentView?.slide_link : null);
  
  // Text priority: Viewing Slide text (if browsing) -> Live text (if live)
  // This ensures text matches the visual slide and View Language
  const displayText = (isLiveMode ? liveContentView?.text : viewingContentView?.text) || "(Translating...)";

  const currentNum = parseInt(viewingSlideId, 10);
  const hasPrev = slideList.length > 0 && slideList.indexOf(currentNum) > 0;
  const hasNext = slideList.length > 0 && slideList.indexOf(currentNum) < slideList.length - 1;

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
            <div style={{display: 'flex', gap: '8px'}}>
                {/* View Language */}
                <div style={{position: 'relative'}} title="Text Language">
                    <span style={{position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.85rem', pointerEvents: 'none'}}>👁️</span>
                    <select 
                        value={viewLang} 
                        onChange={(e) => setViewLang(e.target.value)}
                        style={{paddingLeft: '28px'}}
                    >
                        {supportedLangs.map(lang => <option key={lang} value={lang}>{getLangName(lang)}</option>)}
                    </select>
                </div>
                {/* Listen Language */}
                <div style={{position: 'relative'}} title="Audio Language">
                    <span style={{position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.85rem', pointerEvents: 'none'}}>🔊</span>
                    <select 
                        value={listenLang} 
                        onChange={(e) => setListenLang(e.target.value)}
                        style={{paddingLeft: '28px'}}
                    >
                        {supportedLangs.map(lang => <option key={lang} value={lang}>{getLangName(lang)}</option>)}
                    </select>
                </div>
            </div>
        </div>
      </header>
      
      <div className="sub-header">
        <div className="nav-controls" style={{display:'flex', alignItems:'center', gap:'10px'}}>
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
        </div>

        <label className="autoplay-toggle">
            <input 
            type="checkbox" 
            checked={autoplay} 
            onChange={(e) => setAutoplay(e.target.checked)} 
            /> 
            <span>Autoplay</span>
        </label>
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
             <button className="play-btn" onClick={(e) => { e.stopPropagation(); togglePlay(); }}>
                {isPlaying ? <PauseIcon /> : <PlayIcon />}
             </button>
          </div>
      </div>
    </div>
  );
}

export default App;