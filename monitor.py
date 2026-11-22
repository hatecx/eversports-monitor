"""Daily public Eversports calendar check. Never attempts to book a course."""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright


CALENDAR = "https://www.eversports.de/scl/studio-balance-by-elif"
STATE = Path(__file__).parent / "data" / "notified.json"
ZONE = ZoneInfo("Europe/Berlin")


def qualifies(course, start, end):
    try:
        day = datetime.strptime(course["date"].rsplit(", ", 1)[-1], "%d/%m/%Y").date()
        hour, minute = map(int, course["time"].split(" ")[0].split(":"))
        spots = re.fullmatch(r"(\d+)\s*/\s*\d+ spots available", course["availability"], re.I)
    except (ValueError, KeyError, AttributeError):
        return False
    if not (start <= day <= end and spots and int(spots.group(1)) > 0):
        return False
    name = course["name"].strip().lower()
    special = "reformer" in name and any(
        word in name for word in ("special", "event", "candlelight", "movie", "music", "matcha", "gingerbread")
    )
    standard = name in ("reformer pilates - beginner flow", "reformer pilates - jumpboard")
    if not (special or standard):
        return False
    wd = day.weekday()  # Monday=0
    mins = 60 * hour + minute
    return (wd in (1, 2, 3, 4) and mins >= 1080) or (wd == 6 and mins >= 960) or (wd == 5 and special)


def read_week(page):
    return page.evaluate("""() => [...new Map([...document.querySelectorAll('li.calendar__slot[data-uuid]')]
        .map(e => [e.getAttribute('data-uuid'), {
          uuid: e.getAttribute('data-uuid'), date: e.querySelector('.sr-only')?.textContent?.trim(),
          time: e.querySelector('.session-time')?.textContent?.trim(),
          name: e.querySelector('.session-name')?.textContent?.trim(),
          availability: e.querySelector('.ellipsis')?.textContent?.trim()
        }])).values()]""")


def collect(browser, start, end):
    page = browser.new_page(locale="en-US")
    page.goto(CALENDAR, wait_until="domcontentloaded", timeout=45000)
    # Do not rely on a localized page heading. Check actual calendar slots.
    try:
        page.locator("li.calendar__slot[data-uuid]").first.wait_for(timeout=20000)
    except Exception as exc:
        title = page.title()
        snippet = page.locator("body").inner_text(timeout=5000)[:900].replace("\\n", " ")
        print(f"CALENDAR DIAGNOSTIC: url={page.url!r}; title={title!r}; body={snippet!r}", file=sys.stderr)
        raise RuntimeError("No calendar sessions loaded; inspect diagnostic output above") from exc
    weeks = []
    current = datetime.now(ZONE).date()
    week_start = current - timedelta(days=current.weekday())
    limit = 8
    for index in range(limit):
        # Wait until the displayed calendar contains the expected week's dated sessions.
        expected = week_start + timedelta(days=7 * index)
        expected_end = expected + timedelta(days=6)
        page.wait_for_function("""([start, end]) => {
          const slots = [...document.querySelectorAll('li.calendar__slot[data-uuid]')];
          const dates = slots.map(e => e.querySelector('.sr-only')?.textContent || '')
            .map(s => s.match(/(\\d{2})\\/(\\d{2})\\/(\\d{4})/))
            .filter(Boolean).map(m => m[3] + '-' + m[2] + '-' + m[1]);
          return dates.length > 0 && dates.every(d => d >= start && d <= end);
        }""", arg=[expected.isoformat(), expected_end.isoformat()], timeout=20000)
        weeks.extend(read_week(page))
        if expected_end >= end:
            break
        page.get_by_role("button", name="Go to Next Week").click()
    else:
        raise RuntimeError("Calendar did not cover the full 21-day window")
    return page, list({c["uuid"]: c for c in weeks}.values())


def verify(browser, course):
    """Verify positive remaining capacity and booking action on the actual activity detail page."""
    url = f'https://www.eversports.de/activity/{course["uuid"]}'
    page = browser.new_page(locale="en-US")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.get_by_role("heading", name=course["name"].strip(), exact=True).first.wait_for(timeout=20000)
        text = page.locator("body").inner_text()
        capacity = re.search(r"Availability\s+(\d+) remaining", text)
        date_obj = datetime.strptime(course["date"].rsplit(", ", 1)[-1], "%d/%m/%Y")
        readable = date_obj.strftime("%B %-d, %Y")
        time_string = course["time"].split(" ")[0]
        h, m = map(int, time_string.split(":"))
        formatted_time = datetime(2026, 1, 1, h, m).strftime("%I:%M %p")
        if not (capacity and int(capacity.group(1)) > 0 and readable in text and formatted_time in text):
            return None
        if not page.get_by_role("link", name="Book now").count():
            return None
        return int(capacity.group(1)), page.url
    finally:
        page.close()


def push(course, spots, url):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic or not re.fullmatch(r"[a-zA-Z0-9_-]+", topic):
        raise RuntimeError("NTFY_TOPIC missing or invalid")
    body = f'{course["name"].strip()}\n{course["date"]}, {course["time"].split(" ")[0]} Uhr\n{spots} Plätze frei\n{url}'
    req = Request(f"https://ntfy.sh/{topic}", data=body.encode(), headers={
        "Title": "Pilates-Platz frei!", "Click": url, "Tags": "dancer", "Priority": "default"
    }, method="POST")
    with urlopen(req, timeout=20) as res:
        if res.status != 200:
            raise RuntimeError(f"ntfy status {res.status}")


def main():
    dry = os.environ.get("DRY_RUN", "false").lower() == "true"
    today = datetime.now(ZONE).date()
    start, end = today + timedelta(days=1), today + timedelta(days=21)
    sent = json.loads(STATE.read_text(encoding="utf-8"))
    with sync_playwright() as p:
        binary = os.environ.get("CHROMIUM_EXECUTABLE")
        browser = p.chromium.launch(headless=True, executable_path=binary or None)
        try:
            _, all_courses = collect(browser, start, end)
            matches = [c for c in all_courses if qualifies(c, start, end)]
            print(f"Window {start} to {end}; read {len(all_courses)} courses; matched {len(matches)}")
            for course in matches:
                result = verify(browser, course)
                if not result:
                    print("Not confirmed on detail page:", course["name"], course["date"])
                    continue
                spots, url = result
                print(f'CONFIRMED {course["date"]} {course["time"]} {course["name"]} ({spots} free): {url}')
                if course["uuid"] in sent:
                    continue
                if not dry:
                    push(course, spots, url)
                    sent[course["uuid"]] = datetime.now(ZONE).isoformat()
                    STATE.write_text(json.dumps(sent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"MONITOR FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
