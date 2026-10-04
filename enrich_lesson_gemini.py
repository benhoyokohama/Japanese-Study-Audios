import os
import sys
import json
import re
from google import genai

# 获取环境变量中的 API 密钥
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("错误: 请先配置环境变量 export GEMINI_API_KEY='你的密钥'")
    sys.exit(1)

client = genai.Client(api_key=api_key)

PROMPT_SCHEMA = """
请作为日语专业名师，对以下日语句子进行深度语法拆解与词汇分析：
【目标句子】
{sentence}

请严格按如下 JSON 格式返回结果（不要添加多余标记，仅输出合法JSON对象）：
{{
  "grammar": [
    "语法点1及简明说明（如接续、语气、时态等）",
    "语法点2及简明说明"
  ],
  "vocab": [
    {{"word": "单词(读音)", "level": "N3/N2/N1", "meaning": "中文简释"}}
  ]
}}
注意：
1. vocab 只收录 N4 以上（N3、N2、N1）的核心/考点词汇，日常超简单词（如私、これ、行く）不要列入。
2. grammar 列举 1~3 个核心句型或口语表达特征。
"""

def clean_jp_ruby(text):
    return re.sub(r'<[^>]+>', '', text)

def enrich_lesson(lesson_file):
    with open(lesson_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    print(f"开始使用 gemini-3.8-flash 分析 {lesson_file}，共 {total} 句...")

    for i, item in enumerate(data):
        plain_text = clean_jp_ruby(item['jp'])
        print(f"[{i+1}/{total}] 正在分析: {plain_text[:25]}...")
        try:
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=PROMPT_SCHEMA.format(sentence=plain_text),
                config={"response_mime_type": "application/json"}
            )
            analysis = json.loads(resp.text)
            item['grammar'] = analysis.get('grammar', [])
            item['vocab'] = analysis.get('vocab', [])
        except Exception as e:
            print(f"句 {i+1} 分析跳过: {e}")
            item['grammar'] = []
            item['vocab'] = []

    with open(lesson_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ {lesson_file} 语法与词汇分析注入完成！")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "lessons/2026-100.json"
    enrich_lesson(target)
