import json
import os
import sys
import librosa
import numpy as np

def generate_lesson(lesson_id, raw_items_text):
    mp3_path = f"lessons/{lesson_id}.mp3"
    json_path = f"lessons/{lesson_id}.json"
    
    if not os.path.exists(mp3_path):
        print(f"错误: 找不到音频文件 {mp3_path}，请先放入 lessons 目录。")
        return

    print(f"正在使用提示音指纹模型对 {lesson_id} 进行自动化打轴...")
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

    # 1. 载入我们在 302 课校准好的 1.2 秒提示音黄金指纹模板
    win_sec = 1.2
    win_frames = time_to_frame(win_sec)
    
    # 以 302 课第一个标准结束点 8.94s 为基准切出指纹
    ref_end_frame = time_to_frame(8.94)
    template = S_sub[:, ref_end_frame - win_frames : ref_end_frame]
    template_norm = template / (np.linalg.norm(template) + 1e-8)

    num_frames = S_sub.shape[1] - win_frames
    scores = np.zeros(num_frames)
    for i in range(num_frames):
        patch = S_sub[:, i : i + win_frames]
        scores[i] = np.sum(patch * template_norm) / (np.linalg.norm(patch) + 1e-8)

    # 2. 峰值检索（最小间隔 3.5 秒，相似度阈值 0.45）
    min_dist_frames = time_to_frame(3.5)
    detected_ends = []
    scores_copy = scores.copy()

    while True:
        best_idx = int(np.argmax(scores_copy))
        best_score = float(scores_copy[best_idx])
        if best_score < 0.45:
            break
        end_time = frame_to_time(best_idx + win_frames)
        detected_ends.append(end_time)
        left = max(0, best_idx - min_dist_frames)
        right = min(num_frames, best_idx + min_dist_frames)
        scores_copy[left:right] = 0.0

    detected_ends.sort()
    print(f"成功自动检测到 {len(detected_ends)} 个提示音结束节点！")

    # 3. 组装 JSON 结构（自动计算每句的 start 和 end）
    sentences = []
    current_start = 0.0
    for idx, end_t in enumerate(detected_ends):
        # 兼容文本条目数
        jp_text = raw_items_text[idx] if idx < len(raw_items_text) else f"第 {idx+1} 句词条"
        sentences.append({
            "id": idx + 1,
            "start": current_start,
            "end": end_t,
            "jp": jp_text,
            "cn": ""
        })
        current_start = end_t

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)

    print(f"🎉 自动化课件生成完毕: {json_path}")

if __name__ == "__main__":
    print("自动化课件生成脚本已就绪！")
