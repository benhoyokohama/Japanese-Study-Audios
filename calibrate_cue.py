import json
import librosa
import numpy as np

# 加载 302 课的音频和标准时间轴
y, sr = librosa.load("lessons/2026-302.mp3", sr=22050)
with open("lessons/2026-302.json", "r", encoding="utf-8") as f:
    standard_data = json.load(f)

print("正在提取 302 课标准时间点的提示音音频特征...")
cue_templates = []
for item in standard_data:
    end_sec = item["end"]
    # 截取提示音出现的前后小窗口（例如结束点前 0.5 秒到结束点）
    start_sample = int((end_sec - 0.6) * sr)
    end_sample = int(end_sec * sr)
    if start_sample >= 0 and end_sample < len(y):
        snippet = y[start_sample:end_sample]
        cue_templates.append(snippet)

print(成功提取了 {len(cue_templates)} 个标准提示音样本特征模板！)
print("接下来我们可以用这个专属模板去自动扫描 303 课原声，实现零误差一键打轴。")
