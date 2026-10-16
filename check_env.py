import os
import sys

print("Python:", sys.executable)
try:
    import fitz # PyMuPDF
    print("fitz available")
except ImportError:
    print("fitz not available")

try:
    import pypdf
    print("pypdf available")
except ImportError:
    print("pypdf not available")

try:
    import pdfplumber
    print("pdfplumber available")
except ImportError:
    print("pdfplumber not available")

import subprocess
for cmd in ["tesseract", "swift", "pdftoppm", "pdf2image", "convert"]:
    res = subprocess.run(["which", cmd], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Tool {cmd}: {res.stdout.strip()}")
    else:
        print(f"Tool {cmd}: not found")
