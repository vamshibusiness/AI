import threading
from typing import Optional
from pathlib import Path

from backend.modules.agents.research_agent import ResearchAgent
from backend.modules.llm.local_llm import ask_local_llm


_research_agent: Optional[ResearchAgent] = None
_agent_lock = threading.RLock()


def set_research_agent(agent: ResearchAgent) -> None:
    """
    Allows main.py to create the ResearchAgent once during startup
    and share that same instance with the rest of Jarvis.
    """
    global _research_agent

    with _agent_lock:
        _research_agent = agent


def get_research_agent() -> ResearchAgent:
    """
    Returns the shared ResearchAgent instance.

    If main.py already created the agent, this returns that instance.
    If not, this safely creates one as a fallback.
    """
    global _research_agent

    with _agent_lock:
        if _research_agent is None:
            _research_agent = ResearchAgent()

        return _research_agent


def start_research(topic: str) -> str:
    agent = get_research_agent()
    return agent.start_research(topic)


def get_research_status() -> str:
    agent = get_research_agent()
    return agent.get_status()


def cancel_research() -> str:
    agent = get_research_agent()
    return agent.cancel_research()


def get_completed_research_report(topic: str) -> str:
    agent = get_research_agent()
    report = agent.get_completed_report(topic)

    if not report:
        return f"I could not find a completed research report for {topic}."

    return report


def resume_unfinished_research_tasks() -> str:
    """
    Ensures the shared research agent is loaded.

    If active_research.json contains unfinished work, ResearchAgent resumes it
    automatically during initialization.
    """
    agent = get_research_agent()
    return agent.get_status()

def get_latest_completed_research():
    agent = get_research_agent()
    history = agent.list_completed_research()

    if not history:
        return None

    return history[0]

def list_completed_research():
    agent = get_research_agent()
    return agent.list_completed_research()

def get_completed_research_summary() -> str:
    agent = get_research_agent()
    history = agent.list_completed_research()

    if not history:
        return "I do not have any completed research reports saved yet."

    summaries = []

    for index, item in enumerate(history, start=1):
        topic = item.get("topic", "Untitled research")
        created_at = item.get("created_at") or "unknown date"
        summaries.append(f"{index}. {topic}, created at {created_at}")

    return "Here are the completed research reports I have saved: " + " ".join(summaries)


def ask_question_about_research(question: str, topic: str, report: str) -> str:
    question = (question or "").strip()
    topic = (topic or "the completed research").strip()
    report = (report or "").strip()

    # Self-healing fallback:
    # If the event did not pass the report correctly, reload it from completed research.
    if not report:
        agent = get_research_agent()

        if topic and topic != "the completed research":
            saved_report = agent.get_completed_report(topic)

            if saved_report:
                report = saved_report.strip()

        if not report:
            latest = get_latest_completed_research()

            if latest:
                topic = latest.get("topic", topic)
                report = (latest.get("report") or "").strip()

    print(f"[Research Q&A] Topic: {topic}")
    print(f"[Research Q&A] Question: {question}")
    print(f"[Research Q&A] Report chars: {len(report)}")

    if not report:
        return (
            "I found the completed research session, but the saved report text is empty. "
            "Check completed_research.json to confirm the report was saved correctly."
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You are Jarvis answering questions about a completed research report. "
                "The completed research report is already provided in the user message. "
                "Use only that report as your source of truth. "
                "Do not search for a report. Do not say you cannot find the report if report text is provided. "
                "If the user asks for a summary, recap the completed report in a concise, voice-friendly way. "
                "If the user asks what you found, summarize the most important findings. "
                "If the report does not contain enough detail to answer a specific question, say that the completed research does not fully answer that specific question. "
                "Keep the answer concise and natural for spoken audio."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Research topic: {topic}\n\n"
                f"Completed research report text starts below:\n"
                f"---BEGIN REPORT---\n"
                f"{report}\n"
                f"---END REPORT---\n\n"
                f"User question about this report: {question}"
            ),
        },
    ]

    response = ask_local_llm(messages)

    if isinstance(response, str):
        return response.strip()

    return "".join(response).strip()