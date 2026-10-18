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
let playMode = 1;
let isPlaying = false;
let tickerInterval = null;

function initLessonOptions() {
  if (!window.LESSONS_CONFIG) return;
  lessonSelect.innerHTML = '';
  window.LESSONS_CONFIG.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item.id;
    opt.textContent = item.title;
    if (item.default) opt.selected = true;
    lessonSelect.appendChild(opt);
  });
}
initLessonOptions();

// 保真音调配置（加速人声不变尖）
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
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  if (statusText) statusText.textContent = `播放中: 第 ${idx + 1} / ${sentences.length} 句`;
  updateMediaSessionInfo(idx);
}

function playAtTime(offsetSec) {
  if (!coreAudio.src) return;
  const dur = coreAudio.duration || 0;
  let target = Math.max(0, dur > 0 ? Math.min(offsetSec, dur) : offsetSec);

  coreAudio.currentTime = target;
  coreAudio.playbackRate = parseFloat(speedSelect.value) || 1.0;
  coreAudio.play().then(() => {
    isPlaying = true;
    btnPlayPause.textContent = '⏸ 暂停';
    if (topPlayBtn) topPlayBtn.textContent = '⏸';
    if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
  }).catch(err => {
    console.warn('Playback requires initial user click:', err);
  });
}

function pauseAudio() {
  coreAudio.pause();
  isPlaying = false;
  btnPlayPause.textContent = '▶ 播放';
  if (topPlayBtn) topPlayBtn.textContent = '▶';
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
}

function togglePlayPause() {
  if (isPlaying) {
    pauseAudio();
  } else {
    playAtTime(coreAudio.currentTime || 0);
  }
}

if (topPlayBtn) {
  topPlayBtn.onclick = () => togglePlayPause();
}

function playSentence(idx) {
  if (!sentences || idx < 0 || idx >= sentences.length) return;
  currentIndex = idx;
  highlightSentence(idx);
  const targetTime = Number(sentences[idx].start) || 0;
  playAtTime(targetTime);
}

function handleEndAction() {
  if (playMode === 0) {
    playSentence(currentIndex);
  } else if (playMode === 1) {
    if (currentIndex < sentences.length - 1) playSentence(currentIndex + 1);
    else playSentence(0);
  } else if (playMode === 2) {
    if (currentIndex < sentences.length - 1) playSentence(currentIndex + 1);
    else playNextLesson();
  }
}

function nextSentence() {
  if (!sentences || sentences.length === 0) return;
  if (currentIndex < sentences.length - 1) {
    playSentence(currentIndex + 1);
  } else {
    if (playMode === 1) playSentence(0);
    else playNextLesson();
  }
}

function prevSentence() {
  if (!sentences || sentences.length === 0) return;
  if (currentIndex > 0) {
    playSentence(currentIndex - 1);
  } else {
    playSentence(sentences.length - 1);
  }
}

function playNextLesson() {
  const options = Array.from(lessonSelect.options);
  let cur = options.findIndex(o => o.value === lessonSelect.value);
  let next = (cur + 1) % options.length;
  lessonSelect.selectedIndex = next;
  loadLesson(options[next].value, 0, true);
}

speedSelect.addEventListener('change', function() {
  coreAudio.playbackRate = parseFloat(this.value) || 1.0;
});

if ('mediaSession' in navigator) {
  navigator.mediaSession.setActionHandler('play', () => { if (!isPlaying) togglePlayPause(); });
  navigator.mediaSession.setActionHandler('pause', () => { if (isPlaying) togglePlayPause(); });
  navigator.mediaSession.setActionHandler('nexttrack', () => { nextSentence(); });
  navigator.mediaSession.setActionHandler('previoustrack', () => { prevSentence(); });
}

clearInterval(tickerInterval);
tickerInterval = setInterval(() => {
  const cur = coreAudio.currentTime || 0;
  const dur = coreAudio.duration || 0;

  timeCurrent.textContent = formatTime(cur);
  if (dur > 0) {
    timeDuration.textContent = formatTime(dur);
    if (!seekSlider.matches(':active')) {
      seekSlider.value = (cur / dur) * 100 || 0;
    }
  }

  if (topPlayBtn) {
    topPlayBtn.textContent = isPlaying ? '⏸' : '▶';
  }

  if (isPlaying && sentences && sentences[currentIndex]) {
    const s = sentences[currentIndex];
    const endTime = Math.min(Number(s.end) || dur, dur > 0 ? dur : Infinity);
    if (cur >= endTime - 0.08) {
      handleEndAction();
    }
  }
}, 100);

seekSlider.oninput = () => {
  const dur = coreAudio.duration || 0;
  if (dur > 0) {
    const target = (seekSlider.value / 100) * dur;
    timeCurrent.textContent = formatTime(target);
  }
};

seekSlider.onchange = () => {
  const dur = coreAudio.duration || 0;
  if (dur > 0) {
    const target = (seekSlider.value / 100) * dur;
    playAtTime(target);
    if (sentences && sentences.length > 0) {
      const found = sentences.findIndex(s => target >= Number(s.start) && target < Number(s.end));
      if (found !== -1) {
        currentIndex = found;
        highlightSentence(currentIndex);
      }
    }
  }
};

