import json
import os
import librosa
import numpy as np

lesson_id = "2026-303"
mp3_path = f"lessons/{lesson_id}.mp3"
json_path = f"lessons/{lesson_id}.json"

print(f"正在通过提示音指纹对 {lesson_id} 进行全自动 35 句精准切片打轴...")
y, sr = librosa.load(mp3_path, sr=16000)
hop_length = 256
S = np.abs(librosa.stft(y, n_fft=1024, hop_length=hop_length))

freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
valid_bins = (freqs >= 400) & (freqs <= 4000)
S_sub = S[valid_bins, :]

def time_to_frame(t):
    return int(round(t * sr / hop_length))

def frame_to_time(f):
    return round(f * hop_length / sr, 2)

# 载入我们在 302 课校准好的 1.2 秒提示音黄金指纹模板
win_sec = 1.2
win_frames = time_to_frame(win_sec)
ref_end_frame = time_to_frame(8.94)
template = S_sub[:, ref_end_frame - win_frames : ref_end_frame]
template_norm = template / (np.linalg.norm(template) + 1e-8)

num_frames = S_sub.shape[1] - win_frames
scores = np.zeros(num_frames)
for i in range(num_frames):
    patch = S_sub[:, i : i + win_frames]
    scores[i] = np.sum(patch * template_norm) / (np.linalg.norm(patch) + 1e-8)

# 峰值检索
min_dist_frames = time_to_frame(3.5)
detected_ends = []
scores_copy = scores.copy()

while True:
    best_idx = int(np.argmax(scores_copy))
    best_score = float(scores_copy[best_idx])
    if best_score < 0.45:
        break
    end_time = frame_to_time(best_idx + win_frames)
    detected_ends.append(end_time)
    left = max(0, best_idx - min_dist_frames)
    right = min(num_frames, best_idx + min_dist_frames)
    scores_copy[left:right] = 0.0

detected_ends.sort()
print(f"成功锁定 {len(detected_ends)} 个提示音切片节点！")

