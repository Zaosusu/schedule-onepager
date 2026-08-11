#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mail one HTML schedule table to yourself as the mail body.

Credentials come from the environment ONLY. Nothing is written to disk, no
config file holds a password, and no argument takes one (so it stays out of
your shell history's argv in the obvious way -- see references/smtp-setup.md
for how to keep it out of history entirely).

Required env:
    SMTP_USER   login account, e.g. someone@example.com
    SMTP_PASS   app-specific password / authorization code (NOT your login password)

Optional env:
    SMTP_HOST   default smtp.qq.com
    SMTP_PORT   default 465 (implicit TLS)
    MAIL_TO     default = SMTP_USER (mail it to yourself)
    MAIL_FROM   default = SMTP_USER. Most providers require From == login account.

Usage:
    SMTP_USER=... SMTP_PASS=... python scripts/send_schedule.py my/schedule.html
    python scripts/send_schedule.py my/schedule.html --subject "My schedule (2026-08-11)"
    python scripts/send_schedule.py my/schedule.html --dry-run

Prints exactly one result line: "RESULT: SENT OK" or "RESULT: FAILED <type> <msg>".
"""

import argparse
import datetime
import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formatdate


def html_to_text(html):
    """Crude HTML -> text fallback for clients that refuse to render HTML.

    Not a parser and not trying to be: it only needs to leave something legible
    behind in the rare client that shows text/plain instead.
    """
    text = re.sub(r"(?is)<(script|style|head).*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(tr|div|p|h[1-6]|table)>", "\n", text)
    text = re.sub(r"(?i)</td>", "  ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def main(argv=None):
    p = argparse.ArgumentParser(description="mail an HTML schedule table as the mail body")
    p.add_argument("html", help="path to the HTML table, e.g. my/schedule.html")
    p.add_argument("--subject", default=None, help="mail subject (default includes today's date)")
    p.add_argument("--to", default=None, help="recipient (default: MAIL_TO env, else SMTP_USER)")
    p.add_argument("--dry-run", action="store_true", help="build the message and print a summary, do not send")
    args = p.parse_args(argv)

    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    host = os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    sender = os.environ.get("MAIL_FROM") or user
    recipient = args.to or os.environ.get("MAIL_TO") or user

    if not args.dry_run and (not user or not password):
        print("RESULT: FAILED ConfigError SMTP_USER / SMTP_PASS not set in the environment")
        return 2
    if not recipient:
        print("RESULT: FAILED ConfigError no recipient (set MAIL_TO or pass --to)")
        return 2

    try:
        with open(args.html, encoding="utf-8") as f:
            html = f.read()
    except OSError as e:
        print("RESULT: FAILED %s %s" % (type(e).__name__, e))
        return 2

    subject = args.subject or "My schedule (updated %s)" % datetime.date.today().isoformat()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender or "nobody@example.com"
    msg["To"] = recipient
    msg["Date"] = formatdate(localtime=True)
    # set_content = the text/plain fallback; add_alternative = the HTML that
    # actually gets rendered. HTML body only, deliberately no attachment.
    msg.set_content(html_to_text(html))
    msg.add_alternative(html, subtype="html")

    if args.dry_run:
        print("DRY RUN")
        print("  host    : %s:%d" % (host, port))
        print("  from    : %s" % msg["From"])
        print("  to      : %s" % msg["To"])
        print("  subject : %s" % subject)
        print("  html    : %s (%d bytes)" % (args.html, len(html.encode("utf-8"))))
        print("RESULT: NOT SENT (dry run)")
        return 0

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, password)
            s.send_message(msg)
        print("RESULT: SENT OK")
        return 0
    except Exception as e:  # noqa: BLE001 - one line out, whatever went wrong
        print("RESULT: FAILED %s %s" % (type(e).__name__, repr(e)[:300]))
        return 1


if __name__ == "__main__":
    sys.exit(main())
