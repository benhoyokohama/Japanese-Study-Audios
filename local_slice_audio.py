import os
import subprocess
import sys

# 1. 隔离源文件，避免 ffmpeg 输入输出重名冲突
original_file = "lessons/2026-007.mp3"
source_file = "lessons/source_26min_temp.mp3"

if os.path.exists(original_file):
    # 简单的安全校验：如果文件大于 5MB，认定为 26 分钟的原大文件
    if os.path.getsize(original_file) > 5 * 1024 * 1024:
        os.rename(original_file, source_file)
        print(f"[*] 已将原始大音频安全重命名为 {source_file}")
    elif not os.path.exists(source_file):
        print(f"[!] {original_file} 文件过小，不像是完整的 26 分钟音频，且找不到暂存源文件。请核实！")
        sys.exit(1)
elif not os.path.exists(source_file):
    print(f"[!] 找不到源音频文件 {original_file} 或 {source_file}。请确认 26 分钟音频的位置。")
    sys.exit(1)

# 2. 定义黄金颗粒度切片边界
SLICES = [
    ("2026-007", 0.0, 150.0),
    ("2026-008", 150.0, 330.0),
    ("2026-009", 330.0, 630.0),
    ("2026-010", 630.0, 960.0),
    ("2026-011", 960.0, 1565.0)
]

# 3. 严格执行本地流式切片
for lid, start, end in SLICES:
    out_path = f"lessons/{lid}.mp3"
    duration = end - start
    print(f"[*] 正在秒级切片: {out_path} (区间: {start}s - {end}s)")
    
    # 遵循 ffmpeg 最佳实践：-ss 放在 -i 前面实现极速寻址，使用 -c copy 免二次编码
    cmd = [
        "ffmpeg", "-y", 
        "-ss", str(start), 
        "-t", str(duration), 
        "-i", source_file, 
        "-c", "copy", 
        out_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] 成功生成规范音频: {out_path}")
    except subprocess.CalledProcessError as e:
        print(f"[!] 切片失败 {lid}.mp3: 请检查 ffmpeg 状态。")
        sys.exit(1)

print("SUCCESS: 物理音频本地切片全部完成。")
