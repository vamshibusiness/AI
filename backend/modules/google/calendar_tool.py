import datetime
from pathlib import Path
from googleapiclient.discovery import build
from backend.modules.google.google_auth import get_google_creds
import zoneinfo
from backend.modules.memory.short_term import jarvis_cache


MODULE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_PATH = MODULE_DIR / "config" /"google_credentials.json"
TOKEN_PATH = MODULE_DIR / "config" /"token.json"

def get_today_agenda(target_date=None) -> str:
    """Fetches all primary calendar events for the requested target_date."""
    # 1. Default to today if no date is provided
    if not target_date:
        target_date = datetime.date.today()
    
    try:
        if not CREDENTIALS_PATH.exists():
            return "I can't check your schedule because the Google credentials JSON file is missing."

        creds = get_google_creds(str(CREDENTIALS_PATH), str(TOKEN_PATH))
        service = build('calendar', 'v3', credentials=creds)

        # 2. Determine time boundaries
        # If looking at today, start from NOW. If a future date, start at midnight.
        if target_date == datetime.date.today():
            start_boundary = datetime.datetime.now().astimezone()
        else:
            start_boundary = datetime.datetime.combine(target_date, datetime.time.min).astimezone()

        # End boundary is always 11:59:59 PM of the target date
        end_boundary = datetime.datetime.combine(target_date, datetime.time(23, 59, 59)).astimezone()

        time_min = start_boundary.isoformat()
        time_max = end_boundary.isoformat()

        print(f"[Calendar API] Querying events between {time_min} and {time_max}...")
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        
        day_label = "today" if target_date == datetime.date.today() else f"on {target_date.strftime('%B %d')}"
        speech_output = f"Here is what's on your schedule for {day_label}: "
        
        if not events:
            jarvis_cache.last_spoken_events.clear()
            return f"Your schedule looks completely open for {day_label}."

        speech_output = f"Here is what's on your schedule for {day_label}: "
        jarvis_cache.last_spoken_events.clear()
        
        for event in events:
            summary = event.get('summary', 'An untitled appointment')
            start_time_raw = event['start'].get('dateTime', event['start'].get('date'))
            
            if 'T' in start_time_raw:
                time_obj = datetime.datetime.fromisoformat(start_time_raw.replace('Z', '+00:00'))
                formatted_time = format_time_for_speech(time_obj)
                speech_output += f"At {formatted_time}, you have {summary}. "
                jarvis_cache.last_spoken_events.append(summary)
            else:
                speech_output += f"An all day event: {summary}. "

        return speech_output

    except Exception as e:
        print(f"[Calendar Error] Telemetry failure: {e}")
        return "I ran into a connection error trying to pull your Google Calendar data."
    
def format_time_for_speech(dt: datetime.datetime) -> str:
    hour = dt.strftime("%I").lstrip("0")
    minute = dt.strftime("%M")
    am_pm = dt.strftime("%p")

    if minute == "00":
        return f"{hour} {am_pm}"

    return f"{hour}:{minute} {am_pm}"    
    
def get_calendar_summary(target_date=None) -> dict:
    """Returns structured calendar data for the UI badge."""
    if not target_date:
        target_date = datetime.date.today()

    try:
        if not CREDENTIALS_PATH.exists():
            return {
                "event_count": 0,
                "events": [],
                "error": "Google credentials JSON file is missing.",
            }

        creds = get_google_creds(str(CREDENTIALS_PATH), str(TOKEN_PATH))
        service = build("calendar", "v3", credentials=creds)

        # For today, only count events from now through end of day.
        # For future dates, count the whole day.
        if target_date == datetime.date.today():
            start_boundary = datetime.datetime.now().astimezone()
        else:
            start_boundary = datetime.datetime.combine(
                target_date,
                datetime.time.min
            ).astimezone()

        end_boundary = datetime.datetime.combine(
            target_date,
            datetime.time(23, 59, 59)
        ).astimezone()

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_boundary.isoformat(),
            timeMax=end_boundary.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        parsed_events = []

        for event in events:
            title = event.get("summary", "Untitled event")
            start_raw = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")

            parsed_events.append({
                "title": title,
                "start": start_raw,
            })

        return {
            "event_count": len(parsed_events),
            "events": parsed_events,
            "error": None,
        }

    except Exception as e:
        print(f"[Calendar Error] Summary failure: {e}")
        return {
            "event_count": 0,
            "events": [],
            "error": str(e),
        }    
    

