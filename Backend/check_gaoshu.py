import sqlite3
import os

BACKEND = os.path.dirname(os.path.abspath(__file__))

conn = sqlite3.connect(os.path.join(BACKEND, "course.db"))
conn.row_factory = sqlite3.Row

print("=== All 高等数学 sections in course.db ===")
rows = conn.execute(
    "SELECT course_id, semester, day, start_time, end_time, teacher_num, room_id, credit "
    "FROM course WHERE course_name = '高等数学' ORDER BY semester, day"
).fetchall()

print(f"Total: {len(rows)} sections")
for r in rows:
    print(f"  {r['course_id']} | {r['semester']} | day {r['day']} | {r['start_time']}-{r['end_time']} | T:{r['teacher_num']} | {r['room_id']}")

print()

# Also verify course names used in class_stu
cs = sqlite3.connect(os.path.join(BACKEND, "class_stu.db"))
course_ids = set(r[0] for r in cs.execute("SELECT DISTINCT course_id FROM class_stu").fetchall())
course_names = {}
for cid in course_ids:
    r = conn.execute("SELECT course_name FROM course WHERE course_id = ?", (cid,)).fetchone()
    if r:
        course_names[r[0]] = course_names.get(r[0], 0) + cs.execute("SELECT COUNT(*) FROM class_stu WHERE course_id = ?", (cid,)).fetchone()[0]

print("=== Enrollments summary ===")
for name, cnt in sorted(course_names.items()):
    print(f"  {name:25s}: {cnt:6d}")
print(f"  {'TOTAL':25s}: {sum(course_names.values()):6d}")

conn.close()
cs.close()
print("\nDone.")
