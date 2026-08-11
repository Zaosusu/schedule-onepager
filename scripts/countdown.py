#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weekday / countdown calculator for the schedule table.

Two jobs, both of which exist because doing them in your head is where the
mistakes come from:

1. countdown  -- for each date, print its weekday and how many days out it is.
   Never hand-compute a countdown; the whole table has to be recomputed every
   time the table is touched, and stale countdowns are the #1 defect.

2. --which-year -- an announcement says "Aug 21 (Friday)" but doesn't say the
   year, or says a year that contradicts the weekday. Print the weekday of that
   month/day across nearby years so you can tell which year is actually meant.

Output is deliberately ASCII-only: Chinese text in a Windows console gets
mojibake'd, and this script exists to be read off a terminal.

Usage:
    python scripts/countdown.py 2026-08-21 2026-08-22 2026-09-04
    python scripts/countdown.py --today 2026-08-11 2026-08-21
    python scripts/countdown.py --which-year 08-21
"""

import argparse
import datetime
import sys

WEEKDAY_CN = ["Mon(1)", "Tue(2)", "Wed(3)", "Thu(4)", "Fri(5)", "Sat(6)", "Sun(7)"]


def parse_date(s):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%m-%d", "%m/%d"):
        try:
            d = datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
        if fmt in ("%m-%d", "%m/%d"):
            d = d.replace(year=datetime.date.today().year)
        return d
    raise argparse.ArgumentTypeError("cannot parse date: %s" % s)


def cmd_countdown(dates, today):
    print("today = %s %s" % (today.isoformat(), WEEKDAY_CN[today.weekday()]))
    print("-" * 46)
    for d in sorted(dates):
        delta = (d - today).days
        if delta > 0:
            state = "D-%d" % delta
        elif delta == 0:
            state = "TODAY"
        else:
            state = "DONE (%d days ago)" % -delta
        weekend = "  <-- WEEKEND" if d.weekday() >= 5 else ""
        print("%s  %-8s  %-20s%s" % (d.isoformat(), WEEKDAY_CN[d.weekday()], state, weekend))


def cmd_which_year(md, today):
    try:
        month, day = [int(x) for x in md.replace("/", "-").split("-")]
    except ValueError:
        print("--which-year expects MM-DD, e.g. 08-21")
        return 1
    print("which year has %02d-%02d on which weekday:" % (month, day))
    print("-" * 46)
    for year in range(today.year - 1, today.year + 3):
        try:
            d = datetime.date(year, month, day)
        except ValueError:
            continue  # e.g. Feb 29 in a non-leap year
        print("%s  %s" % (d.isoformat(), WEEKDAY_CN[d.weekday()]))
    print("\nCross-check against the weekday printed on the announcement.")
    print("Announcements get the year wrong far more often than the weekday.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="weekday + countdown helper")
    p.add_argument("dates", nargs="*", type=parse_date, help="dates, e.g. 2026-08-21")
    p.add_argument("--today", type=parse_date, default=None, help="override today (default: system date)")
    p.add_argument("--which-year", metavar="MM-DD", default=None,
                   help="print the weekday of MM-DD across nearby years")
    args = p.parse_args(argv)

    today = args.today or datetime.date.today()

    if args.which_year:
        return cmd_which_year(args.which_year, today)
    if not args.dates:
        p.print_help()
        return 1
    cmd_countdown(args.dates, today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
