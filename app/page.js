'use client';
import { useState, useRef, useEffect } from 'react';

const PRESET_SENTENCES = [
  {
    "id": 1,
    "start": 2.37,
    "end": 6.81,
    "jp": "auミニッツストアはほぼすべての作業を無人で行っています。",
    "cn": "au Minute Store几乎所有的操作都是无人进行的。"
  }
];

export default function Home() {
  const [apiKey, setApiKey] = useState('');
  const [audioFile, setAudioFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState('');
  const [sentences, setSentences] = useState(PRESET_SENTENCES);
  const [loopSentence, setLoopSentence] = useState(PRESET_SENTENCES[0]);
  const [isPlaying, setIsPlaying] = useState(false);
  
  const audioRef = useRef(null);
  const sentenceRefs = useRef({});

  useEffect(() => {
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) setApiKey(savedKey);
  }, []);

  const handleApiKeyChange = (e) => {
    setApiKey(e.target.value);
    localStorage.setItem('gemini_api_key', e.target.value);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioFile(file);
      setAudioUrl(URL.createObjectURL(file));
    }
  };

  const playFrom = (startSeconds, sentence) => {
    if (audioRef.current) {
      audioRef.current.currentTime = startSeconds;
      audioRef.current.play();
      setLoopSentence(sentence);
      setIsPlaying(true);
    }
  };

  const togglePlayPause = () => {
    if (audioRef.current) {
      if (audioRef.current.paused) {
        if (loopSentence) audioRef.current.currentTime = loopSentence.start;
        audioRef.current.play();
        setIsPlaying(true);
      } else {
        audioRef.current.pause();
        setIsPlaying(false);
      }
    }
  };

  const handleTimeUpdate = () => {
    if (loopSentence && audioRef.current) {
      if (audioRef.current.currentTime >= loopSentence.end) {
        audioRef.current.currentTime = loopSentence.start;
        audioRef.current.play();
      }
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8 pb-36">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-slate-800 text-center">🇯🇵 日语音频跟读工具</h1>
        
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <input 
            type="password" 
            placeholder="Gemini API Key..." 
            value={apiKey} 
            onChange={handleApiKeyChange} 
            className="w-full p-2.5 border rounded-lg text-sm" 
          />
        </div>

        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <input type="file" accept="audio/*" onChange={handleFileChange} className="w-full text-sm" />
          {audioUrl && (
            <audio 
              ref={audioRef} 
              controls 
              src={audioUrl} 
              onTimeUpdate={handleTimeUpdate} 
              onPlay={() => setIsPlaying(true)} 
              onPause={() => setIsPlaying(false)} 
              className="w-full mt-3 h-10" 
            />
          )}
        </div>
      </div>
    </main>
  );
}
