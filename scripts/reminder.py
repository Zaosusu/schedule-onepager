#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schedule-onepager · 邮件提醒触发器（直连 SMTP，免去两步确认）
=====================================

两种模式：
  check   —— 扫描今日 TODO 里的具体时间点，到点前直接发邮件
  preview —— 扫描明日 schedule，到点前直接发「前夜预告」

状态文件 my/reminder_state.json 记录已发送的提醒，避免重复。
直接通过 my/smtp_config.json 配置的 SMTP 发送，不走 QQ 邮箱连接器。
"""

import argparse
import json
import os
import re
import sys
import smtplib
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SKILL_ROOT, "my", "personal.db")
STATE_PATH = os.path.join(SKILL_ROOT, "my", "reminder_state.json")
CONFIG_PATH = os.path.join(SKILL_ROOT, "my", "smtp_config.json")
RECIPIENT = "178893717@qq.com"


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


def load_smtp_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"找不到 SMTP 配置文件：{CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def send_email(subject, body, to=None):
    if to is None:
        to = RECIPIENT
    cfg = load_smtp_config()
    msg = MIMEMultipart()
    msg["From"] = cfg["sender_email"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    server = smtplib.SMTP_SSL(cfg["smtp_server"], cfg["smtp_port"])
    try:
        server.login(cfg["sender_email"], cfg["sender_password"])
        server.sendmail(cfg["sender_email"], [to], msg.as_string())
    finally:
        server.quit()


def extract_times(text):
    """从文本中提取 HH:MM 时间列表。"""
    if not text:
        return []
    return re.findall(r'\b(\d{1,2}):(\d{2})(?::\d{2})?\b', text)


def time_to_minutes(h, m):
    return int(h) * 60 + int(m)


def cmd_check(args):
    """扫描今日 TODO 的到时提醒，到点前直接发邮件。"""
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

    sent = []
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
            subject = f"📋 行程提醒：{h:02d}:{m:02d} {task}"
            body = f"提醒：{h:02d}:{m:02d} 有「{task}」，距现在约 {int(delta)} 分钟。"
            try:
                send_email(subject, body)
                sent.append({"todo_id": tid, "task": task, "time": f"{h:02d}:{m:02d}"})
            except Exception as e:
                print(f"✗ 发送失败（#{tid} {task}）：{e}", file=sys.stderr)

    save_state(state)
    if sent:
        print(json.dumps({"mode": "check", "sent": sent}, ensure_ascii=False))
    else:
        print(json.dumps({"mode": "check", "sent": []}, ensure_ascii=False))


def cmd_preview(args):
    """扫描明日 schedule 的前夜预告，直接发邮件。"""
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

    if items:
        lines = [f"明天（{key}）行程：\n"]
        for it in items:
            lines.append(f"- {it['date_label']} {it['weekday']}｜{it['title']}｜{it['role']}")
            if it["detail"]:
                lines.append(f"  {it['detail']}")
        body = "\n".join(lines)
        subject = f"🌙 明日行程预告（{key}）"
        try:
            send_email(subject, body)
            previewed[key] = today.isoformat()
            save_state(state)
            print(json.dumps({"mode": "preview", "sent": True, "date": key, "items": items}, ensure_ascii=False))
        except Exception as e:
            print(f"✗ 发送失败：{e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps({"mode": "preview", "sent": False, "date": key, "items": []}, ensure_ascii=False))


def cmd_send(args):
    """向指定/默认收件人发送任意内容邮件（直连 SMTP，免两步确认）。"""
    subject = args.subject or "WorkBuddy 通知"
    body = args.body or ""
    to = args.to
    try:
        send_email(subject, body, to=to)
        print(json.dumps({"mode": "send", "ok": True, "to": to or RECIPIENT}, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 发送失败：{e}", file=sys.stderr)
        sys.exit(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["check", "preview", "send"])
    p.add_argument("--today")
    p.add_argument("--subject", help="send 模式：邮件主题")
    p.add_argument("--body", help="send 模式：邮件正文（纯文本）")
    p.add_argument("--to", help="send 模式：收件人，缺省用 my/smtp_config.json 的默认收件人")
    args = p.parse_args()
    if args.mode == "check":
        cmd_check(args)
    elif args.mode == "preview":
        cmd_preview(args)
    else:
        cmd_send(args)


if __name__ == "__main__":
    main()
