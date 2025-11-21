import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { doc, onSnapshot } from "firebase/firestore";
import { db } from "./firebase";

function App() {
  const [searchParams] = useSearchParams();
  // Get 'class' or 'courseId' from URL, default to 'current' if neither exists
  const courseId = searchParams.get('class') || searchParams.get('courseId') || 'current';
  
  const [status, setStatus] = useState({ text: "🟡 Connecting...", color: "orange" });
  const [currentLang, setCurrentLang] = useState('en');
  const [message, setMessage] = useState("Waiting for presentation data...");
  const [originalContext,ObOriginalContext] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [autoplay, setAutoplay] = useState(true);
  
  const audioRef = useRef(null);
  const lastAudioUrlRef = useRef("");

  const [supportedLangs, setSupportedLangs] = useState([]);

  const LANGUAGE_NAMES = {
    "en": "English",
    "en-US": "English (US)",
    "zh": "Chinese (中文)",
    "zh-CN": "Mandarin (简体中文)",
    "zh-TW": "Mandarin (繁體中文)",
    "yue": "Cantonese (Gwong2 dung1 waa2)",
    "yue-HK": "Cantonese (香港)",
    "es": "Spanish (Español)",
    "ja": "Japanese (日本語)"
  };

  const getLangName = (code) => {
    return LANGUAGE_NAMES[code] || code;
  };

  useEffect(() => {
    console.log(`Connecting to presentation_broadcast/${courseId}`);
    setStatus({ text: "🟡 Connecting...", color: "orange" });

    const unsubscribe = onSnapshot(doc(db, "presentation_broadcast", courseId), (docSnapshot) => {
      setStatus({ text: "🟢 Live", color: "green" });
      
      if (docSnapshot.exists()) {
        const data = docSnapshot.data();
        updateUI(data);
        
        // Update supported languages list
        let langs = [];
        if (data.supported_languages && Array.isArray(data.supported_languages)) {
            langs = data.supported_languages;
        } else if (data.languages) {
            // Fallback: derive from available keys if explicit list missing
            langs = Object.keys(data.languages);
        }
        
        // Ensure current selection is valid, or default to first available
        if (langs.length > 0) {
            setSupportedLangs(langs);
            // If currentLang is not in the new list (and list isn't empty), switch to first available?
            // Or maybe we shouldn't force switch to avoid annoying UX if it's just a glitch.
            // But if we start with 'en' and the course only has 'zh', we should probably switch.
            // Let's just ensure the user can see the options.
        }
        
      } else {
        setMessage("Waiting for presentation data...");
      }
    }, (error) => {
      console.error("Listen error:", error);
      setStatus({ text: "🔴 Connection Error", color: "red" });
      
      if (error.code === 'permission-denied') {
        setMessage("Permission Denied. Check Firestore Security Rules.");
      }
    });

    return () => unsubscribe();
  }, [courseId, currentLang]); // Re-run if courseId or language changes

  const updateUI = (data) => {
    if (data.original_context) {
      ObOriginalContext("Original Notes: " + data.original_context.substring(0, 100) + "...");
    }

    // Try to find data for currentLang, or try prefixes (e.g. 'en' matches 'en-US')
    let langData = null;
    if (data.languages) {
        langData = data.languages[currentLang];
        if (!langData) {
            // Try finding a key that starts with currentLang (e.g. 'en-US' for 'en') or vice versa
            const match = Object.keys(data.languages).find(k => k.startsWith(currentLang) || currentLang.startsWith(k));
            if (match) langData = data.languages[match];
        }
    }
    
    if (langData) {
      if (langData.text) {
        setMessage(langData.text);
      }

      if (langData.audio_url && langData.audio_url !== lastAudioUrlRef.current) {
        lastAudioUrlRef.current = langData.audio_url;
        setAudioUrl(langData.audio_url);
        // Auto-play handling is done via useEffect on audioUrl change
      }
    } else {
      setMessage(`(No content available for ${currentLang})`);
    }
  };

  // Handle Audio Autoplay
  useEffect(() => {
    if (audioUrl && audioRef.current && autoplay) {
      audioRef.current.play().catch(e => console.log("Autoplay blocked:", e));
    }
  }, [audioUrl, autoplay]);

  const handleLangChange = (e) => {
    setCurrentLang(e.target.value);
    // Reset message temporarily while switching? Or keep old one? 
    // Better to keep old one until next update or re-fetch if we stored full doc.
    // Actually, we have the full doc in the snapshot closure if we used state for data.
    // But for simplicity, we just let the next snapshot update it or rely on the fact 
    // that `updateUI` is called inside the snapshot callback. 
    // WAIT: `updateUI` relies on `currentLang` state.
    // But `updateUI` is defined inside the component, so it sees the *current render's* `currentLang`.
    // The `onSnapshot` callback closes over the variables from when it was defined.
    // So changing `currentLang` won't update the *existing* subscription's callback logic immediately 
    // unless we re-subscribe (which we do because `currentLang` is in dependency array).
  };

  return (
    <div className="container">
      <header>
        <h1>🎓 Xiaoice Class Assistant</h1>
        <div className="controls">
          <div className="status" style={{ color: status.color }}>
            {status.text}
          </div>
          <select value={currentLang} onChange={handleLangChange}>
            {supportedLangs.length > 0 ? (
                supportedLangs.map(lang => (
                    <option key={lang} value={lang}>
                        {getLangName(lang)}
                    </option>
                ))
            ) : (
                <>
                    <option value="en">English</option>
                    <option value="zh">Chinese</option>
                </>
            )}
          </select>
        </div>
      </header>

      <div className="content-area">
        <div className="message-text">
          {message}
        </div>
        
        <div className="audio-controls">
          <audio 
            ref={audioRef} 
            src={audioUrl} 
            controls 
          >
            Your browser does not support the audio element.
          </audio>
          <div style={{ marginTop: '5px', fontSize: '0.8rem', color: '#666' }}>
            <label>
              <input 
                type="checkbox" 
                checked={autoplay} 
                onChange={(e) => setAutoplay(e.target.checked)} 
              /> Auto-play audio
            </label>
          </div>
        </div>

        <div className="context-preview">
          {originalContext}
        </div>
      </div>
    </div>
  );
}

export default App;
