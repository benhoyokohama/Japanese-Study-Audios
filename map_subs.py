import json, re

def time_to_seconds(time_str):
    time_str = time_str.strip().replace(',', '.')
    parts = time_str.split(':')
    h = float(parts[0])
    m = float(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s

def parse_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 兼容各类换行符并匹配 SRT 结构
    pattern = re.compile(r'(\d+)\s*\r?\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\r?\n([\s\S]*?)(?=\r?\n\r?\n|\Z)')
    matches = pattern.findall(content)
    
    subs = []
    for m in matches:
        text = ' '.join([line.strip() for line in m[3].splitlines() if line.strip()])
        subs.append({
            'start': time_to_seconds(m[1]),
            'end': time_to_seconds(m[2]),
            'text': text
        })
    return subs

def main():
    srt_file = 'youtube_sub.zh-Hans.srt'
    json_files = [
        'lessons/2026-007.json',
        'lessons/2026-008.json',
        'lessons/2026-009.json',
        'lessons/2026-010.json',
        'lessons/2026-011.json'
    ]
    offsets = {
        'lessons/2026-007.json': 0.0,
        'lessons/2026-008.json': 150.0,
        'lessons/2026-009.json': 330.0,
        'lessons/2026-010.json': 630.0,
        'lessons/2026-011.json': 960.0
    }
    
    subs = parse_srt(srt_file)
    print(f"[*] 成功解析官方字幕共 {len(subs)} 条")

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            offset = offsets[json_file]
            
            for item in data:
                global_start = item['start'] + offset
                global_end = item['end'] + offset
                
                matched = []
                for sub in subs:
                    # 判断时间区间是否有重叠
                    overlap = max(0.0, min(global_end, sub['end']) - max(global_start, sub['start']))
                    if overlap > 0.1:  # 重叠大于 0.1 秒才算有效命中
                        matched.append(sub['text'])
                
                if matched:
                    # 去重拼接
                    item['cn'] = ' '.join(list(dict.fromkeys(matched)))

            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"[+] 中文字幕映射成功: {json_file}")
        except FileNotFoundError:
            print(f"[-] 找不到文件: {json_file}")

if __name__ == '__main__':
    main()
