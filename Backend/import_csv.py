"""
    import_csv.py - 将 CSV 文件导入 SQLite 数据库

    用法:
        python Backend/import_csv.py courses_output.csv
"""
import csv
import sqlite3
import os
import sys

BACKEND = os.path.dirname(os.path.abspath(__file__))

TABLE_CONFIG = {
    "course": {
        "columns": ["course_id", "day", "start_time", "end_time", "course_name",
                     "teacher_num", "room_id", "week_start", "week_end", "semester", "credit"],
        "insert": """INSERT OR IGNORE INTO course
            (course_id, day, start_time, end_time, course_name,
             teacher_num, room_id, week_start, week_end, semester, credit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    }
}

def import_csv(csv_path: str, table: str = "course") -> dict:
    config = TABLE_CONFIG[table]
    db_path = os.path.join(BACKEND, f"{table}.db")

    conn = sqlite3.connect(db_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    inserted = 0
    skipped = 0
    errors = 0

    for row in rows:
        try:
            vals = tuple(row[c] for c in config["columns"])
            conn.execute(config["insert"], vals)
            inserted += 1
        except Exception as e:
            errors += 1
            print(f"  Error: {row.get('course_id', '?')}: {e}")

    conn.commit()
    conn.close()

    count = inserted - skipped - errors
    return {"total": len(rows), "inserted": inserted, "errors": errors, "skipped": skipped}

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_csv.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        csv_path = os.path.join(BACKEND, csv_path)
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        sys.exit(1)

    print(f"Importing {csv_path}...")
    stats = import_csv(csv_path)
    print(f"  Total: {stats['total']}, Inserted: {stats['inserted']}, Errors: {stats['errors']}")

if __name__ == "__main__":
    main()
