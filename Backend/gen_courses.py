"""
    gen_courses.py - 课程数据自动生成器

    读取 teacher.db + room.db，按约束生成全部课程 CSV。
    输出: courses_output.csv

    约束:
      - 教师指定规则 (康肖松→工科数学分析, 刘峰→高级语言A, 等)
      - 同一时间同一教师不冲突
      - 同一时间同一教室不冲突
      - 教室必须存在于 room.db
      - 教师必须存在于 teacher.db
"""

import sqlite3
import json
import csv
import os
import random

BACKEND = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 1. 读取教师数据
# ---------------------------------------------------------------------------

def load_teachers():
    conn = sqlite3.connect(os.path.join(BACKEND, "teacher.db"))
    cur = conn.execute("SELECT Number, Name FROM teacher")
    teachers = {r[1]: r[0] for r in cur.fetchall()}  # name -> number
    all_list = [{"name": n, "number": num} for n, num in teachers.items()]
    conn.close()
    return teachers, all_list

# ---------------------------------------------------------------------------
# 2. 读取教室数据
# ---------------------------------------------------------------------------

def load_rooms():
    conn = sqlite3.connect(os.path.join(BACKEND, "room.db"))
    cur = conn.execute("SELECT area, building, room_id, capacity FROM room ORDER BY area, building, room_id")
    rooms = []
    for r in cur.fetchall():
        rooms.append({
            "room_id": f"{r[0]}-{r[1]}-{r[2]}",
            "area": r[0],
            "building": r[1],
            "num": r[2],
            "capacity": int(r[3]) if r[3].isdigit() else 40,
        })
    conn.close()
    return rooms

# ---------------------------------------------------------------------------
# 3. 工具函数
# ---------------------------------------------------------------------------

TIME_SLOTS = [
    ("08:00", "09:40", 100, 0),
    ("10:00", "11:40", 100, 0),
    ("14:00", "15:40", 100, 0),
    ("16:00", "17:40", 100, 0),
    ("19:00", "21:30", 150, 5),
]
DAYS = list(range(1, 6))  # 周一 ~ 周五

def time_to_min(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)

def build_course_id(semester_prefix, code, start_time, dur_flag, room_num, credit, checksum=None):
    """构建 17 位 course_id"""
    st_min = time_to_min(start_time)
    room_last3 = room_num[-3:].zfill(3)
    credit_str = str(int(credit * 10)).zfill(2)
    base = f"{semester_prefix}{str(code).zfill(2)}{st_min}{dur_flag}{room_last3}{credit_str}"
    if checksum is None:
        total = sum(int(d) for d in base)
        checksum = total % 10
    return base + str(checksum)

def semester_prefix(sem):
    """semester -> 5位前缀"""
    m = {"2025-2026-1": "25261", "2025-2026-2": "25262", "2025-2026-3": "25263"}
    return m.get(sem, "25261")

# ---------------------------------------------------------------------------
# 4. 课程定义
# ---------------------------------------------------------------------------

# (name, sem, credit, course_code, special_teachers)
# sem: "1"=上, "2"=下, "12"=上下, "3"=第三学期
# special_teachers: None=任意教师, ["name1","name2"]=限定教师列表

