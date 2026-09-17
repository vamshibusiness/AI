# Gmail Agent

## Purpose

The Gmail Agent provides background email monitoring and voice-controlled email management for Jarvis.

Unlike traditional email clients, Jarvis continuously monitors important unread Gmail messages in the background while remaining available for voice conversations.

The Gmail Agent also supports interactive voice-driven email composition using natural conversation.

---

## User Experience

Typical workflow:

1. Gmail Agent monitors Gmail in the background.
2. Important unread emails are summarized.
3. Email summaries are stored locally.
4. User asks to check email.
5. Jarvis reads the summarized messages.
6. Messages are removed from the local inbox queue.

Users may also send emails conversationally.

Example commands:

- Check my email
- Read my emails
- Do I have any new emails?
- Send an email
- Send an email to Lindsay
- Email Bob

---

## Features

### Background Email Monitoring

The Gmail Agent continuously monitors Gmail for:

- Unread emails
- Important emails
- Recent messages

Only qualifying emails are processed.

---

### Email Summarization

Each email is summarized using the Local LLM.

Instead of reading the full email, Jarvis generates a concise voice-friendly summary.

Example:

Original Email

Several paragraphs...

↓

Summary

Project meeting has been moved to Friday afternoon.

---

### Local Email Queue

Summarized emails are stored locally.

After Jarvis reads them aloud:

- Local queue is cleared
- Gmail messages remain in Gmail
- Emails are already marked as read

---

### Interactive Email Sending

Users can naturally compose emails through conversation.

Example:

User

> Send an email.

Jarvis

> Who would you like to email?

User

> Lindsay.

Jarvis

> What is the subject?

User

> Project Update.

Jarvis

> What is your message?

The completed email is then sent through Gmail.

---

### Contact Synchronization

Google Contacts are synchronized automatically.

Jarvis stores:

- First name
- Last name
- Full name
- Email address

This allows users to say:

> Email Lindsay

instead of remembering email addresses.

---

### UI Integration

The Gmail Agent automatically updates:

- Unread email badge
- Dashboard summaries
- Email notification state

---

# Architecture

```
Gmail

↓

Background Poller

↓

Important Email Filter

↓

Local LLM Summary

↓

Local Inbox

↓

Voice Commands

↓

Interactive Email Assistant

↓

Gmail API
```

---

# Module Breakdown

## gmail_agent.py

### Purpose

Runs continuously in the background.

### Responsibilities

- Poll Gmail
- Summarize emails
- Synchronize contacts
- Store summaries
- Refresh UI

---

## gmail_intent.py

### Purpose

Processes Gmail voice commands.

### Responsibilities

- Read saved emails
- Launch interactive send workflow
- Match contact names
- Refresh UI

---

## gmail_storage.py

### Purpose

Stores summarized emails locally.

### Responsibilities

- Save inbox summaries
- Read inbox
- Clear inbox after reading
- Peek inbox for morning briefing

---

## gmail_tool.py

### Purpose

Communicates directly with Gmail.

### Responsibilities

- Authenticate
- Send emails
- Validate addresses
- Build Gmail messages

---

# Background Workflow

Gmail

↓

Unread Email

↓

Important Filter

↓

Summarize

↓

Save Locally

↓

Notify UI

↓

Wait for User

---

# Send Email Workflow

User

↓

Interactive Conversation

↓

Resolve Contact

↓

Collect Subject

↓

Collect Message

↓

Gmail API

↓

Confirmation

---

# Contact Synchronization

Google Contacts are synchronized automatically every six hours.

Stored information includes:

- First name
- Last name
- Full name
- Email address

Users never need to remember email addresses.

---

# Local Storage

The Gmail Agent stores:

```
backend/assets/

inbox.json

google_contacts.json
```

These files provide:

- Offline email summaries
- Contact lookup
- Morning briefing support

---

# Python Files

```
backend/modules/google/



gmail_intent.py

gmail_storage.py

gmail_tool.py

google_auth.py

backend/modules/agents/
gmail_agent.py
```

---

# Python Packages

Google APIs

- google-api-python-client
- google-auth
- google-auth-oauthlib
- google-auth-httplib2

HTTP

- httpx

Email

- email

Encoding

- base64

Filesystem

- pathlib
- os

JSON

- json

Async

- asyncio

Time

- time

Pattern Matching

- re

Networking

- requests

Internal Modules

- local_llm
- gmail_storage
- google_auth

---

# Dependencies

Required

- Gmail API
- Google OAuth
- Local LLM

Configuration Files

```
google_credentials.json

token.json
```

---

# Configuration

Configuration is managed through:

```
jarvis_config.py
```

Important settings include:

- KEEP_GMAIL_DAYS

The Gmail Agent automatically removes old locally stored summaries after the configured retention period.

---

# Design Decisions

## Why Background Polling?

Checking Gmail continuously allows Jarvis to notify users immediately without requiring manual refreshes.

---

## Why Summarize Emails?

Long emails are difficult to read aloud.

Summaries create a much better voice experience while preserving the important information.

---

## Why Store Emails Locally?

Reading Gmail repeatedly would require unnecessary API calls.

Local storage provides:

- Faster responses
- Offline summaries
- Morning briefing integration

---

## Why Synchronize Contacts?

Voice assistants should recognize people by name instead of requiring email addresses.

Automatic synchronization keeps contact information current.

---

## Why Interactive Conversations?

Sending emails naturally requires multiple pieces of information.

The conversational workflow feels much more natural than requiring one long command.

---

# Error Handling

The Gmail Agent automatically handles:

- Missing credentials
- OAuth failures
- Invalid contacts
- Missing email addresses
- Empty inbox
- Gmail API failures
- Contact synchronization failures
- Network interruptions

Whenever possible, Jarvis returns conversational responses instead of technical errors.

---



# Related Documentation

- architecture.md
- local_llm.md
- wake_word.md
- voice.md
- configuration.md
- intent_router.md