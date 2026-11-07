#!/usr/bin/env python3
"""
从 nhkeasier.com 直接抓取最新 NHK News Web Easy 官方原声 MP3 与带 <ruby> 注音正文，
通过 pydub 静音检测精确对齐每句时间轴，补充中文翻译与词汇语法解析，
生成 lessons/2026-nhk-{1..4}.{mp3,json} 并注册到 lessons-config.js 和 index.html。
"""
import os
import re
import json
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

BASE_URL = "https://nhkeasier.com/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
}

# 2026-11-06 最新 4 篇 NHK Easy 新闻逐句精校中文翻译与词汇语法解析
TRANSLATIONS_MAP = {
    # Article 1: 株の値段が大きく下がった
    "東京株式市場で、株の値段が6日、大きく下がりました。": {
        "cn": "6日，东京股票市场的股票价格大幅下跌。",
        "analysis": "📚 <b>经济新闻高频词：</b><br>・<b>東京株式市場（とうきょうかぶしきしじょう）</b>[名]：东京股票市场。<br>・<b>株の値段（かぶのねだん）</b>：股票价格（株価）。<br>・<b>大きく下がる（おおきくさがる）</b>：大幅下跌。"
    },
    "平均の値段が5万7434円になりました。": {
        "cn": "平均股价跌至 57,434 日元。",
        "analysis": "📚 <b>数值变化表达：</b><br>・<b>平均（へいきん）</b>[名 | N3]：平均（此处指日经平均指数）。<br>・<b>〜になる</b>：表示数值或状态变化的结果。"
    },
    "5日より3643円、下がりました。": {
        "cn": "比 5 日下跌了 3,643 日元。",
        "analysis": "📚 <b>比较基准（N4/N3）：</b><br>・<b>5日（いつか）より</b>：比5日（前一天）。「より」表示比较的基准。"
    },
    "今までで3番目に大きく下がりました。": {
        "cn": "创下迄今为止第三大的跌幅。",
        "analysis": "📚 <b>序数与程度副词（N3）：</b><br>・<b>今までで（いままでで）</b>：迄今为止、有史以来。<br>・<b>3番目に（さんばんめに）</b>：第三位地。"
    },
    "アメリカでも5日、株の値段が大きく下がりました。": {
        "cn": "美国股市在 5 日也出现了股价大幅下跌。",
        "analysis": "📚 <b>助词用法：</b><br>・<b>アメリカでも</b>：「でも」表示“在……也”，引出同类情况。"
    },
    "アメリカの選挙でトランプ大統領の共和党が負けて、AIやデータセンターのルールが厳しくなるかもしれないと多くの人が考えています。": {
        "cn": "许多人认为，由于特朗普总统所在的共和党在美国选举中失利，针对 AI 和数据中心的监管规则可能会变得更加严格。",
        "analysis": "📚 <b>原因与推测引用（N3核心）：</b><br>・<b>選挙（せんきょ）</b>[名 | N3]：选举。<br>・<b>厳しい（きびしい）</b>[イ形 | N3]：严格的、严厉的。<br>・<b>〜かもしれないと考える</b>：认为“可能会……”。"
    },
    "このため、アメリカや日本でAIや半導体に関係する会社の株の値段が下がっています。": {
        "cn": "因此，美国和日本与 AI 及半导体相关的公司股价正在下跌。",
        "analysis": "📚 <b>因果衔接与相关表达（N3）：</b><br>・<b>このため</b> [接续]：因此、由于这个原因（新闻常用书面语）。<br>・<b>半導体（はんどうたい）</b>[名]：半导体。<br>・<b>〜に関係する（にかんけいする）</b>[N3]：与……有关联的。"
    },

    # Article 2: 「難民のことを知ってほしい」難民がテーマの映画祭が始まった
    "難民がテーマの映画を集めた「難民映画祭」が始まりました。": {
        "cn": "汇集了以难民为主题的电影的“难民电影节”拉开了帷幕。",
        "analysis": "📚 <b>主题与定语修饰（N3）：</b><br>・<b>難民（なんみん）</b>[名]：难民。<br>・<b>テーマ</b> [名 | N3]：主题、题材。<br>・<b>集める（あつめる）</b>[他動2]：汇集、收集。"
    },
    "国連によると、戦争などで自分のまちから避難した人は、1億1700万人ぐらいいます。": {
        "cn": "据联合国统计，因战争等原因逃离自己家乡避难的人数约为 1.17 亿人。",
        "analysis": "📚 <b>消息来源与防灾词汇（N3）：</b><br>・<b>国連（こくれん）によると</b>：据联合国称（「〜によると」表示消息来源）。<br>・<b>避難（ひなん）する</b> [名・自動3 | N3]：避难、疏散。"
    },
    "国連UNHCR協会は、難民のことを知ってもらうために、毎年、映画祭を開いています。": {
        "cn": "联合国难民署（UNHCR）协会为了让大家了解难民的处境，每年都会举办电影节。",
        "analysis": "📚 <b>目的与授受表达（N3）：</b><br>・<b>〜てもらうために</b>：为了请别人（大众）做某事。<br>・<b>開く（ひらく）</b>[他動1 | N3]：举办、召开（活动、会议等）。"
    },
    "5日は東京で、3つの映画を紹介しました。": {
        "cn": "5 日在东京展映介绍了 3 部电影。",
        "analysis": "📚 <b>数量词与动词：</b><br>・<b>3つ（みっつ）</b>：三个、三部。<br>・<b>紹介（しょうかい）する</b> [名・他動3]：介绍、展映。"
    },
    "1つはシリアをテーマにしたドキュメンタリー映画でした。": {
        "cn": "其中一部是以叙利亚为主题的纪录片电影。",
        "analysis": "📚 <b>N3 核心句型「〜をテーマにする」：</b><br>・<b>〜をテーマにした</b>：以……为主题的。<br>・<b>ドキュメンタリー映画</b>：纪录片电影。"
    },
    "映画をつくった2人は、攻撃される町の様子や、希望を捨てないで生きる様子を記録しています。": {
        "cn": "制作这部电影的两人记录下了遭受袭击的城镇面貌，以及人们不放弃希望努力生存的模样。",
        "analysis": "📚 <b>被动语态与否定伴随（N3）：</b><br>・<b>攻撃（こうげき）される</b> [自動2/被动态 | N3]：遭受攻击。<br>・<b>希望を捨てないで（きぼうをすてないで）</b>：不放弃希望地（「〜ないで」表示伴随状态）。<br>・<b>記録（きろく）する</b> [名・他動3 | N3]：记录。"
    },
    "映画を見た高校生は「難民の問題をたくさんの人に伝えたいと思います」と話していました。": {
        "cn": "观看电影的高中生表示：“我想把难民问题传递给更多的人。”",
        "analysis": "📚 <b>意愿表达（N4/N3）：</b><br>・<b>伝える（つたえる）</b>[他動2 | N3]：传达、传递。<br>・<b>〜たいと思います</b>：表示说话人的愿望或想法，“我想……”。"
    },
    "映画祭は、来月6日までで、オンラインでも見ることができます。": {
        "cn": "电影节将持续到下个月 6 日，也可以在线观看。",
        "analysis": "📚 <b>可能态表达：</b><br>・<b>来月（らいげつ）</b>[名]：下个月。<br>・<b>〜ことができます</b>：能够……、可以……。"
    },

    # Article 3: 秋から冬　海で釣りをするときは天気に気をつけて
    "秋から冬は、釣りをしている人が海に落ちる事故が多くなります。": {
        "cn": "从秋天到冬天，海钓人员落海的事故会增多。",
        "analysis": "📚 <b>季节跨度与状态变化：</b><br>・<b>釣り（つり）</b>[名]：钓鱼。<br>・<b>海に落ちる（うみにおちる）</b>：掉进海里、落海。<br>・<b>多くなる（おおくなる）</b>：变多、增多。"
    },
    "海上保安庁によると、去年、海で釣りをしていた人の事故が200以上ありました。": {
        "cn": "据日本海上保安厅统计，去年海钓人员发生的事故超过了 200 起。",
        "analysis": "📚 <b>机构名称与数量界限（N3）：</b><br>・<b>海上保安庁（かいじょうほあんちょう）</b>[名]：日本海上保安厅。<br>・<b>200以上（にひゃくいじょう）</b>：200起以上。"
    },
    "いちばん多いのは11月でした。": {
        "cn": "事故发生最多的是 11 月。",
        "analysis": "📚 <b>最高级与名词化句式（N4/N3）：</b><br>・<b>いちばん多いのは〜</b>：最多的是……（形容词＋の实现名词化）。"
    },
    "今年も、今月、茨城県鹿嶋市でインドネシアの人が2人亡くなる事故がありました。": {
        "cn": "今年也在本月，茨城县鹿嶋市发生了一起导致两名印度尼西亚人遇难的事故。",
        "analysis": "📚 <b>委婉表达与新闻句式（N3）：</b><br>・<b>亡くなる（なくなる）</b>[自動1 | N3]：去世、遇难。<br>・<b>2人（ふたり）</b>：两人。"
    },
    "専門家は「この季節は、急に天気が変わって、波が高くなることがあります」と話しています。": {
        "cn": "专家表示：“在这个季节，有时天气会突然变化，海浪随之变高。”",
        "analysis": "📚 <b>偶然发生句型（N3）：</b><br>・<b>急に（きゅうに）</b>[副 | N3]：突然地。<br>・<b>〜ことがあります</b>：接动词基本形后，表示“有时会发生……的情况”。"
    },
    "海上保安庁は、海で釣りをするときは、天気に気をつけて、ライフジャケットを着てほしいと言っています。": {
        "cn": "海上保安厅呼吁大家在海边钓鱼时要注意天气变化，并穿好救生衣。",
        "analysis": "📚 <b>愿望与呼吁表达（N4/N3）：</b><br>・<b>気をつける（きをつける）</b>：注意、小心。<br>・<b>ライフジャケット</b> [名]：救生衣。<br>・<b>〜てほしいと言う</b>：呼吁/希望他人做某事。"
    },

    # Article 4: 冬のかに「ズワイガニ」をとる漁が始まった
    "日本海で、冬のかに「ズワイガニ」をとる漁が6日から始まりました。": {
        "cn": "在日本海，捕捞冬季螃蟹“松叶蟹（雪蟹）”的渔季从 6 日正式开始。",
        "analysis": "📚 <b>水产与季节风物词：</b><br>・<b>ズワイガニ</b> [名]：松叶蟹（雪蟹），日本冬季代表性海鲜。<br>・<b>漁（りょう）</b>[名]：捕鱼、捕捞作业。"
    },
    "石川県では、6日午前0時、18の船が漁を始めました。": {
        "cn": "在石川县，6 日凌晨 0 点，18 艘渔船开始了捕捞作业。",
        "analysis": "📚 <b>时间与地点提示：</b><br>・<b>午前0時（ごぜんれいじ）</b>：凌晨零点。<br>・<b>船（ふね）</b>[名]：船、渔船。"
    },
    "そして、午前8時ごろ、たくさん、かにをとった船が金沢港に戻ってきました。": {
        "cn": "随后在上午 8 点左右，满载松叶蟹的渔船返回了金泽港。",
        "analysis": "📚 <b>复合移动表达（N4/N3）：</b><br>・<b>金沢港（かなざわこう）</b>[名]：石川县金泽港。<br>・<b>戻ってくる（もどってくる）</b>：回到（说话人或视角所在地）来。"
    },
    "漁をした人は「みなさんに早く食べてほしいです」と話していました。": {
        "cn": "渔民们表示：“希望大家能早点品尝到。”",
        "analysis": "📚 <b>愿望表达：</b><br>・<b>早く食べてほしい（はやくたべてほしい）</b>：希望（大家）早点吃到。"
    },
    "「ズワイガニ」のオスをとる漁は、来年の3月20日まで行います。": {
        "cn": "公松叶蟹的捕捞期将持续到明年 3 月 20 日。",
        "analysis": "📚 <b>生物性别与正式动词（N3）：</b><br>・<b>オス</b> [名]：雄性、公蟹。<br>・<b>行う（おこなう）</b>[他動1 | N3]：进行、举行。"
    },
    "メスをとる漁は、来月29日までです。": {
        "cn": "母松叶蟹的捕捞期则截止到下个月 29 日。",
        "analysis": "📚 <b>对比与期限表达：</b><br>・<b>メス</b> [名]：雌性、母蟹（为保护海洋资源，母蟹捕捞期比公蟹短）。"
    },
}


