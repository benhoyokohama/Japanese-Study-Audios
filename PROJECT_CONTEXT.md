# 随身日语 (jp-reader) AI 协作交接档案

1. **本地路径**：`/Users/binhe/jp-reader` (虚拟环境 `source venv/bin/activate`)
2. **前端菜单双写**：新增/删除课程必须同步修改 `lessons-config.js` 和 `index.html` 的 `<select id="lessonSelect">`。
3. **JSON 字段规范**：
   - 播放器读取的是 `jp`（存放带 `<ruby>` 的 HTML）、`cn`（中文翻译）、`analysis`（语法词汇解析折叠面板）。
4. **送假名注音与朗读防重**：
   - `furigana.py` 的 `to_ruby()` 需将送假名留在 `<ruby>` 外（如 `<ruby>受<rt>う</rt></ruby>け<ruby>持<rt>も</rt></ruby>つ`）。
   - `tts_lesson_builder.py` 的 `extract_full_word_kana()` 必须只返回一次纯假名读音。
5. **当前进度**：
   - 第 1 课 (`2026-001` NHK新闻)、第 100~101 课、第 200~201 课已上线。
   - N3 词汇 Unit 1 ~ Unit 3 (`2026-300` ~ `2026-311`) 已上线。
   - 下一步待办：从 `vocab_bank/drafts/unit4_ocr.txt` 起构建 Unit 4 (`2026-312` ~ `2026-315`)。