def add_calendar_event(summary: str, start_dt: datetime.datetime, duration_minutes: int = 30) -> str:
    """Inserts a new event into the primary calendar."""
    try:
        creds = get_google_creds(str(CREDENTIALS_PATH), str(TOKEN_PATH))
        service = build('calendar', 'v3', credentials=creds)

        if start_dt.tzinfo is None:
            start_dt = start_dt.astimezone() # This adds your local system timezone offset
    
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
        
        # Google reads local offsets directly out of the ISO string format
        event_body = {
            'summary': summary,
            'start': {'dateTime': start_dt.isoformat()},
            'end': {'dateTime': end_dt.isoformat()},
        }

        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        formatted_time = format_time_for_speech(start_dt)
        day_str = start_dt.strftime("%A, %B %d")
        return f"Successfully scheduled '{summary}' for {day_str} at {formatted_time}."
    except Exception as e:
        print(f"[Calendar Error] Create failure: {e}")
        return "I encountered an error trying to schedule that appointment."


def delete_calendar_event(search_query: str) -> str:
    """Finds an event by matching keywords and removes it from the next 7 days."""
    try:
        creds = get_google_creds(str(CREDENTIALS_PATH), str(TOKEN_PATH))
        service = build('calendar', 'v3', credentials=creds)

        # 1. Look ahead for the next 7 days instead of just today
        now = datetime.datetime.now().astimezone()
        one_week_later = now + datetime.timedelta(days=7)
        
        # 2. Query Google for all events in that window
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now.isoformat(),
            timeMax=one_week_later.isoformat(),
            singleEvents=True, 
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        # 3. Use token-based matching to find the event
        # Filter out short "stop words" to focus on the core request (like 'Bear')
        user_tokens = [t.lower() for t in search_query.split() if len(t) > 2]
        
        for event in events:
            summary = event.get('summary', '').lower()
            # If any significant user keyword is found in the event title, match it
            if any(token in summary for token in user_tokens):
                event_id = event['id']
                event_title = event['summary']
                
                # Delete the event
                service.events().delete(calendarId='primary', eventId=event_id).execute()
                return f"I have successfully removed '{event_title}' from your calendar."

        return f"I couldn't find any upcoming events matching '{search_query}'."
        
    except Exception as e:
        print(f"[Calendar Error] Delete failure: {e}")
        return "I ran into an issue attempting to clear that event."


def modify_calendar_event(search_query: str, new_title: str = None, new_start_dt: datetime.datetime = None) -> str:
    """Finds an existing event and patches its title or timing parameters."""
    try:
        creds = get_google_creds(str(CREDENTIALS_PATH), str(TOKEN_PATH))
        service = build('calendar', 'v3', credentials=creds)

        now_local = datetime.datetime.now().astimezone()
        time_min = now_local.replace(hour=0, minute=0, second=0).isoformat()

        events_result = service.events().list(
            calendarId='primary', timeMin=time_min, maxResults=10, singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        for event in events:
            if search_query.lower() in event.get('summary', '').lower():
                # Prep the patch changes
                body_patch = {}
                if new_title:
                    body_patch['summary'] = new_title
                if new_start_dt:
                    body_patch['start'] = {'dateTime': new_start_dt.isoformat()}
                    # Assume duration stays 30 mins unless specified
                    end_dt = new_start_dt + datetime.timedelta(minutes=30)
                    body_patch['end'] = {'dateTime': end_dt.isoformat()}

                updated_event = service.events().patch(
                    calendarId='primary', eventId=event['id'], body=body_patch
                ).execute()
                return f"Updated '{event['summary']}' successfully."

        return f"I couldn't find an event matching '{search_query}' to update."
    except Exception as e:
        print(f"[Calendar Error] Patch failure: {e}")
        return "I was unable to modify that appointment."    