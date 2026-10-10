import sys

def patch_html():
    file_path = "index.html"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[!] 找不到 {file_path}")
        sys.exit(1)

    new_lines = []
    inserted = False
    
    for line in lines:
        new_lines.append(line)
        if 'value="2026-006"' in line and not inserted:
            indent = line[:len(line) - len(line.lstrip())]
            new_options = [
                f'{indent}<option value="2026-007">第 7 课：森林浴とマインドフルネス (一)</option>\n',
                f'{indent}<option value="2026-008">第 8 课：森林浴とマインドフルネス (二)</option>\n',
                f'{indent}<option value="2026-009">第 9 课：森林浴とマインドフルネス (三)</option>\n',
                f'{indent}<option value="2026-010">第 10 课：森林浴とマインドフルネス (四)</option>\n',
                f'{indent}<option value="2026-011">第 11 课：森林浴とマインドフルネス (五)</option>\n'
            ]
            new_lines.extend(new_options)
            inserted = True

    if not inserted:
        print("[!] 注入失败：未能在 index.html 中找到 value=\"2026-006\" 锚点。")
        sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    print("[+] index.html 局域补丁注入成功！")

if __name__ == "__main__":
    patch_html()
