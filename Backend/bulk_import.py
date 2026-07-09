"""
    bulk_import.py - Batch import script

    One-shot import for all 11 SQLite databases.
    Usage:
        python Backend/bulk_import.py                     # from import_data.json
        python Backend/bulk_import.py my_data.json        # from custom file
        python Backend/bulk_import.py --example           # generate sample template
    Passwords are auto-hashed with pbkdf2.
"""

import json
import sqlite3
import os
import sys
import hashlib
import base64
from datetime import datetime, date

# ---------------------------------------------------------------------------
# Password hashing -- prefer passlib, fallback to hashlib built-in
# ---------------------------------------------------------------------------

try:
    from passlib.hash import pbkdf2_sha256 as _passlib_hasher
    _HAS_PASSLIB = True
except ImportError:
    _HAS_PASSLIB = False

def hash_password(password: str) -> str:
    if _HAS_PASSLIB:
        return _passlib_hasher.hash(password)
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    enc = "$pbkdf2-sha256$rounds=600000$"
    enc += base64.b64encode(salt).decode() + "$"
    enc += base64.b64encode(dk).decode()
    return enc

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Import order (respects logical foreign-key dependencies)
# ---------------------------------------------------------------------------

IMPORT_ORDER = [
    ("admin.db",    "admin"),
    ("teacher.db",  "teacher"),
    ("room.db",     "room"),
    ("classi.db",   "classi"),
    ("students.db", "students"),
    ("course.db",   "course"),
    ("classmate.db","classmate"),
    ("class_stu.db","class_stu"),
    ("grade.db",    "grade"),
    ("library.db",  "library_seat"),
    ("library.db",  "library_reservation"),
    ("todo.db",     "todo"),
]

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_record(table: str, record: dict, index: int) -> list[str]:
    errors = []
    if table == "admin":
        if not record.get("Name"): errors.append(f"[{index}] admin.Name missing")
        if not record.get("Number"): errors.append(f"[{index}] admin.Number missing")
    elif table == "teacher":
        if not record.get("Name"): errors.append(f"[{index}] teacher.Name missing")
        if not record.get("Number"): errors.append(f"[{index}] teacher.Number missing")
    elif table == "room":
        if not record.get("area"): errors.append(f"[{index}] room.area missing")
        if not record.get("building"): errors.append(f"[{index}] room.building missing")
        if not record.get("room_id"): errors.append(f"[{index}] room.room_id missing")
    elif table == "classi":
        if not record.get("class_id"): errors.append(f"[{index}] classi.class_id missing")
        cap = record.get("capacity")
        if cap is not None and (not isinstance(cap, int) or cap <= 0):
            errors.append(f"[{index}] classi.capacity must be positive int")
    elif table == "students":
        if not record.get("StuNum"): errors.append(f"[{index}] students.StuNum missing")
        if not record.get("Name"): errors.append(f"[{index}] students.Name missing")
    elif table == "course":
        if not record.get("course_id"): errors.append(f"[{index}] course.course_id missing")
        day = record.get("day")
        if day is not None and day not in range(1, 8):
            errors.append(f"[{index}] course.day must be 1-7")
    return errors

def validate_data(all_data: dict) -> list[str]:
    all_errors = []
    for _, table in IMPORT_ORDER:
        records = all_data.get(table, [])
        for i, rec in enumerate(records):
            all_errors.extend(validate_record(table, rec, i))
    return all_errors

# ---------------------------------------------------------------------------
# Core import logic
# ---------------------------------------------------------------------------

def safe_int(val, default=None):
    if val is None: return default
    try: return int(val)
    except (ValueError, TypeError): return default

def safe_float(val, default=0.0):
    if val is None: return default
    try: return float(val)
    except (ValueError, TypeError): return default

