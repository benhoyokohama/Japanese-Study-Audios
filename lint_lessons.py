import os
import json
import re
import sys

LESSONS_DIR = "lessons"
# 剔除合法词汇 "心配"，保留真正的 ASR 幻觉黑名单
BLOCKLIST = ["自然人力", "新人力", "心臨よく", "昨日香り", "心臨よくお", "キラ、土"]

def run_lint():
    if not os.path.exists(LESSONS_DIR):
        print(f"[-] 未找到 {LESSONS_DIR} 目录，跳过质检。")
        return True

    has_error = False
    
    # 严格拦截基文混入平假名的违规切分
    # [\u3040-\u309F] 为平假名 Unicode 区间，匹配严格处于 <ruby> 和 <rt> 之间的文本
    ruby_hiragana_pattern = re.compile(r'<ruby>[^<]*[\u3040-\u309F]+[^<]*<rt>')

    for filename in sorted(os.listdir(LESSONS_DIR)):
        if not filename.endswith(".json"):
            continue
            
        filepath = os.path.join(LESSONS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"[-] {filename}: JSON 格式损坏 - {e}")
                has_error = True
                continue

        for idx, item in enumerate(data):
            for lang in ["jp", "cn"]:
                text = item.get(lang, "")
                if not isinstance(text, str) or not text:
                    continue

                # 1. 拦截 ASR 幻觉硬伤词汇
                for bad_word in BLOCKLIST:
                    if bad_word in text:
                        print(f"[-] {filename} [句{idx}][{lang}]: 触发黑名单词汇 '{bad_word}'\n    -> {text}")
                        has_error = True

                # 2. 校验 <ruby>/<rt> 标签配对闭合
                if text.count("<ruby>") != text.count("</ruby>") or text.count("<rt>") != text.count("</rt>"):
                    print(f"[-] {filename} [句{idx}][{lang}]: Ruby 标签未闭合\n    -> {text}")
                    has_error = True

                # 3. 拦截基文中混入平假名的非法切分
                if ruby_hiragana_pattern.search(text):
                    print(f"[-] {filename} [句{idx}][{lang}]: Ruby 基文混入平假名(送假名未剥离)\n    -> {text}")
                    has_error = True

                # 4. 拦截句首标点异常
                if re.search(r'^[、。！？，]', text.strip()):
                    print(f"[-] {filename} [句{idx}][{lang}]: 标点符号出现在句首\n    -> {text}")
                    has_error = True

    if has_error:
        print("\n[!] 数据质检未通过，流水线已中止！请根据上方日志批量修复脏数据。")
        return False
        
    print("[+] Linter 质检通过：未发现 ASR 幻觉、Ruby 标签完全闭合、送假名剥离合规、无句首标点。")
    return True

if __name__ == "__main__":
    if not run_lint():
        sys.exit(1)
