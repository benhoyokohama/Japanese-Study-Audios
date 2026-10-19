import json
import librosa
import numpy as np

mp3_path = "lessons/2026-302.mp3"
json_path = "lessons/2026-302.json"

with open(json_path, "r", encoding="utf-8") as f:
    std_data = json.load(f)

std_ends = [float(item["end"]) for item in std_data]

y, sr = librosa.load(mp3_path, sr=16000)
hop_length = 256
S = np.abs(librosa.stft(y, n_fft=1024, hop_length=hop_length))

freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
valid_bins = (freqs >= 400) & (freqs <= 4000)
S_sub = S[valid_bins, :]

def time_to_frame(t):
    return int(round(t * sr / hop_length))

def frame_to_time(f):
    return round(f * hop_length / sr, 2)

# 1. 将标准模板缩短为 1.2 秒（聚焦提示音最核心的头部与衰减段）
win_sec = 1.2
win_frames = time_to_frame(win_sec)
first_end_frame = time_to_frame(std_ends[0])
template = S_sub[:, first_end_frame - win_frames : first_end_frame]
template_norm = template / (np.linalg.norm(template) + 1e-8)

num_frames = S_sub.shape[1] - win_frames
scores = np.zeros(num_frames)
for i in range(num_frames):
    patch = S_sub[:, i : i + win_frames]
    scores[i] = np.sum(patch * template_norm) / (np.linalg.norm(patch) + 1e-8)

# 诊断一下刚才漏掉的 29.54s 附近 (27s ~ 32s) 的最高匹配得分是多少
f_start = time_to_frame(27.0) - win_frames
f_end = time_to_frame(32.0) - win_frames
local_best_idx = f_start + int(np.argmax(scores[f_start:f_end]))
print(f"[Diagnostic] Around 29.54s, peak is at {frame_to_time(local_best_idx + win_frames)}s with score {scores[local_best_idx]:.3f}")

# 2. 将最小间隔设为 3.5 秒（兼容无例句的短词条），阈值设为 0.45
min_dist_frames = time_to_frame(3.5)
detected_ends = []
scores_copy = scores.copy()

while True:
    best_idx = int(np.argmax(scores_copy))
    best_score = float(scores_copy[best_idx])
    if best_score < 0.45:
        break
    end_time = frame_to_time(best_idx + win_frames)
    detected_ends.append((end_time, round(best_score, 3)))
    left = max(0, best_idx - min_dist_frames)
    right = min(num_frames, best_idx + min_dist_frames)
    scores_copy[left:right] = 0.0

detected_ends.sort(key=lambda x: x[0])

print(f"\nManual count  : {len(std_ends)} | Detected count: {len(detected_ends)}\n")
print(f"{'No.':<4} | {'Manual(s)':<10} | {'Detected(s)':<12} | {'Diff(s)':<8} | {'Confidence'}")
print("-" * 55)

max_len = max(len(std_ends), len(detected_ends))
for i in range(max_len):
    m_str = f"{std_ends[i]:.2f}" if i < len(std_ends) else "---"
    if i < len(detected_ends):
        d_val, conf = detected_ends[i]
        d_str = f"{d_val:.2f}"
        diff_str = f"{d_val - std_ends[i]:+.2f}" if i < len(std_ends) else "---"
        conf_str = f"{conf:.3f}"
    else:
        d_str, diff_str, conf_str = "---", "---", "---"
    print(f"{i+1:<4} | {m_str:<10} | {d_str:<12} | {diff_str:<8} | {conf_str}")
