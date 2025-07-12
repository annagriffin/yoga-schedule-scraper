from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

# ✅ Load .env variables if running locally
load_dotenv()

# ✅ Config from environment
CALENDAR_ID = os.environ.get("BOULDER_YOGA_CALENDAR_ID")
if not CALENDAR_ID:
    raise RuntimeError("Missing BOULDER_YOGA_CALENDAR_ID environment variable.")

SCOPES = ['https://www.googleapis.com/auth/calendar']

def build_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("calendar", "v3", credentials=creds)

def get_sync_window():
    """Calculate the start and end of the next full week (Sunday–Saturday) in UTC."""
    mountain = pytz.timezone("America/Denver")
    today_mt = datetime.now(mountain)

    # Always get the upcoming Sunday (even if today is Sunday)
    days_until_sunday = (6 - today_mt.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7

    next_sunday_mt = today_mt + timedelta(days=days_until_sunday)

    # Start of next Sunday at 00:00 Mountain Time
    start_mt = datetime.combine(next_sunday_mt.date(), datetime.min.time())
    start_mt = mountain.localize(start_mt)

    end_mt = start_mt + timedelta(days=7)
    return start_mt.astimezone(pytz.utc), end_mt.astimezone(pytz.utc)


def delete_synced_events_for_next_week(service, calendar_id):
    """Delete events containing a sync key from next week's calendar window."""
    start, end = get_sync_window()
    print(f"🧹 Deleting synced events between {start} and {end}...")

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    if not events:
        print("✅ No events found to delete.")
        return

    count = 0
    for event in events:
        desc = event.get("description", "")
        if "🔑 Key:" in desc:
            service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
            print(f"🗑️ Deleted: {event.get('summary', 'Untitled Event')}")
            count += 1

    print(f"✅ {count} synced events deleted.")

def main():
    service = build_service()
    delete_synced_events_for_next_week(service, CALENDAR_ID)

if __name__ == "__main__":
    main()
