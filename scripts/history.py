# -*- coding: utf-8 -*-
"""
每日历史记录 CLI —— 数据存 SQLite，HTML 只是可选的浏览视图（数据源仍是 DB）。

三种模式（排期表 / 今日 TODO / 每日历史记录）各自独立，本脚本只负责「历史记录」。

用法:
  # 追加一条（--date 省略默认今天；--cat 分类可选）
  python history.py add --date 2026-08-18 --cat 评审细则 --text "决赛评审细则 v2 已提交"

  # 查询（默认最近 20 条，倒序；可按日期过滤）
  python history.py list [--date 2026-08-18] [--limit 20]

  # 统计（按日期+分类计条数，便于回看哪天做了什么）
  python history.py stats

  # 导出 HTML 视图（供浏览器看，非数据源）
  python history.py export [--out 每日历史记录.html]

DB 路径解析优先级（任一命中即用）:
  1. --db 参数
  2. 环境变量 DAILY_HISTORY_DB
  3. 脚本同目录的 daily_history.db   （兼容把本脚本直接放到工作目录自用）
  4. 否则 <skill根>/my/daily_history.db  （个人区，已在 .gitignore）

数据文件: daily_history.db（SQLite，标准库 sqlite3，无需任何第三方依赖）
表结构:   daily_history(id, log_date 'YYYY-MM-DD', category, content, created_at)
"""
import argparse
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(BASE)                      # scripts/ 的上一级
DEFAULT_MY_DB = os.path.join(SKILL_ROOT, "my", "daily_history.db")
DEFAULT_HTML = os.path.join(BASE, "每日历史记录.html")

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  log_date   TEXT NOT NULL,
  category   TEXT,
  content    TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_history_date ON daily_history(log_date);
