import glob
from ocr_pdf import ocr_pdf_pages

pdf_files = glob.glob("raw_books/*.pdf")
if not pdf_files:
    print("❌ 未找到 raw_books/*.pdf")
    exit(1)

pdf_path = pdf_files[0]
print(f"📖 正在使用本地 Apple Vision OCR 扫描: {pdf_path} (第 1 ~ 30 页)...")
results = ocr_pdf_pages(pdf_path, 1, 30)

with open("unit1_raw.txt", "w", encoding="utf-8") as f:
    for p, text in sorted(results.items()):
        f.write(f"\n==================== PAGE {p} ====================\n")
        f.write(text + "\n")

print("\n✅ 扫描完成！结果已保存至 unit1_raw.txt。")
print("=== 各页首尾预览（用于确认 Unit 1 精确起止页码）===")
for p, text in sorted(results.items()):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        print(f"Page {p:2d} ({len(lines):2d} 行): 开头 -> {lines[0][:25]} | 结尾 -> {lines[-1][:25]}")
