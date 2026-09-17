import json
import datetime
import re
import requests
from backend.modules.llm.local_llm import ask_local_llm_stream  # Or your non-streaming call if you have one
from backend.modules.google.calendar_tool import (
    get_today_agenda, add_calendar_event, delete_calendar_event, modify_calendar_event, format_time_for_speech
)
from backend.modules.memory.short_term import jarvis_cache

def is_calendar_request(command: str) -> bool:
    command = command.lower()
    keywords = [
        # --- Core Calendar Terms ---
        "schedule", "calendar", "agenda", "appointment", "meeting", "remind me",
        
        # --- Viewing / Status Checking ---
        "what's on", "am i free", "am i busy", "plans for", "doing today", 
        "doing tomorrow", "look like today", "look like tomorrow", "what do i have",
        
        # --- Adding / Creating ---
        "put down", "book a", "set up", "set", "add a", "add an", "lock in", "create a",
        "event", "calendar event",
        
        # --- Deleting / Canceling ---
        "cancel", "delete", "remove", "clear my", "get rid of", "wipe my",
        
        # --- Modifying / Rescheduling ---
        "reschedule", "postpone", "move my", "change my", "shift my", "update my"
    ]
    return any(keyword in command for keyword in keywords)

def safe_text(value) -> str:
    if value is None:
        return ""

    return str(value).strip()

def parse_calendar_action_with_llm(command: str) -> dict:
    """Uses the local model to extract action schema arguments from raw natural voice inputs."""
    now_local = datetime.datetime.now().astimezone()
    
    
    system_parser_prompt = f"""
    You are a structured language parser subroutine for an executive assistant. Your job is to analyze commands and format them into flawless JSON parameters.
    Current Local Timestamp Context: {now_local.strftime("%Y-%m-%d %H:%M:%S %z")} (Today is {now_local.strftime("%A")})
    If the user mentions a time or date, normalize it to a full ISO 8601 string (YYYY-MM-DDTHH:MM:SS).
    For "tomorrow", use { (now_local + datetime.timedelta(days=1)).strftime("%Y-%m-%d") }.

    Output strictly a single valid JSON block without markdown packaging or explanation.
    
    Allowed Action Schemas:
    1. View Schedule: {{"action": "view", "date": "YYYY-MM-DD or null"}}
    2. Add Event:    {{"action": "add", "title": "Event Name", "time": "YYYY-MM-DDTHH:MM:SS±HH:MM"}}
    3. Delete Event: {{"action": "delete", "target_query": "Name to find, or pronoun like that/it/this if the user refers to the last spoken event. Never use null for delete target_query."}}
    4. Modify Event: {{"action": "modify", "target_query": "Old Name", "new_title": "New Name or null", "new_time": "YYYY-MM-DDTHH:MM:SS±HH:MM or null"}}
    
    Analyze this request: "{command}"
    """

    # Combine into a single message packet
    payload = [{"role": "user", "content": system_parser_prompt}]
    
    raw_json_str = ""
    # Collect the full token generation sequence
    for token in ask_local_llm_stream(payload):
        raw_json_str += token

    try:
        # Clean up any accidental markdown syntax wrappers if the model generated them
        clean_json_str = re.sub(r"```json|```", "", raw_json_str).strip()
        return json.loads(clean_json_str)
    except Exception as e:
        print(f"[Parser Failure] Model output was unparsable: {raw_json_str}. Error: {e}")
        return {"action": "view"} # Fallback safe mechanism
    
def refresh_calendar_badge():
    try:
        requests.get("http://localhost:8000/calendar/refresh-summary", timeout=0.5)
    except requests.RequestException:
        print("[Calendar Intent] Could not refresh calendar badge.")    

def handle_calendar_command(command: str) -> str:
    """Routes the structured parameters to the correct execution script tool."""
    parsed_args = parse_calendar_action_with_llm(command)
    print(f"[Intent Router] Parsed Action Parameters: {parsed_args}")

    action = parsed_args.get("action", "view")

    if action == "add":
        title = parsed_args.get("title", "An appointment")
        time_str = parsed_args.get("time")
        if not time_str:
            return "I couldn't lock down the exact time you wanted that scheduled."
        
        start_dt = datetime.datetime.fromisoformat(time_str)
        
        # 1. Capture the return value from the tool
        # Ensure your add_calendar_event returns a dict like {'status': 'success', 'date': datetime_obj}
        result = add_calendar_event(title, start_dt)
        refresh_calendar_badge()
        
        
        today = datetime.date.today()
        event_date = start_dt.date()
        
        if event_date == today:
            day_str = "today"
        elif event_date == (today + datetime.timedelta(days=1)):
            day_str = "tomorrow"
        else:
            day_str = event_date.strftime("on %A, %B %d")
            
        return f"Successfully scheduled '{title}' for {day_str} at {format_time_for_speech(start_dt)}."

    elif action == "delete":
        target = safe_text(parsed_args.get("target_query")).lower()
        command_lower = command.lower()

        pronouns = ["that", "it", "this", "that one", "my appointment", "the event"]

        # If the parser returned null, but the user said "cancel that",
        # use the last event Jarvis spoke about.
        if not target and any(p in command_lower for p in pronouns):
            if jarvis_cache.last_spoken_events:
                target = jarvis_cache.last_spoken_events[-1].lower()
                print(f"[Memory Inject] Swapping implied target for '{target}'")
            else:
                return "I'm not sure which event you are referring to. What is the title?"

        if not target:
            return "Which appointment would you like me to remove?"

        # Context Substitution Block
        if target in pronouns:
            if jarvis_cache.last_spoken_events:
                resolved_target = jarvis_cache.last_spoken_events[-1]
                print(f"[Memory Inject] Swapping '{target}' for '{resolved_target}'")
                target = resolved_target
            else:
                return "I'm not sure which event you are referring to. What is the title?"

        result = delete_calendar_event(target)
        refresh_calendar_badge()
        return result

    elif action == "modify":
        target = safe_text(parsed_args.get("target_query")).lower()
        new_title = safe_text(parsed_args.get("new_title")) or None
        new_time_str = safe_text(parsed_args.get("new_time")) or None
        
        if not target:
            return "Which appointment are we trying to modify?"
            
        
        pronouns = ["that", "it", "this", "that one", "my appointment", "the event"]
        if target in pronouns and jarvis_cache.last_spoken_events:
            target = jarvis_cache.last_spoken_events[-1]
            print(f"[Memory Inject] Swapping pronoun for '{target}'")
            
        new_dt = datetime.datetime.fromisoformat(new_time_str) if new_time_str else None
        result = modify_calendar_event(target, new_title=new_title, new_start_dt=new_dt)
        refresh_calendar_badge()
        return result
    
    elif action == "view":
        # Get the date from the LLM or default to today
        target_date_str = parsed_args.get("date") 
        
        if target_date_str:
            target_date = datetime.datetime.fromisoformat(target_date_str).date()
        else:
            target_date = datetime.date.today()
            
        return get_today_agenda(target_date)

    else:
        return get_today_agenda()
    

class CalendarHandler:
    def is_related(self, command: str) -> bool:
        """Boolean check used by the intent router."""
        return is_calendar_request(command)
    
    def handle(self, command: str, history: list = None) -> str:
        """Execution entry point used by the intent router."""
        return handle_calendar_command(command)    