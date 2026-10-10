import os
import subprocess

# 假设源大音频文件名为 source_full.mp3（如果之前下载成了别的名字可以对应调整）
SOURCE_AUDIO = "lessons/2026-007_full.mp3" # 或者直接用已有的大文件

SLICES = [
    ("2026-007", 0.0, 150.0),
    ("2026-008", 150.0, 330.0),
    ("2026-009", 330.0, 630.0),
    ("2026-010", 630.0, 960.0),
    ("2026-011", 960.0, 1565.0)
]

def local_slice():
    if not os.path.exists(SOURCE_AUDIO):
        print(f"[!] 找不到本地源音频文件: {SOURCE_AUDIO}，将使用 yt-dlp 从本地缓存切片。")
        return

    os.makedirs("lessons", exist_ok=True)
    for lid, start, end in SLICES:
        out_path = f"lessons/{lid}.mp3"
        duration = end - start
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-i", SOURCE_AUDIO,
            "-t", str(duration), "-acodec", "copy", out_path
        ]
        print(f"[*] 正在本地切片: {lid}.mp3 (从 {start}s 到 {end}s)")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    print("[+] 本地快速切片全部完成！")

if __name__ == "__main__":
    local_slice()
