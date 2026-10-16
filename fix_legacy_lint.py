import json
import re

def fix_text(text):
    if not isinstance(text, str):
        return text
    # 修复 ASR 幻觉
    text = text.replace("心臨よく", "森林浴")
    # 修复复合词送假名
    text = text.replace("<ruby>繰り返<rt>くりかえ</rt></ruby>", "<ruby>繰<rt>く</rt></ruby>り<ruby>返<rt>かえ</rt></ruby>")
    text = text.replace("<ruby>食べ物<rt>たべもの</rt></ruby>", "<ruby>食<rt>た</rt></ruby>べ<ruby>物<rt>もの</rt></ruby>")
    text = text.replace("<ruby>当たり前<rt>あたりまえ</rt></ruby>", "<ruby>当<rt>あ</rt></ruby>たり<ruby>前<rt>まえ</rt></ruby>")
    text = text.replace("<ruby>買い物<rt>かいもの</rt></ruby>", "<ruby>買<rt>か</rt></ruby>い<ruby>物<rt>もの</rt></ruby>")
    text = text.replace("<ruby>付き合<rt>つきあ</rt></ruby>", "<ruby>付<rt>つ</rt></ruby>き<ruby>合<rt>あ</rt></ruby>")
    text = text.replace("<ruby>受け取<rt>うけと</rt></ruby>", "<ruby>受<rt>う</rt></ruby>け<ruby>取<rt>と</rt></ruby>")
    text = text.replace("<ruby>本能寺の変<rt>ほんのうじのへん</rt></ruby>", "<ruby>本能寺<rt>ほんのうじ</rt></ruby>の<ruby>変<rt>へん</rt></ruby>")
    text = text.replace("含<ruby>ふく<rt></rt></ruby>めて", "<ruby>含<rt>ふく</rt></ruby>めて")
    text = text.replace("誰<ruby>だれ<rt></rt></ruby>", "誰")
    return text

files = [
    "2026-011.json", "2026-012.json", "2026-013.json", "2026-014.json",
    "2026-015.json", "2026-016.json", "2026-017.json", "2026-101.json",
    "2026-200.json"
]

for f in files:
    path = f"lessons/{f}"
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    for item in data:
        for lang in ["jp", "cn"]:
            if lang in item:
                item[lang] = fix_text(item[lang])
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
print("Legacy lesson repairs applied.")
