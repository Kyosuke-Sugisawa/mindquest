from flask import Flask, render_template, request, redirect, make_response, session
import uuid
import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
   return psycopg2.connect(
    "postgresql://neondb_owner:npg_6fs2QGmZHNVB@ep-square-heart-a98wgsz8-pooler.gwc.azure.neon.tech/neondb?sslmode=require",
    cursor_factory=RealDictCursor
)




load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

with open("type_data.json", encoding="utf-8") as f:
    type_data = json.load(f)

type_labels = {
    "common": "全タイプ",
    "賢者": "賢者",
    "武闘家": "武闘家",
    "僧侶": "僧侶",
    "魔法使い": "魔法使い",
    "盗賊": "盗賊",
    "芸術家": "芸術家",
    "守護者": "守護者",
    "指揮官": "指揮官"
}

@app.context_processor
def inject_type_labels():
    return dict(type_labels=type_labels)

    cursor = conn.cursor()

    # ユーザー情報
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_token TEXT UNIQUE,
            name TEXT,
            type TEXT,
            level INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 日記テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_token TEXT,
            content TEXT,
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 🔥 クエストテーブル（←これがなかった！）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            type TEXT,
            structure TEXT,
            steps_json TEXT
        )
    ''')

        # クエスト完了ログ（ユーザーごとの振り返り保存用）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quest_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_token TEXT,
            quest_id INTEGER,
            responses TEXT,
            ai_feedback TEXT,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

    
def check_and_add_feedback_column():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(journal)")
    columns = [row["title"] for row in cursor.fetchall()]
    if "feedback" not in columns:
        cursor.execute("ALTER TABLE journal ADD COLUMN feedback TEXT")
        conn.commit()
    conn.close()



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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"][:10]
        token = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_token, name, level) VALUES (%s, %s, %s)", (token, name, 1))
        conn.commit()
        conn.close()
        response = make_response(redirect("/menu"))
        response.set_cookie("user_token", token)
        return response
    return render_template("name_input.html")

@app.route("/menu")
def menu():
    token = request.cookies.get("user_token")
    user_data = {"name": "名無し", "user_type": "未設定", "level": 0}

    if token:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, type, level FROM users WHERE user_token = %s", (token,))
        row = cursor.fetchone()
        conn.close()

        if row:
            user_data["name"] = row["name"]
            user_data["user_type"] = row["type"]
            user_data["level"] = row["level"]

    return render_template("menu.html", **user_data)

@app.route("/name/change", methods=["GET", "POST"])
def name_change():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")

    if request.method == "POST":
        new_name = request.form.get("name", "").strip()[:10]
        if new_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET name = %s WHERE user_token = %s", (new_name, token))
            conn.commit()
            conn.close()
            return redirect("/menu")
    
    return render_template("name_change.html")



@app.route("/types")
def show_types():
    return render_template("types.html")

@app.route("/quest")
def quest():
    return render_template("quest.html")

@app.route("/start")
def start():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")
    return render_template("start.html", questions=questions)

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
        prompt = f"""
以下の自由記述を読み、書き手の性格傾向を分析してください。

1. RPG風の8タイプ（賢者, 武闘家, 僧侶, 魔法使い, 盗賊, 芸術家, 守護者, 指揮官）それぞれに対して、
  「0〜7点の補正スコア」をつけてください。
  出力形式は以下のJSONにしてください：

```json
{{"賢者": 2, "武闘家": 0, "僧侶": 4, "魔法使い": 1, "盗賊": 0, "芸術家": 0, "守護者": 3, "指揮官": 0}}
```

2. 続けて、書き手の特徴や良さをやさしく自然な口調で300字以内でコメントしてください。
  ・形式：「comment:」で始めて、後ろにコメント本文を置いてください。
  ・内容は親しみやすくポジティブなものにしてください。
  ・性格タイプを例に出してもOKです。

--- 記述ここから ---
{combined_text}
--- 記述ここまで ---
"""
        try:
            model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
            chat = model.start_chat()
            response = chat.send_message(prompt)
            reply = response.text.strip()

            score_match = re.search(r"\{.*?\}", reply, re.DOTALL)
            if score_match:
                bonus_dict = json.loads(score_match.group())
                for t in types:
                    bonus_score[t] = bonus_dict.get(t, 0)

            comment_match = re.search(r"comment:\s*(.+)", reply, re.DOTALL)
            if comment_match:
                comment_text = comment_match.group(1).strip()
                comments.append(comment_text)
            else:
                comments.append("コメントの抽出に失敗しました。")

        except Exception as e:
            comments.append(f"[エラー]: {e}")
    else:
        comments.append("自由記述が未入力のため、コメントはありません。")

    total_score = {t: raw_score[t] + bonus_score[t] for t in types}
    result_type = max(total_score, key=total_score.get)

    new_type = result_type  # ← これを追加！

    token = request.cookies.get("user_token")
    if token:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET type = %s WHERE user_token = %s", (new_type, token))
        conn.commit()
        conn.close()

    info = type_data.get({
        "賢者": "sage", "武闘家": "monk", "僧侶": "priest", "魔法使い": "mage",
        "盗賊": "thief", "芸術家": "artist", "守護者": "guardian", "指揮官": "commander"
    }.get(result_type))

    return render_template(
        "result.html",
        type=result_type,
        raw_score=raw_score,
        bonus_score=bonus_score,
        score=total_score,
        comment="\n\n".join(comments),
        info=info
    )

@app.route("/journal")
def journal():
    token = request.cookies.get("user_token")

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # title を含めず、存在するカラムだけを SELECT
    cursor.execute("""
        SELECT id, content, feedback, created_at 
        FROM journal 
        WHERE user_token = %s 
        ORDER BY created_at DESC
    """, (token,))
    
    entries = [
    {
        "id": row["id"],
        "content": row["content"],
        "feedback": row["feedback"],
        "created_at": row["created_at"]
    } for row in cursor.fetchall()
]


    conn.close()
    return render_template("journal.html", entries=entries)

@app.route("/journal/analyze", methods=["POST"])
def journal_analyze():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, created_at FROM journal WHERE user_token = %s ORDER BY created_at DESC LIMIT 1", (token,))
    row = cursor.fetchone()

    if row:
        entry_id = row["id"]
        content = row["content"]

        prompt = (
            "以下の文章から、書き手の気持ちや心の状態を読み取り、"
            "共感コメントを優しい口調で返してください。\n\n"
            f"文章：{content}"
        )

        try:
            model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
            chat = model.start_chat()
            result = chat.send_message(prompt)
            feedback = result.text.strip()

            cursor.execute("UPDATE journal SET feedback = %s WHERE id = %s", (feedback, entry_id))
            conn.commit()

        except Exception as e:
            feedback = f"[エラー] {e}"
    else:
        feedback = "日記がまだ書かれていません"

    # 日記一覧を再取得して返す（←ここを正しく修正）
    cursor.execute("SELECT id, content, feedback, created_at FROM journal WHERE user_token = %s ORDER BY created_at DESC", (token,))
    entries = [
        {
            "id": row["id"],
            "content": row["content"],
            "feedback": row["feedback"],
            "created_at": row["created_at"]
        } for row in cursor.fetchall()
    ]
    conn.close()

    return render_template("journal.html", entries=entries, analysis=feedback)


@app.route("/journal/compose", methods=["POST"])
def journal_compose():
    try:
        steps = [request.form.get(f"step{i}", "") for i in range(1, 7)]
        labels = ["出来事", "感情", "思考", "分析", "行動", "結果"]
        prompt = (
            "以下の6つの情報をもとに、自然な文章でまとまった日記文を作成してください。\n"
            "ステップ番号や箇条書きではなく、文章の流れで書いてください。\n\n"
        )
        for label, step in zip(labels, steps):
            prompt += f"{label}：{step}\n"

        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
        chat = model.start_chat()
        result = chat.send_message(prompt)
        composed_text = result.text.strip()

        return render_template("journal_preview.html", composed=composed_text)

    except Exception as e:
        return f"エラー：{e}"


@app.route("/journal/save", methods=["POST"])
def journal_save():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")

    content = request.form.get("content", "").strip()
    if not content:
        return redirect("/journal")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO journal (user_token, content) VALUES (%s, %s)", (token, content))
    conn.commit()
    conn.close()
    return redirect("/journal")

@app.route("/journal/delete", methods=["POST"])
def journal_delete():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")

    entry_id = request.form.get("entry_id")
    if not entry_id:
        return redirect("/journal")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM journal WHERE id = %s AND user_token = %s", (entry_id, token))
    conn.commit()
    conn.close()

    return redirect("/journal")


@app.route("/journal/feedback", methods=["POST"])
def journal_feedback():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")

    content = request.form.get("content", "").strip()
    if not content:
        return redirect("/journal")

    prompt = (
        "以下の文章を読んで、書き手の気持ちや思考に寄り添った共感コメントを、優しく丁寧な口調で返してください。\n\n"
        f"{content}"
    )

    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
        chat = model.start_chat()
        result = chat.send_message(prompt)
        feedback = result.text.strip()
    except Exception as e:
        feedback = f"[エラー] {e}"

    return render_template("journal_preview.html", composed=content, analysis=feedback)

@app.route("/journal/hint", methods=["GET"])
def journal_hint():
    prompt = (
        "ユーザーが日記を書こうとしているが、書き始められず困っていると仮定して、"
        "気持ちを引き出す優しい問いかけや書き出しのヒントを返してください。"
    )

    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
        chat = model.start_chat()
        result = chat.send_message(prompt)
        return result.text.strip()
    except Exception as e:
        return f"エラー: {e}"

from flask import render_template, request, redirect, url_for

@app.route("/journal/edit", methods=["POST"])
def journal_edit():
    content = request.form.get("content", "")
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, feedback, created_at FROM journal WHERE user_token = %s ORDER BY created_at DESC", (token,))
    entries = cursor.fetchall()
    conn.close()

    return render_template("journal.html", entries=entries, content=content)

@app.route("/quest/all")
def quest_all():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")

    conn = get_db_connection()
    cursor = conn.cursor()

    search_query = request.args.get("search", "").strip()
    filter_type = request.args.get("filter", "").strip()

    sql = sql = 'SELECT id, title, description, "type" FROM quests'
    cursor.execute(sql)

    params = []
    conditions = []

    if search_query:
        conditions.append("(title ILIKE %s OR description ILIKE %s)")
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    if filter_type:
        conditions.append("type = %s")
        params.append(filter_type)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY id DESC"

    cursor.execute(sql, params)
    quests = [
    {"id": row["id"], "title": row["title"], "description": row["description"], "type": row["type"]}
    for row in cursor.fetchall()
]


    cursor.execute("SELECT type FROM users WHERE user_token = %s", (token,))
    row = cursor.fetchone()
    user_type = row["type"].strip() if row and row["type"] else None

    conn.close()

    return render_template(
        "quest_list.html",
        title="📜 すべてのクエスト",
        quests=quests,
        user_type=user_type
    )


@app.route("/quest/by_type")
def quest_by_type():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type FROM users WHERE user_token = %s", (token,))
    row = cursor.fetchone()
    user_type = row["id"].strip() if row and row["id"] else None

    search_query = request.args.get("search", "").strip()
    filter_type = request.args.get("filter", "").strip()

    sql = "SELECT id, title, description, type FROM quests WHERE type = %s"
    params = [user_type]

    if search_query:
        sql += " AND (title ILIKE %s OR description ILIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    if filter_type:
        sql += " AND type = %s"
        params.append(filter_type)

    cursor.execute(sql, params)
    quests = [
    {"id": row["id"], "title": row["title"], "description": row["description"], "type": row["type"]}
    for row in cursor.fetchall()
]

    conn.close()

    return render_template(
        "quest_list.html",
        title="🎯 性格別クエスト",
        quests=quests,
        user_type=user_type
    )


@app.route("/quest/common")
def quest_common():
    token = request.cookies.get("user_token")
    if not token:
        return redirect("/register")

    conn = get_db_connection()
    cursor = conn.cursor()

    search_query = request.args.get("search", "").strip()
    filter_type = request.args.get("filter", "").strip()

    sql = "SELECT id, title, description, type FROM quests WHERE type = 'common'"
    params = []

    if search_query:
        sql += " AND (title ILIKE %s OR description ILIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    if filter_type:
        sql += " AND type = %s"
        params.append(filter_type)

    cursor.execute(sql, params)
    quests = [
    {"id": row["id"], "title": row["title"], "description": row["description"], "type": row["type"]}
    for row in cursor.fetchall()
]


    cursor.execute("SELECT type FROM users WHERE user_token = %s", (token,))
    row = cursor.fetchone()
    user_type = row["id"].strip() if row and row["id"] else None

    conn.close()

    return render_template(
        "quest_list.html",
        title="🌱 全タイプ共通クエスト",
        quests=quests,
        user_type=user_type
    )


@app.route("/reset")
def reset():
    token = request.cookies.get("user_token")
    if token:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_token = %s", (token,))
        cursor.execute("DELETE FROM journal WHERE user_token = %s", (token,))
        conn.commit()
        conn.close()
    response = make_response(redirect("/register"))
    response.delete_cookie("user_token")
    return response

# クエスト一覧（管理画面）
@app.route("/admin/quests")
def admin_quests():
    conn = get_db_connection()
    cursor = conn.cursor()

    keyword = request.args.get("keyword", "")
    quest_type = request.args.get("quest_type", "")
    page = int(request.args.get("page", 1))
    per_page = 30
    offset = (page - 1) * per_page

    base_query = 'SELECT id, title, description, "type" FROM quests'
    conditions = []
    params = []

    if keyword:
        conditions.append("(title ILIKE %s OR description ILIKE %s)")
        params.extend(["%" + keyword + "%", "%" + keyword + "%"])
    if quest_type:
        conditions.append('"type" = %s')
        params.append(quest_type)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    cursor.execute(base_query, tuple(params))
    quests = cursor.fetchall()

    # クエスト総数の取得（ページネーション用）
    count_query = "SELECT COUNT(*) AS count FROM quests"
    if conditions:
        count_query += " WHERE " + " AND ".join(conditions)

    cursor.execute(count_query, tuple(params[:-2]))  # LIMITとOFFSETは除外
    row = cursor.fetchone()
    total = row["count"] if row and "count" in row else 0
    total_pages = (total + per_page - 1) // per_page

    # 全クエストタイプ取得
    cursor.execute('SELECT DISTINCT "type" FROM quests')
    types = sorted(set(r["type"] for r in cursor.fetchall() if r["type"]))

    conn.close()

    return render_template(
        "admin_quests.html",
        quests=quests,
        keyword=keyword,
        quest_type=quest_type,
        current_page=page,
        total_pages=total_pages,
        types=types
    )




@app.route("/admin/quests/update", methods=["POST"])
def update_quest():
    quest_id = request.form.get("id")
    title = request.form.get("title")
    description = request.form.get("description")
    type_ = request.form.get("type")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE quests SET title = %s, description = %s, type = %s WHERE id = %s",
        (title, description, type_, quest_id)
    )
    conn.commit()
    conn.close()

    return redirect("/admin/quests")

import json

@app.route("/admin/quests/custom/create", methods=["POST"])
def create_custom_quest():
    title = request.form.get("title")
    description = request.form.get("description")
    type_ = request.form.get("type")
    steps_json = request.form.get("steps_json")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO quests (title, description, type, structure, steps_json) VALUES (%s, %s, %s, %s, %s);",
                   (title, description, type_, "multi_step", steps_json))
    conn.commit()
    conn.close()
    return redirect("/admin/quests")



import json

@app.route("/admin/quests/create", methods=["GET", "POST"])
def create_quest():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT code, name FROM types ORDER BY id")
    type_rows = cursor.fetchall()
    type_options = [{"code": "common", "name": "全タイプ向け"}] + [
        {"code": row["code"], "name": row["name"]} for row in type_rows
    ]

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        quest_type = request.form.get("type")
        steps_json = request.form.get("steps_json", "[]")

        cursor.execute(
            "INSERT INTO quests (title, description, type, structure, steps_json) VALUES (%s, %s, %s, %s, %s)",
            (title, description, quest_type, "multi_step", steps_json)
        )
        conn.commit()
        quest_id = cursor.lastrowid
        conn.close()

        return redirect(f"/admin/quests/edit_steps/{quest_id}")

    conn.close()
    return render_template(
        "quest_create.html",
        title="",
        description="",
        selected_type="common",
        type_options=type_options,
        steps_json="[]"
    )


@app.route("/admin/quests/edit_steps/<int:quest_id>", methods=["GET", "POST"])
def edit_quest_steps(quest_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT code, name FROM types ORDER BY id")
    type_rows = cursor.fetchall()
    type_options = [{"code": "common", "name": "全タイプ向け"}] + [
        {"code": row["code"], "name": row["name"]} for row in type_rows
    ]

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        quest_type = request.form.get("type")
        steps_json = request.form.get("steps_json", "[]")

        cursor.execute(
            "UPDATE quests SET title = %s, description = %s, type = %s, steps_json = %s WHERE id = %s",
            (title, description, quest_type, steps_json, quest_id)
        )
        conn.commit()
        conn.close()
        return redirect("/admin/quests")

    cursor.execute("SELECT title, description, type, steps_json FROM quests WHERE id = %s", (quest_id,))
    quest = cursor.fetchone()
    conn.close()

    if not quest:
        return "指定されたクエストが見つかりません", 404

    return render_template(
        "quest_create.html",
        title=quest["title"],
        description=quest["description"],
        selected_type=quest["type"],
        type_options=type_options,
        steps_json=quest["steps_json"] or "[]"
    )


@app.route("/quest/<int:quest_id>", methods=["GET", "POST"])
def quest_do(quest_id):
    if request.method == "POST":
        return redirect(url_for("quest_feedback", quest_id=quest_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, steps_json FROM quests WHERE id = %s", (quest_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "クエストが見つかりませんでした", 404

    # ✅ 辞書形式に対応
    quest = {
        "id": row["id"],
        "title": row["title"],
        "steps_json": row["steps_json"]
    }

    try:
        steps_raw = json.loads(quest["steps_json"] or "[]")
        for step in steps_raw:
            if step.get("type") == "grid":
                grid = step.get("grid", {})
                step["grid"] = {
                    "rows": int(grid.get("rows") or 2),
                    "cols": int(grid.get("cols") or 2)
                }
        steps = steps_raw
    except Exception:
        steps = []

    return render_template("quest_do.html", quest=quest, steps=steps)

@app.route("/quest/feedback/<int:quest_id>", methods=["GET", "POST"])
def quest_feedback(quest_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, steps_json FROM quests WHERE id = %s", (quest_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "クエストが見つかりませんでした", 404

    # ✅ 辞書形式でアクセス！
    title = row["title"]
    steps = json.loads(row["steps_json"]) if row["steps_json"] else []

    summary = []
    for i, step in enumerate(steps):
        if step["type"] == "grid":
            grid = []
            for r in range(step.get("grid", {}).get("rows", 2)):
                row_data = []
                for c in range(step.get("grid", {}).get("cols", 2)):
                    val = request.form.get(f"step_{i}_r{r}c{c}", "")
                    row_data.append(val)
                grid.append(row_data)
            answer = "\n".join(["｜".join(r) for r in grid])
        else:
            answer = request.form.get(f"step_{i}", "")
        summary.append(f"{step['label']}\n{answer}\n")

    text = "\n".join(summary)

    # Geminiプロンプト
    prompt = f"""
以下はユーザーが自己理解ワークに回答した内容です。
「各質問に対してどのように答えたか」に注目し、そこから読み取れる傾向や強み、
気づきポイントを前向きなトーンでフィードバックしてください。

出力形式は以下のようにしてください：

---
【フィードバック】
・回答の内容から、あなたには〜の傾向があるようです。
・〜という姿勢が見られ、とても素晴らしいです。
・今後は〜を意識するとさらに良くなるかもしれません。

制限：200字以内、やさしい口調で、親しみやすく。
---

【ユーザーの回答】
{text}
"""


    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
        chat = model.start_chat()
        result = chat.send_message(prompt)
        feedback = result.text.strip()

        # ✅ ログ保存
        token = request.cookies.get("user_token")
        if token:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO quest_logs (user_token, quest_id, responses, ai_feedback)
                VALUES (%s, %s, %s, %s)
            ''', (
                token,
                quest_id,
                json.dumps(summary, ensure_ascii=False),
                feedback
            ))
            conn.commit()
            conn.close()

    except Exception as e:
        feedback = f"[エラー] {e}"

    return render_template("quest_feedback.html", title=title, feedback=feedback)