COURSE_DEFS = [
    # === 公共基础课 ===
    ("高等数学", "12", 5.0, 1, None),
    ("工科数学分析", "12", 6.0, 2, ["康肖松"]),
    ("高级语言程序设计A", "1", 4.0, 3, ["刘峰"]),
    ("高级语言程序设计B", "1", 4.0, 4, None),
    ("线性代数A", "1", 4.0, 5, None),
    ("线性代数B", "1", 4.0, 6, None),
    ("高等代数", "12", 4.0, 7, None),
    ("高级交际英语", "1", 3.0, 8, None),
    ("文化与思辨", "2", 3.0, 9, None),
    ("大学交际英语", "12", 3.0, 10, None),
    ("军事理论与技能", "12", 4.0, 11, None),
    ("军事高新技术及其应用", "1", 2.0, 12, None),
    ("素质体育", "12", 1.0, 13, None),
    ("思想道德与法治", "1", 2.5, 14, None),
    ("中国近代史纲要", "2", 2.0, 15, None),
    ("马克思主义原理", "2", 2.0, 16, None),
    ("大学物理", "2", 3.5, 17, None),

    # === 专业核心课 ===
    ("计算机系统基础", "2", 4.0, 18, ["李清安", "龚奕利"]),
    ("数据结构A", "2", 4.0, 19, ["汪鼎文", "张乐飞"]),
    ("数据结构B", "2", 4.0, 20, None),
    ("人工智能导引", "2", 2.0, 21, ["刘菊华", "刘友发", "杜博"]),
    ("数字逻辑与数字电路", "2", 3.0, 22, ["瞿涛", "武小平"]),
    ("软件系统实践", "3", 1.0, 23, ["李清安", "龚奕利", "王健"]),
    ("计算机组成原理", "1", 4.0, 24, None),
    ("操作系统", "2", 3.5, 25, None),
    ("计算机网络", "1", 3.0, 26, None),
    ("编译原理", "2", 3.0, 27, None),
    ("数据库系统", "1", 4.0, 28, None),
    ("面向对象程序设计(Java)", "2", 4.0, 29, None),
    ("概率论", "1", 3.0, 30, None),
    ("离散数学", "1", 3.0, 31, None),
    ("软件工程", "2", 3.0, 32, None),
    ("算法设计与分析", "1", 3.5, 33, ["董文永"]),

    # === 专业选修/进阶课 ===
    ("机器学习", "2", 3.0, 34, None),
    ("网络安全", "2", 2.5, 35, None),
    ("软件安全", "2", 2.5, 36, None),
    ("组合数学", "2", 3.0, 37, None),
    ("嵌入式系统", "1", 3.0, 38, None),
    ("物联网技术", "2", 2.5, 39, None),
    ("并行与分布式计算", "2", 2.5, 40, None),
    ("云计算平台与技术", "2", 2.0, 41, None),
    ("计算机图形学", "1", 3.0, 42, None),
    ("数字图像处理", "2", 3.0, 43, None),
    ("虚拟现实与增强现实", "1", 2.0, 44, None),
    ("计算机视觉", "2", 2.0, 45, None),
    ("自然语言处理", "2", 3.0, 46, None),
    ("数据挖掘", "2", 3.0, 47, None),
    ("信息检索", "1", 2.5, 48, None),
    ("计算机体系结构", "1", 3.0, 49, None),
    ("软件需求工程", "1", 2.0, 50, None),
    ("人机交互", "2", 2.0, 51, None),
    ("智能计算系统", "2", 3.0, 52, None),
    ("计算理论", "2", 3.0, 53, None),
    ("接口与通信", "2", 2.0, 54, None),
    ("多媒体技术", "1", 2.5, 55, None),
    ("区块链技术与应用", "2", 2.0, 56, None),
    ("生物信息学", "2", 2.0, 57, None),
    ("大数据分析", "2", 2.5, 58, None),
    ("EDA技术", "1", 2.0, 59, None),
    ("网络编程", "2", 2.5, 60, None),
    ("Web信息处理", "2", 2.0, 61, None),
]

# ---------------------------------------------------------------------------
# 5. 排课逻辑
# ---------------------------------------------------------------------------

def assign_teachers(defs, teacher_lookup, fallback_pool):
    """为每门课分配教师"""
    result = []
    used_names = set()

    for name, sem, credit, code, special in defs:
        if special:
            # 指定的教师列表 -> 每位老师开一门课
            for tname in special:
                tnum = teacher_lookup.get(tname)
                if not tnum:
                    print(f"  [WARN] 教师 {tname} 不在 teacher.db 中，跳过")
                    continue
                result.append((name, sem, credit, code, tname, tnum))
        else:
            # 从fallback中取一个
            result.append((name, sem, credit, code, None, None))
    return result


def fill_teachers(assignments, teacher_lookup, fallback_pool):
    """为没有指定教师的课程分配教师"""
    final = []
    used_this_sem = {}
    for item in assignments:
        name, sem, credit, code, spec_name, spec_num = item
        if spec_num:
            final.append((name, sem, credit, code, spec_name, spec_num))
        else:
            # 选一个未用过的教师
            pool = [t for t in fallback_pool if t["number"] not in used_this_sem.get(sem, set()) or not used_this_sem.get(sem)]
            if not pool:
                pool = fallback_pool
            t = random.choice(pool)
            if sem not in used_this_sem:
                used_this_sem[sem] = set()
            used_this_sem[sem].add(t["number"])
            final.append((name, sem, credit, code, t["name"], t["number"]))
    return final


