import sqlite3

# クエストテーブル定義は残してOK（なければ作る）
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    desc TEXT NOT NULL,
    type TEXT NOT NULL
);
""")

# 全クエスト削除だけ実行
cursor.execute("DELETE FROM quests;")

conn.commit()
conn.close()

print("🧹 クエスト全削除完了！")
