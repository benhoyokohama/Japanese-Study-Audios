import os
import re
import json
from cue_detector import detect_cues

lesson_id = "2026-304"
mp3_path = f"lessons/{lesson_id}.mp3"
json_path = f"lessons/{lesson_id}.json"

if not os.path.exists(mp3_path):
    print(f"❌ 找不到 {mp3_path}！请先把 2026-304.mp3 复制到 lessons/ 文件夹下！")
    exit(1)

# 1. 调用我们封版的通用提示音模块，精准提取 19 个提示音节点
cues = detect_cues(mp3_path, threshold=0.80)
print(f"✅ [{lesson_id}] 检测到 {len(cues)} 个提示音节点:")
for i, (t, conf) in enumerate(cues, 1):
    print(f"   [{i:2d}] {t:6.2f}s (置信度: {conf:.3f})")

# 2. 经原声核对无误的第 304 课（Unit 1 い行 Part 1：胃 ～ 衣装，共 19 词）
items_304 = [
    "胃[い] ⓪ [名] 胃\n△胃[い]が痛[いた]い。/ 胃疼。\n△胃[い]にもたれる。/ 积食，不消化。",
    "言[い]い換[か]える ⓪④ [他動2] 换句话说；改变说法\n△これは言[い]い換[か]えるとこのようになる。/ 这换种说法是这样的。",
    "いい加減[かげん] ⓪ [名・ナ形・副] 适当，适度；敷衍，搪塞；相当，很\n△ちょうどいい加減[かげん]の温度[おんど] / 正合适的温度\n△いい加減[かげん]な返事[へんじ] / 敷衍的回答\n△いい加減[かげん]頭[あたま]にくる。/ 相当生气。",
    "言[い]い出[だ]す ③ [他動1] 开始说；说出口，提出\n△彼[かれ]はちょっと考[かんが]えてまた言[い]い出[だ]した。/ 他想了一下又接着往下说。\n△彼[かれ]が突然[とつぜん]妙[みょう]なことを言[い]い出[だ]した。/ 他突然提出莫名其妙的事。",
    "言[い]い直[なお]す ④ [他動1] 重说；改口说\n△もう一度[いちど]言[い]い直[なお]す。/ 重说一遍。",
    "意外[いがい] ⓪ [名・ナ形] 出乎意料，意外\n△意外[いがい]な事件[じけん] / 意外的事件\n△意外[いがい]に思[おも]う。/ 感到意外。",
    "息[いき] ① [名] 呼吸，喘气；气息；步调\n△大[おお]きく息[いき]をする。/ 深呼吸。\n△息[いき]が合[あ]う。/ 步调一致，合得来。",
    "意義[いぎ] ① [名] （单词等的）意思；意义，价值\n△単語[たんご]の意義[いぎ] / 单词的意思\n△意義[いぎ]がある会議[かいぎ] / 有意义的会议",
    "生[い]き生[い]き ③ [副・自動3] 生气勃勃，栩栩如生\n△この絵[え]は生[い]き生[い]きとしている。/ 这幅画栩栩如生。",
    "いきなり ⓪ [副] 冷不防，突然\n△いきなり人[ひと]が部屋[へや]に入[はい]った。/ 突然有人闯进了房间。",
    "生[い]き物[もの] ②③ [名] 生物，动物\n△生[い]き物[もの]を可愛[かわい]がる。/ 爱护生物。",
    "育児[いくじ] ① [名・自動3] 育儿，养育儿童\n△母[はは]は育児[いくじ]に忙[いそが]しい。/ 母亲忙于育儿。",
    "いくらなんでも ①⑤ [副] 无论怎样，不管怎么说\n△いくらなんでもそのお金[かね]は受[う]け取[と]れない。/ 不管怎么说，那笔钱我是不能收的。",
    "以後[いご] ① [名・副] 今后，以后；（某时间或事件）之后\n△以後[いご]気[き]をつけるように。/ 今后要注意。\n△五時[ごじ]以後[いご]は暇[ひま]だ。/ 五点以后有空。",
    "イコール ② [名] 等于，相等；等号\n△AイコールB / A等于B",
    "勇[いさ]ましい ④ [イ形] 勇敢，奋勇；雄壮，威武\n△勇[いさ]ましい兵士[へいし] / 勇敢的士兵\n△勇[いさ]ましい行進曲[こうしんきょく] / 雄壮的进行曲",
    "意地[いじ] ② [名] 固执，倔强；志气；贪心，欲望\n△意地[いじ]を張[は]る。/ 固执己见。\n△意地[いじ]が汚[きたな]い。/ 贪婪，嘴馋。",
    "維持[いじ] ① [名・他動3] 维持，保持\n△健康[けんこう]を維持[いじ]する。/ 保持健康。\n△治安[ちあん]を維持[いじ]する。/ 维持治安。",
    "衣装[いしょう] ① [名] 服装，衣裳；（戏剧、舞蹈等的）行头，戏装\n△花嫁[はなよめ]衣装[いしょう] / 新娘礼服"
]

if len(cues) != len(items_304):
    print(f"⚠️ 提示音数量 ({len(cues)}) 与词条数 ({len(items_304)}) 不一致，请检查！")

sentences = []
current_start = 0.0
for idx, (end_t, conf) in enumerate(cues):
    jp_text = items_304[idx] if idx < len(items_304) else f"词条 {idx+1}"
    sentences.append({
        "id": idx + 1,
        "start": current_start,
        "end": end_t,
        "jp": jp_text,
        "cn": ""
    })
    current_start = end_t

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(sentences, f, ensure_ascii=False, indent=2)
print(f"✅ 已生成 {json_path} (共 {len(sentences)} 条)")

# 3. 自动将 2026-304 写入 lessons-config.js（避免手动改错或漏改）
config_path = "lessons-config.js"
with open(config_path, "r", encoding="utf-8") as f:
    cfg = f.read()

if "2026-304" not in cfg:
    # 将之前的 default: true 改为 false，并把 304 设为最新默认课（或追加在末尾）
    new_entry = '  { id: "2026-304", title: "第 304 课：N3 文字词汇·い行 (一)", default: true },\n];'
    cfg = cfg.replace("default: true", "default: false")
    cfg = re.sub(r'\]\s*;?\s*$', new_entry, cfg.strip()) + "\n"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(cfg)
    print("✅ 已自动将第 304 课写入 lessons-config.js 并设为默认展示课程！")
else:
    print("ℹ️ lessons-config.js 中已包含 2026-304。")
