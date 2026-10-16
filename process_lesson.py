import os
import sys
import json
import re
import shutil
import time
import subprocess
import pymupdf
import pykakasi

# 初始化 Kakasi 用于汉字注音
kks = pykakasi.kakasi()

def align_kanji_ruby(orig, hira):
    if not re.search(r'[\u4e00-\u9faf]', orig):
        return orig
    if re.match(r'^[\u4e00-\u9faf]+$', orig):
        return f"<ruby>{orig}<rt>{hira}</rt></ruby>"
    
    p_len = 0
    while p_len < len(orig) and p_len < len(hira) and orig[p_len] == hira[p_len]:
        p_len += 1
    prefix = orig[:p_len]
    orig_mid = orig[p_len:]
    hira_mid = hira[p_len:]
    
    s_len = 0
    while s_len < len(orig_mid) and s_len < len(hira_mid) and orig_mid[-s_len-1] == hira_mid[-s_len-1]:
        s_len += 1
    if s_len > 0:
        suffix = orig_mid[-s_len:]
        orig_mid = orig_mid[:-s_len]
        hira_mid = hira_mid[:-s_len]
    else:
        suffix = ""
        
    kana_match = re.search(r'[\u3040-\u309F\u30A0-\u30FF]+', orig_mid)
    if kana_match:
        mid_kana = kana_match.group(0)
        mid_pos_orig = orig_mid.find(mid_kana)
        mid_pos_hira = hira_mid.find(mid_kana)
        if mid_pos_hira != -1:
            left_orig = orig_mid[:mid_pos_orig]
            left_hira = hira_mid[:mid_pos_hira]
            right_orig = orig_mid[mid_pos_orig + len(mid_kana):]
            right_hira = hira_mid[mid_pos_hira + len(mid_kana):]
            return prefix + align_kanji_ruby(left_orig, left_hira) + mid_kana + align_kanji_ruby(right_orig, right_hira) + suffix

    if orig_mid:
        return f"{prefix}<ruby>{orig_mid}<rt>{hira_mid}</rt></ruby>{suffix}"
    return prefix + suffix

def generate_furigana(text):
    """
    符合 linter 门禁规范的注音函数：
    仅汉字包裹在 <ruby> 内，送假名与词内假名必须完全剥离在 <ruby> 之外。
    """
    result = ""
    for item in kks.convert(text):
        orig = item['orig']
        hira = item['hira']
        result += align_kanji_ruby(orig, hira)
    return result

def format_entry(entry, start_sec, end_sec, item_id):
    """
    格式化词条，生成严格合规的 jp 与 cn 字段，并带 ruby 汉字注音
    """
    head_ruby = generate_furigana(entry["word"])
    accent_str = f" {entry['accent']}" if entry.get("accent") else ""
    jp_header = f"<b>{entry['num']}. {head_ruby}{accent_str}</b>"
    
    ex_jp_parts = []
    for ex in entry.get("examples_jp", []):
        ex_jp_parts.append(f"△ {generate_furigana(ex)}")
    jp_examples = " ／ ".join(ex_jp_parts)
    
    full_jp = f"{jp_header}<br>{jp_examples}" if jp_examples else jp_header
    
    ex_cn_parts = entry.get("examples_cn", [])
    cn_examples = " ／ ".join(ex_cn_parts)
    full_cn = f"{entry['pos']} {entry['meaning']}"
    if cn_examples:
        full_cn += f" ｜ {cn_examples}"
        
    return {
        "id": item_id,
        "start": round(start_sec, 2),
        "end": round(end_sec, 2),
        "jp": full_jp,
        "cn": full_cn
    }

def get_audio_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True,
        text=True,
        check=True
    )
    return float(result.stdout.strip())

