import base64
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path

from googleapiclient.discovery import build

from backend.modules.google.google_auth import get_google_creds


# gmail_actions.py lives in backend/modules/google/
BACKEND_DIR = Path(__file__).resolve().parents[2]

CREDENTIALS_PATH = BACKEND_DIR / "config" / "google_credentials.json"
TOKEN_PATH = BACKEND_DIR / "config" / "token.json"


def send_email(to_address: str, subject: str, body: str) -> dict:
    """
    Send a plain-text email through the authenticated Gmail account.

    Returns the Gmail API response, including the sent message ID.
    """
    to_address = to_address.strip()
    subject = subject.strip()
    body = body.strip()

    _, parsed_address = parseaddr(to_address)

    if not parsed_address or "@" not in parsed_address:
        raise ValueError(f"Invalid recipient email address: {to_address}")

    if not subject:
        subject = "Message from Jarvis"

    if not body:
        raise ValueError("Email body cannot be empty.")

    creds = get_google_creds(
        str(CREDENTIALS_PATH),
        str(TOKEN_PATH),
    )

    service = build("gmail", "v1", credentials=creds)

    message = EmailMessage()
    message["To"] = parsed_address
    message["Subject"] = subject
    message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    response = (
       service.users()
       .messages()
       .send(
           userId="me",
            body={
               "raw": encoded_message
            },
        )
        .execute()
    )

    print(f"[Gmail] Sent email to {parsed_address}.")
    print(f"[Gmail] API response: {response}")

    return response
    