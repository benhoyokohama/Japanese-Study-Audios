import json, re, os

with open("vocab_bank/ocr_pages_cache.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

os.makedirs("vocab_bank/drafts", exist_ok=True)

# 1. 找出每个单元的起始页与结束页（排除練習問題页）
unit_pages = {}
current_unit = 2

for pg in sorted(cache.keys(), key=lambda x: int(x)):
    p_int = int(pg)
    if p_int < 25:
        continue
    text = cache[pg] if isinstance(cache[pg], str) else "\n".join(cache[pg])
    lines = text.splitlines()
    
    # 检查是否有“第X単元”标题
    for l in lines[:10]:
        m = re.search(r"第\s*(\d+)\s*単", l)
        if m and "練習" not in l:
            current_unit = int(m.group(1))
            
    if "練習問題" in text or "模擬テスト" in text or "付録" in text:
        continue
        
    unit_pages.setdefault(current_unit, []).append(p_int)

print("📚 全书各单元正文页码分布：")
for u in sorted(unit_pages.keys()):
    pgs = unit_pages[u]
    print(f"  Unit {u:2d}: 第 {min(pgs):3d} ~ {max(pgs):3d} 页 (共 {len(pgs)} 页)")
    # 将每个单元的原始 OCR 文本按页导出到 vocab_bank/drafts/unit{u}_ocr.txt
    with open(f"vocab_bank/drafts/unit{u}_ocr.txt", "w", encoding="utf-8") as out:
        for p in pgs:
            out.write(f"================ 第 {p} 页 ================\n")
            out.write(cache[str(p)] + "\n\n")

print("\n✅ 已将 Unit 2 ~ Unit 20 原始文本归档至 vocab_bank/drafts/unitX_ocr.txt！")