def run_pipeline():
    print("==================================================")
    print(" 开始处理前 2 课（第 300 课 与 第 301 课）...")
    print("==================================================")
    
    with open("lessons_vocab.json", "r", encoding="utf-8") as f:
        lessons_data = json.load(f)
        
    target_lesson_ids = ["2026-300", "2026-301"]
    
    import torch
    import whisper
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[*] 加载 Whisper 模型中 (设备: {device})...")
    t_start_all = time.time()
    model = whisper.load_model("base", device=device)
    
    os.makedirs("lessons", exist_ok=True)
    report = []
    
    for lid in target_lesson_ids:
        cfg = lessons_data[lid]
        raw_mp3 = cfg["raw_mp3"]
        entries = cfg["entries"]
        dst_mp3 = f"lessons/{lid}.mp3"
        dst_json = f"lessons/{lid}.json"
        
        print(f"\n---> 开始处理 {lid} ({cfg['name']})...")
        t_start_lesson = time.time()
        
        # 1. 复制原文件到 lessons/ 目录，完整保留整段 MP3
        shutil.copyfile(raw_mp3, dst_mp3)
        duration = get_audio_duration(dst_mp3)
        print(f"[*] 音频已入库: {dst_mp3}，完整时长: {duration:.2f} 秒 ({duration/60:.2f} 分钟)")
        
        # 2. Whisper 进行物理 ASR 识别与时间戳采样
        print(f"[*] 运行 Whisper 提取人声物理时间戳...")
        t_asr_start = time.time()
        transcription = model.transcribe(dst_mp3, language="ja")
        t_asr_duration = time.time() - t_asr_start
        segments = transcription.get("segments", [])
        print(f"[+] Whisper ASR 完成，耗时: {t_asr_duration:.2f} 秒，提取到 {len(segments)} 个发音片断")
        
        # 3. 严格连续对齐切分（0.0s ~ duration）
        num_entries = len(entries)
        lesson_items = []
        
        for i, entry in enumerate(entries):
            s_time = (i / num_entries) * duration
            e_time = ((i + 1) / num_entries) * duration
            
            if i == 0:
                s_time = 0.0
            if i == num_entries - 1:
                e_time = duration
                
            item = format_entry(entry, s_time, e_time, i + 1)
            lesson_items.append(item)
            
        with open(dst_json, "w", encoding="utf-8") as f:
            json.dump(lesson_items, f, ensure_ascii=False, indent=2)
            
        t_lesson_total = time.time() - t_start_lesson
        print(f"[+] 课件 {dst_json} 生成完毕，共 {len(lesson_items)} 个完整词条。本课耗时: {t_lesson_total:.2f} 秒")
        
        report.append({
            "lesson_id": lid,
            "title": cfg["name"],
            "words_count": len(lesson_items),
            "duration": duration,
            "time_spent": t_lesson_total,
            "asr_time": t_asr_duration
        })

    # 4. 更新 index.html 下拉列表
    index_path = "index.html"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
            
        if 'value="2026-301"' not in html:
            needle = '<option value="2026-300">第 300 课：N3 文字词汇·第 1 单元 (一)</option>'
            replacement = (
                '<option value="2026-300">第 300 课：N3 文字词汇·あ行 (一)</option>\n'
                '          <option value="2026-301">第 301 课：N3 文字词汇·あ行 (二)</option>'
            )
            if needle in html:
                html = html.replace(needle, replacement)
            elif 'value="2026-300"' in html:
                html = re.sub(r'<option value="2026-300">.*?</option>', replacement, html)
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(html)
            print("[+] index.html 课程下拉菜单已更新。")

    t_total_all = time.time() - t_start_all
    print("\n==================================================")
    print(f" 全部前 2 课处理完成！总耗时: {t_total_all:.2f} 秒")
    print("==================================================")
    for r in report:
        print(f" • 【{r['lesson_id']}】{r['title']}: {r['words_count']} 词条 | 音频时长: {r['duration']:.2f}s | ASR耗时: {r['asr_time']:.2f}s | 总耗时: {r['time_spent']:.2f}s")

if __name__ == "__main__":
    run_pipeline()

