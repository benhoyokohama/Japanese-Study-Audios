#!/usr/bin/env python3
import re

POS_PATTERN = re.compile(
    r'^(名|代|副|接|感|連体|連語|接頭|接尾|自動[123]|他動[123]|自他動[123]|イ形|ナ形|動[123]|形|形動|サ変|カ変|ラ変|五段|一段|・|\s)+$'
)

def _format_ruby_with_okurigana(base: str, reading: str) -> str:
    """
    智能对齐带送假名的词头，将假名精准放在汉字上方，送假名留在外侧：
    - 動かす[うごかす] -> <ruby>動<rt>うご</rt></ruby>かす
    - 受け持つ[うけもつ] -> <ruby>受け持<rt>うけも</rt></ruby>つ
    - 嘘つき[うそつき] -> <ruby>嘘<rt>うそ</rt></ruby>つき
    - 市場[いちば] -> <ruby>市場<rt>いちば</rt></ruby>
    """
    prefix = ""
    while base and base[0] in "～~・":
        prefix += base[0]
        base = base[1:]

    # 剥离开头相同的平假名（如 お札[おさつ] -> お + 札[さつ]）
    while base and reading and base[0] == reading[0] and ('\u3040' <= base[0] <= '\u309f'):
        prefix += base[0]
        base = base[1:]
        reading = reading[1:]

    # 剥离末尾相同的平假名送假名（如 動かす[うごかす] -> 動[うご] + かす）
    suffix = ""
    while base and reading and base[-1] == reading[-1] and ('\u3040' <= base[-1] <= '\u309f'):
        suffix = base[-1] + suffix
        base = base[:-1]
        reading = reading[:-1]

    # 如果中间夹有单个平假名（如 受け持つ / うけもつ，base="受け持", reading="うけも"）
    # 尝试进一步精确拆分为 <ruby>受<rt>う</rt></ruby>け<ruby>持<rt>も</rt></ruby>
    m_mid = re.match(r'^([一-龥々ヶ]+)([ぁ-ん]+)([一-龥々ヶ]+)$', base)
    if m_mid:
        k1, okuri, k2 = m_mid.groups()
        # 在 reading 中寻找中间的 okuri（从第2个字符开始找）
        pos = reading.find(okuri, 1)
        if pos != -1 and pos + len(okuri) < len(reading):
            r1 = reading[:pos]
            r2 = reading[pos + len(okuri):]
            return f"{prefix}<ruby>{k1}<rt>{r1}</rt></ruby>{okuri}<ruby>{k2}<rt>{r2}</rt></ruby>{suffix}"

    if base:
        return f"{prefix}<ruby>{base}<rt>{reading}</rt></ruby>{suffix}"
    return f"{prefix}{reading}{suffix}"

def to_ruby(text: str) -> str:
    """将 漢字[かな] 及 带送假名词头[かな] 转换为标准 <ruby> 标签，保留词性 [名] 等不变"""
    def repl(match):
        base = match.group(1)
        reading = match.group(2).strip()
        if POS_PATTERN.match(reading):
            return match.group(0)
        return _format_ruby_with_okurigana(base, reading)

    # 匹配包含至少一个汉字或数字温度符号的词块 + [平假名读音]
    pattern = re.compile(r'([～~]?[ぁ-ん]*[一-龥々ヶ0-9０-９℃]+[ぁ-ん一-龥々ヶ0-9０-９℃]*)\[([ぁ-んー]+)\]')
    return pattern.sub(repl, text)

def strip_furigana(text: str) -> str:
    """去除例句中的 [かな] 注音括号，供日语 TTS 自然朗读汉字"""
    def repl(match):
        base = match.group(1)
        reading = match.group(2).strip()
        if POS_PATTERN.match(reading):
            return match.group(0)
        return base
    pattern = re.compile(r'([～~]?[ぁ-ん]*[一-龥々ヶ0-9０-９℃]+[ぁ-ん一-龥々ヶ0-9０-９℃]*)\[([ぁ-んー]+)\]')
    return pattern.sub(repl, text)