def clean_ruby_html(html_fragment: str) -> str:
    """仅保留 <ruby> 与 <rt> 标签，剥离其它 HTML 标签、属性与多余 ASCII 空白（保留全角空格）。"""
    cleaned = re.sub(r"<rp>.*?</rp>", "", html_fragment, flags=re.DOTALL)
    cleaned = re.sub(r"</?(?!ruby\b|rt\b)[a-zA-Z0-9]+(?:\s[^>]*)?>", "", cleaned)
    cleaned = re.sub(r"<(ruby|rt)\s+[^>]*>", r"<\1>", cleaned)
    cleaned = re.sub(r"[ \t\r\n\f\v]+", "", cleaned).strip()
    return cleaned


def strip_ruby_to_plain(ruby_html: str) -> str:
    """剥离 <rt> 注音与 <ruby> 标签，还原纯日文文本（保留全角空格）。"""
    no_rt = re.sub(r"<rt>.*?</rt>", "", ruby_html, flags=re.DOTALL)
    plain = re.sub(r"<[^>]+>", "", no_rt)
    return re.sub(r"[ \t\r\n\f\v]+", "", plain).strip()


def split_paragraph_sentences(p_ruby: str) -> list[str]:
    """按句号「。」切分段落为独立句子列表（兼容「。」」结尾）。"""
    parts = re.split(r"(?<=。)(?!」)|(?<=。」)", p_ruby)
    return [s.strip() for s in parts if s.strip()]


