#!/usr/bin/env python3
"""
从 NHK ラジオニュース 官方播客 RSS (https://www.nhk.or.jp/s-media/news/podcast/list/v1/all.xml)
抓取最新一期真人播音员新闻 MP3，截取完整单条新闻片段，
使用 pydub.silence 对齐句间停顿、通过 furigana.to_ruby 生成精确注音，
并注册课程 2026-nhk-radio-1 到 lessons-config.js 与 index.html。
"""
import os
import re
import json
import xml.etree.ElementTree as ET
import requests
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from furigana import to_ruby

RSS_URL = "https://www.nhk.or.jp/s-media/news/podcast/list/v1/all.xml"
LESSON_ID = "2026-nhk-radio-1"
LESSON_TITLE = "🎙️ NHKラジオ真人播音 (11/08)：ベトナム書記長インタビュー・半導体やAI協力"

# 2026年11月08日 20:00 NHKラジオニュース 第2条完整新闻（79.5s ~ 181.0s）
# 所有汉字均附带精确读音标注，经 furigana.to_ruby() 转换为标准 <ruby> 标签
RADIO_SENTENCES = [
    {
        "raw_jp": (
            "ベトナムの最高指導者[さいこうしどうしゃ]、"
            "トー・ラム共産党書記長[きょうさんとうしょきちょう]がNHKのインタビューに応[おう]じ、"
            "半導体[はんどうたい]やAIなど、先端分野[せんたんぶんや]での人材育成[じんざいいくせい]や"
            "技術力[ぎじゅつりょく]の向上[こうじょう]に向[む]けて、"
            "日本[にほん]からのさらなる投資[とうし]や協力[きょうりょく]に期待[きたい]を示[しめ]しました。"
        ),
        "cn": "越南最高领导人、越共中央总书记苏林接受了 NHK 的专访，就半导体及 AI 等尖端领域的人才培养与技术提升，表达了对来自日本进一步投资与合作的期待。",
        "analysis": (
            "📚 <b>NHK 广播新闻导语核心词：</b><br>"
            "・<b>最高指導者（さいこうしどうしゃ）</b>[名]：最高领导人。<br>"
            "・<b>〜に応じる（におうじる）</b>[自動2 | N3]：答应、接受（采访、要求等）。<br>"
            "・<b>先端分野（せんたんぶんや）</b>[名]：尖端领域、前沿领域。<br>"
            "・<b>人材育成（じんざいいくせい）</b>[名]：人才培养。<br>"
            "・<b>期待を示す（きたいをしめす）</b>[惯用]：表示期待、展现出期望。"
        ),
    },
    {
        "raw_jp": (
            "ベトナムの最高指導者[さいこうしどうしゃ]、"
            "トー・ラム共産党書記長兼国家主席[きょうさんとうしょきちょうけんこっかしゅせき]は、"
            "今日[きょう]から4日間[よっかかん]の日程[にってい]で日本[にほん]を訪問[ほうもん]し、"
            "天皇皇后両陛下[てんのうこうごうりょうへいか]と会見[かいけん]するほか、"
            "高市総理大臣[たかいちそうりだいじん]と首脳会談[しゅのうかいだん]を行[おこな]う予定[よてい]です。"
        ),
        "cn": "越南最高领导人、越共中央总书记兼国家主席苏林从今天起开启为期 4 天的访日行程，除会见天皇和皇后陛下外，还计划与高市首相举行首脑会谈。",
        "analysis": (
            "📚 <b>外交访问高频表达（N3）：</b><br>"
            "・<b>日程（にってい）</b>[名 | N3]：日程、行程安排。<br>"
            "・<b>訪問（ほうもん）する</b> [名・他動3 | N3]：访问、拜访。<br>"
            "・<b>〜ほか</b> [N3语法]：除……之外（还……）。<br>"
            "・<b>首脳会談（しゅのうかいだん）</b>[名]：首脑会谈。"
        ),
    },
    {
        "raw_jp": (
            "これを前[まえ]に、トー・ラム書記長[しょきちょう]は、"
            "首都[しゅと]ハノイでNHKのインタビューに応[おう]じ、"
            "「今回[こんかい]の訪問[ほうもん]で両国[りょうこく]の絆[きずな]はさらに強[つよ]まり、"
            "双方[そうほう]の国民[こくみん]に多[おお]くの恩恵[おんけい]をもたらすと確信[かくしん]している」"
            "と述[の]べました。"
        ),
        "cn": "在此之前，苏林总书记在首都河内接受 NHK 采访时表示：“我深信此次访问将进一步加深两国纽带，并为双方国民带来诸多福祉。”",
        "analysis": (
            "📚 <b>正式引述与书面词汇（N3/N2）：</b><br>"
            "・<b>これを前に（これをまえに）</b>：在此之前、借此行前夕。<br>"
            "・<b>絆（きずな）</b>[名]：纽带、羁绊。<br>"
            "・<b>恩恵（おんけい）をもたらす</b>：带来恩惠/福祉。<br>"
            "・<b>確信（かくしん）する</b> [名・他動3 | N3]：确信、深信。<br>"
            "・<b>述べる（のべる）</b>[他動2 | N3]：阐述、表示（新闻报道最常用引述动词）。"
        ),
    },
    {
        "raw_jp": (
            "また、今年[ことし]の日本[にほん]との貿易額[ぼうえきがく]が、先月[せんげつ]の時点[じてん]で、"
            "すでに去年[きょねん]1年間[いちねんかん]の額[がく]に迫[せま]るおよそ500億[おく]ドル、"
            "日本円[にほんえん]で7兆[ちょう]9000億円[おくえん]あまりに達[たっ]したことに触[ふ]れ、"
            "経済的[けいざいてき]な結[むす]びつきが強[つよ]まっていることを歓迎[かんげい]しました。"
        ),
        "cn": "此外，他还提及今年与日本的贸易额截至上个月已达约 500 亿美元（折合日元逾 7.9 万亿日元），逼近去年全年总额，对两国经济联系日益紧密表示欢迎。",
        "analysis": (
            "📚 <b>经贸数据播报句式（N3核心）：</b><br>"
            "・<b>貿易額（ぼうえきがく）</b>[名]：贸易额。<br>"
            "・<b>〜に迫る（にせまる）</b>[自動1 | N3]：逼近、接近。<br>"
            "・<b>〜あまり</b> [接尾 | N3]：……多、……余（如 7兆9000億円あまり）。<br>"
            "・<b>〜に達する（にたっする）</b>[自動3 | N3]：达到（某一数值或水准）。<br>"
            "・<b>〜に触れる（にふれる）</b>[自動2 | N3]：提及、谈到。"
        ),
    },
    {
        "raw_jp": (
            "その上[うえ]で、今後[こんご]は半導体[はんどうたい]やAI、クリーンエネルギーなど、"
            "先端分野[せんたんぶんや]での人材育成[じんざいいくせい]や技術力[ぎじゅつりょく]の向上[こうじょう]が"
            "求[もと]められるとして、"
            "日本[にほん]からのさらなる投資[とうし]や協力[きょうりょく]に期待[きたい]を示[しめ]しました。"
        ),
        "cn": "在此基础上他指出，今后在半导体、AI 及清洁能源等尖端领域亟需培养人才与提升技术实力，期待日本提供进一步的投资与合作。",
        "analysis": (
            "📚 <b>递进衔接与被动客观表述（N3）：</b><br>"
            "・<b>その上で（そのうえで）</b>[接续 | N3]：在此基础上、不仅如此。<br>"
            "・<b>技術力の向上（ぎじゅつりょくのこうじょう）</b>：技术实力的提高。<br>"
            "・<b>〜として</b> [N3语法]：作为……、认为/指出……（说明理由或前提）。"
        ),
    },
    {
        "raw_jp": (
            "一方[いっぽう]、緊張[きんちょう]が続[つづ]く中東地域[ちゅうとうちいき]など"
            "不安定化[ふあんていか]する国際情勢[こくさいじょうせい]について、"
            "トー・ラム書記長[しょきちょう]は"
            "「世界[せかい]が不確実性[ふかくじつせい]から解放[かいほう]されるのを待[ま]っていては"
            "発展[はってん]していけない。"
            "国[くに]を前[まえ]に進[すす]めるための状況[じょうきょう]を主体的[しゅたいてき]につくっていく」"
            "と述[の]べ、外交[がいこう]の多角化[たかくか]を進[すす]める姿勢[しせい]を強調[きょうちょう]しました。"
        ),
        "cn": "另一方面，谈及持续紧张的中东地区等日趋动荡的国际局势，苏林总书记表示：“如果坐等世界摆脱不确定性，就无法实现发展。我们将主动创造推动国家前行的局面”，强调了推进外交多元化的姿态。",
        "analysis": (
            "📚 <b>话题转换与政论高频词（N3/N2）：</b><br>"
            "・<b>一方（いっぽう）</b>[接续 | N3]：另一方面。<br>"
            "・<b>国際情勢（こくさいじょうせい）</b>[名]：国际局势。<br>"
            "・<b>解放（かいほう）される</b> [N3]：被解放、摆脱。<br>"
            "・<b>主体的（しゅたいてき）</b>[ナ形]：主动地、自主地。<br>"
            "・<b>多角化（たかくか）</b>[名]：多元化、多角化。<br>"
            "・<b>姿勢を強調する（しせいをきょうちょうする）</b>：强调姿态/立场。"
        ),
    },
]