function copySentenceText(idx, btn) {
  if (!sentences || !sentences[idx]) return;
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = (sentences[idx].jp || '').replace(/<rt>.*?<\/rt>/g, '').replace(/<\/?ruby>/g, '');
  const rawJp = tempDiv.textContent.trim();
  const textToCopy = rawJp + (sentences[idx].cn ? "\n" + sentences[idx].cn : "");

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
      if (e.target.closest('button')) return;
      playSentence(idx);
    });

    const startT = (s.start !== undefined) ? Number(s.start).toFixed(2) : '0.00';
    const endT = (s.end !== undefined) ? Number(s.end).toFixed(2) : '0.00';

    let cnHtml = '';
    if (s.cn && s.cn.trim() !== '') {
      cnHtml = `<div class="cn-text">${s.cn}</div>`;
    }

    let grammarHtml = '';
    if (s.analysis && s.analysis.trim() !== '') {
      grammarHtml = `
        <details class="analysis-details" onclick="event.stopPropagation();">
          <summary>📚 词汇与语法解析（点击展开）</summary>
          <div class="analysis-content">${s.analysis}</div>
        </details>
      `;
    }

    card.innerHTML = `
      <div class="card-top">
        <span>句 ${s.id || idx + 1} &nbsp; [${startT}s - ${endT}s]</span>
        <div style="display:flex; gap:8px;">
          <button class="icon-btn copy-btn" title="复制日文句子">📋</button>
          <button class="icon-btn play-btn" title="播放单句">▶</button>
        </div>
      </div>
      <div class="jp-text">${s.jp || ''}</div>
      ${cnHtml}
      ${grammarHtml}
    `;

    const copyBtn = card.querySelector('.copy-btn');
    copyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      copySentenceText(idx, copyBtn);
    });

    const playBtn = card.querySelector('.play-btn');
    playBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      playSentence(idx);
    });

    cardsList.appendChild(card);
  });
}

async function loadLesson(lessonId, startSentenceIdx = 0, autoPlay = false) {
  pauseAudio();
  statusText.textContent = '正在加载课文与音频...';

  try {
    const jsonUrl = `./lessons/${lessonId}.json?t=${Date.now()}`;
    const mp3Url = `./lessons/${lessonId}.mp3`;

    const jsonRes = await fetch(jsonUrl);
    if (!jsonRes.ok) throw new Error(`课文加载失败: ${jsonRes.status}`);
    sentences = await jsonRes.json();

    coreAudio.src = mp3Url;
    coreAudio.load();

    coreAudio.onloadedmetadata = () => {
      timeDuration.textContent = formatTime(coreAudio.duration);
    };

    currentIndex = startSentenceIdx;
    renderCards();
    highlightSentence(currentIndex);
    statusText.textContent = '准备就绪';

    if (autoPlay) {
      playSentence(currentIndex);
    }
  } catch (err) {
    console.error(err);
    statusText.textContent = '⚠️ 加载失败: ' + err.message;
    cardsList.innerHTML = `<div style="padding:20px;text-align:center;color:#ef4444;background:#fee2e2;border-radius:10px;">
      加载失败: ${err.message}<br><br>
      <button onclick="location.reload()" style="padding:6px 12px;cursor:pointer;">刷新重试</button>
    </div>`;
  }
}

lessonSelect.onchange = () => loadLesson(lessonSelect.value, 0, false);
loadLesson(lessonSelect.value || '2026-302', 0, false);

// 显式挂载到全局，确保所有外部调用和事件100%生效
window.playSentence = playSentence;
window.togglePlayPause = togglePlayPause;
window.nextSentence = nextSentence;
window.prevSentence = prevSentence;
window.toggleLoopMode = toggleLoopMode;

// 倒计时停止逻辑
let sleepSecondsLeft = 0;
let sleepTimerId = null;

function formatTimerDisplay(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60).toString().padStart(2, '0');
  return `⏱ ${m}:${s}`;
}

if (timerSelect) {
  timerSelect.addEventListener('change', function() {
    const val = parseInt(this.value, 10);
    if (sleepTimerId) {
      clearInterval(sleepTimerId);
      sleepTimerId = null;
    }

    const defaults = {'0': '⏱ 关', '15': '⏱ 15m', '30': '⏱ 30m', '60': '⏱ 60m'};
    Array.from(this.options).forEach(opt => {
      if (defaults[opt.value]) opt.text = defaults[opt.value];
    });

    if (val === 0) {
      sleepSecondsLeft = 0;
      return;
    }

    sleepSecondsLeft = val * 60;
    this.options[this.selectedIndex].text = formatTimerDisplay(sleepSecondsLeft);

    sleepTimerId = setInterval(() => {
      sleepSecondsLeft--;
      if (sleepSecondsLeft <= 0) {
        clearInterval(sleepTimerId);
        sleepTimerId = null;
        pauseAudio();
        timerSelect.value = '0';
        Array.from(timerSelect.options).forEach(opt => {
          if (defaults[opt.value]) opt.text = defaults[opt.value];
        });
      } else {
        timerSelect.options[timerSelect.selectedIndex].text = formatTimerDisplay(sleepSecondsLeft);
      }
    }, 1000);
  });
}