# 红宝书第 303 课（あ行收尾完整 35 个词条及例句文本）
full_303_texts = [
    "現れる ④ [自動2] 出现，出来；显现，露出\n△月が現れる。/ 月亮出来。\n△効果が現れる。/ 效果显现出来。",
    "表れる ① [自動2] 表现，显出\n△態度に表れる。/ 表现在态度上。\n△努力が結果に表れる。/ 努力有了结果。",
    "有難い ④ [イ形] 难得，少有；值得感谢的\n△有難い機会 / 难得的机会\n△それは有難いことだ。/ 那太值得感谢了。",
    "或いは ② [副・接] 或是，或者；也许，或许\n△コーヒー或いはジュースを飲む。/ 喝咖啡或者果汁。\n△明日は或いは雨が降るかもしれない。/ 明天也许要下雨。",
    "歩き回る ⑤⓪ [自動1] 走遍，到处走\n△田舎を歩き回る。/ 在乡间到处走。",
    "アルバイト ③ [名] （课余时间）打工，工读\n△アルバイトに家庭教師をしている。/ 打工当家庭教师。",
    "あれくらい／あれぐらい ⑤⓪ [副] 那么，那般\n△あれくらい暑い日は体験したことがない。/ 从来没有遇到过那么炎热的日子。",
    "あれこれ ② [名・副] 这个那个，种种\n△あれこれ考えて眠れなかった。/ 想这想那，睡不着。\n△あれこれ不都合な事情がある。/ 有种种不方便。",
    "あれほど ⓪ [副] 那样，那么\n△あれほど汚いのに、洗濯もしないで着ている。/ 明面那么脏了，洗都没洗就穿了。",
    "アレルギー ③ [名] （医）过敏，变态反应\n△アレルギー体質 / 过敏性体质\n△卵アレルギー / 对鸡蛋过敏",
    "泡 ⓪ [名] 泡，沫，水花儿\n△石鹸の泡 / 肥皂泡\n△泡が立つ。/ 起泡。",
    "合わせる ③ [他動2] 合二为一，合并；使一致\n△二つの部屋を合わせて一つの部屋に改造する。/ 将两间屋子合并成一间。\n△力を合わせて働く。/ 同心协力地工作。\n△調子を合わせる。/ 使步调一致。",
    "慌ただしい ⑤ [イ形] 慌张，匆忙；繁忙\n△慌ただしく入ってくる。/ 慌张地走进来。\n△慌ただしい都市生活 / 繁忙的都市生活",
    "暗記 ⓪ [名・他動3] 熟记，记住，背诵\n△公式を暗記する。/ 熟记公式。\n△習ったことを全部暗記する。/ 将学到的东西全部背诵下来。",
    "アンケート ①③ [名] 问卷调查，民意测验\n△アンケートをとる。/ 进行问卷调查。",
    "暗証番号 ⑤ [名] 密码\n△暗証番号を覚える。/ 记住密码。",
    "安全 ⓪ [名・ナ形] 安全，保险，平安\n△安全第一主義 / 安全第一的原则\n△荷物が安全に着いた。/ 行李平安到达。",
    "あんた ① [代] （比「あなた」随便）你\n△あんた、何しているの？/ 你干什么呢？",
    "安定 ⓪ [名・自動3] 安稳，稳定；安定\n△底の広い瓶は安定がいい。/ 底部大的瓶子放得稳。\n△物価が安定している。/ 物价稳定。",
    "あんまり ⓪ [ナ形・副] 太，过于；（下接否定）（不）那么\n△それはあんまりな言い方だ。/ 那样说太过分了。\n△あんまり甘くない。/ 不那么甜。",
    "胃 ① [名] 胃\n△胃が痛い。/ 胃疼。\n△胃にもたれる。/ 积食，不消化。",
    "言い換える ③④ [他動2] 换句话说；改变说法\n△これは言い換えるとこのようになる。/ 这换种说法是这样的。",
    "いい加減 ③ [ナ形] 适当，适度；敷衍，搪塞\n△ちょうどいい加減の温度 / 正合适的温度\n△いい加減な返事 / 敷衍的回答",
    "言い出す ③ [他動1] 开始说；说出口\n△彼はちょっと考えてまた言い出した。/ 他考虑了一下又开始说了起来。",
    "言い直す ④ [他動1] 重说；改口说\n△もう一度言い直す。/ 重说一遍。",
    "意外 ① [ナ形・副] 出乎意料，意想不到\n△意外な事件 / 意外的事件\n△意外に思う。/ 感到意外。",
    "息 ① [名] 呼吸，喘气；气息；步调\n△大きく息をする。/ 深呼吸。\n△息が合う。/ 步调一致，合得来。",
    "意義 ① [名] （单词的）意思；意义，价值\n△単語の意義 / 单词的意思\n△意義がある会議 / 有意义的会议",
    "生き生き ③② [副・自動3] 活泼，生动，栩栩如生\n△この絵は生き生きとしている。/ 这幅画栩栩如生。",
    "いきなり ① [副] 冷不防，突然间\n△いきなり人が部屋に入った。/ 突然有人闯进了房间。",
    "生き物 ③② [名] 生物，动物；有生命力的东西\n△生き物を可愛がる。/ 爱护生物。",
    "育児 ①① [名] 育儿\n△母は育児に忙しい。/ 母亲忙于育儿。",
    "いくらなんでも ①⑥ [副] 无论怎样，即使……也\n△いくらなんでもそのお金は受け取れない。/ 无论怎样那笔钱都不能收下。",
    "以後 ① [名] 今后，将来；（某时期或时间）之后\n△以後気をつけるように。/ 今后要小心。",
    "以前 ① [名] 以前；过去，从前"
]

sentences = []
current_start = 0.0
for idx, end_t in enumerate(detected_ends):
    jp_text = full_303_texts[idx] if idx < len(full_303_texts) else f"第 {idx+1} 句词条"
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

print(f"🎉 303 课精准打轴 JSON 生成完毕 ({len(sentences)} 句): {json_path}")
