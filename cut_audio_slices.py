import os
import subprocess

SLICES = [
    ("2026-007", 0.0, 150.0),
    ("2026-008", 150.0, 330.0),
    ("2026-009", 330.0, 630.0),
    ("2026-010", 630.0, 960.0),
    ("2026-011", 960.0, 1565.0)
]

URL = "https://youtu.be/DB-x1ro2NZ4"

def cut_slices():
    os.makedirs("lessons", exist_ok=True)
    for lid, start, end in SLICES:
        mp3_path = f"lessons/{lid}.mp3"
        if os.path.exists(mp3_path):
            print(f"Audio file already exists, skipping: {mp3_path}")
            continue
            
        print(f"Generating {lid}.mp3 (Range: {start}s - {end}s)...")
        section_arg = f"*{start}-{end}"
        cmd = [
            "yt-dlp", "-x", "--audio-format", "mp3",
            "--download-sections", section_arg,
            "-o", f"lessons/{lid}.%(ext)s",
            URL
        ]
        try:
            subprocess.run(cmd, check=True)
            print(f"Successfully generated: {mp3_path}")
        except Exception as e:
            print(f"Failed to generate {lid}.mp3: {e}")

if __name__ == "__main__":
    cut_slices()
