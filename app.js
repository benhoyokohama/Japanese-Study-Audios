const coreAudio = document.getElementById('coreAudio');
const lessonSelect = document.getElementById('lessonSelect');
const speedSelect = document.getElementById('speedSelect');
const timerSelect = document.getElementById('timerSelect');
const cardsList = document.getElementById('cardsList');
const statusText = document.getElementById('statusText');
const btnPlayPause = document.getElementById('btnPlayPause');
const topPlayBtn = document.getElementById('topPlayBtn');
const btnLoopMode = document.getElementById('btnLoopMode');
const timeCurrent = document.getElementById('timeCurrent');
const timeDuration = document.getElementById('timeDuration');
const seekSlider = document.getElementById('seekSlider');

let sentences = [];
let currentIndex = 0;
let playMode = 1; // 0: 单句循环, 1: 全文循环, 2: 顺序播放
let isPlaying = false;
let isSwitchingLesson = false;
const lessonJsonCache = {};
const MP3_VER = '20261031_urite';

// Web Audio API 极低音量保活器：防止 iOS 锁屏在切课加载新 MP3 的瞬间挂起后台线程
let keepAliveCtx = null;
function ensureAudioKeepAlive() {
  try {
    if (!keepAliveCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      keepAliveCtx = new AudioCtx();
      const osc = keepAliveCtx.createOscillator();
      const gain = keepAliveCtx.createGain();
      gain.gain.value = 0.00001; // 人耳完全不可闻的极微弱信号，维持 iOS 后台活跃
      osc.connect(gain);
      gain.connect(keepAliveCtx.destination);
      osc.start();
    }
    if (keepAliveCtx && keepAliveCtx.state === 'suspended') {
      keepAliveCtx.resume().catch(() => {});
    }
  } catch (e) {}
}

