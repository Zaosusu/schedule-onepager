#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schedule-onepager · 邮件提醒触发器
=====================================

两种模式：
  check   —— 扫描今日 TODO 里的具体时间点，输出待发送的「到时提醒」
  preview —— 扫描明日 schedule，输出待发送的「前夜预告」

状态文件 my/reminder_state.json 记录已发送的提醒，避免重复。
输出 JSON 到 stdout，供 automation prompt 读取后用 QQ 邮箱发送。
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
import sqlite3

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SKILL_ROOT, "my", "personal.db")
STATE_PATH = os.path.join(SKILL_ROOT, "my", "reminder_state.json")


def resolve_today(args_today=None):
    return datetime.strptime(args_today, "%Y-%m-%d").date() if args_today else date.today()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"todo_reminded": {}, "schedule_previewed": {}}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def extract_times(text):
    """从文本中提取 HH:MM 时间列表。"""
    if not text:
        return []
    return re.findall(r'\b(\d{1,2}):(\d{2})(?::\d{2})?\b', text)


def time_to_minutes(h, m):
    return int(h) * 60 + int(m)


def cmd_check(args):
    """扫描今日 TODO 的到时提醒。"""
    today = resolve_today(args.today)
    now = datetime.now()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, task, note FROM todo WHERE todo_date=? AND status != '已完成'",
        (today.isoformat(),),
    ).fetchall()
    conn.close()

    state = load_state()
    reminded = state.setdefault("todo_reminded", {})

    reminders = []
    for tid, task, note in rows:
        times = extract_times(task + " " + (note or ""))
        if not times:
            continue
        for hh, mm in times:
            h, m = int(hh), int(mm)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                continue
            task_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if task_time < now:
                continue  # 已过去，跳过
            delta = (task_time - now).total_seconds() / 60
            if delta > 60:
                continue  # 超过1小时，等下一轮再检查
            key = f"{tid}:{h:02d}:{m:02d}"
            if key in reminded:
                continue
            reminded[key] = now.isoformat()
            reminders.append({
                "todo_id": tid,
                "task": task,
                "time": f"{h:02d}:{m:02d}",
                "delta_min": round(delta),
            })

    save_state(state)
    print(json.dumps({"mode": "check", "reminders": reminders}, ensure_ascii=False))


def cmd_preview(args):
    """扫描明日 schedule 的前夜预告。"""
    today = resolve_today(args.today)
    tomorrow = today + timedelta(days=1)
    conn = get_conn()
    rows = conn.execute(
        "SELECT date_label, weekday, title, role, detail FROM schedule "
        "WHERE iso_date = ? ORDER BY sort_key",
        (tomorrow.isoformat(),),
    ).fetchall()
    conn.close()

    state = load_state()
    previewed = state.setdefault("schedule_previewed", {})
    key = tomorrow.isoformat()
    if key in previewed:
        print(json.dumps({"mode": "preview", "sent": True, "items": []}, ensure_ascii=False))
        return

    items = []
    for r in rows:
        items.append({
            "date_label": r[0],
            "weekday": r[1],
            "title": r[2],
            "role": r[3],
            "detail": r[4],
        })

    previewed[key] = today.isoformat()
    save_state(state)
    print(json.dumps({"mode": "preview", "sent": False, "date": key, "items": items}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["check", "preview"])
    p.add_argument("--today")
    args = p.parse_args()
    if args.mode == "check":
        cmd_check(args)
    else:
        cmd_preview(args)


if __name__ == "__main__":
    main()