"""


def resolve_db(arg_db):
    if arg_db:
        return arg_db
    env = os.environ.get("DAILY_HISTORY_DB")
    if env:
        return env
    sibling = os.path.join(BASE, "daily_history.db")
    if os.path.exists(sibling):
        return sibling
    return DEFAULT_MY_DB


def get_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def cmd_add(args):
    path = resolve_db(args.db)
    conn = get_db(path)
    conn.execute(
        "INSERT INTO daily_history(log_date, category, content) VALUES (?,?,?)",
        (args.date, args.cat or "", args.text),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM daily_history ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    print(f"已记录 #{row[0]}  {args.date}  [{args.cat or '未分类'}]  {args.text}")


def cmd_list(args):
    path = resolve_db(args.db)
    conn = get_db(path)
    if args.date:
        rows = conn.execute(
            "SELECT id, log_date, category, content FROM daily_history WHERE log_date=? "
            "ORDER BY log_date DESC, id DESC",
            (args.date,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, log_date, category, content FROM daily_history "
            "ORDER BY log_date DESC, id DESC LIMIT ?",
            (args.limit,),
        ).fetchall()
    conn.close()
    if not rows:
        print("（无记录）")
        return
    for rid, d, cat, content in rows:
        cat = f"[{cat}] " if cat else ""
        print(f"#{rid}  {d}  {cat}{content}")


def cmd_stats(args):
    path = resolve_db(args.db)
    conn = get_db(path)
    rows = conn.execute(
        "SELECT log_date, category, COUNT(*) FROM daily_history "
        "GROUP BY log_date, category ORDER BY log_date DESC, category"
    ).fetchall()
    conn.close()
    if not rows:
        print("（无记录）")
        return
    print("日期          分类           条数")
    print("-" * 36)
    for d, cat, n in rows:
        print(f"{d}  {cat or '未分类':<12}  {n}")


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cmd_export(args):
    path = resolve_db(args.db)
    conn = get_db(path)
    rows = conn.execute(
        "SELECT log_date, category, content FROM daily_history ORDER BY log_date DESC, id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        print("数据库为空，没有可导出的记录")
        return

    by_date = {}
    for d, cat, content in rows:
        by_date.setdefault(d, []).append((cat, content))

    blocks = []
    for d in by_date:
        rows_html = []
        for cat, content in by_date[d]:
            rows_html.append(
                "<tr>"
                f'<td style="padding:11px 9px;border:1px solid #d8dced;color:#0f6b7a;font-weight:bold;width:86px;">{_esc(cat)}</td>'
                f'<td style="padding:11px 9px;border:1px solid #d8dced;color:#333333;line-height:1.7;">{_esc(content)}</td>'
                "</tr>"
            )
        blocks.append(
            '<tr><td style="padding:22px 24px 0 24px;">'
            f'<div style="font-size:16px;font-weight:bold;color:#0f6b7a;border-left:4px solid #0f6b7a;padding-left:10px;">{_esc(d)}</div>'
            "</td></tr>"
            '<tr><td style="padding:8px 24px 0 24px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            'style="border-collapse:collapse;font-size:14px;">'
            + "".join(rows_html)
            + "</table></td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日历史记录</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6fb;">
<table bgcolor="#f4f6fb" role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f4f6fb;">
<tr><td align="center" style="padding:20px 10px;">

<table bgcolor="#ffffff" role="presentation" width="760" cellpadding="0" cellspacing="0" border="0" style="width:760px;max-width:760px;background-color:#ffffff;border:1px solid #d8dced;font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif;">

  <tr><td style="padding:22px 24px 16px 24px;border-bottom:3px solid #0f6b7a;">
    <div style="font-size:23px;font-weight:bold;color:#0f6b7a;letter-spacing:1px;">每日历史记录</div>
    <div style="font-size:13px;color:#77809e;padding-top:6px;">记录每天做了什么 · 由 daily_history.db（SQLite）导出 · 与排期表 / 今日 TODO 各自独立</div>
  </td></tr>

{chr(10).join(blocks)}

  <tr><td style="padding:22px 24px 22px 24px;">
    <div style="border-top:1px solid #e4e7f2;padding-top:12px;font-size:12px;color:#99a0bb;line-height:1.8;">
      数据源：daily_history.db（SQLite）。追加用 <code>history.py add</code>，查看用 <code>history.py list</code>，本视图由 <code>history.py export</code> 生成。
    </div>
  </td></tr>

</table>

</td></tr>
</table>
</body>
</html>
"""
    out = args.out or DEFAULT_HTML
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已导出 {len(rows)} 条记录 -> {out}")


def main():
    parser = argparse.ArgumentParser(description="每日历史记录（SQLite）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="追加一条记录")
    p_add.add_argument("--db", default="", help="DB 路径（默认见脚本顶部说明）")
    p_add.add_argument("--date", default="", help="日期 YYYY-MM-DD（默认今天）")
    p_add.add_argument("--cat", default="", help="分类，如 鼓楼黑客松 / 评审细则")
    p_add.add_argument("--text", required=True, help="做了什么")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="查询记录")
    p_list.add_argument("--db", default="", help="DB 路径")
    p_list.add_argument("--date", default="", help="按日期过滤 YYYY-MM-DD")
    p_list.add_argument("--limit", type=int, default=20, help="条数（默认 20）")
    p_list.set_defaults(func=cmd_list)

    p_stats = sub.add_parser("stats", help="按日期+分类统计条数")
    p_stats.add_argument("--db", default="", help="DB 路径")
    p_stats.set_defaults(func=cmd_stats)

    p_exp = sub.add_parser("export", help="导出 HTML 视图")
    p_exp.add_argument("--db", default="", help="DB 路径")
    p_exp.add_argument("--out", default="", help="输出路径（默认 每日历史记录.html）")
    p_exp.set_defaults(func=cmd_export)

    args = parser.parse_args()
    if args.cmd == "add" and not args.date:
        import datetime
        args.date = datetime.date.today().isoformat()
    args.func(args)


if __name__ == "__main__":
    main()