def import_table(conn: sqlite3.Connection, table: str, records: list) -> int:
    if not records:
        return 0
    count = 0

    if table == "admin":
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO admin (Name, Number, password_hash) VALUES (?, ?, ?)",
                (r["Name"], r["Number"], hash_password(r.get("password", "123456")))
            )
            count += 1

    elif table == "teacher":
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO teacher (Name, Number, password_hash) VALUES (?, ?, ?)",
                (r["Name"], r["Number"], hash_password(r.get("password", "123456")))
            )
            count += 1

    elif table == "room":
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO room (area, building, room_id, capacity) VALUES (?, ?, ?, ?)",
                (str(r["area"]), str(r["building"]), str(r["room_id"]), str(r.get("capacity", "")))
            )
            count += 1

    elif table == "classi":
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO classi (class_id, name, master_id, capacity) VALUES (?, ?, ?, ?)",
                (r["class_id"], r.get("name", ""), r.get("master_id", ""), safe_int(r.get("capacity"), 0))
            )
            count += 1

    elif table == "students":
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO students (Name, StuNum, Cls, password_hash, gpa) VALUES (?, ?, ?, ?, ?)",
                (r["Name"], r["StuNum"], r.get("Cls", ""),
                 hash_password(r.get("password", "123456")),
                 safe_float(r.get("gpa", 0.0)))
            )
            count += 1

    elif table == "course":
        for r in records:
            conn.execute(
                """INSERT OR IGNORE INTO course (course_id, day, start_time, end_time,
                course_name, teacher_num, room_id, week_start, week_end, semester, credit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (r["course_id"], safe_int(r.get("day"), 1),
                 r.get("start_time", "08:00"), r.get("end_time", "09:40"),
                 r.get("course_name", ""), r.get("teacher_num", ""),
                 r.get("room_id", ""), safe_int(r.get("week_start"), 1),
                 safe_int(r.get("week_end"), 18), r.get("semester", ""),
                 safe_float(r.get("credit", 0)))
            )
            count += 1

    elif table == "classmate":
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO classmate (class_id, stu_num) VALUES (?, ?)",
                (r["class_id"], r["stu_num"])
            )
            count += 1

    elif table == "class_stu":
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO class_stu (course_id, stu_num) VALUES (?, ?)",
                (str(r["course_id"]), r["stu_num"])
            )
            count += 1

    elif table == "grade":
        for r in records:
            conn.execute(
                """INSERT OR IGNORE INTO grade
                (course_id, stu_num, score, semester, exam_type, remark)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (r["course_id"], r["stu_num"], safe_float(r.get("score", 0)),
                 r.get("semester", ""), r.get("exam_type", "期末考试"),
                 r.get("remark", ""))
            )
            count += 1

    elif table == "library_seat":
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO library_seat (seat_id, area, floor, description, status) VALUES (?, ?, ?, ?, ?)",
                (r["seat_id"], r["area"], safe_int(r.get("floor"), 1),
                 r.get("description", ""), r.get("status", "available"))
            )
            count += 1

    elif table == "library_reservation":
        for r in records:
            conn.execute(
                """INSERT OR IGNORE INTO library_reservation
                (user_id, seat_id, date, start_time, end_time, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (r["user_id"], r["seat_id"], r["date"], r["start_time"],
                 r["end_time"], r.get("status", "reserved"),
                 r.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            )
            count += 1

    elif table == "todo":
        for r in records:
            conn.execute(
                """INSERT OR IGNORE INTO todo
                (user_id, title, description, date, status, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (r["user_id"], r["title"], r.get("description", ""),
                 r.get("date", date.today().isoformat()),
                 r.get("status", "pending"), r.get("priority", "medium"),
                 r.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                 r.get("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            )
            count += 1

    return count

def _refresh_gpa_cache(backend_dir: str):
    try:
        from student import score_to_grade_point
    except ImportError:
        return
    grade_path = os.path.join(backend_dir, "grade.db")
    course_path = os.path.join(backend_dir, "course.db")
    student_path = os.path.join(backend_dir, "students.db")
    if not all(os.path.exists(p) for p in [grade_path, course_path, student_path]):
        return
    g_conn = sqlite3.connect(grade_path)
    g_conn.row_factory = sqlite3.Row
    stu_nums = g_conn.execute("SELECT DISTINCT stu_num FROM grade").fetchall()
    c_conn = sqlite3.connect(course_path)
    c_conn.row_factory = sqlite3.Row
    s_conn = sqlite3.connect(student_path)
    for row in stu_nums:
        stu_num = row["stu_num"]
        grades = g_conn.execute(
            "SELECT course_id, score FROM grade WHERE stu_num = ?", (stu_num,)
        ).fetchall()
        if not grades:
            continue
        course_ids = [g["course_id"] for g in grades]
        ph = ",".join("?" * len(course_ids))
        credits = c_conn.execute(
            f"SELECT course_id, credit FROM course WHERE course_id IN ({ph})", course_ids
        ).fetchall()
        credit_map = {c["course_id"]: c["credit"] for c in credits}
        total_w = total_c = 0.0
        for g in grades:
            gp = score_to_grade_point(g["score"])
            cr = credit_map.get(g["course_id"], 0)
            total_w += gp * cr; total_c += cr
        gpa = round(total_w / total_c, 2) if total_c > 0 else 0.0
        s_conn.execute("UPDATE students SET gpa = ? WHERE StuNum = ?", (gpa, stu_num))
    s_conn.commit()
    s_conn.close(); c_conn.close(); g_conn.close()

def import_all(data: dict, backend_dir: str = BACKEND_DIR) -> dict:
    stats = {}
    total_ok = True
    for db_file, table in IMPORT_ORDER:
        records = data.get(table, [])
        if not records:
            stats[table] = {"total": 0, "inserted": 0, "db": db_file, "status": "skipped"}
            continue
        db_path = os.path.join(backend_dir, db_file)
        conn = sqlite3.connect(db_path)
        try:
            inserted = import_table(conn, table, records)
            conn.commit()
            stats[table] = {"total": len(records), "inserted": inserted, "db": db_file, "status": "ok"}
        except Exception as e:
            conn.rollback()
            stats[table] = {"total": len(records), "inserted": 0, "db": db_file, "status": f"error: {e}"}
            total_ok = False
        finally:
            conn.close()
    if data.get("students"):
        try:
            _refresh_gpa_cache(backend_dir)
            print("  GPA cache refreshed")
        except Exception as e:
            print(f"  GPA refresh failed (data still imported): {e}")
    stats["_summary"] = {
        "success": total_ok,
        "tables_imported": sum(1 for s in stats.values() if isinstance(s, dict) and s.get("status") == "ok"),
        "total_records": sum(s.get("total", 0) for s in stats.values() if isinstance(s, dict)),
    }
    return stats

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

EXAMPLE_DATA = {
    "admin": [{"Name": "Admin", "Number": "A001", "password": "admin123"}],
    "teacher": [
        {"Name": "Zhang", "Number": "T001", "password": "123456"},
        {"Name": "Li", "Number": "T002", "password": "123456"},
    ],
    "room": [
        {"area": "3", "building": "1", "room_id": "209", "capacity": "60"},
        {"area": "3", "building": "1", "room_id": "415", "capacity": "90"},
        {"area": "3", "building": "3", "room_id": "301", "capacity": "90"},
    ],
    "classi": [
        {"class_id": "CS101", "name": "CS Class 1", "master_id": "T001", "capacity": 40},
        {"class_id": "CS102", "name": "CS Class 2", "master_id": "T002", "capacity": 35},
    ],
    "students": [
        {"Name": "San Zhang", "StuNum": "2024001", "Cls": "CS101", "password": "123456"},
        {"Name": "Si Li", "StuNum": "2024002", "Cls": "CS101", "password": "123456"},
        {"Name": "Wu Wang", "StuNum": "2024003", "Cls": "CS102", "password": "123456"},
    ],
    "course": [
        {"course_id": "C001", "day": 1, "start_time": "08:00", "end_time": "09:40",
         "course_name": "Data Structures", "teacher_num": "T001", "room_id": "3-1-209",
         "week_start": 1, "week_end": 18, "semester": "2024-2025-1", "credit": 3.0},
        {"course_id": "C002", "day": 3, "start_time": "10:00", "end_time": "11:40",
         "course_name": "OS", "teacher_num": "T002", "room_id": "3-3-301",
         "week_start": 1, "week_end": 16, "semester": "2024-2025-1", "credit": 4.0},
    ],
    "classmate": [
        {"class_id": "CS101", "stu_num": "2024001"},
        {"class_id": "CS101", "stu_num": "2024002"},
        {"class_id": "CS102", "stu_num": "2024003"},
    ],
    "class_stu": [
        {"course_id": "C001", "stu_num": "2024001"},
        {"course_id": "C001", "stu_num": "2024002"},
        {"course_id": "C002", "stu_num": "2024003"},
    ],
    "grade": [
        {"course_id": "C001", "stu_num": "2024001", "score": 92.0, "semester": "2024-2025-1"},
        {"course_id": "C001", "stu_num": "2024002", "score": 85.5, "semester": "2024-2025-1"},
        {"course_id": "C002", "stu_num": "2024003", "score": 78.0, "semester": "2024-2025-1"},
    ],
}

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

NR = "\n"

def print_report(stats: dict):
    summary = stats.pop("_summary", {})
    sep = "=" * 55
    lines = [f"{sep}", "  Bulk Import Report", sep]
    ok_count = fail_count = 0
    for table, info in stats.items():
        if not isinstance(info, dict): continue
        status = info.get("status", "?")
        db = info.get("db", "")
        total = info.get("total", 0)
        inserted = info.get("inserted", 0)
        if status == "ok":
            flag = "[OK]"; ok_count += 1
        elif status == "skipped":
            flag = "[--]"
        else:
            flag = "[!!]"; fail_count += 1
        lines.append(f"  {flag} {table:20s} -> {db:15s}  {inserted:4d}/{total} records")
    lines.append("-" * 55)
    lines.append(f"  Total: {summary.get('tables_imported', 0)} tables, "
                 f"{summary.get('total_records', 0)} records")
    lines.append(f"  {'All imported successfully' if fail_count == 0 else f'{fail_count} table(s) failed'}")
    lines.append(sep)
    print(NR.join(lines))

def generate_example(path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(EXAMPLE_DATA, f, ensure_ascii=False, indent=2)
    print(f"  Example file created: {path}")
    print(f"  Edit it and run: python Backend/bulk_import.py {path}")

def main():
    if "--example" in sys.argv:
        generate_example(os.path.join(BACKEND_DIR, "import_data.json"))
        return
    json_path = os.path.join(BACKEND_DIR, "import_data.json")
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            json_path = arg; break
    if not os.path.exists(json_path):
        print(f"  File not found: {json_path}")
        print(f"  Generate template: python Backend/bulk_import.py --example")
        sys.exit(1)
    print(f"  Reading: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    errors = validate_data(data)
    if errors:
        print(f"  {len(errors)} validation error(s):")
        for e in errors[:20]: print(f"    - {e}")
        sys.exit(1)
    print("  Validation passed, importing...")
    stats = import_all(data)
    print_report(stats)
    if not stats.get("_summary", {}).get("success"):
        sys.exit(1)

if __name__ == "__main__":
    main()