def fetch_nhkeasier_html(cache_path: str = "/tmp/nhkeasier.html") -> str:
    """获取 nhkeasier.com 首页 HTML（优先在线请求，失败时可回退本地缓存）。"""
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=20)
        resp.encoding = "utf-8"
        resp.raise_for_status()
        html = resp.text
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(html)
        except OSError:
            pass
        return html
    except Exception as e:
        if os.path.exists(cache_path):
            print(f"[*] 在线请求受限 ({e})，使用本地缓存 {cache_path}")
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        raise


def parse_latest_articles(html: str, limit: int = 4) -> list[dict]:
    """解析最新一天的 4 篇新闻，提取标题、带 <ruby> 的句子列表及官方 MP3 链接。"""
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for art in soup.find_all("article"):
        h3 = art.find("h3")
        audio = art.find("audio")
        if not h3 or not audio:
            continue

        src = audio.get("src")
        if not src and audio.find("source"):
            src = audio.find("source").get("src")
        if not src:
            continue

        mp3_url = urljoin(BASE_URL, src)
        title_ruby = clean_ruby_html(h3.decode_contents())
        title_plain = strip_ruby_to_plain(title_ruby)

        time_tag = art.find("time")
        date_str = "2026-11-06"
        if time_tag and time_tag.get_text(strip=True):
            m = re.search(r"\d{4}-\d{2}-\d{2}", time_tag.get_text(strip=True))
            if m:
                date_str = m.group(0)

        sentences = []
        for p in art.find_all("p"):
            p_ruby = clean_ruby_html(p.decode_contents())
            sentences.extend(split_paragraph_sentences(p_ruby))

        if sentences:
            articles.append({
                "title_ruby": title_ruby,
                "title_plain": title_plain,
                "date": date_str,
                "mp3_url": mp3_url,
                "sentences": sentences,
            })
        if len(articles) >= limit:
            break

    return articles


