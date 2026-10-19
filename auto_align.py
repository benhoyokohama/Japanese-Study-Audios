import json
import os
import librosa
import numpy as np

def detect_cue_points(audio_path):
    """
    通过音频频谱和能量突变点，自动识别原声录音末尾的提示音时间戳
    """
    y, sr = librosa.load(audio_path, sr=22050)
    
    # 计算短时能量 (RMS)
    hop_length = 512
    rmse = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.times_like(rmse, sr=sr, hop_length=hop_length)
    
    # 结合频谱特征（寻找提示音特有的高频突变峰值）
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    
    # 动态设定阈值寻找提示音位置（可根据你实际提示音的响度微调）
    peaks = []
    threshold = np.mean(rmse) + 1.8 * np.std(rmse)
    
    in_peak = False
    for i, val in enumerate(rmse):
        if val > threshold and not in_peak:
            # 记录提示音出现的起始秒数
            peaks.append(times[i])
            in_peak = True
        elif val < threshold * 0.7:
            in_peak = False
            
    print(f"成功识别到 {len(peaks)} 个提示音节点。")
    return peaks

print("音频提示音特征识别脚本已就绪。你可以把原声 MP3 放入 lessons 目录进行测试。")
