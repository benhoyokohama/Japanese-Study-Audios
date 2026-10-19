import os
import librosa
import numpy as np

TEMPLATE_PATH = "cue_template.npy"
SR = 16000
HOP_LENGTH = 256
N_FFT = 1024
WIN_SEC = 1.2

def _time_to_frame(t):
    return int(round(t * SR / HOP_LENGTH))

def _frame_to_time(f):
    return round(f * HOP_LENGTH / SR, 2)

def _extract_sub_spec(mp3_path):
    y, _ = librosa.load(mp3_path, sr=SR)
    S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP_LENGTH))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=N_FFT)
    valid_bins = (freqs >= 400) & (freqs <= 4000)
    return S[valid_bins, :]

def build_global_template(ref_mp3="lessons/2026-302.mp3", ref_end_sec=8.94):
    """从已验证的 302 课第 1 个提示音提取全局唯一标准模板并持久化保存"""
    S_sub = _extract_sub_spec(ref_mp3)
    win_frames = _time_to_frame(WIN_SEC)
    end_frame = _time_to_frame(ref_end_sec)
    template = S_sub[:, end_frame - win_frames : end_frame]
    template_norm = template / (np.linalg.norm(template) + 1e-8)
    np.save(TEMPLATE_PATH, template_norm)
    print(f"[CueDetector] Global template saved to {TEMPLATE_PATH}")
    return template_norm

def detect_cues(mp3_path, threshold=0.80, nms_sec=2.0):
    """通用提示音检测函数：输入任意 mp3 路径，返回 [(end_sec, confidence), ...]"""
    if not os.path.exists(TEMPLATE_PATH):
        template_norm = build_global_template()
    else:
        template_norm = np.load(TEMPLATE_PATH)

    S_sub = _extract_sub_spec(mp3_path)
    win_frames = template_norm.shape[1]
    num_frames = S_sub.shape[1] - win_frames

    scores = np.zeros(num_frames)
    for i in range(num_frames):
        patch = S_sub[:, i : i + win_frames]
        scores[i] = np.sum(patch * template_norm) / (np.linalg.norm(patch) + 1e-8)

    # 仅做 2.0s 的非极大值抑制（防止同一个 2 秒长的提示音自己重复触发自己）
    nms_frames = _time_to_frame(nms_sec)
    detected = []
    scores_copy = scores.copy()

    while True:
        best_idx = int(np.argmax(scores_copy))
        best_score = float(scores_copy[best_idx])
        if best_score < threshold:
            break
        end_time = _frame_to_time(best_idx + win_frames)
        detected.append((end_time, round(best_score, 3)))
        left = max(0, best_idx - nms_frames)
        right = min(num_frames, best_idx + nms_frames)
        scores_copy[left:right] = 0.0

    detected.sort(key=lambda x: x[0])
    return detected

if __name__ == "__main__":
    # 强制从 302 课重建一次纯净的全局模板
    build_global_template("lessons/2026-302.mp3", 8.94)
    
    # 测试 303 课
    cues_303 = detect_cues("lessons/2026-303.mp3", threshold=0.80)
    print(f"\n--- 2026-303.mp3 检测结果 (共 {len(cues_303)} 个提示音) ---")
    for i, (t, conf) in enumerate(cues_303, 1):
        print(f"[{i:2d}] {t:6.2f}s  (置信度: {conf:.3f})")
