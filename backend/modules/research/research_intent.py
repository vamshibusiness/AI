import re

from backend.modules.research.research_tool import (
    start_research,
    get_research_status,
    cancel_research,
    get_completed_research_report,
    resume_unfinished_research_tasks,
    get_latest_completed_research,
    ask_question_about_research,

)


def is_research_request(command: str) -> bool:
    command = command.lower()

    keywords = [
        "start research",
        "begin research",
        "do research",
        "run research",
        "research on",
        "research about",
        "research for",
        "research why",
        "research status",
        "status of research",
        "status on research",
        "cancel research",
        "stop research",
        "research report",
        "what did you find",
        "finish any task not complete",
        "finish unfinished research",
        "resume research",
        "continue research",
        "active research",
        "current research",
        "what are you researching",
        "what research are you doing",
    ]

    return any(keyword in command for keyword in keywords)


def is_research_status_request(command: str) -> bool:
    command = command.lower()

    keywords = [
        "research status",
        "status of research",
        "status on research",
        "how is the research going",
        "are you still researching",
        "active research",
        "current research",
        "what are you researching",
        "what research are you doing",
    ]

    return any(keyword in command for keyword in keywords)

def is_show_request(command: str) -> bool:
    command = command.lower()

    keywords = [
         "show research",
        "show research status",
        "show all research",
    ]

    return any(keyword in command for keyword in keywords)

def is_cancel_research_request(command: str) -> bool:
    command = command.lower()

    keywords = [
        "cancel research",
        "stop research",
        "cancel the research",
        "stop the research",
    ]

    return any(keyword in command for keyword in keywords)


def is_resume_research_request(command: str) -> bool:
    command = command.lower()

    keywords = [
        "finish any task not complete",
        "finish unfinished research",
        "resume research",
        "continue research",
        "continue unfinished research",
    ]

    return any(keyword in command for keyword in keywords)


def is_completed_report_request(command: str) -> bool:
    command = command.lower()

    keywords = [
        "research report",
        "completed research",
        "what did you find",
        "show research",
        "read research",
    ]

    return any(keyword in command for keyword in keywords)


def clean_topic(topic: str) -> str:
    topic = topic.strip()
    topic = re.sub(r"\s+please$", "", topic, flags=re.IGNORECASE)
    topic = topic.strip(" .?!")
    return topic


def extract_research_topic(command: str) -> str:
    command = command.strip()

    patterns = [
        r"(?:start|begin|do|run)\s+(?:a\s+)?research(?:\s+(?:task|report))?\s+(?:on|about|for)\s+(.+)",
        r"research\s+(?:on|about|for)\s+(.+)",
        r"(?:what did you find|show research|read research|research report)\s+(?:on|about|for)?\s*(.+)",
        r"research\s+(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)

        if match:
            topic = clean_topic(match.group(1))

            blocked_topics = [
                "status",
                "the status",
                "cancel",
                "stop",
                "report",
                "the report",
            ]

            if topic.lower() not in blocked_topics:
                return topic

    return ""


def handle_research_command(command: str) -> str:
    
    if is_cancel_research_request(command):
        return cancel_research()
    
    if is_research_status_request(command):
        return get_research_status()

    if is_resume_research_request(command):
        return resume_unfinished_research_tasks()

    if is_completed_report_request(command):
        topic = extract_research_topic(command)

        if not topic:
            return "Please tell me which completed research topic you want me to read."

        return get_completed_research_report(topic)

    topic = extract_research_topic(command)

    if not topic:
        return "Please say start research on, followed by the topic you want me to research."

    return start_research(topic)

def handle_interactive_research_questions(
    listen_func,
    speak_func,
    initial_command: str = "",
    topic: str = None,
    report: str = None,
    announce: bool = True,
) -> str:
    if not topic or not report:
        latest = get_latest_completed_research()

        if not latest:
            speak_func("I do not have a completed research report ready yet.")
            return "System Note: Research Q&A could not start because no completed research was found."

        topic = latest.get("topic", "the completed research")
        report = latest.get("report", "")

    if announce:
        speak_func(f"Research is complete on {topic}.")

    while True:
        question = listen_func()

        if not question or not question.strip():
            speak_func("Just let me know anytime you would like to discuss the research")
            return "System Note: Research Q&A ended because no question was heard."

        question_lower = question.lower()

        exit_phrases = [
            "done with research",
            "exit research",
            "stop research questions",
            "that's all",
            "that is all",
            "go back",
            "cancel",
            "nevermind",
            "never mind",
            "close",
            "thank you",

        ]

        if any(phrase in question_lower for phrase in exit_phrases):
            speak_func("Okay. I will keep the research saved.")
            return "System Note: User exited research Q&A mode."

        answer = ask_question_about_research(
            question=question,
            topic=topic,
            report=report,
        )

        speak_func(answer)
        speak_func("You can ask another research question, or say done with research.")

class ResearchHandler:
    def is_related(self, command: str) -> bool:
        """Boolean check used by the intent router."""
        return is_research_request(command)

    def handle(self, command: str, history: list = None) -> str:
        """Execution entry point used by the intent router."""
        return handle_research_command(command)
    
    def execute_interactive(
        self,
        listen_func,
        speak_func,
        initial_command: str = "",
        topic: str = None,
        report: str = None,
        announce: bool = True,
    ) -> str:
        return handle_interactive_research_questions(
            listen_func=listen_func,
            speak_func=speak_func,
            initial_command=initial_command,
            topic=topic,
            report=report,
            announce=announce,
        )