const STORAGE_LAST_LESSON = 'jp_reader_last_lesson';
function getSavedProgress(lessonId) {
  try {
    const raw = localStorage.getItem('jp_reader_prog_' + lessonId);
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}
function saveProgress(lessonId, idx, timeSec) {
  if (!lessonId) return;
  try {
    localStorage.setItem(STORAGE_LAST_LESSON, lessonId);
    localStorage.setItem('jp_reader_prog_' + lessonId, JSON.stringify({
      idx: idx || 0,
      time: timeSec || 0,
      updatedAt: Date.now()
    }));
  } catch (e) {}
}

function initLessonOptions() {
  const configList = (typeof LESSONS !== 'undefined' && Array.isArray(LESSONS)) ? LESSONS : window.LESSONS_CONFIG;
  const savedLessonId = localStorage.getItem(STORAGE_LAST_LESSON);
  if (configList && configList.length > 0) {
    lessonSelect.innerHTML = '';
    const hasSaved = savedLessonId && configList.some(item => item.id === savedLessonId);
    configList.forEach((item, idx) => {
      const opt = document.createElement('option');
      opt.value = item.id;
      opt.textContent = item.title;
      if (hasSaved ? (item.id === savedLessonId) : (item.default || idx === 0)) {
        opt.selected = true;
      }
      lessonSelect.appendChild(opt);
    });
  }
}
initLessonOptions();

coreAudio.preservesPitch = true;
coreAudio.webkitPreservesPitch = true;
coreAudio.mozPreservesPitch = true;

function formatTime(sec) {
  if (!sec || isNaN(sec)) return '0:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function toggleLoopMode() {
  playMode = (playMode + 1) % 3;
  if (playMode === 0) btnLoopMode.textContent = '🔂 单句循环';
  else if (playMode === 1) btnLoopMode.textContent = '🔁 全文循环';
  else btnLoopMode.textContent = '➡️ 顺序播放';
}

function preloadNextLesson() {
  try {
    const options = Array.from(lessonSelect.options);
    const cur = options.findIndex(o => o.value === lessonSelect.value);
    if (cur === -1) return;
    const nextId = options[(cur + 1) % options.length].value;
    if (!lessonJsonCache[nextId]) {
      fetch(`./lessons/${nextId}.json?t=${Date.now()}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) lessonJsonCache[nextId] = d; })
        .catch(() => {});
    }
  } catch (e) {}
}

function updateMediaSessionInfo(idx) {
  if (!('mediaSession' in navigator)) return;
  const s = sentences && sentences[idx] ? sentences[idx] : null;
  let titleText = '随身日语';
  if (s) {
    const temp = document.createElement('div');
    temp.innerHTML = (s.jp || '').replace(/<rt>.*?<\/rt>/g, '').replace(/<\/?ruby>/g, '');
    titleText = temp.textContent.trim() || `第 ${idx + 1} 句`;
  }
  navigator.mediaSession.metadata = new MediaMetadata({
    title: titleText,
    artist: lessonSelect.options[lessonSelect.selectedIndex]?.text || '随身日语',
    album: '日语精听跟读'
  });
  navigator.mediaSession.playbackState = isPlaying ? 'playing' : 'paused';
}

function highlightSentence(idx) {
  document.querySelectorAll('.sentence-card').forEach((c, i) => {
    c.classList.toggle('active', i === idx);
  });
  const card = document.getElementById(`card-${idx}`);
  if (card && document.visibilityState === 'visible') {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  if (statusText) statusText.textContent = `播放中: 第 ${idx + 1} / ${sentences.length} 句`;
  saveProgress(lessonSelect.value, idx, coreAudio.currentTime || 0);
  updateMediaSessionInfo(idx);
}

function playAtTime(offsetSec) {
  if (!coreAudio.src) return;
  ensureAudioKeepAlive();
  const dur = coreAudio.duration || 0;
  coreAudio.currentTime = Math.max(0, dur > 0 ? Math.min(offsetSec, dur) : offsetSec);
  coreAudio.playbackRate = parseFloat(speedSelect.value) || 1.0;
  coreAudio.play().then(() => {
    isPlaying = true;
    btnPlayPause.textContent = '⏸ 暂停';
    if (topPlayBtn) topPlayBtn.textContent = '⏸';
    if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
    preloadNextLesson();
  }).catch(err => console.warn('Play error:', err));
}

function pauseAudio() {
  coreAudio.pause();
  isPlaying = false;
  btnPlayPause.textContent = '▶ 播放';
  if (topPlayBtn) topPlayBtn.textContent = '▶';
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
}

function togglePlayPause() {
  if (isPlaying) pauseAudio();
  else playAtTime(coreAudio.currentTime || 0);
}
if (topPlayBtn) topPlayBtn.onclick = () => togglePlayPause();

function playSentence(idx) {
  if (!sentences || idx < 0 || idx >= sentences.length) return;
  currentIndex = idx;
  highlightSentence(idx);
  playAtTime(Number(sentences[idx].start) || 0);
}

function playNextLesson() {
  if (isSwitchingLesson) return;
  isSwitchingLesson = true;
  const options = Array.from(lessonSelect.options);
  let cur = options.findIndex(o => o.value === lessonSelect.value);
  let next = (cur + 1) % options.length;
  lessonSelect.selectedIndex = next;
  loadLesson(options[next].value, 0, true).finally(() => {
    setTimeout(() => { isSwitchingLesson = false; }, 1000);
  });
}

function nextSentence() {
  if (!sentences || sentences.length === 0) return;
  if (currentIndex < sentences.length - 1) playSentence(currentIndex + 1);
  else if (playMode === 1) playSentence(0);
  else playNextLesson();
}

function prevSentence() {
  if (!sentences || sentences.length === 0) return;
  if (currentIndex > 0) playSentence(currentIndex - 1);
  else playSentence(sentences.length - 1);
}

speedSelect.addEventListener('change', function() {
  coreAudio.playbackRate = parseFloat(this.value) || 1.0;
});

if ('mediaSession' in navigator) {
  navigator.mediaSession.setActionHandler('play', () => { if (!isPlaying) togglePlayPause(); });
  navigator.mediaSession.setActionHandler('pause', () => { if (isPlaying) togglePlayPause(); });
  navigator.mediaSession.setActionHandler('nexttrack', () => nextSentence());
  navigator.mediaSession.setActionHandler('previoustrack', () => prevSentence());
}

// 核心进度与锁屏无缝切课监听（同时绑定 timeupdate 与 250ms 定时器）
function onPlaybackProgress() {
  if (isSwitchingLesson) return;
  const cur = coreAudio.currentTime || 0;
  const dur = coreAudio.duration || 0;

  timeCurrent.textContent = formatTime(cur);
  if (dur > 0) {
    timeDuration.textContent = formatTime(dur);
    if (!seekSlider.matches(':active')) {
      seekSlider.value = (cur / dur) * 100 || 0;
    }
  }
  if (!isPlaying || !sentences || sentences.length === 0) return;

  // 1. 单句循环模式
  if (playMode === 0) {
    const s = sentences[currentIndex];
    if (s && cur >= (Number(s.end) || dur) - 0.08) {
      playSentence(currentIndex);
    }
    return;
  }

  // 2. 关键：在整课音频结束前 0.35 秒（末尾静音区内），趁硬件解码器仍处于活跃 Playing 状态立即热切换！
  const lastSentenceEnd = Number(sentences[sentences.length - 1].end) || dur;
  const effectiveEnd = dur > 0 ? Math.min(dur, lastSentenceEnd) : lastSentenceEnd;
  if (effectiveEnd > 5 && cur >= effectiveEnd - 0.35) {
    if (playMode === 1) {
      playSentence(0);
    } else if (playMode === 2) {
      playNextLesson();
    }
    return;
  }

  // 3. 根据当前真实播放时间 cur 自动匹配并高亮句子（不主动修改 currentTime，确保音频流零中断）
  for (let i = 0; i < sentences.length; i++) {
    const st = Number(sentences[i].start) || 0;
    const ed = Number(sentences[i].end) || Infinity;
    if (cur >= st && cur < ed) {
      if (currentIndex !== i) {
        currentIndex = i;
        highlightSentence(i);
      }
      break;
    }
  }
  saveProgress(lessonSelect.value, currentIndex, cur);
}

setInterval(onPlaybackProgress, 250);
coreAudio.addEventListener('timeupdate', onPlaybackProgress);
coreAudio.addEventListener('ended', () => {
  if (isSwitchingLesson) return;
  if (playMode === 0) playSentence(currentIndex);
  else if (playMode === 1) playSentence(0);
  else if (playMode === 2) playNextLesson();
});

seekSlider.oninput = () => {
  const dur = coreAudio.duration || 0;
  if (dur > 0) timeCurrent.textContent = formatTime((seekSlider.value / 100) * dur);
};
seekSlider.onchange = () => {
  const dur = coreAudio.duration || 0;
  if (dur > 0) {
    const target = (seekSlider.value / 100) * dur;
    playAtTime(target);
    const found = sentences.findIndex(s => target >= Number(s.start) && target < Number(s.end));
    if (found !== -1) {
      currentIndex = found;
      highlightSentence(currentIndex);
    }
  }
};

function copySentenceText(idx, btn) {
  if (!sentences || !sentences[idx]) return;
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = (sentences[idx].jp || '').replace(/<rt>.*?<\/rt>/g, '').replace(/<\/?ruby>/g, '');
  const textToCopy = tempDiv.textContent.trim() + (sentences[idx].cn ? "\n" + sentences[idx].cn : "");
  navigator.clipboard.writeText(textToCopy).then(() => {
    btn.textContent = '✅';
    setTimeout(() => { btn.textContent = '📋'; }, 1200);
  });
}

function renderCards() {
  cardsList.innerHTML = '';
  sentences.forEach((s, idx) => {
    const card = document.createElement('div');
    card.className = `sentence-card ${idx === currentIndex ? 'active' : ''}`;
    card.id = `card-${idx}`;
    card.addEventListener('click', (e) => {
      if (!e.target.closest('button')) playSentence(idx);
    });
    const startT = Number(s.start || 0).toFixed(2);
    const endT = Number(s.end || 0).toFixed(2);
    const cnHtml = (s.cn && s.cn.trim()) ? `<div class="cn-text">${s.cn}</div>` : '';
    const grammarHtml = (s.analysis && s.analysis.trim()) ? `
      <details class="analysis-details" onclick="event.stopPropagation();">
        <summary>📚 词汇与语法解析（点击展开）</summary>
        <div class="analysis-content">${s.analysis}</div>
      </details>` : '';
    card.innerHTML = `
      <div class="card-top">
        <span>句 ${s.id || idx + 1} &nbsp; [${startT}s - ${endT}s]</span>
        <div style="display:flex; gap:8px;">
          <button class="icon-btn copy-btn" title="复制日文句子">📋</button>
          <button class="icon-btn play-btn" title="播放单句">▶</button>
        </div>
      </div>
      <div class="jp-text">${s.jp || ''}</div>
      ${cnHtml}${grammarHtml}
    `;
    card.querySelector('.copy-btn').addEventListener('click', (e) => { e.stopPropagation(); copySentenceText(idx, e.currentTarget); });
    card.querySelector('.play-btn').addEventListener('click', (e) => { e.stopPropagation(); playSentence(idx); });
    cardsList.appendChild(card);
  });
}

async function loadLesson(lessonId, startSentenceIdx = null, autoPlay = false) {
  if (!autoPlay) pauseAudio();
  statusText.textContent = '正在加载课文与音频...';
  localStorage.setItem(STORAGE_LAST_LESSON, lessonId);

  try {
    const jsonUrl = `./lessons/${lessonId}.json?t=${Date.now()}`;
    const mp3Url = `./lessons/${lessonId}.mp3?v=${MP3_VER}`;

    // 锁屏连播核心：在任何异步操作前，第一行直接同步切换音频源并立即 play()
    if (autoPlay) {
      ensureAudioKeepAlive();
      coreAudio.src = mp3Url;
      coreAudio.playbackRate = parseFloat(speedSelect.value) || 1.0;
      coreAudio.play().then(() => {
        isPlaying = true;
        btnPlayPause.textContent = '⏸ 暂停';
        if (topPlayBtn) topPlayBtn.textContent = '⏸';
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
      }).catch(e => console.warn('AutoPlay error:', e));
    }

    if (lessonJsonCache[lessonId]) {
      sentences = lessonJsonCache[lessonId];
    } else {
      const jsonRes = await fetch(jsonUrl);
      if (!jsonRes.ok) throw new Error(`加载失败: ${jsonRes.status}`);
      sentences = await jsonRes.json();
      lessonJsonCache[lessonId] = sentences;
    }

    const savedProg = getSavedProgress(lessonId);
    let targetIdx = (startSentenceIdx !== null) ? startSentenceIdx : (savedProg ? savedProg.idx : 0);
    if (targetIdx < 0 || targetIdx >= sentences.length) targetIdx = 0;
    let targetTime = (startSentenceIdx === null && savedProg && savedProg.time > 0)
      ? savedProg.time
      : (sentences[targetIdx] ? Number(sentences[targetIdx].start) || 0 : 0);

    if (!autoPlay) {
      coreAudio.src = mp3Url;
      coreAudio.load();
    }

    coreAudio.onloadedmetadata = () => {
      const dur = coreAudio.duration || 0;
      timeDuration.textContent = formatTime(dur);
      if (!autoPlay && targetTime > 0 && targetTime < dur) {
        coreAudio.currentTime = targetTime;
        timeCurrent.textContent = formatTime(targetTime);
        seekSlider.value = (targetTime / dur) * 100 || 0;
      }
    };

    currentIndex = targetIdx;
    renderCards();
    highlightSentence(currentIndex);
    preloadNextLesson();
  } catch (err) {
    console.error(err);
    statusText.textContent = '⚠️ 加载失败: ' + err.message;
  }
}

lessonSelect.onchange = () => loadLesson(lessonSelect.value, null, false);
loadLesson(lessonSelect.value || '2026-101', null, false);

window.playSentence = playSentence;
window.togglePlayPause = togglePlayPause;
window.nextSentence = nextSentence;
window.prevSentence = prevSentence;
window.toggleLoopMode = toggleLoopMode;

let sleepSecondsLeft = 0;
let sleepTimerId = null;
if (timerSelect) {
  timerSelect.addEventListener('change', function() {
    const val = parseInt(this.value, 10);
    if (sleepTimerId) { clearInterval(sleepTimerId); sleepTimerId = null; }
    const defaults = {'0': '⏱ 关', '15': '⏱ 15m', '30': '⏱ 30m', '60': '⏱ 60m'};
    Array.from(this.options).forEach(opt => { if (defaults[opt.value]) opt.text = defaults[opt.value]; });
    if (val === 0) return;
    sleepSecondsLeft = val * 60;
    sleepTimerId = setInterval(() => {
      sleepSecondsLeft--;
      if (sleepSecondsLeft <= 0) {
        clearInterval(sleepTimerId); sleepTimerId = null;
        pauseAudio(); timerSelect.value = '0';
        Array.from(timerSelect.options).forEach(opt => { if (defaults[opt.value]) opt.text = defaults[opt.value]; });
      } else {
        const m = Math.floor(sleepSecondsLeft / 60);
        const s = Math.floor(sleepSecondsLeft % 60).toString().padStart(2, '0');
        timerSelect.options[timerSelect.selectedIndex].text = `⏱ ${m}:${s}`;
      }
    }, 1000);
  });
}

document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' || e.key === ' ') {
    const tag = document.activeElement ? document.activeElement.tagName : '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    e.preventDefault();
    if (document.activeElement && (tag === 'BUTTON' || tag === 'SELECT')) document.activeElement.blur();
    togglePlayPause();
  }
});