def ensure_radio_raw_mp3(xml_cache="/tmp/nhk_podcast.xml", raw_mp3="/tmp/nhk_radio_raw.mp3") -> str:
    """确保本地已下载最新一期 NHK ラジオニュース 原始 MP3。"""
    if os.path.exists(raw_mp3) and os.path.getsize(raw_mp3) > 500_000:
        print(f"[✓] 已就绪 NHK ラジオニュース 原始广播音频: {raw_mp3}")
        return raw_mp3

    if not os.path.exists(xml_cache):
        resp = requests.get(RSS_URL, timeout=15)
        resp.raise_for_status()
        with open(xml_cache, "wb") as f:
            f.write(resp.content)

    tree = ET.parse(xml_cache)
    root = tree.getroot()
    enclosure = root.find(".//item/enclosure")
    if enclosure is None or not enclosure.get("url"):
        raise RuntimeError("未能在 NHK Podcast RSS 中找到音频 enclosure URL")

    mp3_url = enclosure.get("url")
    print(f"[*] 正在下载 NHK ラジオニュース 真人广播音频: {mp3_url}")
    r = requests.get(mp3_url, timeout=30)
    r.raise_for_status()
    with open(raw_mp3, "wb") as f:
        f.write(r.content)
    return raw_mp3


def build_radio_lesson():
    raw_mp3 = ensure_radio_raw_mp3()
    full_audio = AudioSegment.from_file(raw_mp3)

    # 截取第 2 条新闻（79.5s ~ 181.0s）并追加 1.5s 末尾静音缓冲防止切课截断
    clip_start_ms = 79_500
    clip_end_ms = 181_000
    segment_audio = full_audio[clip_start_ms:clip_end_ms] + AudioSegment.silent(duration=1500)

    os.makedirs("lessons", exist_ok=True)
    out_mp3 = f"lessons/{LESSON_ID}.mp3"
    out_json = f"lessons/{LESSON_ID}.json"
    segment_audio.export(out_mp3, format="mp3", bitrate="128k")
    total_dur = len(segment_audio) / 1000.0
    print(f"[+] 已导出真人广播单条新闻音频: {out_mp3} (总时长: {total_dur:.2f}s)")

    # 使用 pydub.silence 识别播音员自然停顿并归并到 6 个完整句子
    nonsilent = detect_nonsilent(
        segment_audio,
        min_silence_len=350,
        silence_thresh=segment_audio.dBFS - 16,
        seek_step=10,
    )
    chunks = [[st / 1000.0, ed / 1000.0] for st, ed in nonsilent]
    n_sent = len(RADIO_SENTENCES)

    while len(chunks) > n_sent and len(chunks) > 1:
        min_gap = float("inf")
        merge_idx = 0
        for i in range(len(chunks) - 1):
            gap = chunks[i + 1][0] - chunks[i][1]
            if gap < min_gap:
                min_gap = gap
                merge_idx = i
        chunks[merge_idx][1] = chunks[merge_idx + 1][1]
        chunks.pop(merge_idx + 1)

    records = []
    for idx, (s_info, (st, ed)) in enumerate(zip(RADIO_SENTENCES, chunks)):
        start_t = round(max(0.0, st - 0.15), 2)
        if idx < n_sent - 1:
            next_st = chunks[idx + 1][0]
            end_t = round(min(next_st - 0.20, ed + 0.65), 2)
        else:
            end_t = round(total_dur, 2)
        if idx > 0 and start_t < records[-1]["end"]:
            start_t = records[-1]["end"]

        records.append({
            "id": idx + 1,
            "start": start_t,
            "end": end_t,
            "jp": to_ruby(s_info["raw_jp"]),
            "cn": s_info["cn"],
            "analysis": s_info["analysis"],
        })

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[+] 已生成带 <ruby> 注音与语法解析的字幕: {out_json} (共 {len(records)} 句)")

    # 注册到 lessons-config.js 与 index.html 的第 2 课位置（紧随 2026-001 之后）
    cfg_path = "lessons-config.js"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = f.read()
    if f"id: '{LESSON_ID}'" not in cfg:
        anchor = "{ id: '2026-001', title: '第 1 课：NHKニュース・太平洋側は夏のような暑さ' },"
        entry = f"  {{ id: '{LESSON_ID}', title: '{LESSON_TITLE}' }},"
        cfg = cfg.replace(anchor, f"{anchor}\n{entry}", 1)
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(cfg)
        print(f"✅ 已将 {LESSON_ID} 注册到 {cfg_path} (第 2 课位置)")

    html_path = "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    if f'value="{LESSON_ID}"' not in html:
        anchor_opt = '<option value="2026-001">第 1 课：NHKニュース・太平洋側は夏のような暑さ</option>'
        new_opt = f'          <option value="{LESSON_ID}">{LESSON_TITLE}</option>'
        html = html.replace(anchor_opt, f"{anchor_opt}\n{new_opt}", 1)
        html = re.sub(r"lessons-config\.js\?v=[^\"]+", "lessons-config.js?v=20261108_radio", html)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ 已将 {LESSON_ID} 注册到 {html_path} (第 2 课位置)")


if __name__ == "__main__":
    build_radio_lesson()
