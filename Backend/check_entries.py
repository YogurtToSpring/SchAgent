import sqlite3, os
BACKEND = os.path.dirname(os.path.abspath(__file__))
conn = sqlite3.connect(os.path.join(BACKEND, "course.db"))
conn.row_factory = sqlite3.Row

# Key courses we need
for name in ["高等数学", "工科数学分析", "计算机系统基础"]:
    rows = conn.execute("SELECT course_id, course_name, semester, teacher_num FROM course WHERE course_name=? ORDER BY semester", (name,)).fetchall()
    print(f"\n=== {name} ({len(rows)} entries) ===")
    for r in rows:
        print(f"  {r['course_id']} | {r['semester']} | T:{r['teacher_num'][:5]}...")

# Find a specific teacher's course
teachers = {"康肖松": "T2010301978099", "李清安": "T09424919823613", "龚奕利": "T46814030139067"}
for tname, tnum in teachers.items():
    rows = conn.execute("SELECT course_id, course_name, semester FROM course WHERE course_name=? AND teacher_num=?", ("工科数学分析", tnum)).fetchall()
    print(f"\n{tname} teaching 工科数学分析: {len(rows)} entries")
    for r in rows:
        print(f"  {r['course_id']} {r['semester']}")
conn.close()