def ensure_mp3_downloaded(mp3_url: str, out_mp3_path: str):
    """直接下载 nhkeasier.com 上的官方原声 MP3（严禁使用 TTS 重新合成）。"""
    os.makedirs(os.path.dirname(out_mp3_path) or ".", exist_ok=True)
    if os.path.exists(out_mp3_path) and os.path.getsize(out_mp3_path) > 100_000:
        print(f"  [✓] 官方原声 MP3 已就绪: {out_mp3_path} ({os.path.getsize(out_mp3_path)} bytes)")
        return

    print(f"  [*] 正在下载官方原声 MP3: {mp3_url} -> {out_mp3_path}")
    resp = requests.get(mp3_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    with open(out_mp3_path, "wb") as f:
        f.write(resp.content)
    print(f"  [✓] 下载完成: {out_mp3_path} ({len(resp.content)} bytes)")


def align_official_audio(sentences: list[str], mp3_path: str) -> list[dict]:
    """
    使用 pydub.silence 检测 NHK 官方慢速原声的句间停顿（通常为 2.0s ~ 3.5s），
    将切分出的非静音块合并至与句子数量完全一致，生成精确的 start / end 时间轴。
    """
    audio = AudioSegment.from_file(mp3_path)
    total_dur = len(audio) / 1000.0
    silence_thresh = audio.dBFS - 16 if audio.dBFS != float("-inf") else -40

    nonsilent_ranges = detect_nonsilent(
        audio,
        min_silence_len=600,
        silence_thresh=silence_thresh,
        seek_step=10,
    )

    n_sent = len(sentences)
    if not nonsilent_ranges:
        nonsilent_ranges = [[0, len(audio)]]

    chunks = [[st / 1000.0, ed / 1000.0] for st, ed in nonsilent_ranges]

    # 检查音频末尾静音余量：因为前端 app.js 会在 effectiveEnd - 0.35s 处触发连播/循环切课，
    # 且日语末尾「〜ます。／〜です。」发音轻柔，若原声末尾静音不足 1.8s，自动追加 1.5s 静音缓冲。
    trailing_silence = total_dur - chunks[-1][1]
    if trailing_silence < 1.8:
        audio = audio + AudioSegment.silent(duration=1500)
        audio.export(mp3_path, format="mp3", bitrate="128k")
        total_dur = len(audio) / 1000.0
        print(f"  [+] 已为 {mp3_path} 末尾追加 1.5s 静音缓冲 (新总时长: {total_dur:.2f}s)")

    # 句内逗号停顿较短（通常 <= 1.3s），句号停顿较长（通常 >= 2.0s），
    # 反复合并间隔最小的两个相邻语音块，直到块数等于句子数 n_sent
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
    if len(chunks) == n_sent:
        for idx, (sent_ruby, (st, ed)) in enumerate(zip(sentences, chunks)):
            start_t = round(max(0.0, st - 0.15), 2)
            if idx < n_sent - 1:
                next_st = chunks[idx + 1][0]
                end_t = round(min(next_st - 0.25, ed + 0.85), 2)
            else:
                # 最后一句直接延伸至追加静音缓冲后的音频末尾，确保句尾余音完整播完
                end_t = round(total_dur, 2)
            if idx > 0 and start_t < records[-1]["end"]:
                start_t = records[-1]["end"]

            plain = strip_ruby_to_plain(sent_ruby)
            trans_info = TRANSLATIONS_MAP.get(plain, {"cn": "", "analysis": ""})
            item = {
                "id": idx + 1,
                "start": start_t,
                "end": end_t,
                "jp": sent_ruby,
                "cn": trans_info.get("cn", ""),
            }
            if trans_info.get("analysis"):
                item["analysis"] = trans_info["analysis"]
            records.append(item)
    else:
        # 兜底：按纯文本字符数比例分配有效语音区间
        speech_start = chunks[0][0]
        speech_end = chunks[-1][1]
        span = max(1.0, speech_end - speech_start)
        weights = [max(1, len(strip_ruby_to_plain(s))) for s in sentences]
        total_w = sum(weights)
        cur_t = speech_start
        for idx, (sent_ruby, w) in enumerate(zip(sentences, weights)):
            seg_dur = span * (w / total_w)
            next_t = speech_end if idx == n_sent - 1 else cur_t + seg_dur
            plain = strip_ruby_to_plain(sent_ruby)
            trans_info = TRANSLATIONS_MAP.get(plain, {"cn": "", "analysis": ""})
            item = {
                "id": idx + 1,
                "start": round(cur_t, 2),
                "end": round(min(total_dur, next_t), 2),
                "jp": sent_ruby,
                "cn": trans_info.get("cn", ""),
            }
            if trans_info.get("analysis"):
                item["analysis"] = trans_info["analysis"]
            records.append(item)
            cur_t = next_t

    return records


def register_lessons(new_entries: list[tuple[str, str]]):
    """将生成的 NHK 官方原声课程注册到 lessons-config.js 和 index.html。"""
    cfg_path = "lessons-config.js"
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = f.read()
        to_add = [
            f"  {{ id: '{lid}', title: '{title}' }}"
            for lid, title in new_entries
            if f"id: '{lid}'" not in cfg
        ]
        if to_add:
            cfg = re.sub(r"\n\];\s*$", ",\n" + ",\n".join(to_add) + "\n];\n", cfg.strip())
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(cfg)
            print(f"✅ 已将 {len(to_add)} 节 NHK 课程注册到 {cfg_path}")

    html_path = "index.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        opts_to_add = [
            f'          <option value="{lid}">{title}</option>'
            for lid, title in new_entries
            if f'value="{lid}"' not in html
        ]
        if opts_to_add:
            html = html.replace("        </select>", "\n".join(opts_to_add) + "\n        </select>", 1)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"✅ 已将 {len(opts_to_add)} 节 NHK 课程注册到 {html_path}")


