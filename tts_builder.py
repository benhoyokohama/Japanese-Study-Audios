import os
import re
import json
import asyncio
import edge_tts
from pydub import AudioSegment
from furigana import strip_furigana

VOICE_JA = "ja-JP-NanamiNeural"
VOICE_ZH = "zh-CN-XiaoxiaoNeural"

AUDIO_BANK_DIR = "vocab_bank/audio"
os.makedirs(AUDIO_BANK_DIR, exist_ok=True)
os.makedirs("temp_tts", exist_ok=True)

def parse_item_to_segments(raw_text: str):
    """1つの単語データを [(言語, 読み上げテキスト, ポーズms), ...] に分解する"""
    lines = raw_text.strip().split('\n')
    segs = []
    
    first_line = lines[0].strip()
    # 1. アクセント記号や [品詞] の前の日本語単語を抽出
    word_part = re.split(r'\s*(?:[⓪①②③④⑤⑥⑦⑧⑨⑩]|\[)', first_line)[0]
    word_ja = strip_furigana(word_part).strip()
    word_ja_clean = word_ja.lstrip("～~")
    
    # 2. 最後の ] より後ろの中国語意味を抽出
    last_bracket_idx = first_line.rfind(']')
    meaning_zh = first_line[last_bracket_idx + 1:].strip() if last_bracket_idx != -1 else ""
    # 括弧内の補足説明を整理
    meaning_zh_clean = re.sub(r'（.*?）|\(.*?\)', '', meaning_zh).strip()
    if not meaning_zh_clean:
        meaning_zh_clean = meaning_zh
        
    segs.append(("ja", f"{word_ja_clean}。{word_ja_clean}。", 300))
    if meaning_zh_clean:
        segs.append(("zh", f"{meaning_zh_clean}。", 400))
        
    for line in lines[1:]:
        line = line.lstrip('△').strip()
        if '/' in line:
            ex_ja, ex_zh = line.split('/', 1)
            ex_ja = strip_furigana(ex_ja).strip()
            ex_zh = ex_zh.strip()
            if ex_ja == "AイコールB":
                ex_ja = "エー イコール ビー"
            segs.append(("ja", ex_ja, 250))
            segs.append(("zh", ex_zh, 450))
            
    return segs

async def synth_segment(lang: str, text: str, out_path: str):
    voice = VOICE_JA if lang == "ja" else VOICE_ZH
    rate = "-5%" if lang == "ja" else "+0%"
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(out_path)
            return
        except Exception as e:
            if attempt == 2:
                raise e
            await asyncio.sleep(1.5)

async def ensure_word_audio(word_record: dict) -> AudioSegment:
    """単語ごとの音声ファイル (vocab_bank/audio/{word_id}.mp3) を生成またはキャッシュから読み込む"""
    wid = word_record["word_id"]
    cached_mp3 = os.path.join(AUDIO_BANK_DIR, f"{wid}.mp3")
    
    if os.path.exists(cached_mp3) and os.path.getsize(cached_mp3) > 1000:
        return AudioSegment.from_mp3(cached_mp3)
        
    segs = parse_item_to_segments(word_record["raw"])
    item_audio = AudioSegment.empty()
    
    for s_idx, (lang, text, pause_ms) in enumerate(segs):
        tmp_mp3 = f"temp_tts/{wid}_{s_idx}.mp3"
        await synth_segment(lang, text, tmp_mp3)
        seg_audio = AudioSegment.from_mp3(tmp_mp3)
        item_audio += seg_audio + AudioSegment.silent(duration=pause_ms)
        if os.path.exists(tmp_mp3):
            os.remove(tmp_mp3)
            
    # 単語末尾の余白 500ms
    item_audio += AudioSegment.silent(duration=500)
    item_audio.export(cached_mp3, format="mp3", bitrate="128k")
    return item_audio

async def compile_lesson(lesson_id: str, title: str, word_records: list):
    """指定された単語リストから1課分の MP3 と JSON を生成する"""
    print(f"\n🎧 正在生成 {lesson_id} ({title}) - 共 {len(word_records)} 词...")
    full_audio = AudioSegment.silent(duration=200)
    sentences = []
    
    for idx, rec in enumerate(word_records, 1):
        wid = rec["word_id"]
        start_sec = round(len(full_audio) / 1000.0, 2)
        word_audio = await ensure_word_audio(rec)
        full_audio += word_audio
        end_sec = round(len(full_audio) / 1000.0, 2)
        
        sentences.append({
            "id": idx,
            "word_id": wid,
            "start": start_sec,
            "end": end_sec,
            "jp": rec["jp_ruby"],
            "cn": ""
        })
        first_line_preview = rec["raw"].splitlines()[0][:28]
        print(f"  [{idx:02d}/{len(word_records)}] 【{wid}】 {first_line_preview} ({start_sec:.2f}s ~ {end_sec:.2f}s)")
        
    mp3_out = f"lessons/{lesson_id}.mp3"
    json_out = f"lessons/{lesson_id}.json"
    full_audio.export(mp3_out, format="mp3", bitrate="128k")
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)
    print(f"✅ {lesson_id} 完成！总时长: {len(full_audio)/1000.0:.2f} 秒")

async def main():
    with open("vocab_bank/unit1.json", "r", encoding="utf-8") as f:
        unit1 = json.load(f)
        
    lessons_plan = [
        ("2026-300", "第 300 课：N3 词汇·第一单元 (1) [1-1~1-30]", unit1[0:30]),
        ("2026-301", "第 301 课：N3 词汇·第一单元 (2) [1-31~1-60]", unit1[30:60]),
        ("2026-302", "第 302 课：N3 词汇·第一单元 (3) [1-61~1-90]", unit1[60:90]),
        ("2026-303", "第 303 课：N3 词汇·第一单元 (4) [1-91~1-120]", unit1[90:120]),
    ]
    
    for lid, title, records in lessons_plan:
        await compile_lesson(lid, title, records)
        
    # lessons-config.js のタイトルとデフォルト設定を更新
    if os.path.exists("lessons-config.js"):
        with open("lessons-config.js", "r", encoding="utf-8") as f:
            cfg = f.read()
        # 2026-304 の行があれば削除し、300~303 のタイトルを更新
        cfg = re.sub(r'^\s*\{[^}]*2026-304[^}]*\},?\n?', '', cfg, flags=re.MULTILINE)
        cfg = cfg.replace("default: true", "default: false")
        for lid, title, _ in lessons_plan:
            cfg = re.sub(
                rf'(id:\s*["\']{lid}["\']\s*,\s*title:\s*["\'])[^"\']*(["\'])',
                rf'\g<1>{title}\g<2>',
                cfg
            )
        # 2026-300 をデフォルト表示に設定
        cfg = re.sub(
            r'(id:\s*["\']2026-300["\'][^}]*default:\s*)false',
            r'\1true',
            cfg
        )
        with open("lessons-config.js", "w", encoding="utf-8") as f:
            f.write(cfg)
        print("\n✅ 已更新 lessons-config.js 课程目录名称！")

if __name__ == "__main__":
    asyncio.run(main())
