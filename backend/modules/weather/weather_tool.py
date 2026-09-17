import datetime
import requests


STATE_ABBREVIATIONS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy with rime", 51: "light drizzle", 53: "moderate drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "moderate rain", 65: "heavy rain",
    71: "light snow", 73: "moderate snow", 75: "heavy snow", 80: "light rain showers",
    81: "moderate rain showers", 82: "heavy rain showers", 95: "thunderstorms",
}


def normalize_state(state: str):
    state = state.strip()
    if len(state) == 2:
        return STATE_ABBREVIATIONS.get(state.upper())
    return state.title()


def get_coordinates(city: str, state: str):
    state_name = normalize_state(state)
    if not state_name:
        return None

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city,
        "count": 10,
        "countryCode": "US",
        "language": "en",
        "format": "json",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])

    for result in results:
        result_state = result.get("admin1", "")
        if result_state.lower() == state_name.lower():
            return {
                "name": result["name"],
                "state": result_state,
                "latitude": result["latitude"],
                "longitude": result["longitude"],
            }
    return None


def get_weather(city: str, state: str, time_range: str = "current"):
    location = get_coordinates(city, state)
    if not location:
        return f"I couldn't find weather for {city}, {state}."

    url = "https://api.open-meteo.com/v1/forecast"
    
    # Shared base query configuration
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
    }

    # CASE 1: Real-time Snapshot
    if time_range in ["current", "today"]:
        params["current"] = "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        current = response.json()["current"]
        temperature = round(current["temperature_2m"])
        humidity = current["relative_humidity_2m"]
        wind_speed = round(current["wind_speed_10m"])
        condition = WEATHER_CODES.get(current["weather_code"], "unknown conditions")

        return (
            f"The weather in {location['name']}, {location['state']} is currently "
            f"{temperature} degrees with {condition}. "
            f"Humidity is {humidity}% and wind speed is around "
            f"{wind_speed} miles per hour."
        )

    # CASE 2: Multi-day Forecast Summary
    elif time_range == "week":
        params["daily"] = "weather_code,temperature_2m_max,temperature_2m_min"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        daily = response.json()["daily"]
        forecast_lines = []

        # Parse out the upcoming days (limiting to 5 for natural voice readout length)
        for i in range(min(5, len(daily["time"]))):
            date_str = daily["time"][i]
            day_name = datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
            max_temp = round(daily["temperature_2m_max"][i])
            min_temp = round(daily["temperature_2m_min"][i])
            condition = WEATHER_CODES.get(daily["weather_code"][i], "unknown conditions")
            
            forecast_lines.append(f"{day_name}: a high of {max_temp} and low of {min_temp} with {condition}.")

        summary = f"Here is the forecast for the upcoming week in {location['name']}, {location['state']}: "
        return summary + " ".join(forecast_lines)

    # CASE 3: Targeted Calendar Date or Tomorrow
    else:
        target_date = time_range
        if time_range == "tomorrow":
            target_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

        params["start_date"] = target_date
        params["end_date"] = target_date
        params["daily"] = "weather_code,temperature_2m_max,temperature_2m_min"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "daily" not in data or not data["daily"]["time"]:
                return f"I couldn't look up a forecast for that timeframe."

            daily = data["daily"]
            max_temp = round(daily["temperature_2m_max"][0])
            min_temp = round(daily["temperature_2m_min"][0])
            condition = WEATHER_CODES.get(daily["weather_code"][0], "unknown conditions")

            friendly_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").strftime("%B %d")
            day_prefix = "Tomorrow" if time_range == "tomorrow" else f"On {friendly_date}"

            return (
                f"{day_prefix} in {location['name']}, {location['state']}, expect "
                f"a high of {max_temp} degrees and a low of {min_temp} degrees with {condition}."
            )
        except Exception:
            return "I couldn't look up the weather for that specific date. Make sure it is within a 14-day window."