def schedule_courses(courses, rooms):
    """为所有课程安排时间和教室，避免冲突"""
    # occupancy: (day, slot_idx, room_id) -> occupied
    # teacher_occ: (day, slot_idx, teacher_num) -> occupied
    occupancy = set()
    teacher_occ = set()
    results = []

    # 按 semester 分组
    by_sem = {}
    for c in courses:
        name, sem_str, credit, code, tname, tnum = c
        for sem in sem_str:  # "12" -> ["1", "2"]
            full_sem = f"2025-2026-{sem}" if sem != "3" else "2024-2025-3"
            if sem == "3":
                full_sem = "2025-2026-3"
            by_sem.setdefault(full_sem, []).append((name, credit, code, tname, tnum))

    random.seed(42)

    for full_sem, sem_courses in by_sem.items():
        sem_prefix = semester_prefix(full_sem)
        # 对这个学期的课程排课
        for (name, credit, code, tname, tnum) in sem_courses:
            scheduled = False
            attempts = 0
            while not scheduled and attempts < 200:
                attempts += 1
                day = random.choice(DAYS)
                slot_idx = random.randint(0, len(TIME_SLOTS) - 1)
                room = random.choice(rooms)
                room_id = room["room_id"]

                key = (day, slot_idx, room_id)
                tkey = (day, slot_idx, tnum)

                if key in occupancy or tkey in teacher_occ:
                    continue

                # 成功分配
                start_time, end_time, dur_min, dur_flag = TIME_SLOTS[slot_idx]
                occupancy.add(key)
                teacher_occ.add(tkey)

                cid = build_course_id(sem_prefix, code, start_time, dur_flag, room["num"], credit)

                results.append({
                    "course_id": cid,
                    "day": day,
                    "start_time": start_time,
                    "end_time": end_time,
                    "course_name": name,
                    "teacher_num": tnum,
                    "room_id": room_id,
                    "week_start": 1,
                    "week_end": 16,
                    "semester": full_sem,
                    "credit": credit,
                })
                scheduled = True

            if not scheduled:
                print(f"  [WARN] 无法安排课程: {name} {full_sem} {tname}")

    return results


# ---------------------------------------------------------------------------
# 6. 主流程
# ---------------------------------------------------------------------------

def main():
    print("=== 课程数据生成器 ===\n")

    # 加载数据
    print("正在加载 teacher.db ...")
    teacher_lookup, fallback_pool = load_teachers()
    print(f"  共 {len(teacher_lookup)} 位教师\n")

    print("正在加载 room.db ...")
    rooms = load_rooms()
    print(f"  共 {len(rooms)} 间教室\n")

    print(f"正在定义 {len(COURSE_DEFS)} 门课程...")

    # 分配教师
    print("正在分配教师...")
    assignments = assign_teachers(COURSE_DEFS, teacher_lookup, fallback_pool)
    courses = fill_teachers(assignments, teacher_lookup, fallback_pool)
    print(f"  共 {len(courses)} 条课程-教师绑定\n")

    # 排课
    print("正在排课（时间和教室）...")
    schedule = schedule_courses(courses, rooms)
    print(f"  成功安排 {len(schedule)} 门课程\n")

    # 输出 CSV
    output_path = os.path.join(BACKEND, "courses_output.csv")
    fields = ["course_id", "day", "start_time", "end_time", "course_name",
              "teacher_num", "room_id", "week_start", "week_end", "semester", "credit"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in schedule:
            writer.writerow(row)

    print(f"已输出: {output_path}")
    print(f"可用以下命令导入: python Backend/import_csv.py {output_path}")

    # 打印前10行预览
    print("\n前 10 行预览:")
    for r in schedule[:10]:
        print(f"  {r['course_id']} | 周{r['day']} {r['start_time']}-{r['end_time']} | {r['course_name']:10s} | {r['teacher_num']:18s} | {r['room_id']}")

    # 统计
    by_sem = {}
    by_name = {}
    for r in schedule:
        by_sem[r["semester"]] = by_sem.get(r["semester"], 0) + 1
        by_name[r["course_name"]] = by_name.get(r["course_name"], 0) + 1

    print("\n按学期统计:")
    for sem, cnt in sorted(by_sem.items()):
        print(f"  {sem}: {cnt} 门课")

if __name__ == "__main__":
    main()
