import csv, sqlite3
import os

BACKEND = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BACKEND, "courses_output.csv"), "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# 1. Basic stats
from collections import Counter
sem = Counter(r["semester"] for r in rows)
print("By semester:")
for s in sorted(sem):
    print(f"  {s}: {sem[s]}")

names = Counter(r["course_name"] for r in rows)
print(f"\nUnique course names: {len(names)}")

# 2. course_id uniqueness
cids = [r["course_id"] for r in rows]
print(f"Total rows: {len(rows)}")
print(f"Unique course_ids: {len(set(cids))}")
print(f"No duplicates: {len(cids) == len(set(cids))}")

# 3. Special teacher verification
conn = sqlite3.connect(os.path.join(BACKEND, "teacher.db"))
name_to_num = {r[1]: r[0] for r in conn.execute("SELECT Number, Name FROM teacher")}
num_to_name = {v: k for k, v in name_to_num.items()}
conn.close()

spec = {
    "工科数学分析": ["康肖松"],
    "高级语言程序设计A": ["刘峰"],
    "计算机系统基础": ["李清安", "龚奕利"],
    "数据结构A": ["汪鼎文", "张乐飞"],
    "人工智能导引": ["刘菊华", "刘友发", "杜博"],
    "数字逻辑与数字电路": ["瞿涛", "武小平"],
    "软件系统实践": ["李清安", "龚奕利", "王健"],
    "算法设计与分析": ["董文永"],
}

print("\nSpecial teacher checks:")
all_ok = True
for course, expected_names in spec.items():
    course_rows = [r for r in rows if r["course_name"] == course]
    actual_names = [num_to_name.get(r["teacher_num"], "?") for r in course_rows]
    expected_nums = [name_to_num.get(n, "?") for n in expected_names]
    ok = all(a_num in expected_nums for a_num in [r["teacher_num"] for r in course_rows])
    status = "OK" if ok else "FAIL"
    print(f"  {status} {course:20s}: {actual_names}")
    if not ok:
        all_ok = False

if all_ok:
    print("  All special assignments correct.")
else:
    print("  PROBLEMS FOUND")

# 4. Room existence check
conn2 = sqlite3.connect(os.path.join(BACKEND, "room.db"))
existing_rooms = set(r[0] for r in conn2.execute("SELECT area||'-'||building||'-'||room_id FROM room"))
conn2.close()

room_ok = all(r["room_id"] in existing_rooms for r in rows)
print(f"\nAll rooms exist in room.db: {room_ok}")

# 5. Teacher existence check
teacher_nums = set(name_to_num.values())
teacher_ok = all(r["teacher_num"] in teacher_nums for r in rows)
print(f"All teachers exist in teacher.db: {teacher_ok}")

print("\nDone.")
