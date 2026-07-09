import sqlite3
import csv

conn = sqlite3.connect('classmate.db')  # 替换为实际路径
cur = conn.cursor()

with open('students_final.csv', 'r', encoding='utf-8-sig') as f:  # utf-8-sig 自动处理 BOM
    reader = csv.reader(f)
    next(reader)  # 跳过表头
    for row in reader:
        # row[0] 是空的 id，我们忽略它，只取后三列
        student_id,name,class_id,password,gpa = row[1], row[2], row[3], row[4], row[5]
        cur.execute(
            'INSERT INTO classmate (class_id,stu_num) VALUES (?, ?)',
            (class_id,student_id)
        )

conn.commit()
conn.close()
print("导入完成！")