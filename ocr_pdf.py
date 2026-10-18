import sys
import pypdfium2 as pdfium
import Quartz
import Vision
from Cocoa import NSURL

def ocr_pdf_pages(pdf_path, start_page, end_page, lang="ja-JP"):
    pdf = pdfium.PdfDocument(pdf_path)
    total_pages = len(pdf)
    print(f"打开 PDF: {pdf_path} (共 {total_pages} 页)")

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_([lang])
    request.setUsesLanguageCorrection_(True)

    extracted_results = {}

    for page_num in range(start_page, end_page + 1):
        if page_num < 1 or page_num > total_pages:
            continue

        print(f"\n==================== 第 {page_num} 页 ====================")
        page = pdf[page_num - 1]
        image = page.render(scale=300/72).to_pil()
        temp_img_path = f"/tmp/page_{page_num}.png"
        image.save(temp_img_path)

        img_url = NSURL.fileURLWithPath_(temp_img_path)
        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(img_url, None)
        success, error = handler.performRequests_error_([request], None)

        if not success:
            print(f"第 {page_num} 页识别失败: {error}")
            continue

        page_lines = []
        for observation in request.results():
            line_text = observation.topCandidates_(1)[0].string()
            page_lines.append(line_text)

        full_text = "\n".join(page_lines)
        extracted_results[page_num] = full_text
        print(full_text)

    return extracted_results

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python3 ocr_pdf.py <pdf文件路径> <起始页> <结束页>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    p_start = int(sys.argv[2])
    p_end = int(sys.argv[3])

    ocr_pdf_pages(pdf_file, p_start, p_end)
