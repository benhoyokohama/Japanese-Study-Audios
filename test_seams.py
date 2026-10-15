import os
import json
import shutil
import subprocess

MAX_AUDIO_DRIFT_SEC = 3.0

def _mp3_duration(path):
    if not shutil.which("ffprobe"):
        return None
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())

def test_lessons_json():
    lessons_dir = "lessons"
    assert os.path.exists(lessons_dir), "lessons/ 目录不存在"
    json_files = [f for f in os.listdir(lessons_dir) if f.endswith(".json")]
    print(f"[*] 发现 {len(json_files)} 个课件 JSON 文件，开始进行结构与边界回归校验...")
    for file in json_files:
        path = os.path.join(lessons_dir, file)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, list), f"{file} 根结构必须是数组"
            for item in data:
                assert "id" in item and "start" in item and "end" in item and "jp" in item and "cn" in item, f"{file} 中的句子缺少必要字段"
        mp3_path = os.path.join(lessons_dir, file.replace(".json", ".mp3"))
        if os.path.exists(mp3_path):
            duration = _mp3_duration(mp3_path)
            if duration is not None:
                last_end = data[-1]["end"]
                drift = abs(duration - last_end)
                assert drift <= MAX_AUDIO_DRIFT_SEC, (
                    f"{file} 末句 end={last_end} 与音频时长 {duration:.2f}s 相差 {drift:.2f}s，声画未对齐"
                )
    print("ALL TESTS PASSED / GREEN: 课件数据回归测试全部通过！")

if __name__ == "__main__":
    test_lessons_json()
