#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lint one schedule HTML table before mailing it.

Checks two classes of defect, both of which have actually happened:

  A. constructs that mail clients strip or ignore (<style>, flex, grid,
     position, CSS variables, external fonts, script, <link>) and background
     colours declared in CSS with no bgcolor="" attribute to fall back on
  B. stale time state -- the "updated on" line in the header not being today

What it deliberately does NOT do: verify the countdowns. Doing that properly
means parsing the table's semantics, and a half-working parser that silently
passes a wrong table is worse than no parser. Instead it prints every date and
every countdown cell it found, side by side, for you to eyeball.

Output is ASCII-only on purpose (Windows console + Chinese = mojibake).

Usage:
    python scripts/lint_schedule.py my/schedule.html
    python scripts/lint_schedule.py my/schedule.html --today 2026-03-09

Exit code 0 = no errors, 1 = at least one error.
"""

import argparse
import datetime
import re
import sys

FORBIDDEN = [
    (r"<style[\s>]", "<style> block -- mail clients strip it; inline every rule"),
    (r"<script[\s>]", "<script> -- always stripped"),
    (r"<link[\s>]", "<link> to external CSS -- not fetched"),
    (r"@font-face|fonts\.googleapis", "external font -- use a system font stack"),
    (r"var\(--", "CSS variable -- unsupported"),
    (r"display\s*:\s*(flex|grid)", "flexbox/grid -- use nested <table> layout"),
    (r"position\s*:\s*(absolute|fixed|sticky)", "positioning -- unsupported"),
    (r"background-clip\s*:\s*text", "background-clip:text -- unsupported"),
]

CN_MONTH_DAY = re.compile(r"(\d{1,2})月(\d{1,2})日")
COUNTDOWN_CELL = re.compile(r">\s*(\d+)\s*天\s*<|>\s*(今天)\s*<|>\s*(已完成)\s*<")
HEADER_UPDATED = re.compile(r"更新[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日")
TAG_WITH_BG = re.compile(r"<(tr|table|td)\b[^>]*background-color\s*:[^>]*>", re.IGNORECASE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def strip_comments(html):
    """Drop HTML comments before linting.

    Comments are never rendered, so a comment that documents a forbidden
    construct ("禁 <style> / flex / grid") must not trip the check -- the
    template does exactly that. Replaced with newlines so line numbers survive.
    """
    return HTML_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), html)


def lint(html, today):
    errors, warnings = [], []

    for pattern, why in FORBIDDEN:
        for m in re.finditer(pattern, html, re.IGNORECASE):
            line = html.count("\n", 0, m.start()) + 1
            errors.append("line %d: %s" % (line, why))

    # every CSS background-color on a layout tag needs a bgcolor="" fallback
    for m in TAG_WITH_BG.finditer(html):
        tag = m.group(0)
        if "bgcolor" not in tag.lower():
            line = html.count("\n", 0, m.start()) + 1
            errors.append('line %d: <%s> sets background-color in CSS but has no bgcolor="" fallback'
                          % (line, m.group(1).lower()))

    # header "updated on" must be today
    m = HEADER_UPDATED.search(html)
    if not m:
        warnings.append("no dated update line in the header -- expected "
                        "GENGXIN: YYYY-nian-M-yue-D-ri; readers cannot tell how stale the table is")
    else:
        stamped = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if stamped != today:
            errors.append("header says updated %s but today is %s -- "
                          "rule 6: refresh the whole table's time state, not just one row"
                          % (stamped.isoformat(), today.isoformat()))

    if "<meta charset" not in html.lower():
        warnings.append("no <meta charset> -- some clients will mangle the Chinese")

    return errors, warnings


def summarize(html):
    dates = ["%02d-%02d" % (int(a), int(b)) for a, b in CN_MONTH_DAY.findall(html)]
    # Render countdown cells as ASCII so a Windows console can show them.
    counts = []
    for days, today_cell, done_cell in COUNTDOWN_CELL.findall(html):
        if days:
            counts.append("D-%s" % days)
        elif today_cell:
            counts.append("TODAY")
        elif done_cell:
            counts.append("DONE")
    print("dates found      (%d): %s" % (len(dates), ", ".join(dates) or "-"))
    print("countdowns found (%d): %s" % (len(counts), ", ".join(counts) or "-"))
    print("Eyeball these: every row's countdown must match its date against today.")
    print("This script does not verify them -- run scripts/countdown.py and compare.")


def main(argv=None):
    p = argparse.ArgumentParser(description="lint a schedule HTML table")
    p.add_argument("html")
    p.add_argument("--today", default=None, help="override today, e.g. 2026-03-09")
    p.add_argument("--no-date-check", action="store_true",
                   help="skip the header-date check (use when linting examples/)")
    args = p.parse_args(argv)

    today = (datetime.datetime.strptime(args.today, "%Y-%m-%d").date()
             if args.today else datetime.date.today())

    try:
        with open(args.html, encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        print("FAILED to read %s: %s" % (args.html, e))
        return 1

    html = strip_comments(raw)
    errors, warnings = lint(html, today)
    if args.no_date_check:
        errors = [e for e in errors if "header says updated" not in e]
        warnings = [w for w in warnings if "no dated update line" not in w]

    for w in warnings:
        print("WARN  %s" % w)
    for e in errors:
        print("ERROR %s" % e)

    print("-" * 60)
    summarize(html)
    print("-" * 60)
    print("RESULT: %d error(s), %d warning(s)" % (len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
