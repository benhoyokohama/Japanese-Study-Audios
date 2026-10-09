import asyncio
import os
import json
import edge_tts
import re

LESSON_ID = "2026-001"
JSON_PATH = f"lessons/{LESSON_ID}.json"
MP3_PATH = f"lessons/{LESSON_ID}.mp3"

async def regenerate_audio():
    print(f"[*] 开始针对单课 {LESSON_ID} 进行强制假名纠错音频重合成...")
    if not os.path.exists(JSON_PATH):
        print(f"[!] 找不到 {JSON_PATH}")
        return
        
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        sentences = json.load(f)
        
    full_text = ""
    for item in sentences:
        jp_text = item["jp"]
        # 核心纠错：在送往 TTS 朗读时，将容易读错的“海兵隊”直接替换为正确的假名串
        clean_text = jp_text.replace("海兵隊", "かいへいたい")
        # 剥离所有 ruby 标签，仅保留纯文本供 TTS 朗读
        clean_text = re.sub(r'<ruby>(.*?)<rt>.*?</rt></ruby>', r'\1', clean_text)
        full_text += clean_text + " "

    print(f"[*] 正在调用 edge-tts 生成完美纠错音频...")
    communicate = edge_tts.Communicate(full_text.strip(), "ja-JP-NanamiNeural")
    await communicate.save(MP3_PATH)
    print(f"[+] 课件 {LESSON_ID} 音频已强制重合成完毕: {MP3_PATH}")

if __name__ == "__main__":
    asyncio.run(regenerate_audio())
