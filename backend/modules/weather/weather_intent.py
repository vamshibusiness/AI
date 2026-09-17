import datetime
import re
from backend.modules.weather.weather_tool import get_weather
from backend.config.jarvis_config import USER_CITY, USER_STATE

# Dictionary maps both full names and abbreviations to uniform two-letter codes
STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "al": "AL", "ak": "AK", "az": "AZ", "ar": "AR", "ca": "CA", "co": "CO", "ct": "CT", "de": "DE",
    "fl": "FL", "ga": "GA", "hi": "HI", "id": "ID", "il": "IL", "in": "IN", "ia": "IA", "ks": "KS",
    "ky": "KY", "la": "LA", "me": "ME", "md": "MD", "ma": "MA", "mi": "MI", "mn": "MN", "ms": "MS",
    "mo": "MO", "mt": "MT", "ne": "NE", "nv": "NV", "nh": "NH", "nj": "NJ", "nm": "NM", "ny": "NY",
    "nc": "NC", "nd": "ND", "oh": "OH", "ok": "OK", "or": "OR", "pa": "PA", "ri": "RI", "sc": "SC",
    "sd": "SD", "tn": "TN", "tx": "TX", "ut": "UT", "vt": "VT", "va": "VA", "wa": "WA", "wv": "WV",
    "wi": "WI", "wy": "WY"
}

# ==========================================
# CONTEXT PERSISTENCE LAYER (SHORT-TERM MEMORY)
# ==========================================
LAST_CITY = USER_CITY
LAST_STATE = USER_STATE


def is_weather_request(command: str) -> bool:
    command = command.lower()
    return "weather" in command or "wheather" in command


def extract_city_state(command: str):
    """
    Strips out conversational punctuation and cleanly isolates multi-word 
    cities and states even if trailing words exist.
    """
    clean_command = command.lower().replace(",", " ").replace("?", "").replace(".", "").strip()
    
    if " in " not in clean_command:
        return None, None
        
    parts = clean_command.split(" in ")
    location_part = f" {parts[-1].strip()} " 
    
    found_state_key = None
    best_index = -1
    
    for state_key in STATES.keys():
        padded_key = f" {state_key} "
        idx = location_part.rfind(padded_key)
        if idx > best_index:
            best_index = idx
            found_state_key = state_key
            
    if found_state_key:
        city_part = location_part[:best_index].strip()
        if city_part:
            return city_part.title(), STATES[found_state_key]
            
    return None, None


def extract_time_range(command: str):
    command = command.lower()

    # 1. Match standard YYYY-MM-DD format
    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", command)
    if iso_match:
        return iso_match.group(0)

    # 2. Match MM/DD format
    mmdd_match = re.search(r"\b(\d{1,2})/(\d{1,2})\b", command)
    if mmdd_match:
        month = int(mmdd_match.group(1))
        day = int(mmdd_match.group(2))
        year = datetime.datetime.now().year
        return f"{year}-{month:02d}-{day:02d}"

    # 3. Match named textual dates
    months = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
    ]
    months_pat = "|".join(months)
    text_date_match = re.search(rf"\b({months_pat})\s+(\d{1,2})(?:st|nd|rd|th)?\b", command)
    if text_date_match:
        month_str = text_date_match.group(1)
        day = int(text_date_match.group(2))
        
        month_map = {
            "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
            "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
            "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
            "nov": 11, "november": 11, "dec": 12, "december": 12
        }
        month = month_map[month_str[:3]]
        year = datetime.datetime.now().year
        return f"{year}-{month:02d}-{day:02d}"

    # 4. Fallback to general relative timeframes
    if "week" in command or "7 day" in command or "seven day" in command:
        return "week"
    if "tomorrow" in command:
        return "tomorrow"
    if "today" in command:
        return "today"

    return "current"


def handle_weather_command(command: str):
    global LAST_CITY, LAST_STATE
    
    city, state = extract_city_state(command)
    time_range = extract_time_range(command)

    # Context Check: If no location was extracted from this current command sentence...
    if not city or not state:
        # Look into short-term cache memory to see if a location was provided in a previous turn
        if LAST_CITY and LAST_STATE:
            city = LAST_CITY
            state = LAST_STATE
            print(f"Context retained. Defaulting back to last known location: {city}, {state}")
        else:
            return "I heard a weather request, but I need a city and state."
    else:
        # Cache the newly confirmed location details for upcoming follow-up phrases
        LAST_CITY = city
        LAST_STATE = state

    return get_weather(city, state, time_range)


class WeatherHandler:
    def is_related(self, command: str) -> bool:
        """Boolean check used by the intent router."""
        return is_weather_request(command)
    
    def handle(self, command: str, history: list = None) -> str:
        """Execution entry point used by the intent router."""
        return handle_weather_command(command)