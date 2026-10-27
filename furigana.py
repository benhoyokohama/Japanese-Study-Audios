#!/usr/bin/env python3
import re

POS_PATTERN = re.compile(
    r'^(名|代|副|接|感|連体|連語|接頭|接尾|自動[123]|他動[123]|自他動[123]|イ形|ナ形|動[123]|形|形動|サ変|カ変|ラ変|五段|一段|・|\s)+$'
)

def _format_ruby_with_okurigana(base: str, reading: str) -> str:
    """
    智能对齐带送假名的词头，将假名精准放在汉字上方，送假名与助词留在外侧：
    - 動かす[うごかす] -> <ruby>動<rt>うご</rt></ruby>かす
    - 受け持つ[うけもつ] -> <ruby>受<rt>う</rt></ruby>け<ruby>持<rt>も</rt></ruby>つ
    - お札[おさつ] -> お<ruby>札<rt>さつ</rt></ruby>
    - や山梨県[やまなしけん] -> や<ruby>山梨県<rt>やまなしけん</rt></ruby>
    """
    prefix = ""
    while base and base[0] in "～~・":
        prefix += base[0]
        base = base[1:]

    # 剥离末尾相同的平假名送假名（如 動かす[うごかす] -> 動[うご] + かす）
    suffix = ""
    while base and reading and base[-1] == reading[-1] and ('ぁ' <= base[-1] <= 'ん'):
        suffix = base[-1] + suffix
        base = base[:-1]
        reading = reading[:-1]

    # 处理开头的平假名（仅当 base 以平假名开头时）
    while base and ('ぁ' <= base[0] <= 'ん'):
        # 只有当 reading 比剩余汉字数明显更长、且首假名一致（如词头 お札[おさつ]）时，才剥离 reading 首假名
        # 若只是句子中的助词粘连（如 や山梨県[やまなしけん]），只把助词移到 prefix，绝不吞掉 reading！
        if reading and base[0] == reading[0] and base[0] in "おご" and len(reading) > len(base):
            prefix += base[0]
            base = base[1:]
            reading = reading[1:]
        else:
            prefix += base[0]
            base = base[1:]

    # 如果中间夹有平假名送假名（如 受け持つ / うけもつ，此时 base="受け持", reading="うけも"）
    m_mid = re.match(r'^([一-龥々ヶ]+)([ぁ-ん]+)([一-龥々ヶ]+)$', base)
    if m_mid:
        k1, okuri, k2 = m_mid.groups()
        pos = reading.find(okuri, 1)
        if pos != -1 and pos + len(okuri) < len(reading):
            r1 = reading[:pos]
            r2 = reading[pos + len(okuri):]
            return f"{prefix}<ruby>{k1}<rt>{r1}</rt></ruby>{okuri}<ruby>{k2}<rt>{r2}</rt></ruby>{suffix}"

    if base:
        return f"{prefix}<ruby>{base}<rt>{reading}</rt></ruby>{suffix}"
    return f"{prefix}{reading}{suffix}"

# 匹配词块：可选波浪号 + 可选接头词(お/ご) + 汉字块(可含中间送假名及末尾送假名) + [平假名读音]
RUBY_PATTERN = re.compile(r'([～~]?[おご]?[一-龥々ヶ]+(?:[ぁ-ん]+[一-龥々ヶ]+)*[ぁ-ん]*)\[([ぁ-んー]+)\]')


def normalize_tilde_ruby(text: str) -> str:
    # 将 〜箇所[〜かしょ] 规范化为 〜箇所[かしょ]，确保正则完美生成 <ruby>
    text = re.sub(r'([〜~])([一-龥々ヶ]+)\[[〜~]([ぁ-んァ-ンー]+)\]', r'\1\2[\3]', text)
    return text

def to_ruby(text: str) -> str:
    text = normalize_tilde_ruby(text)
    """将 漢字[かな] 及 带送假名词头[かな] 转换为标准 <ruby> 标签，保留词性 [名] 等不变"""
    def repl(match):
        base = match.group(1)
        reading = match.group(2).strip()
        if POS_PATTERN.match(reading):
            return match.group(0)
        return _format_ruby_with_okurigana(base, reading)

    return RUBY_PATTERN.sub(repl, text)

def strip_furigana(text: str) -> str:
    """去除例句中的 [かな] 注音括号，供日语 TTS 自然朗读汉字"""
    def repl(match):
        base = match.group(1)
        reading = match.group(2).strip()
        if POS_PATTERN.match(reading):
            return match.group(0)
        return base
    return RUBY_PATTERN.sub(repl, text)
