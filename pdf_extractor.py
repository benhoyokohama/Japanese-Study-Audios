import os
import glob
import fitz  # PyMuPDF

# 1. 自动匹配你截图中的「00N2冲刺」目录与 N3 红宝书 PDF
base_dir = os.path.expanduser("~/Documents/00日语学习/00N2冲刺")
pdf_matches = glob.glob(os.path.join(base_dir, "*12749811.pdf"))
mp3_dirs = glob.glob(os.path.join(base_dir, "*N3*MP3*"))

if not pdf_matches:
    print(f"未在 {base_dir} 找到 PDF，尝试全局搜索...")
    pdf_matches = glob.glob(os.path.expanduser("~/Documents/**/*12749811.pdf"), recursive=True)

if not pdf_matches:
    print("❌ 找不到 _12749811.pdf，请检查路径权限。")
    exit(1)

pdf_path = pdf_matches[0]
print(f"✅ 成功锁定 N3 红宝书 PDF: {pdf_path}")

if mp3_dirs:
    print(f"✅ 成功锁定 N3 MP3 光盘目录: {mp3_dirs[0]}")
    # 列出光盘目录下的部分音频文件结构
    sample_mp3s = sorted(glob.glob(os.path.join(mp3_dirs[0], "**", "*.mp3"), recursive=True))[:10]
    print(f"   光盘内共找到 MP3 文件，前几个示例: {[os.path.basename(p) for p in sample_mp3s[:5]]}")

# 2. 打开 PDF 并检查总页数
doc = fitz.open(pdf_path)
print(f"📖 PDF 总页数: {len(doc)} 页")

# 3. 将前 45 页（目录 + Unit 1 完整内容）导出为 200 DPI 清晰 PNG 图库，方便随时按页码提取
out_dir = "pdf_pages/n3"
os.makedirs(out_dir, exist_ok=True)

print("正在将前 45 页转化为本地高清图片缓存 (pdf_pages/n3/)...")
for page_num in range(min(45, len(doc))):
    out_file = os.path.join(out_dir, f"page_{page_num+1:03d}.png")
    if not os.path.exists(out_file):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=200)
        pix.save(out_file)

print(f"🎉 转化完成！图片已保存在 /Users/binhe/jp-reader/{out_dir}/ 目录下。")
