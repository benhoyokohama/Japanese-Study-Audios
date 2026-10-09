import os
import json

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
    print("ALL TESTS PASSED / GREEN: 课件数据回归测试全部通过！")

if __name__ == "__main__":
    test_lessons_json()
