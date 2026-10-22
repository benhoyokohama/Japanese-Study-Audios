#!/usr/bin/env python3
"""
全书批量 OCR 扫描与自动编号入库脚本 (Unit 2 ~ Unit 20)
功能：
  1. 自动定位本地 N3 红宝书 PDF 文件
  2. 调用 macOS 原生 Vision OCR 逐页扫描（实时保存页级缓存到 vocab_bank/ocr_pages.json，支持随时中断续传）
  3. 自动按 4 位数字词条编号 (0121 ~ 2400+) 切分词条，并映射为 【U-N】 编号（如 0121 -> 2-1）
  4. 自动生成 vocab_bank/unit2_draft.json ~ unit20_draft.json 及可读文本 vocab_bank/unit2_raw.txt ~
"""
import os
import re
import glob
import json
import Quartz
from Foundation import NSURL
from ocr_pdf import ocr_pdf_pages
from furigana import to_ruby

os.makedirs("vocab_bank/drafts", exist_ok=True)
OCR_CACHE_FILE = "vocab_bank/ocr_pages_cache.json"

def find_pdf():
    pdfs = glob.glob("*.pdf") + glob.glob("raw_books/*.pdf")
    if not pdfs:
        raise FileNotFoundError("未找到红宝书 PDF 文件，请确认 PDF 在当前目录或 raw_books/ 下")
    return pdfs[0]

def get_total_pages(pdf_path: str) -> int:
    url = NSURL.fileURLWithPath_(os.path.abspath(pdf_path))
    doc = Quartz.PDFDocument.alloc().initWithURL_(url)
    return doc.pageCount()

def main():
    pdf_path = find_pdf()
    total_pages = get_total_pages(pdf_path)
    print(f"📘 找到原书: {pdf_path} (共 {total_pages} 页)")

    # 1. 读取已有的页级 OCR 缓存（支持断点续传）
    if os.path.exists(OCR_CACHE_FILE):
        with open(OCR_CACHE_FILE, "r", encoding="utf-8") as f:
            pages_cache = json.load(f)
    else:
        pages_cache = {}

    # 第 1 单元在 14~23 页左右，我们从第 22 页开始扫到全书结束，每次扫 10 页并落盘缓存
    start_p = 22
    step = 10
    for p in range(start_p, total_pages + 1, step):
        end_p = min(p + step - 1, total_pages)
        need_scan = [pg for pg in range(p, end_p + 1) if str(pg) not in pages_cache]
        if not need_scan:
            continue
        print(f"🔍 正在 OCR 扫描第 {p} ~ {end_p} / {total_pages} 页...", flush=True)
        res = ocr_pdf_pages(pdf_path, p, end_p)
        for pg, lines in res.items():
            pages_cache[str(pg)] = lines
        with open(OCR_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(pages_cache, f, ensure_ascii=False, indent=2)

    print("✅ 全书页面 OCR 扫描完成！正在解析词条与分配 【单元-序号】 编号...")

    # 2. 按页码顺序合并所有文本行，排除练习题页（含“練習問題”或“答案”的页面）
    all_lines = []
    for pg in sorted(pages_cache.keys(), key=lambda x: int(x)):
        page_lines = pages_cache[pg]
        page_text = "\n".join(page_lines)
        if "練習問題" in page_text or "模擬テスト" in page_text:
            continue
        all_lines.extend(page_lines)

    # 3. 识别 4 位数字开头的词条行（如 "0121 市場..." 或独立一行的 "0121"）
    raw_entries = {}
    current_num = None
    current_buf = []

    num_inline_pat = re.compile(r'^([012]\d{3})\s+(.+)$')
    num_alone_pat = re.compile(r'^([012]\d{3})$')

    i = 0
    while i < len(all_lines):
        line = all_lines[i].strip()
        if not line or re.match(r'^Unit\s*\d+', line, re.I) or re.match(r'^\d+$', line) and len(line) < 4:
            i += 1
            continue

        m_inline = num_inline_pat.match(line)
        m_alone = num_alone_pat.match(line)

        if m_inline:
            num = int(m_inline.group(1))
            if 121 <= num <= 2500:
                if current_num and current_buf:
                    raw_entries[current_num] = "\n".join(current_buf)
                current_num = num
                current_buf = [m_inline.group(2).strip()]
                i += 1
                continue
        elif m_alone:
            num = int(m_alone.group(1))
            if 121 <= num <= 2500 and i + 1 < len(all_lines):
                if current_num and current_buf:
                    raw_entries[current_num] = "\n".join(current_buf)
                current_num = num
                current_buf = [all_lines[i + 1].strip()]
                i += 2
                continue

        if current_num is not None:
            # 过滤页眉页脚噪音
            if not any(noise in line for noise in ["新日本语能力考试", "N3文字词汇", "红宝书"]):
                current_buf.append(line)
        i += 1

    if current_num and current_buf:
        raw_entries[current_num] = "\n".join(current_buf)

    # 4. 按每单元 120 词（Unit 2: 121~240, Unit 3: 241~360...）分装入库并编号
    max_num = max(raw_entries.keys()) if raw_entries else 120
    max_unit = (max_num - 1) // 120 + 1

    summary = []
    for u in range(2, max_unit + 1):
        u_start = (u - 1) * 120 + 1
        u_end = u * 120
        unit_records = []
        txt_lines = []

        for idx_in_unit, global_num in enumerate(range(u_start, u_end + 1), 1):
            wid = f"{u}-{idx_in_unit}"
            raw_body = raw_entries.get(global_num, f"【待补全: 原书编号 {global_num:04d}】")
            unit_records.append({
                "word_id": wid,
                "book_num": f"{global_num:04d}",
                "raw": raw_body,
                "jp_ruby": to_ruby(f"【{wid}】 {raw_body}")
            })
            txt_lines.append(f"=== 【{wid}】 (原书 {global_num:04d}) ===\n{raw_body}\n")

        found_cnt = sum(1 for r in unit_records if "待补全" not in r["raw"])
        if found_cnt == 0:
            continue

        json_path = f"vocab_bank/drafts/unit{u}_draft.json"
        txt_path = f"vocab_bank/drafts/unit{u}_raw.txt"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(unit_records, f, ensure_ascii=False, indent=2)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines))

        summary.append(f"  📗 Unit {u:2d} (编号 {u}-1 ~ {u}-120 | 原书 {u_start:04d}~{u_end:04d}): 自动捕获 {found_cnt}/120 词 -> 已存入 {json_path}")

    print("\n🎉 全书自动提取与编号汇总：")
    for s in summary:
        print(s)
    print("\n💡 所有页面级原始 OCR 结果已永久缓存在 vocab_bank/ocr_pages_cache.json，明天无需再次等待 OCR 扫描！")

if __name__ == "__main__":
    main()
