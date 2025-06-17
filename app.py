from flask import Flask, render_template, request
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

questions = [
    ("物事を分析しすぎて、決断が遅くなることがある", ["賢者"]),
    ("計画を立ててからでないと動けないことが多い", ["賢者"]),
    ("感情より理屈を優先してしまう傾向がある", ["賢者"]),
    ("議論になると正しさを追求しすぎてしまう", ["賢者"]),
    ("考えるより先に動いてしまうことがある", ["武闘家"]),
    ("衝動的に行動して、あとで振り返ることがある", ["武闘家"]),
    ("気持ちが高ぶるとつい強く出てしまうことがある", ["武闘家"]),
    ("ストレートな物言いで誤解されることがある", ["武闘家"]),
    ("相手のことを考えすぎて自分の意見を抑えてしまう", ["僧侶"]),
    ("困っている人を見ると手を差し伸べずにはいられない", ["僧侶"]),
    ("人の感情に敏感で、共感しすぎて疲れることがある", ["僧侶"]),
    ("誰かを傷つけないよう慎重に言葉を選ぶ", ["僧侶"]),
    ("気分によって考え方や意見が変わることがある", ["魔法使い"]),
    ("その時の感情に任せて行動してしまうことがある", ["魔法使い"]),
    ("気持ちの浮き沈みが激しいと感じる", ["魔法使い"]),
    ("感情をうまく伝えるのが難しいと感じる", ["魔法使い"]),
    ("自由で柔軟な発想を大切にしている", ["盗賊"]),
    ("ルールに縛られず、直感で動くことが多い", ["盗賊"]),
    ("自由を制限されるとストレスを感じる", ["盗賊"]),
    ("集団より一人で行動する方が気が楽", ["盗賊"]),
    ("独自の視点で物事を捉えるのが好きだ", ["芸術家"]),
    ("思いついたことをすぐ形にしたくなる", ["芸術家"]),
    ("感受性が強く、些細なことにも心が動く", ["芸術家"]),
    ("自分の世界を大切にしていて他人に踏み込まれたくない", ["芸術家"]),
    ("安定を求めて慎重に物事を考える", ["守護者"]),
    ("リスクよりも確実性を優先する行動をとる", ["守護者"]),
    ("大きな変化に対して不安を感じやすい", ["守護者"]),
    ("協調性を大切にし、チームワークを重視する", ["守護者"]),
    ("全体を俯瞰して効率よく進めることを考える", ["指揮官"]),
    ("自ら先頭に立って行動をリードすることが多い", ["指揮官"]),
    ("感情を抑えて冷静に振る舞おうとする傾向がある", ["指揮官"]),
    ("人を導いたり、指示を出す立場になることが多い", ["指揮官"])
]

with open("type_data.json", encoding="utf-8") as f:
    type_data = json.load(f)

def analyze_written_personality(written_text):
    prompt = f"""以下の自由記述から、当てはまりそうな性格タイプを最大2つ選び、それぞれに1〜3点の補正を提案し、コメントを述べてください。

タイプ一覧：賢者、武闘家、僧侶、魔法使い、盗賊、芸術家、守護者、指揮官

記述：{written_text}

出力形式:
{{
  "補正": {{"賢者": 2, "守護者": 1}},
  "コメント": "あなたの慎重で安定を重視する傾向は賢者と守護者タイプに近いです。"
}}"""
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
        chat = model.start_chat()
        response = chat.send_message(prompt)
        if not response.text.strip():
            return {"補正": {}, "コメント": "（空欄のためコメントなし）"}
        cleaned = re.sub(r"```json|```", "", response.text.strip())
        try:
            return json.loads(cleaned)
        except:
            return {"補正": {}, "コメント": cleaned}
    except Exception as e:
        return {"補正": {}, "コメント": f"[エラー]: {e}"}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start")
def start():
    return render_template("start.html", questions=questions)

@app.route("/guide")
def guide():
    return render_template("guide.html")

@app.route("/chat")
def chat():
    return render_template("chat.html")

@app.route("/result", methods=["POST"])
def result():
    types = ["賢者", "武闘家", "僧侶", "魔法使い", "盗賊", "芸術家", "守護者", "指揮官"]
    raw_score = {t: 0 for t in types}
    bonus_score = {t: 0 for t in types}
    comments = []

    for i, q in enumerate(questions):
        ans = request.form.get(f"q{i}")
        for t in q[1]:
            if ans == "yes":
                raw_score[t] += 3
            elif ans == "maybe":
                raw_score[t] += 1

    written_inputs = [request.form.get(k, "").strip() for k in ["written1", "written2", "written3"]]
    combined_text = "\n".join([txt for txt in written_inputs if txt])

    if combined_text:
        analysis = analyze_written_personality(combined_text)
        if isinstance(analysis, dict):
            if "補正" in analysis:
                for t, val in analysis["補正"].items():
                    if t in bonus_score:
                        bonus_score[t] += val
            if "コメント" in analysis:
                comments.append(analysis["コメント"])
    else:
        comments.append("自由記述が未入力のため、コメントはありません。")

    total_score = {t: raw_score[t] + bonus_score[t] for t in types}
    result_type = max(total_score, key=total_score.get)

    type_key_map = {
        "賢者": "sage", "武闘家": "monk", "僧侶": "priest", "魔法使い": "mage",
        "盗賊": "thief", "芸術家": "artist", "守護者": "guardian", "指揮官": "commander"
    }
    info = type_data.get(type_key_map.get(result_type))

    return render_template("result.html",
        type=result_type,
        raw_score=raw_score,
        bonus_score=bonus_score,
        score=total_score,
        comment="\n\n".join(comments),
        info=info
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
