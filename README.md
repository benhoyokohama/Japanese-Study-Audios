# 🇯🇵 随身日语听力跟读系统 (jp-reader) 开发与课件生成指南

本项目是一个支持 **顶部假名注音 (`<ruby>`)**、**单句循环/全文连播**、**保真变速**、**本地播放进度记忆 (`localStorage`)** 以及 **可选词汇/语法折叠解析** 的轻量级日语精听跟读 Web 应用。

线上地址：`[https://benhoyokohama.github.io/Japanese-Study-Audios/](https://benhoyokohama.github.io/Japanese-Study-Audios/)`

---

## 一、 系统核心能力与支持的 3 类课件模式

本项目统一通过 `lessons/{lesson_id}.mp3` + `lessons/{lesson_id}.json` 驱动前端渲染，支持以下三种课件生成工作流：

1. **文字 + 双语 TTS 生成词汇/句子课件（如 300～303 课）**
   - 适用场景：N3/N2 红宝书词汇单元、自定义生词复习课、无现成音频的文本教材。
   - 核心特性：每个词条独立生成单条音频并缓存在 `vocab_bank/audio/{word_id}.mp3`，既可按单元批量打包（每课 30 词），也可随时按编号（如 `1-15, 1-61`）1 秒拼装自定义复习课。
2. **YouTube 视频 + 内生日文字幕生成精听课件（如 100/101/200/201 课）**
   - 适用场景：NHK 高中历史讲座、中田敦彦 YouTube 大学、日剧/新闻切片等。
   - 核心特性：提取原视频音频与时间轴字幕，转化为逐句跟读卡片。
3. **可选的「📚 词汇与语法解析」折叠面板（如 100/101/200/201 课）**
   - 核心特性：`app.js` 会自动检测每句 JSON 中是否包含 `"analysis"` 字段。
   - **按需启用**：若某句 JSON 含有非空的 `"analysis"` 字符串（支持 HTML 格式），前端卡片下方会自动渲染 `<details>` 折叠解析面板；若无该字段或为空（如 300～303 词汇课），则自动隐藏，保持界面清爽。

---

## 二、 目录与核心模块说明

```text
jp-reader/
├── index.html                      # 前端主页面
├── app.js                          # 播放器核心逻辑（含 localStorage 课程与句子断点记忆）
├── lessons-config.js               # 课程下拉菜单注册表 (window.LESSONS_CONFIG)
├── furigana.py                     # 【核心模块 1】假名注音转换与剥离模块
├── ocr_pdf.py                      # 【核心模块 2】macOS 原生 Vision 框架 PDF 高精度 OCR 提取器
├── tts_lesson_builder.py           # 【核心模块 3】文字 + Edge-TTS 双语音频合成与课件打包引擎
├── build_unit1_db.py               # 第一单元 (1-1~1-120) 词库入库与 NotebookLM 闪卡导出脚本
├── vocab_bank/
│   ├── unit1.json                  # 结构化单元词库（含 word_id, raw, jp_ruby）
│   └── audio/                      # 词条级独立 MP3 缓存 (如 1-1.mp3 ~ 1-120.mp3)
└── lessons/
    ├── 2026-300.mp3 / .json        # 生成后的课程音频与时间轴数据
    └── ...
```

---

## 三、 核心代码模块使用说明

### 1. 假名注音模块 (`furigana.py`)
前端原生支持 HTML `<ruby>漢字<rt>かな</rt></ruby>` 顶部假名显示。在编写或录入教材文本时，只需使用人类易读的 `漢字[かな]` 格式，调用 `furigana.py` 即可自动转换，且**会自动跳过 `[名]`、`[他動2]` 等词性方括号**：

```python
from furigana import to_ruby, strip_furigana

raw = "【1-61】 現[あらわ]れる ④ [自動2] 出现\n△月[つき]が現[あらわ]れる。/ 月亮出来。"
html_ruby = to_ruby(raw)
# 输出: 【1-61】 <ruby>現<rt>あらわ</rt></ruby>れる ④ [自動2] 出现...

clean_text = strip_furigana(raw)
# 输出供例句朗读的纯汉字文本: 【1-61】 現れる ④ [自動2] 出现...
```

### 2. 文字 + TTS 课件生成工作流 (`tts_lesson_builder.py`)

#### ⚠️ 关键防错机制（必读）：
日语单个词条（无上下文）发给 TTS 时，若保留汉字极易发生多音字误读（如 `現れる` 误读、或正则在 `[` 处错误截断导致送假名丢失）。因此 `tts_lesson_builder.py` 的 `extract_full_word_kana()` **强制将首行单词转换为纯假名（如 `現[あらわ]れる` -> `あらわれる`）发给 TTS 朗读两遍**，确保单词读音 100% 准确。

#### 用法 A：抽选不熟的词条编号，1 秒拼装自定义生词复习课
当单词音频已缓存在 `vocab_bank/audio/` 后，可直接通过命令行挑出任意词条生成新课：
```bash
python3 tts_lesson_builder.py \
  --db vocab_bank/unit1.json \
  --lesson-id 2026-399 \
  --word-ids "1-16,1-26,1-53,1-61,1-62,1-109"
```

---

## 四、 课件 JSON 标准数据格式规范

无论是「文字+TTS」、「YouTube 字幕切片」还是「带语法解析的精读课」，最终输出的 `lessons/{lesson_id}.json` 均遵循以下统一结构：

```json
[
  {
    "id": 1,
    "word_id": "1-61",
    "start": 0.2,
    "end": 16.54,
    "jp": "【1-61】 <ruby>現<rt>あらわ</rt></ruby>れる ④ [自動2] 出现，出来...",
    "cn": "（可选）独立中文翻译行，词汇课可留空字符串",
    "analysis": "（可选）📚 <b>重点词汇与语法解析：</b><br>・..."
  }
]
```

---

## 五、 发布与防缓存更新流程

1. 在 `lessons-config.js` 的 `window.LESSONS_CONFIG` 数组中注册新课程的 `id` 与 `title`。
2. 如修改了已有课程的同名 `.mp3`，请更新 `app.js` 中 `mp3Url` 的 `?v=xxx` 版本号以强制刷新浏览器缓存。
3. 提交并更新稳定标签 `v-stable`：
```bash
git add -A
git commit -m "feat: add new lessons"
git tag -f v-stable
git push && git push origin -f v-stable
```
