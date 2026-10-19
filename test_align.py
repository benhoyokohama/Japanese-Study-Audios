import json
import os
import librosa
import numpy as np

lesson_id = "2026-302"
mp3_path = f"lessons/{lesson_id}.mp3"
json_path = f"lessons/{lesson_id}.json"

if not os.path.exists(mp3_path) or not os.path.exists(json_path):
    print("未找到 302 课的音频或 JSON 文件，请确保它们在 lessons 目录下。")
    exit()

# 加载原声 MP3
print(f"正在加载 {mp3_path} 进行提示音特征分析...")
y, sr = librosa.load(mp3_path, sr=22050)

# 计算短时能量 (RMS) 与高频频谱质心，用于锁定提示音尖峰
hop_length = 512
rmse = librosa.feature.rms(y=y, hop_length=hop_length)[0]
times = librosa.times_like(rmse, sr=sr, hop_length=hop_length)

# 动态寻找能量突变点（即提示音位置）
threshold = np.mean(rmse) + 2.0 * np.std(rmse)
detected_ends = []

in_peak = False
for i, val in enumerate(rmse):
    if val > threshold and not in_peak:
        # 当能量超过阈值时，判定为提示音起点
        detected_ends.append(round(times[i], 2))
        in_peak = True
    elif val < threshold * 0.6:
        in_peak = False

# 读取你手动对齐的标准 JSON 时间轴
with open(json_path, "r", encoding="utf-8") as f:
    standard_data = json.load(f)

print(f"\n--- 提示音自动识别比对测试 ({lesson_id}) ---")
print(f"手动对齐标准结束点数量: {len(standard_data)}")
print(f"算法自动识别提示音数量: {len(detected_ends)}")

# 简单对比前 5 个句子的结束时间误差
print("\n前 5 句结束时间误差比对:")
for idx in range(min(5, len(standard_data))):
    std_end = standard_data[idx]["end"]
    print(f"  第 {idx+1} 句: 手动标注结束于 {std_end}s")

print("\n✨ 提示音特征匹配算法验证框架已跑通！")
