import os
import sys
import json
import re
import subprocess
import glob
import pykakasi
import webvtt

# ================= 配置区 =================
TARGET_URL = "https://www.youtube.com/watch?v=tl_PsLmNTsw"
RAW_PREFIX = "raw_108"
LESSON_DIR = "lessons"
START_LESSON_ID = 12
SLICE_DURATION_SEC = 240.0     # 切片目标时长（秒）
MAX_VALID_TIME_SEC = 1364.0    # 22分44秒截断 (剔除无字幕跟读)
# =========================================

kks = pykakasi.kakasi()

def generate_furigana(text):
    """
    严格合规的注音算法：仅汉字包裹 rt，送假名完全置于 ruby 外。
    """
    result = ""
    for item in kks.convert(text):
        orig = item['orig']
        hira = item['hira']
        
        if not re.search(r'[\u4e00-\u9faf]', orig):
            result += orig
            continue
            
        prefix_len = 0
        for i in range(min(len(orig), len(hira))):
            if orig[i] == hira[i]: prefix_len += 1
            else: break
                
        suffix_len = 0
        for i in range(1, min(len(orig)-prefix_len, len(hira)-prefix_len) + 1):
            if orig[-i] == hira[-i]: suffix_len += 1
            else: break
                
        prefix = orig[:prefix_len]
        suffix = orig[len(orig)-suffix_len:] if suffix_len > 0 else ""
        base_orig = orig[prefix_len:len(orig)-suffix_len] if suffix_len > 0 else orig[prefix_len:]
        base_hira = hira[prefix_len:len(hira)-suffix_len] if suffix_len > 0 else hira[prefix_len:]
        
        if base_orig:
            result += f"{prefix}<ruby>{base_orig}<rt>{base_hira}</rt></ruby>{suffix}"
        else:
            result += orig
            
    return result

def clean_vtt(filepath):
    captions = []
    if not os.path.exists(filepath):
        return captions

    for caption in webvtt.read(filepath):
        clean_text = re.sub(r'<[^>]+>', '', caption.text)
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        if not lines:
            continue
            
        dedup_lines = []
        for line in lines:
            if not dedup_lines or line not in dedup_lines[-1]:
                dedup_lines.append(line)
        final_text = ' '.join(dedup_lines)
        if not final_text:
            continue
            
        start = caption.start_in_seconds
        end = caption.end_in_seconds

        if start >= MAX_VALID_TIME_SEC:
            continue
        if end > MAX_VALID_TIME_SEC:
            end = MAX_VALID_TIME_SEC

        if captions:
            last = captions[-1]
            if final_text == last['text']:
                last['end'] = max(last['end'], end)
                continue
            if final_text.startswith(last['text']):
                last['text'] = final_text
                last['end'] = max(last['end'], end)
                continue
            if last['text'].startswith(final_text):
                last['end'] = max(last['end'], end)
                continue
                
        captions.append({'start': start, 'end': end, 'text': final_text})
    return captions

def slice_audio(input_audio, output_audio, start_sec, end_sec):
    cmd = [
        "ffmpeg", "-y", "-i", input_audio,
        "-ss", str(start_sec), "-to", str(end_sec),
        "-c:a", "libmp3lame", "-q:a", "2", output_audio
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def main():
    print(f"[*] 检查本地原始素材 ({RAW_PREFIX})...")
    
    mp3_path = f"{RAW_PREFIX}.mp3"
    ja_files = glob.glob(f"{RAW_PREFIX}.ja*.vtt")
    
    # 若缺失则触发下载
    if not os.path.exists(mp3_path) or not ja_files:
        print("[*] 触发 yt-dlp 抓取缺失的源数据...")
        dl_cmd = [
            "yt-dlp", "--extract-audio", "--audio-format", "mp3",
            "--write-auto-subs", "--sub-langs", "ja,zh-Hans",
            "-o", f"{RAW_PREFIX}.%(ext)s", TARGET_URL
        ]
        try:
            subprocess.run(dl_cmd, check=True)
            ja_files = glob.glob(f"{RAW_PREFIX}.ja*.vtt")
        except subprocess.CalledProcessError as e:
            print(f"[-] 抓取失败: {e}")
            sys.exit(1)

    if not ja_files:
        print("[-] 异常: 日文基准字幕缺失，构建阻断。")
        sys.exit(1)

    ja_file = ja_files[0]
    cn_files = glob.glob(f"{RAW_PREFIX}.zh-Hans*.vtt")
    cn_file = cn_files[0] if cn_files else None

    print("[*] 清洗 VTT 并处理边界...")
    ja_caps = clean_vtt(ja_file)
    cn_caps = clean_vtt(cn_file) if cn_file else []

    slices = []
    current_slice = []
    slice_start = 0.0

    for cap in ja_caps:
        current_slice.append(cap)
        if cap['end'] - slice_start >= SLICE_DURATION_SEC:
            slices.append({'start_time': slice_start, 'end_time': cap['end'], 'ja_caps': current_slice})
            slice_start = cap['end']
            current_slice = []

    if current_slice:
        slices.append({'start_time': slice_start, 'end_time': current_slice[-1]['end'], 'ja_caps': current_slice})

    os.makedirs(LESSON_DIR, exist_ok=True)
    current_lesson_id = START_LESSON_ID
    print(f"[*] 切分完毕，共划分为 {len(slices)} 个课件。")

    for slc in slices:
        slc_start = slc['start_time']
        slc_end = slc['end_time']
        formatted_id = f"2026-{current_lesson_id:03d}"
        
        print(f"[*] 构建 {formatted_id} (区间: {slc_start:.1f}s - {slc_end:.1f}s)...")
        out_mp3 = os.path.join(LESSON_DIR, f"{formatted_id}.mp3")
        slice_audio(mp3_path, out_mp3, slc_start, slc_end)

        lesson_data = []
        item_id = 1
        for ja in slc['ja_caps']:
            matched_cn_texts = []
            for cn in cn_caps:
                overlap = min(ja['end'], cn['end']) - max(ja['start'], cn['start'])
                if overlap > 0 and cn['text'] not in matched_cn_texts:
                    matched_cn_texts.append(cn['text'])

            rel_start = max(0.0, round(ja['start'] - slc_start, 3))
            rel_end = round(ja['end'] - slc_start, 3)

            lesson_data.append({
                "id": item_id,
                "start": rel_start,
                "end": rel_end,
                "jp": generate_furigana(ja['text']),
                "cn": " ".join(matched_cn_texts)
            })
            item_id += 1

        out_json = os.path.join(LESSON_DIR, f"{formatted_id}.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(lesson_data, f, ensure_ascii=False, indent=2)
            
        current_lesson_id += 1

if __name__ == "__main__":
    main()
