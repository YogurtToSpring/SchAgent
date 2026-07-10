"""
    enroll_courses.py - 选课数据生成器 v3

    仅自动导入 雷军班(C001) + 弘毅班(C002) 的选课。
    其他班级由学生自行选课。

    规则:
      - 工科数学分析(康肖松) → C001 + C002
      - 高等数学             → 不导入C001/C002
      - 计算机系统基础        → C002=李清安, C001=龚奕利
"""

import sqlite3, os, random
from collections import defaultdict

BACKEND = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 所有需要自动导入的课程
# ---------------------------------------------------------------------------

AUTO_COURSES = [
    # (course_name, sem, credit)
    ("工科数学分析",      "12", 6.0),
    ("高级语言程序设计A",  "1",  4.0),
    ("高级语言程序设计B",  "1",  4.0),
    ("线性代数A",         "1",  4.0),
    ("线性代数B",         "1",  4.0),
    ("高等代数",          "12", 4.0),
    ("高级交际英语",      "1",  3.0),
    ("文化与思辨",        "2",  3.0),
    ("大学交际英语",      "12", 3.0),
    ("军事理论与技能",    "12", 4.0),
    ("军事高新技术及其应用", "1", 2.0),
    ("素质体育",          "12", 1.0),
    ("思想道德与法治",    "1",  2.5),
    ("中国近代史纲要",    "2",  2.0),
    ("马克思主义原理",    "2",  2.0),
    ("数据结构A",        "2",  4.0),
    ("数据结构B",        "2",  4.0),
    ("人工智能导引",     "2",  2.0),
    ("数字逻辑与数字电路", "2", 3.0),
    ("软件系统实践",     "3",  1.0),
]

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print("=== 选课生成器 v3 (仅雷军班+弘毅班自动导入) ===\n")
    
    # 1. 加载数据
    print("[1/4] Loading students...")
    conn = sqlite3.connect(os.path.join(BACKEND, "students.db"))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT StuNum, Name, Cls FROM students ORDER BY Cls, StuNum").fetchall()
    conn.close()
    
    by_cls = defaultdict(list)
    for r in rows:
        by_cls[r["Cls"]].append({"num": r["StuNum"], "name": r["Name"], "cls": r["Cls"]})
    
    for cid in sorted(by_cls):
        print(f"  {cid}: {len(by_cls[cid])} students")
    
    c001 = by_cls.get("C001", [])
    c002 = by_cls.get("C002", [])
    auto_stu = c001 + c002
    print(f"\n  Auto-enrolling: C001({len(c001)}) + C002({len(c002)}) = {len(auto_stu)} students")
    
    # 2. 清理 + 准备
    print("\n[2/4] Clearing class_stu.db...")
    cs = sqlite3.connect(os.path.join(BACKEND, "class_stu.db"))
    before = cs.execute("SELECT COUNT(*) FROM class_stu").fetchone()[0]
    cs.execute("DELETE FROM class_stu")
    print(f"  Cleared {before} old records")
    
    # 3. 查询 course_id
    print("\n[3/4] Querying course IDs...")
    co = sqlite3.connect(os.path.join(BACKEND, "course.db"))
    co.row_factory = sqlite3.Row
    
    # 工科数学分析 - 康肖松
    gks1 = co.execute("SELECT course_id FROM course WHERE course_name='工科数学分析' AND teacher_num='T2010301978099' AND semester='2025-2026-1'").fetchone()
    gks2 = co.execute("SELECT course_id FROM course WHERE course_name='工科数学分析' AND teacher_num='T2010301978099' AND semester='2025-2026-2'").fetchone()
    
    # 计算机系统基础
    cs_li = co.execute("SELECT course_id FROM course WHERE course_name='计算机系统基础' AND teacher_num='T09424919823613' AND semester='2025-2026-2'").fetchone()
    cs_gong = co.execute("SELECT course_id FROM course WHERE course_name='计算机系统基础' AND teacher_num='T46814030139067' AND semester='2025-2026-2'").fetchone()
    
    # 其他课程 (按名称+学期找任意教学班)
    course_map = {}
    for name, sem_str, credit in AUTO_COURSES:
        for ch in sem_str:
            fs = f"2025-2026-{ch}"
            r = co.execute("SELECT course_id FROM course WHERE course_name=? AND semester=? LIMIT 1", (name, fs)).fetchone()
            if r:
                course_map[(name, fs)] = r[0]
            else:
                print(f"  WARNING: No course found for {name} {fs}")
    
    co.close()
    
    # 打印关键映射
    print(f"  工科数学分析(康肖松) S1: {gks1[0] if gks1 else 'NOT FOUND'}")
    print(f"  工科数学分析(康肖松) S2: {gks2[0] if gks2 else 'NOT FOUND'}")
    print(f"  计算机系统基础(李清安→C002): {cs_li[0] if cs_li else 'NOT FOUND'}")
    print(f"  计算机系统基础(龚奕利→C001): {cs_gong[0] if cs_gong else 'NOT FOUND'}")
    
    # 4. 生成选课
    print("\n[4/4] Generating enrollments...")
    inserted = 0
    
    def ins(cid, stu):
        nonlocal inserted
        if not cid: return
        cs.execute("INSERT OR IGNORE INTO class_stu (course_id, stu_num) VALUES (?,?)", (cid, stu["num"]))
        inserted += 1
    
    # 普通课程 - 每个学生选每门课
    for (name, fs), cid in course_map.items():
        if name == "工科数学分析":
            continue  # 单独处理
        for s in auto_stu:
            ins(cid, s)
    
    # 工科数学分析 - 康肖松 (C001+C002)
    print(f"\n  工科数学分析(康肖松):")
    for sid, sem_label in [(gks1[0] if gks1 else None, "S1"), (gks2[0] if gks2 else None, "S2")]:
        if not sid: continue
        for s in auto_stu:
            ins(sid, s)
        print(f"    {sem_label}: {len(auto_stu)} students")
    
    # 计算机系统基础
    print(f"\n  计算机系统基础:")
    cid_li = cs_li[0] if cs_li else None
    cid_gong = cs_gong[0] if cs_gong else None
    for s in c001:
        ins(cid_gong, s)
    for s in c002:
        ins(cid_li, s)
    print(f"    C001(雷军班,{len(c001)}) -> 龚奕利 ({cid_gong})")
    print(f"    C002(弘毅班,{len(c002)}) -> 李清安 ({cid_li})")
    
    cs.commit()
    
    # 验证
    total = cs.execute("SELECT COUNT(*) FROM class_stu").fetchone()[0]
    stu_cnt = cs.execute("SELECT COUNT(DISTINCT stu_num) FROM class_stu").fetchone()[0]
    s2035 = cs.execute("SELECT COUNT(*) FROM class_stu WHERE stu_num='2025300002035'").fetchone()[0]
    print(f"\n  Total enrollments: {total}")
    print(f"  Total students: {stu_cnt}")
    print(f"  马子蘅(2025300002035): {s2035} courses")
    
    # 马子蘅选课详情
    co2 = sqlite3.connect(os.path.join(BACKEND, "course.db"))
    co2.row_factory = sqlite3.Row
    print(f"\n  马子蘅选课详情:")
    for r in cs.execute("SELECT course_id FROM class_stu WHERE stu_num='2025300002035' ORDER BY course_id"):
        c = co2.execute("SELECT course_name, semester, teacher_num FROM course WHERE course_id=?", (r[0],)).fetchone()
        if c: print(f"    {c['course_name']:20s} {c['semester']} T:{c['teacher_num'][:8]}...")
    co2.close()
    
    cs.close()
    print(f"\n  Inserted {inserted} enrollment records")
    print("Done.")

if __name__ == "__main__":
    main()
