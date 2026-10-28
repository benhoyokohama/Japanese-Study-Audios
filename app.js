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

const lessonJsonCache = {};
let preloadedAudioUrl = '';

function preloadNextLessonAssets() {
  try {
    const options = Array.from(lessonSelect.options);
    const cur = options.findIndex(o => o.value === lessonSelect.value);
    if (cur === -1) return;
    const nextId = options[(cur + 1) % options.length].value;
    if (!lessonJsonCache[nextId]) {
      fetch(`./lessons/${nextId}.json?t=${Date.now()}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (data) lessonJsonCache[nextId] = data; })
        .catch(() => {});
    }
    const nextMp3 = `./lessons/${nextId}.mp3?v=20261028_lockfix`;
    if (preloadedAudioUrl !== nextMp3) {
      preloadedAudioUrl = nextMp3;
      const preloadAudio = new Audio();
      preloadAudio.preload = 'auto';
      preloadAudio.src = nextMp3;
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
  } else if (savedLessonId) {
    const exists = Array.from(lessonSelect.options).some(o => o.value === savedLessonId);
    if (exists) lessonSelect.value = savedLessonId;
  }
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
  saveProgress(lessonSelect.value, idx, coreAudio.currentTime || (sentences[idx] ? Number(sentences[idx].start) : 0));
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
    preloadNextLessonAssets();
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

function playSentence(idx, seamless = false) {
  if (!sentences || idx < 0 || idx >= sentences.length) return;
  currentIndex = idx;
  highlightSentence(idx);
  const targetTime = Number(sentences[idx].start) || 0;
  // 如果是自然顺延到下一句且当前时间已经紧邻目标句开头，不重复赋值 currentTime，保持锁屏音频流绝对连续
  if (seamless && !coreAudio.paused && Math.abs((coreAudio.currentTime || 0) - targetTime) < 0.35) {
    return;
  }
  playAtTime(targetTime);
}

function handleEndAction() {
  if (playMode === 0) {
    playSentence(currentIndex, false);
  } else if (playMode === 1) {
    if (currentIndex < sentences.length - 1) playSentence(currentIndex + 1, true);
    else playSentence(0, false);
  } else if (playMode === 2) {
    if (currentIndex < sentences.length - 1) playSentence(currentIndex + 1, true);
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

function syncPlaybackTick() {
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

  if (!isPlaying || !sentences || sentences.length === 0) return;

  // 单句循环模式：严格卡在当前句末尾循环
  if (playMode === 0) {
    const s = sentences[currentIndex];
    if (s) {
      const endTime = Math.min(Number(s.end) || dur, dur > 0 ? dur : Infinity);
      if (cur >= endTime - 0.08) {
        playSentence(currentIndex, false);
      }
    }
    return;
  }

  // 全文循环(1) 或 顺序播放(2)：
  // 关键修复：熄屏时定时器可能休眠很久，唤醒时直接根据真实音频时间 cur 查找当前实际所在的句子，
  // 绝不能因为滞后的 currentIndex 触发 playSentence 把音频拉回前面的句子！
  const lastIdx = sentences.length - 1;
  const lastEnd = Number(sentences[lastIdx].end) || dur;

  // 如果已经到达全课最后一句末尾，什么都不做，100% 交由原生 audio 'ended' 事件切下一课
  if ((dur > 0 && cur >= dur - 0.25) || (lastEnd > 0 && cur >= lastEnd - 0.15)) {
    if (currentIndex !== lastIdx) {
      currentIndex = lastIdx;
      highlightSentence(lastIdx);
    }
    return;
  }

  // 正常顺延：根据真实时间 cur 匹配当前句并高亮，绝不主动重置 coreAudio.currentTime
  let matchedIdx = -1;
  for (let i = 0; i < sentences.length; i++) {
    const st = Number(sentences[i].start) || 0;
    const ed = Number(sentences[i].end) || Infinity;
    if (cur >= st - 0.05 && cur < ed - 0.05) {
      matchedIdx = i;
      break;
    }
  }
  if (matchedIdx !== -1 && matchedIdx !== currentIndex) {
    currentIndex = matchedIdx;
    highlightSentence(currentIndex);
  }
  saveProgress(lessonSelect.value, currentIndex, cur);
}

clearInterval(tickerInterval);
tickerInterval = setInterval(syncPlaybackTick, 200);
coreAudio.addEventListener('timeupdate', syncPlaybackTick);

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

async function loadLesson(lessonId, startSentenceIdx = null, autoPlay = false) {
  if (!autoPlay) {
    pauseAudio();
  }
  statusText.textContent = '正在加载课文与音频...';
  localStorage.setItem(STORAGE_LAST_LESSON, lessonId);

  try {
    const jsonUrl = `./lessons/${lessonId}.json?t=${Date.now()}`;
    const mp3Url = `./lessons/${lessonId}.mp3?v=20261028_lockfix`;

    // 关键修复1：如果是自动连播下一课 (autoPlay)，在当前同步调用栈第一行立即切换 src 并 play()，
    // 绝不等待任何异步操作，也绝不在后续回调里二次修改 currentTime 打断音频流！
    if (autoPlay) {
      coreAudio.src = mp3Url;
      coreAudio.playbackRate = parseFloat(speedSelect.value) || 1.0;
      const playPromise = coreAudio.play();
      if (playPromise !== undefined) {
        playPromise.then(() => {
          isPlaying = true;
          btnPlayPause.textContent = '⏸ 暂停';
          if (topPlayBtn) topPlayBtn.textContent = '⏸';
          if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
        }).catch(err => console.warn('Auto-play next lesson blocked:', err));
      }
    }

    // 优先使用预加载缓存的 JSON，熄屏切课时实现 0 毫秒同步渲染
    if (lessonJsonCache[lessonId]) {
      sentences = lessonJsonCache[lessonId];
    } else {
      const jsonRes = await fetch(jsonUrl);
      if (!jsonRes.ok) throw new Error(`课文加载失败: ${jsonRes.status}`);
      sentences = await jsonRes.json();
      lessonJsonCache[lessonId] = sentences;
    }

    const savedProg = getSavedProgress(lessonId);
    let targetIdx = (startSentenceIdx !== null && startSentenceIdx !== undefined)
      ? startSentenceIdx
      : (savedProg ? savedProg.idx : 0);
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
      // 只有在非自动从头连播（或指定了大于 0.5s 的恢复位置）时才修改 currentTime，
      // 严禁在 autoPlay 从 0 秒开播时二次赋值 currentTime 打断锁屏音频流！
      if (!autoPlay && targetTime > 0 && targetTime < dur) {
        coreAudio.currentTime = targetTime;
        timeCurrent.textContent = formatTime(targetTime);
        seekSlider.value = (targetTime / dur) * 100 || 0;
      }
    };

    currentIndex = targetIdx;
    renderCards();
    highlightSentence(currentIndex);
    statusText.textContent = autoPlay
      ? `播放中: 第 ${currentIndex + 1} / ${sentences.length} 句`
      : `已恢复至: 第 ${currentIndex + 1} / ${sentences.length} 句`;

    // 提前预热下一课的 JSON 和音频
    setTimeout(preloadNextLessonAssets, 1500);

    if (autoPlay) {
      requestWakeLock();
    }
  } catch (err) {
    console.error(err);
    statusText.textContent = '⚠️ 加载失败: ' + err.message;
  }
}

lessonSelect.onchange = () => loadLesson(lessonSelect.value, null, false);
loadLesson(lessonSelect.value || '2026-300', null, false);

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

// 手机熄屏/后台兜底：当整条音频自然播放结束时，直接触发末尾动作（跳下一课或循环）
coreAudio.addEventListener('ended', () => {
  if (playMode === 0) {
    playSentence(currentIndex);
  } else if (playMode === 1) {
    playSentence(0);
  } else if (playMode === 2) {
    playNextLesson();
  }
});

// 辅助功能：支持 Screen Wake Lock API，播放期间尽量保持屏幕唤醒
let wakeLock = null;
async function requestWakeLock() {
  if ('wakeLock' in navigator && isPlaying) {
    try {
      wakeLock = await navigator.wakeLock.request('screen');
    } catch (e) {}
  }
}
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && isPlaying) {
    requestWakeLock();
  }
});

// 快捷键支持：按空格键切换 播放/暂停（并阻止页面默认向下滚动）
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' || e.key === ' ') {
    const tag = document.activeElement ? document.activeElement.tagName : '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    e.preventDefault();
    if (document.activeElement && (tag === 'BUTTON' || tag === 'SELECT')) {
      document.activeElement.blur();
    }
    togglePlayPause();
  }
});