@app.route("/admin/quests/delete/<int:quest_id>", methods=["POST"])
def delete_quest(quest_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quests WHERE id = %s", (quest_id,))
    conn.commit()
    conn.close()
    return redirect("/admin/quests")

@app.route("/admin/db_dump")
def db_dump():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, "description", type FROM quests ORDER BY id DESC LIMIT %s OFFSET %s', (limit, offset))
    rows = cursor.fetchall()
    conn.close()

    html = """
    <h2>quests テーブルの中身</h2>
    <table border="1" cellpadding="8" cellspacing="0">
    <tr>
        <th>ID</th>
        <th>タイトル</th>
        <th>説明</th>
        <th>タイプ</th>
        <th>ステップ内容</th>
    </tr>
    """
    for row in rows:
        html += f"""
        <tr>
            <td>{row["id"]}</td>
            <td>{row["title"]}</td>
            <td>{row["description"]}</td>
            <td>{row["type"]}</td>
            <td><pre>{row["steps_json"]}</pre></td>
        </tr>
        """
    html += "</table>"
    return html


@app.route("/credit")
def credit():
    return render_template("credit.html")

from datetime import datetime, timedelta

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y/%m/%d %H:%M'):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except:
            return value
    # SQLiteはUTCで保存されているので+9時間
    value = value + timedelta(hours=9)
    return value.strftime(format)

@app.context_processor
def inject_type_labels():
    return dict(type_labels=type_labels)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
