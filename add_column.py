import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# すでにあるカラムか確認（念のため）
cursor.execute("PRAGMA table_info(quests)")
columns = [row[1] for row in cursor.fetchall()]

if "structure" not in columns:
    cursor.execute("ALTER TABLE quests ADD COLUMN structure TEXT")

if "steps_json" not in columns:
    cursor.execute("ALTER TABLE quests ADD COLUMN steps_json TEXT")

conn.commit()
conn.close()

print("構造列とJSON列を追加しました。")
