import os
import sys
import json
import whisper

LESSONS = ["2026-007", "2026-008", "2026-009", "2026-010", "2026-011"]

def process_lessons():
    print("[*] 正在加载 Whisper base 模型...")
    model = whisper.load_model("base")
    
    for lid in LESSONS:
        mp3_path = f"lessons/{lid}.mp3"
        json_path = f"lessons/{lid}.json"
        
        if not os.path.exists(mp3_path):
            print(f"[!] 找不到物理音频 {mp3_path}，跳过。")
            continue
            
        print(f"[*] 正在对 {lid}.mp3 进行底层物理 ASR 识别与毫秒级时间戳提取...")
        result = model.transcribe(mp3_path, language="ja")
        
        segments_data = []
        for i, segment in enumerate(result["segments"]):
            segments_data.append({
                "id": i + 1,
                "start": round(segment["start"], 2),
                "end": round(segment["end"], 2),
                "jp": segment["text"].strip(),
                "cn": "" 
            })
            
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(segments_data, f, ensure_ascii=False, indent=4)
            
        print(f"[+] 课件 {lid}.json 覆写完毕：成功解析出 {len(segments_data)} 个精准独立句段。")

if __name__ == "__main__":
    process_lessons()
