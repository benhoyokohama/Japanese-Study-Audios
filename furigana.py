import re

# 词性标签正则（避免把 [名]、[他動2] 等误转为 ruby 注音）
POS_PATTERN = re.compile(
    r'^(?:名|代|連体|自動\d*|他動\d*|自他動\d*|形|イ形|ナ形|副|接|感|慣用|嘆|助|接尾|接頭|造|[・\s\d])+$'
)

def to_ruby(text: str) -> str:
    """将 漢字[かんじ] 转换为 <ruby>漢字<rt>かんじ</rt></ruby>"""
    def repl(match):
        kanji = match.group(1)
        kana = match.group(2).strip()
        if POS_PATTERN.match(kana):
            return match.group(0)
        return f"<ruby>{kanji}<rt>{kana}</rt></ruby>"

    # 匹配连续汉字（含々、ヶ）后紧跟的 [假名]
    return re.sub(r'([一-龯々ヶ]+)\[([^\]]+)\]', repl, text)

def strip_furigana(text: str) -> str:
    """剥离所有 <ruby> 和 [假名] 注音，仅保留汉字正文供 TTS 朗读"""
    # 1. 还原 <ruby>漢字<rt>かな</rt></ruby> -> 漢字
    text = re.sub(r'<ruby>(.*?)<rt>.*?</rt></ruby>', r'\1', text)
    # 2. 去掉 漢字[かな] 中的 [かな]（保留词性标签外的内容）
    def repl_bracket(match):
        kanji = match.group(1)
        kana = match.group(2).strip()
        if POS_PATTERN.match(kana):
            return match.group(0)
        return kanji
    return re.sub(r'([一-龯々ヶ]+)\[([^\]]+)\]', repl_bracket, text)

if __name__ == "__main__":
    import json, os
    for lid in ["2026-303", "2026-304"]:
        path = f"lessons/{lid}.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                item["jp"] = to_ruby(item.get("jp", ""))
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 已使用 furigana 模块将 {path} 转换为顶部注音格式！")
            print("   第 1 句预览:", data[0]["jp"].splitlines()[0])
