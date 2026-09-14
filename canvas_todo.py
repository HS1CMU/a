#!/usr/bin/env python3
"""List Canvas assignments that are past due (unsubmitted) or due soon.

Usage:
    export CANVAS_TOKEN='<your Canvas access token>'
    python3 canvas_todo.py            # last 7 days overdue + next 7 days upcoming
    python3 canvas_todo.py 14 14      # customize: days_back days_ahead

Never hardcode the token in this file or commit it to git.
"""
import os
import sys
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("CANVAS_BASE", "https://canvas.cmu.edu")
TOKEN = os.environ.get("CANVAS_TOKEN")
if not TOKEN:
    sys.exit("Set CANVAS_TOKEN first (Canvas -> Account -> Settings -> New Access Token).")

DAYS_BACK = int(sys.argv[1]) if len(sys.argv) > 1 else 7
DAYS_AHEAD = int(sys.argv[2]) if len(sys.argv) > 2 else 7


def get(path, **params):
    """GET a paginated Canvas endpoint and return all items."""
    url = f"{BASE}/api/v1/{path}?{urllib.parse.urlencode(params, doseq=True)}"
    items = []
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
        with urllib.request.urlopen(req) as resp:
            items.extend(json.load(resp))
            url = None
            for part in resp.headers.get("Link", "").split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip(" <>")
    return items


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


now = datetime.now(timezone.utc)
lo, hi = now - timedelta(days=DAYS_BACK), now + timedelta(days=DAYS_AHEAD)

overdue, upcoming = [], []
for course in get("courses", enrollment_state="active", per_page=100):
    name = course.get("name") or course.get("course_code") or str(course["id"])
    assignments = get(
        f"courses/{course['id']}/assignments",
        include=["submission"], per_page=100, order_by="due_at",
    )
    for a in assignments:
        due = parse(a.get("due_at"))
        if not due or not a.get("published", True):
            continue
        sub = a.get("submission") or {}
        done = sub.get("workflow_state") not in (None, "unsubmitted") or sub.get("submitted_at")
        row = (due, name, a["name"], a.get("html_url"))
        if lo <= due < now and not done:
            overdue.append(row)
        elif now <= due <= hi and not done:
            upcoming.append(row)


def show(title, rows):
    print(f"\n=== {title} ({len(rows)}) ===")
    for due, course, title_, url in sorted(rows):
        print(f"{due.astimezone().strftime('%m-%d %H:%M')}  [{course}]  {title_}\n    {url}")


show(f"Past {DAYS_BACK} days, NOT submitted", overdue)
show(f"Next {DAYS_AHEAD} days, not yet submitted", upcoming)
