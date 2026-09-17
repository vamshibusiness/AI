import datetime
from concurrent.futures import ThreadPoolExecutor

from backend.modules.google.gmail_intent import read_saved_emails
from backend.modules.google.calendar_tool import get_today_agenda
from backend.modules.weather.weather_tool import get_weather
from backend.modules.llm.memory_manager import load_user_profile
from backend.modules.llm.local_llm import ask_local_llm
from backend.config.jarvis_config import USER_CITY, USER_STATE, USER_TITLE


def is_morning_briefing_request(command: str) -> bool:
    command = command.lower()

    keywords = [
        "morning briefing",
        "daily briefing",
        "start my day",
        "brief me",
        "what's my day look like",
        "what does my day look like",
        "give me my briefing",
    ]

    return any(keyword in command for keyword in keywords)


def get_memory_suggestion() -> str:
    user_facts = load_user_profile()

    if not user_facts:
        return ""

    facts_text = "\n".join([f"- {fact}" for fact in user_facts[-15:]])

    messages = [
        {
            "role": "system",
            "content": (
                "You are Jarvis preparing a very short morning briefing suggestion. "
                "Use only the user's saved memory facts. "
                "Give one useful suggestion for today. "
                "Keep it under two sentences. "
                "If there is nothing useful, return an empty string."
            ),
        },
        {
            "role": "user",
            "content": f"User memory facts:\n{facts_text}",
        },
    ]

    try:
        response = ask_local_llm(messages)

        if isinstance(response, str):
            return response.strip()

        return "".join(response).strip()

    except Exception as e:
        print(f"[Morning Briefing] Memory suggestion failed: {e}")
        return ""


def handle_morning_briefing(command: str, history: list = None) -> str:
    today = datetime.date.today()

    sections = []

    sections.append(f"Good morning, {USER_TITLE}. Here is your briefing.")

    # 1. Emails
    try:
        email_summary = read_saved_emails()
        sections.append(email_summary)
    except Exception as e:
        print(f"[Morning Briefing] Email check failed: {e}")
        sections.append("I could not check your emails right now.")

    # 2. Calendar
    try:
        calendar_summary = get_today_agenda(today)
        sections.append(f"Your calendar: {calendar_summary}")
    except Exception as e:
        print(f"[Morning Briefing] Calendar check failed: {e}")
        sections.append("I could not check your calendar right now.")

    # 3. Weather
    try:
        weather_summary = get_weather(USER_CITY, USER_STATE, "today")
        sections.append(f"Weather: {weather_summary}")
    except Exception as e:
        print(f"[Morning Briefing] Weather check failed: {e}")
        sections.append("I could not check the weather right now.")

    # 4. Memory suggestion
    suggestion = get_memory_suggestion()

    if suggestion:
        sections.append(f"My suggestion: {suggestion}")

    return " ".join(sections)

def handle_morning_briefing_streamed(speak_func, command: str = "", history: list = None) -> str:
    today = datetime.date.today()

    speak_func(f"Good morning, {USER_TITLE}. Here is your briefing.")

    # Calendar and weather are mostly API/network calls, so they can run while emails are being read.
    with ThreadPoolExecutor(max_workers=3) as executor:
        calendar_future = executor.submit(get_today_agenda, today)
        weather_future = executor.submit(get_weather, USER_CITY, USER_STATE, "today")
        suggestions_future = executor.submit(get_memory_suggestion)

        # 1. Speak emails immediately while calendar/weather load in the background.
        try:
            email_summary = read_saved_emails()
            speak_func(email_summary)
        except Exception as e:
            print(f"[Morning Briefing] Email check failed: {e}")
            speak_func("I could not check your emails right now.")

        # 2. Calendar should hopefully be ready by now.
        try:
            calendar_summary = calendar_future.result(timeout=30)
            speak_func(calendar_summary)
        except Exception as e:
            print(f"[Morning Briefing] Calendar check failed: {e}")
            speak_func("I could not check your calendar right now.")

        # 3. Weather should hopefully be ready by now.
        try:
            weather_summary = weather_future.result(timeout=30)
            speak_func(f"Weather: {weather_summary}")
        except Exception as e:
            print(f"[Morning Briefing] Weather check failed: {e}")
            speak_func("I could not check the weather right now.")

        # 4. Do memory suggestion last because it uses the local LLM/GPU.
        try:
            suggestion = suggestions_future.result(timeout=30)

            if suggestion:
                speak_func(f"My suggestion: {suggestion}")

        except Exception as e:
            print(f"[Morning Briefing] Memory suggestion failed: {e}")

    return "System Note: Morning briefing was delivered progressively."


class MorningBriefingHandler:
    def is_related(self, command: str) -> bool:
        return is_morning_briefing_request(command)

    def handle(self, command: str, history: list = None) -> str:
        return handle_morning_briefing(command, history)
    
    def handle_streamed(self, speak_func, command: str, history: list = None) -> str:
        return handle_morning_briefing_streamed(speak_func, command, history)