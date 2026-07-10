import sqlite3
from random import randint
from grade import compute_score


{
  "course_id": "252610311405327406",
  "stu_num": "2025302110200",
  "regular_score": 0,
  "final_exam_score": 0,
  "semester": "2025-2026-1",
  "exam_type": "正常",
  "remark": ""
}

print("id, course_id, stu_num, score, regular_score, final_score, semester, exam_type, remark")
conn = sqlite3.connect("grade.db")
conn.row_factory = sqlite3.Row

base = 2025302110200
for i in range(45):
    reg = randint(80, 100)
    final = randint(60, 100)
    alls = compute_score(reg, final)
    if final > 55:
        conn.execute(
            "INSERT INTO grade (course_id, stu_num, score, regular_score, final_score, semester, exam_type, remark) VALUES (?,?,?,?,?,?,?,?)",
            (25262028400327609, base, alls, reg, final, "2025-2026-2", "正常", "")
        )
    else :
        alls = final
        conn.execute(
            "INSERT INTO grade (course_id, stu_num, score, regular_score, final_score, semester, exam_type, remark) VALUES (?,?,?,?,?,?,?,?)",
            (25262028400327609, base, alls, reg, final, "2025-2026-2", "挂科", "重修")
        )
    base += 1

# conn.commit()
# conn.close()

conn.execute(
        "INSERT INTO grade (course_id, stu_num, score, regular_score, final_score, semester, exam_type, remark) VALUES (?,?,?,?,?,?,?,?)",
        (25262028400327609, 2025300002035, 100, 100, 100, "2025-2026-2", "正常", "")
    )

conn.commit()
conn.close()