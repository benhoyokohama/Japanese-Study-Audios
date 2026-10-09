import asyncio
import os
import json
import edge_tts

LESSON_ID = "2026-001"
JSON_PATH = f"lessons/{LESSON_ID}.json"
MP3_PATH = f"lessons/{LESSON_ID}.mp3"

async def regenerate_audio():
    print(f"[*] 开始针对单课 {LESSON_ID} 进行精准音频重合成...")
    if not os.path.exists(JSON_PATH):
        print(f"[!] 找不到 {JSON_PATH}")
        return
        
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        sentences = json.load(f)
        
    # 为了让 edge-tts 彻底正确朗读“海兵隊”，我们在送往 TTS 合成时，
    # 可以将该句中的汉字显式替换为假名或调整注音文本，确保发音为「かいへいたい」
    # 比如将原文本中的 “海兵隊” 替换为 “かいへいたい” 专门用于语音合成流
    full_text = ""
    for item in sentences:
        # 针对第2句中的海兵隊进行文本层面的 TTS 纠错适配
        jp_text = item["jp"]
        # 移除 ruby 标签保留纯文本，或将海兵隊替换为平假名以供 TTS 完美朗读
        clean_text = jp_text.replace("<ruby>海兵隊<rt>かいへいたい</rt></ruby>", "かいへいたい")
        # 清理其他 ruby 标签（保留纯文本供 TTS 朗读）
        import re
        clean_text = re.sub(r'<ruby>(.*?)<rt>.*?</rt></ruby>', r'\1', clean_text)
        full_text += clean_text + " "

    print(f"[*] 正在调用 edge-tts 合成纠错音频...")
    communicate = edge_tts.Communicate(full_text.strip(), "ja-JP-NanamiNeural")
    await communicate.save(MP3_PATH)
    print(f"[+] 课件 {LESSON_ID} 音频已成功重新合成并覆盖: {MP3_PATH}")

if __name__ == "__main__":
    asyncio.run(regenerate_audio())
