import sqlite3
import csv

conn = sqlite3.connect('classi.db')  # 替换为实际路径
cur = conn.cursor()

with open('classi.csv', 'r', encoding='utf-8-sig') as f:  # utf-8-sig 自动处理 BOM
    reader = csv.reader(f)
    next(reader)  # 跳过表头
    for row in reader:
        # row[0] 是空的 id，我们忽略它，只取后三列
        class_id, name, master_id, capacity = row[1], row[2], row[3], row[4]
        cur.execute(
            'INSERT INTO classi (class_id, name, master_id, capacity) VALUES (?, ?, ?, ?)',
            (class_id, name, master_id, capacity)
        )

conn.commit()
conn.close()
print("导入完成！")