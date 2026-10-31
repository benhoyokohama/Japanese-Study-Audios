#!/usr/bin/env python3
"""
随身日语 (jp-reader) - 文字 + TTS 课件生成标准引擎 (支持多音字自动精准注音朗读)
"""
import os
import re
import json
import asyncio
import argparse
import edge_tts
from pydub import AudioSegment
from furigana import POS_PATTERN, RUBY_PATTERN, to_ruby, strip_furigana

VOICE_JA = "ja-JP-NanamiNeural"
VOICE_ZH = "zh-CN-XiaoxiaoNeural"
AUDIO_BANK_DIR = "vocab_bank/audio"

os.makedirs(AUDIO_BANK_DIR, exist_ok=True)
os.makedirs("temp_tts", exist_ok=True)

def extract_full_word_kana(first_line: str) -> str:
    """提取词条首行完整纯假名读音（支持整词注音与单字注音，绝不重复朗读）"""
    word_part = first_line.strip().split()[0]
    word_part = re.sub(r'\[([^\]]+)\]', lambda m: '' if POS_PATTERN.match(m.group(1).strip()) else m.group(0), word_part)
    word_part = re.sub(r'[⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫～~〜・]', '', word_part).strip()

    brackets = re.findall(r'\[([ぁ-んァ-ンー]+)\]', word_part)
    if len(brackets) == 1 and word_part.endswith(f"[{brackets[0]}]"):
        base_before = word_part[:word_part.rfind('[')]
        kana_inside = brackets[0]
        m_tail = re.search(r'([ぁ-ん]+)$', base_before)
        if (m_tail and kana_inside.endswith(m_tail.group(1))) or (base_before[:1] in 'おご' and kana_inside.startswith(base_before[:1])):
            return kana_inside

    res = re.sub(r'[一-龥々ヶ]+\[([ぁ-んァ-ンー]+)\]', lambda m: m.group(1), word_part)
    return res.strip()

def prepare_tts_ja_sentence(ex_ja: str, head_line: str) -> str:
    """将例句中的 漢字[かな] 100% 转换为所标注的精确假名送入 TTS，彻底杜绝多音字误读"""
    ex_ja = re.sub(r"([〜~])([一-龥々ヶ]+)\[[〜~]([ぁ-んァ-ンー]+)\]", r"\1\2[\3]", ex_ja)
    ex_ja = re.sub(r"[一-龥々ヶ]+\[([ぁ-んァ-ンー]+)\]", lambda m: m.group(1), ex_ja)
    ex_ja = strip_furigana(ex_ja).strip()
    if ex_ja == "AイコールB":
        ex_ja = "エー イコール ビー"
    return ex_ja

def parse_item_to_segments(raw_text: str):
    """将词条原始文本拆解为 [(语言, 朗读文本, 停顿毫秒), ...]"""
    lines = raw_text.strip().split('\n')
    segs = []
    first_line = lines[0].strip()

    word_kana = extract_full_word_kana(first_line)
    segs.append(("ja", f"{word_kana}。{word_kana}。", 300))

    last_bracket_idx = first_line.rfind(']')
    meaning_zh = first_line[last_bracket_idx + 1:].strip() if last_bracket_idx != -1 else ""
    meaning_zh_clean = re.sub(r'（.*?）|\(.*?\)', '', meaning_zh).strip() or meaning_zh
    if meaning_zh_clean:
        segs.append(("zh", f"{meaning_zh_clean}。", 400))

    for line in lines[1:]:
        line = line.lstrip('△').strip()
        if '/' in line:
            ex_ja, ex_zh = line.split('/', 1)
            ex_ja = prepare_tts_ja_sentence(ex_ja, first_line)
            ex_zh = ex_zh.strip()
            segs.append(("ja", ex_ja, 250))
            segs.append(("zh", ex_zh, 450))
    return segs

async def synth_segment(lang: str, text: str, out_path: str):
    voice = VOICE_JA if lang == "ja" else VOICE_ZH
    rate = "-5%" if lang == "ja" else "+0%"
    for attempt in range(5):
        try:
            comm = edge_tts.Communicate(text, voice, rate=rate)
            await asyncio.wait_for(comm.save(out_path), timeout=12.0)
            return
        except Exception:
            await asyncio.sleep(1.5)
    raise RuntimeError(f"TTS 合成超时失败: {text}")

async def ensure_word_audio(rec: dict, force: bool = False) -> AudioSegment:
    wid = rec["word_id"]
    cached_mp3 = os.path.join(AUDIO_BANK_DIR, f"{wid}.mp3")
    if not force and os.path.exists(cached_mp3) and os.path.getsize(cached_mp3) > 1000:
        return AudioSegment.from_mp3(cached_mp3)

    segs = parse_item_to_segments(rec["raw"])
    print(f"  🎙️ 合成词条 【{wid:5s}】 -> {segs[0][1]} | 例句: {[s[1] for s in segs[2:] if s[0]=='ja']}", flush=True)
    item_audio = AudioSegment.empty()
    for s_idx, (lang, text, pause_ms) in enumerate(segs):
        tmp = f"temp_tts/{wid}_{s_idx}.mp3"
        await synth_segment(lang, text, tmp)
        item_audio += AudioSegment.from_mp3(tmp) + AudioSegment.silent(duration=pause_ms)
        if os.path.exists(tmp):
            os.remove(tmp)

    item_audio += AudioSegment.silent(duration=500)
    item_audio.export(cached_mp3, format="mp3", bitrate="128k")
    return item_audio

async def build_lesson(lesson_id: str, records: list, force_audio: bool = False):
    print(f"\n📦 正在构建课程 {lesson_id} (共 {len(records)} 词)...")
    full_audio = AudioSegment.silent(duration=200)
    sentences = []

    for idx, rec in enumerate(records, 1):
        wid = rec["word_id"]
        start_sec = round(len(full_audio) / 1000.0, 2)
        word_audio = await ensure_word_audio(rec, force=force_audio)
        full_audio += word_audio
        end_sec = round(len(full_audio) / 1000.0, 2)

        jp_html = to_ruby(f"【{wid}】 {rec['raw']}")
        rec["jp_ruby"] = jp_html
        item_data = {
            "id": idx,
            "word_id": wid,
            "start": start_sec,
            "end": end_sec,
            "jp": jp_html,
            "cn": rec.get("cn", "")
        }
        if rec.get("analysis"):
            item_data["analysis"] = rec["analysis"]
        sentences.append(item_data)

    mp3_out = f"lessons/{lesson_id}.mp3"
    json_out = f"lessons/{lesson_id}.json"
    full_audio.export(mp3_out, format="mp3", bitrate="128k")
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)
    print(f"✅ 课程 {lesson_id} 构建完成！总时长: {len(full_audio)/1000.0:.2f}s")
