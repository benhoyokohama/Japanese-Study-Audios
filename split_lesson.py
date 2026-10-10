import os
import json

def generate_split_lessons():
    os.makedirs('lessons', exist_ok=True)
    lessons_data = {
        "2026-007": [
            {"id": 1, "start": 0.0, "end": 150.0, "jp": "こんにちは、<ruby>阿野<rt>あの</rt></ruby>です。アノズ・ジャパニーズ・ポッドキャストへようこそ。今日のテーマは<ruby>森林浴<rt>しんりんよく</rt></ruby>とマインドフルネスです。", "cn": "大家好，我是阿野。欢迎来到阿野日语播客，今天的主题是森林浴与正念。"}
        ],
        "2026-008": [
            {"id": 1, "start": 150.0, "end": 330.0, "jp": "<ruby>森林浴<rt>しんりんよく</rt></ruby>とは何か、その歴史と効果についてお話しします。木々の香りがストレスを減らしてくれます。", "cn": "讲述什么是森林浴，它的历史和效果。树木的香气能减少压力。"}
        ],
        "2026-009": [
            {"id": 1, "start": 330.0, "end": 630.0, "jp": "次は「禅（ぜん）」の考え方についてです。今していることに集中し、頭の中を休ませるシンプルな方法です。", "cn": "接下来是关于“禅”的想法。专注于当下，让大脑休息的简单方法。"}
        ],
        "2026-010": [
            {"id": 1, "start": 630.0, "end": 960.0, "jp": "マインドフルネスの具体的なやり方です。呼吸に意識を向け、3分間で頭の中をスッキリさせましょう。", "cn": "正念的具体做法。将意识集中在呼吸上，用3分钟让大脑清爽起来。"}
        ],
        "2026-011": [
            {"id": 1, "start": 960.0, "end": 1565.0, "jp": "デジタルデトックスや日常の掃除、お茶の時間を通じて心を穏やかに保つコツを紹介します。", "cn": "介绍通过数字排毒、日常清扫和茶歇来保持内心平静的秘诀。"}
        ]
    }
    for lid, content in lessons_data.items():
        path = f"lessons/{lid}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
        print(f"[+] 已生成子课件数据: {path}")
    print("SUCCESS: 所有 5 个子课件 JSON 生成完毕。")

if __name__ == "__main__":
    generate_split_lessons()
