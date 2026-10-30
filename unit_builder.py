#!/usr/bin/env python3
"""
通用单元构建器：输入单元号与 [(wid, raw), ...]，自动生成 JSON、闪卡、4节课程音频并自动注册到前端
（自适应 120 词/单元 或 140 词/单元，自动均匀分为 4 课）
"""
import os
import re
import json
import asyncio
from furigana import to_ruby
from tts_lesson_builder import build_lesson

CN_NUMS = {1:"一",2:"二",3:"三",4:"四",5:"五",6:"六",7:"七",8:"八",9:"九",10:"十",
           11:"十一",12:"十二",13:"十三",14:"十四",15:"十五",16:"十六",17:"十七",18:"十八",19:"十九",20:"二十"}

async def build_and_register_unit(unit_num: int, raw_items: list):
    os.makedirs("vocab_bank", exist_ok=True)
    os.makedirs("lessons", exist_ok=True)
    cn_u = CN_NUMS.get(unit_num, str(unit_num))
    total = len(raw_items)

    records = []
    md_lines = [
        f"# 🇯🇵 N3 红宝书·第{cn_u}单元 (Unit {unit_num}: {unit_num}-1 ~ {unit_num}-{total}) NotebookLM 闪卡词库\n",
        "| 编号 | 日语词条 (带假名) | 词性与中文释义 | 经典例句 (日/中对照) |",
        "| :--- | :--- | :--- | :--- |"
    ]

    for wid, raw in raw_items:
        jp_ruby = to_ruby(f"【{wid}】 {raw}")
        records.append({"word_id": wid, "raw": raw, "jp_ruby": jp_ruby})
        lines = raw.split("\n")
        head = lines[0]
        exs = "<br>".join(lines[1:])
        md_lines.append(f"| **【{wid}】** | {head.split()[0]} | {' '.join(head.split()[1:])} | {exs} |")

    json_path = f"vocab_bank/unit{unit_num}.json"
    md_path = f"Unit{unit_num}_NotebookLM_Flashcards.md"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
    print(f"✅ 已保存 {json_path} ({total} 词) 与 {md_path}！")

    base_lid = 300 + (unit_num - 1) * 4
    cfg_entries = []
    html_opts = []

    # 将本单元词条均匀分为 4 课
    chunk = total // 4
    for part in range(4):
        lid = f"2026-{base_lid + part}"
        start_i = part * chunk
        end_i = total if part == 3 else (part + 1) * chunk
        sub_recs = records[start_i:end_i]
        await build_lesson(lid, sub_recs)
        title = f"第 {base_lid + part} 课：N3 词汇·第{cn_u}单元 ({part + 1}) [{unit_num}-{start_i + 1}~{unit_num}-{end_i}]"
        cfg_entries.append(f"  {{ id: '{lid}', title: '{title}' }}")
        html_opts.append(f'          <option value="{lid}">{title}</option>')

    first_lid = f"2026-{base_lid}"
    with open("lessons-config.js", "r", encoding="utf-8") as f:
        cfg = f.read()
    if first_lid not in cfg:
        cfg = re.sub(r"\n\];\s*$", ",\n" + ",\n".join(cfg_entries) + "\n];\n", cfg.strip())
        with open("lessons-config.js", "w", encoding="utf-8") as f:
            f.write(cfg)
        print(f"✅ 已将 {first_lid} ~ 2026-{base_lid+3} 自动注册到 lessons-config.js！")

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    if f'value="{first_lid}"' not in html:
        html = html.replace("        </select>", "\n".join(html_opts) + "\n        </select>", 1)
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ 已将 {first_lid} ~ 2026-{base_lid+3} 自动注册到 index.html！")