def main():
    print("🌐 正在获取 nhkeasier.com 最新新闻...")
    html = fetch_nhkeasier_html()
    articles = parse_latest_articles(html, limit=4)
    print(f"✅ 成功解析出 {len(articles)} 篇最新 NHK News Web Easy 新闻！\n")

    os.makedirs("lessons", exist_ok=True)
    registered_list = []

    for idx, art in enumerate(articles, 1):
        lesson_id = f"2026-nhk-{idx}"
        mp3_path = f"lessons/{lesson_id}.mp3"
        json_path = f"lessons/{lesson_id}.json"

        print(f"📦 [{idx}/{len(articles)}] 正在构建 {lesson_id}: {art['title_plain']} ({art['date']})")
        ensure_mp3_downloaded(art["mp3_url"], mp3_path)

        records = align_official_audio(art["sentences"], mp3_path)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        dur = records[-1]["end"] if records else 0.0
        print(f"  [✓] 已生成 {json_path} (共 {len(records)} 句，原声对齐时长 {dur:.2f}s)\n")

        short_date = art["date"][5:].replace("-", "/")
        lesson_title = f"NHKニュース ({short_date}-{idx})：{art['title_plain']}"
        registered_list.append((lesson_id, lesson_title))

    register_lessons(registered_list)
    print("🎉 全部 NHK News Web Easy 官方原声课程构建并注册完成！")


if __name__ == "__main__":
    main()
