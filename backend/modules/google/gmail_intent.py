import json
from pathlib import Path
from html import unescape
import re
import requests
from email.utils import parseaddr
from backend.modules.google.gmail_tool import send_email
from backend.modules.google.gmail_storage import consume_inbox, peek_inbox
from backend.config.jarvis_config import USER_TITLE 

BACKEND_DIR = Path(__file__).resolve().parents[2]
CONTACTS_PATH = BACKEND_DIR / "assets" / "google_contacts.json"

def is_gmail_request(command: str) -> bool:
    command = command.lower()
    keywords = [
         "check email", "check emails", "check my email", "check my emails",
         "latest email", "latest emails", "have email", "have emails",
         "read email", "read emails", "new email", "new emails",
         "read messages", "read my messages", "read mail", "read my mail",
         "send email", "send an email", "email to", "read my emails", "read my email"
    ]
    return any(keyword in command for keyword in keywords)

def get_readable_sender(raw_sender: str) -> str:
    decoded_sender = unescape(raw_sender)
    name, address = parseaddr(decoded_sender)
    return name or address or "an unknown sender"

def read_saved_emails() -> str:
    inbox = consume_inbox()
    refresh_gmail_badge()

    if not inbox:
        return f"You do not have any new emails, {USER_TITLE}."

    email_count = len(inbox)
    email_word = "email" if email_count == 1 else "emails"
    spoken_summaries = []

    for item in inbox:
        sender = get_readable_sender(item.get("sender", ""))
        summary = item.get("snippet", "No summary was available.")

        spoken_summaries.append(
            f"From {sender}. [[pause:1]] {summary}. [[pause:1]]"
        )

    return f"You have {email_count} new important {email_word}. [[pause:1]] " + " ".join(spoken_summaries)

def peek_saved_emails() -> str:
    inbox = peek_inbox()

    if not inbox:
        return f"You do not have any new emails, {USER_TITLE}."

    email_count = len(inbox)
    email_word = "email" if email_count == 1 else "emails"
    spoken_summaries = []

    for item in inbox:
        sender = get_readable_sender(item.get("sender", ""))
        summary = item.get("snippet", "No summary was available.")
        spoken_summaries.append(f"From {sender}: {summary}")

    return f"You have {email_count} new important {email_word}. " + " ".join(spoken_summaries)

def refresh_gmail_badge():
    try:
        requests.get("http://localhost:8000/gmail/refresh-summary", timeout=0.5)
    except requests.RequestException:
        print("[Gmail Intent] Could not refresh Gmail badge.")


def handle_interactive_email(listen_func, speak_func, initial_command: str = "") -> str:
    """
    Takes control of the microphone and speaker to walk through sending an email.
    If a name is provided in the initial command, it skips the first prompt.
    """
    raw_recipient = None

    # 1. Check if the user already said who to email in their wake-word command
    if initial_command:
        match = re.search(r'(?:send (?:an )?email to|email)\s+(.+)', initial_command, re.IGNORECASE)
        if match:
            raw_recipient = match.group(1).strip()

    # 2. If no name was found, ask for it normally
    if not raw_recipient:
        speak_func("Who would you like to email?")
        raw_recipient = listen_func()

    if not raw_recipient or "cancel" in raw_recipient.lower() or "nevermind" in raw_recipient.lower():
        speak_func("Email canceled.")
        return "System Note: The user canceled the email request."

    # 3. Strip punctuation added by Whisper
    recipient = re.sub(r'[^\w\s]', '', raw_recipient).strip()

    # 4. Safely load contacts
    contacts = []
    if CONTACTS_PATH.exists():
        try:
            with open(CONTACTS_PATH, 'r', encoding='utf-8') as f:
                data = f.read().strip()
                if data:  
                    contacts = json.loads(data)
        except Exception as e:
            print(f"[Gmail Intent] Failed to load contacts file: {e}")

    if not contacts:
        speak_func("Your contacts list is empty or unavailable. I cannot send the email.")
        return "System Note: Failed to send email because contacts file was empty."

    # 5. Fuzzy match the spoken name
    target_email = None
    target_name = None
    
    for c in contacts:
        first = c.get('first_name', '').lower()
        full = c.get('full_name', '').lower()
        recip_lower = recipient.lower()
        
        if recip_lower in full or (first and recip_lower == first):
            target_email = c.get('email')
            target_name = c.get('first_name', c.get('full_name', 'Unknown'))
            break

    if not target_email:
        speak_func(f"I could not find an email address for {recipient}.")
        return f"System Note: Failed to send email. Contact '{recipient}' not found."

   
    speak_func("What is the subject of the email?")
    subject = listen_func()

    if not subject or "cancel" in subject.lower():
        speak_func("Email canceled.")
        return "System Note: The user canceled the email request during the subject phase."
    
    # Clean up any trailing punctuation Whisper might add to the subject
    subject = subject.strip()
    if subject.endswith('.'):
        subject = subject[:-1]

   
    speak_func(f"What is your message to {target_name}?")
    body = listen_func()

    if not body or "cancel" in body.lower():
        speak_func("Email canceled.")
        return "System Note: The user canceled the email request during the draft phase."

    # 8. Send it (Now passing the actual spoken subject!)
    speak_func(f"Sending your message to {target_name}.")
    
    try:
        send_email(to_address=target_email, subject=subject, body=body)
        speak_func("Message sent successfully.")
        return f"System Note: Successfully sent an email to {target_name} with subject '{subject}'."
    except Exception as e:
        print(f"[Gmail Handler Error] Failed to send email: {e}")
        speak_func("I encountered an error while trying to send the email.")
        return f"System Note: Failed to send email due to API error: {e}"


class GmailHandler:
    def is_related(self, command: str) -> bool:
        return is_gmail_request(command)
    
    def handle(self, command: str, history: list = None) -> str:
        """Execution entry point used by the standard intent router for reading emails."""
        return read_saved_emails()
        
    def execute_interactive(self, listen_func, speak_func, initial_command: str = "") -> str:
        return handle_interactive_email(listen_func, speak_func, initial_command)
    
    