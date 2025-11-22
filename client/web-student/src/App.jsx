import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { doc, onSnapshot, collection, query, orderBy, limitToLast } from "firebase/firestore";
import { db } from "./firebase";

function App() {
  const [searchParams] = useSearchParams();
  // Get 'class' or 'courseId' from URL, default to 'current' if neither exists
  const courseId = searchParams.get('class') || searchParams.get('courseId') || 'current';
  
  const [status, setStatus] = useState({ text: "🟡 Connecting...", color: "orange" });
  const [currentLang, setCurrentLang] = useState('en');
  const [messages, setMessages] = useState([]);
  const [audioUrl, setAudioUrl] = useState("");
  const [autoplay, setAutoplay] = useState(true);
  const [supportedLangs, setSupportedLangs] = useState([]);
  
  const audioRef = useRef(null);
  const lastAudioUrlRef = useRef("");
  const messagesEndRef = useRef(null);

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 1. Listen to metadata (Status & Supported Languages)
  useEffect(() => {
    console.log(`Connecting to presentation_broadcast/${courseId}`);
    setStatus({ text: "🟡 Connecting...", color: "orange" });

    const unsubscribe = onSnapshot(doc(db, "presentation_broadcast", courseId), (docSnapshot) => {
      setStatus({ text: "🟢 Live", color: "green" });
      
      if (docSnapshot.exists()) {
        const data = docSnapshot.data();
        
        // Update supported languages list
        let langs = [];
        if (data.supported_languages && Array.isArray(data.supported_languages)) {
            langs = data.supported_languages;
        } else if (data.languages) {
            langs = Object.keys(data.languages);
        }
        
        if (langs.length > 0) {
            setSupportedLangs(langs);
        }
      }
    }, (error) => {
      console.error("Listen error:", error);
      setStatus({ text: "🔴 Connection Error", color: "red" });
    });

    return () => unsubscribe();
  }, [courseId]);

  // 2. Listen to Messages (Chat History)
  useEffect(() => {
    const messagesRef = collection(db, "presentation_broadcast", courseId, "messages");
    const q = query(messagesRef, orderBy("updated_at", "asc"), limitToLast(100));

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const msgs = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      
      setMessages(msgs);

      // Handle Audio for the latest message
      if (msgs.length > 0) {
        const lastMsg = msgs[msgs.length - 1];
        const langData = getLangData(lastMsg, currentLang);
        
        if (langData && langData.audio_url && langData.audio_url !== lastAudioUrlRef.current) {
          lastAudioUrlRef.current = langData.audio_url;
          setAudioUrl(langData.audio_url);
        }
      }
    });

    return () => unsubscribe();
  }, [courseId, currentLang]);

  // Helper to get data for current language (with fallback)
  const getLangData = (data, lang) => {
    if (!data.languages) return null;
    let langData = data.languages[lang];
    if (!langData) {
        const match = Object.keys(data.languages).find(k => k.startsWith(lang) || lang.startsWith(k));
        if (match) langData = data.languages[match];
    }
    return langData;
  };

  // Handle Audio Autoplay
  useEffect(() => {
    if (audioUrl && audioRef.current && autoplay) {
      audioRef.current.play().catch(e => console.log("Autoplay blocked:", e));
    }
  }, [audioUrl, autoplay]);

  const handleLangChange = (e) => {
    setCurrentLang(e.target.value);
    // Reset audio url ref so it can re-play if we switch back or to a lang with same URL (unlikely)
    lastAudioUrlRef.current = ""; 
    // Actually, we might want to re-play the *current* latest message in the new language immediately?
    // The `useEffect` for messages will re-run because `currentLang` changed? 
    // No, I put `currentLang` in dependency array of message effect? 
    // Yes. So it will re-evaluate `msgs` (which are from snapshot, but snapshot callback closes over state? No, snapshot persists).
    // Wait, `onSnapshot` doesn't re-run just because `currentLang` changed unless we unsubscribe/resubscribe.
    // But we DO want to re-evaluate the "latest audio" logic when language changes.
    // My current `useEffect` [courseId, currentLang] DOES re-subscribe. That's slightly inefficient (fetches all docs again? No, Firestore SDK caches).
    // Better: Separate the listener from the "current lang audio update" logic.
    // But for now, re-subscribing is safest to ensure closure freshness.
  };

  return (
    <div className="container">
      <header>
        <h1>🎓 LangBridge</h1>
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

      <div className="chat-area">
        {messages.length === 0 && (
           <div className="empty-state">Waiting for presentation to start...</div>
        )}
        {messages.map((msg) => {
          const langData = getLangData(msg, currentLang);
          const content = langData ? langData.text : "(Translating...)";
          const isSystem = !langData; // Or check if it's a system message?

          return (
            <div key={msg.id} className={`chat-message ${isSystem ? 'system' : 'presenter'}`}>
              <div className="message-bubble">
                {langData ? langData.text : <span style={{fontStyle: 'italic', opacity: 0.6}}>(Content not available in {getLangName(currentLang)})</span>}
              </div>
              {msg.original_context && (
                 <div className="original-context">
                   {msg.original_context.substring(0, 80)}{msg.original_context.length > 80 ? "..." : ""}
                 </div>
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="footer-controls">
          <div className="audio-player-wrapper">
            <audio 
                ref={audioRef} 
                src={audioUrl} 
                controls 
                className="main-audio"
            />
            <label className="autoplay-toggle">
              <input 
                type="checkbox" 
                checked={autoplay} 
                onChange={(e) => setAutoplay(e.target.checked)} 
              /> Autoplay
            </label>
          </div>
      </div>
    </div>
  );
}

export default App;