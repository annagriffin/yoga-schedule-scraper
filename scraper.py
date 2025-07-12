import hashlib
import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from dateutil import parser
import pytz
import sys


# Config
load_dotenv()  # Load variables from .env if available

BOULDER_YOGA_CALENDAR_ID = os.environ.get("BOULDER_YOGA_CALENDAR_ID")
if not BOULDER_YOGA_CALENDAR_ID:
    raise RuntimeError("Missing BOULDER_YOGA_CALENDAR_ID environment variable.")
SCOPES = ['https://www.googleapis.com/auth/calendar']
mountain = pytz.timezone("America/Denver")

if os.environ.get("GITHUB_ACTIONS") == "true":
    sys.stdout = open("action_output_log.txt", "w")
    sys.stderr = sys.stdout

def extract_key_from_description(description: str) -> str:
    match = re.search(r"🔑 Key:\s*([a-f0-9]{64})", description)
    return match.group(1) if match else None

def extract_teacher_from_description(description: str) -> str:
    match = re.search(r"👤 Teacher\s*:\s*(.*)", description)
    return match.group(1).strip() if match else ""

def datetimes_equal(dt1: str, dt2: str) -> bool:
    return parser.isoparse(dt1) == parser.isoparse(dt2)

def normalize_summary(summary: str) -> str:
    return summary.replace("[UPDATED] ", "").strip()


def get_event_changes(existing_event: dict, new_event: dict) -> list:
    changes = []

    old_summary = normalize_summary(existing_event.get("summary", ""))
    new_summary = normalize_summary(new_event.get("summary", ""))

    if old_summary != new_summary:
        changes.append(f"  📝 summary: {existing_event.get('summary')} -> {new_event.get('summary')}")

    if existing_event.get("location") != new_event.get("location"):
        changes.append(f"  📍 location: {existing_event.get('location')} -> {new_event.get('location')}")

    if not datetimes_equal(existing_event["start"]["dateTime"], new_event["start"]["dateTime"]):
        changes.append(f"  ⏰ start time: {existing_event['start']['dateTime']} -> {new_event['start']['dateTime']}")

    if not datetimes_equal(existing_event["end"]["dateTime"], new_event["end"]["dateTime"]):
        changes.append(f"  ⏳ end time: {existing_event['end']['dateTime']} -> {new_event['end']['dateTime']}")

    old_teacher = extract_teacher_from_description(existing_event.get("description", ""))
    new_teacher = extract_teacher_from_description(new_event.get("description", ""))
    if old_teacher and new_teacher and old_teacher != new_teacher:
        changes.append(f"  👤 teacher: {old_teacher} -> {new_teacher}")

    return changes

def fetch_existing_events(service, calendar_id: str, time_min: datetime, time_max: datetime) -> dict:
    existing_events_by_key = {}
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min.isoformat() + 'Z',
        timeMax=time_max.isoformat() + 'Z',
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    for event in events_result.get("items", []):
        description = event.get("description", "")
        key = extract_key_from_description(description)
        if key:
            existing_events_by_key[key] = event

    return existing_events_by_key


def create_or_update_event(service, calendar_id, event_data, key, existing_events_by_key):
    if key in existing_events_by_key:
        existing_event = existing_events_by_key[key]
        changes = get_event_changes(existing_event, event_data)
        if changes:
            event_data["summary"] = "[UPDATED] " + event_data["summary"]
            event_data["description"] += "\n\n🔄 Changes:\n" + "\n".join(changes)
            updated = service.events().update(
                calendarId=calendar_id,
                eventId=existing_event["id"],
                body=event_data
            ).execute()
            print(f"🔁 Updated: {updated['summary']} → {updated['htmlLink']}")
        else:
            print(f"⏩ Skipped (no change): {event_data['summary']}")
    else:
        created = service.events().insert(calendarId=calendar_id, body=event_data).execute()
        print(f"✅ Created: {created['summary']} → {created['htmlLink']}")

def get_next_week_schedule_url():
    today = datetime.now()
    next_week = today + timedelta(days=7)
    days_to_sunday = (next_week.weekday() + 1) % 7
    next_sunday = next_week - timedelta(days=days_to_sunday)
    url_date = next_sunday.strftime("%Y-%m-%d")
    return f"https://booking.yogapodboulderlongmont.com/co/boulder-30th-street/{url_date}/schedule?"

def fetch_html():
    url = get_next_week_schedule_url()
    print(f"🔗 Fetching: {url}")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def parse_and_sync_events(html, service):
    soup = BeautifulSoup(html, "html.parser")
    sections = soup.select("div.schedule-day")

    time_min = datetime.now()
    time_max = time_min + timedelta(days=10)
    existing = fetch_existing_events(service, BOULDER_YOGA_CALENDAR_ID, time_min, time_max)

    for section in sections:
        date_str = section.select_one(".schedule-day-header-date").get_text(strip=True)
        full_date = datetime.strptime(date_str, "%m/%d").replace(year=datetime.now().year)

        for item in section.select("ul.classes > li.class, ul.classes > li.class-full"):
            title = item.select_one(".class-name")
            title_text = title.get_text(strip=True) if title else "N/A"

            title_text_lower = title_text.lower()

            if "live stream" in title_text_lower or re.search(r"\b2\b", title_text_lower) or "front desk staff" in title_text_lower or "silent" in title_text_lower:
                continue

            time_div = item.select_one(".class-time")
            duration_text = "N/A"
            time_text = "N/A"
            if time_div:
                duration_span = time_div.select_one("span.class-duration")
                if duration_span:
                    duration_text = duration_span.get_text(strip=True).strip("()")
                    duration_span.extract()
                time_text = time_div.get_text(strip=True)

            teacher = item.select_one(".class-teacher")
            teacher_text = teacher.get_text(strip=True) if teacher else "N/A"

            tooltip_html = title.select_one(".tip")["title"] if title and title.select_one(".tip") else ""
            class_description = BeautifulSoup(tooltip_html, "html.parser").get_text("\n").strip() if tooltip_html else ""

            start_str, end_str = time_text.split(" - ")
            start_dt = mountain.localize(datetime.strptime(f"{full_date.date()} {start_str}", "%Y-%m-%d %I:%M%p"))
            end_dt = mountain.localize(datetime.strptime(f"{full_date.date()} {end_str}", "%Y-%m-%d %I:%M%p"))


            raw_key = f"{start_dt.isoformat()}|{title_text}"
            key = hashlib.sha256(raw_key.encode()).hexdigest()

            description = (
                f"🧘 Class   : {title_text}\n"
                f"⏰ Time    : {time_text}\n"
                f"⏳ Duration: {duration_text}\n"
                f"👤 Teacher : {teacher_text}"
            )
            if class_description:
                description += f"\n\n📖 Description:\n{class_description}"
            description += f"\n\n🔑 Key: {key}"

            event = {
                'summary': title_text,
                'location': '1890 30th St, Boulder, CO 80301',
                'description': description,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'America/Denver',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'America/Denver',
                },
            }

            create_or_update_event(service, BOULDER_YOGA_CALENDAR_ID, event, key, existing)

def build_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("calendar", "v3", credentials=creds)

def main():
    html = fetch_html()
    service = build_service()
    parse_and_sync_events(html, service)

    if os.environ.get("GITHUB_ACTIONS") == "true":
        sys.stdout.close()

if __name__ == "__main__":
    main()