# Calendar 

## Purpose

The Calendar allows Jarvis to manage a user's Google Calendar using natural voice commands.

Users can view schedules, create appointments, modify existing events, delete appointments, and ask scheduling questions using conversational language.

The Calendar Agent combines local LLM reasoning with the Google Calendar API to provide a natural voice-first experience.

---

## User Experience

Typical conversation flow:

1. User asks a calendar question.
2. Jarvis determines the request is calendar-related.
3. The local LLM converts natural language into structured calendar actions.
4. Google Calendar is queried or updated.
5. Jarvis summarizes the results using natural speech.
6. The UI dashboard is automatically refreshed.

Example commands:

- What's on my calendar today?
- What's on my calendar tomorrow?
- Do I have anything Friday?
- Schedule a meeting with John tomorrow at 2 PM.
- Delete my dentist appointment.
- Move my meeting to 3 PM.
- Rename my meeting to Project Review.
- Am I free tomorrow afternoon?

---

## Features

### View Schedule

Supports:

- Today's agenda
- Future dates
- Schedule summaries
- Free/busy lookups

---

### Create Events

Users can naturally create appointments.

Examples:

- Schedule lunch tomorrow at noon.
- Add a meeting Friday at 3.
- Book a doctor's appointment Monday morning.

The Local LLM converts conversational language into structured event data.

---

### Modify Events

Existing events can be updated.

Supports:

- Title changes
- Date changes
- Time changes

---

### Delete Events

Appointments can be removed using conversational language.

Examples:

- Delete my dentist appointment.
- Cancel lunch with John.
- Remove that meeting.

---

### Context Memory

The Calendar Agent remembers recently discussed events.

Example:

Jarvis:

> You have a meeting with Lindsay at 3 PM.

User:

> Move that to 4.

Jarvis automatically understands what "that" refers to.

---

### UI Integration

Whenever calendar data changes:

- Event badge refreshes
- Schedule updates
- Dashboard remains synchronized

---

# Architecture

```
User

↓

Intent Router

↓

Calendar Intent

↓

Local LLM Parser

↓

Structured Action

↓

Google Calendar API

↓

Voice Response

↓

UI Refresh
```

---

# Module Breakdown

## calendar_intent.py

### Purpose

Processes natural language calendar requests.

### Responsibilities

- Detect calendar requests
- Parse natural language
- Convert requests into structured actions
- Route actions to Calendar Tool
- Refresh the UI

---

## calendar_tool.py

### Purpose

Communicates with Google Calendar.

### Responsibilities

- Read schedules
- Create events
- Modify events
- Delete events
- Format responses for speech
- Generate UI summaries

---

## main.py

### Purpose

Provides Calendar API endpoints for the UI.

### Responsibilities

- Cache calendar summaries
- Broadcast dashboard updates
- Refresh calendar badges

---

# Supported Actions

View

- Today
- Tomorrow
- Future dates

Create

- Meetings
- Appointments
- Events

Modify

- Rename events
- Change date
- Change time

Delete

- Remove appointments
- Cancel meetings

---

# Natural Language Understanding

The Local LLM converts conversational language into structured JSON.

Example:

User:

> Schedule lunch with Bob tomorrow at noon.

Generated structure:

```json
{
  "action": "add",
  "title": "Lunch with Bob",
  "time": "2026-06-18T12:00:00"
}
```

This allows users to speak naturally without memorizing commands.

---

# Memory

The Calendar Agent temporarily remembers recently referenced events.

Example:

Jarvis:

> You have a meeting called Project Review.

User:

> Delete that.

Jarvis correctly identifies "that" as Project Review.

---

# UI Synchronization

Whenever an event changes:

- Calendar badge updates
- Dashboard refreshes
- Cached schedule refreshes

This keeps the UI synchronized with Google Calendar.

---

# Python Files

```
backend/modules/google/

calendar_intent.py

calendar_tool.py

google_auth.py

backend/main.py
```

---

# Python Packages

Google APIs

- google-api-python-client
- google-auth
- google-auth-oauthlib
- google-auth-httplib2

Networking

- requests

Date & Time

- datetime
- zoneinfo

JSON

- json

Pattern Matching

- re

Filesystem

- pathlib

Internal Modules

- local_llm
- short_term
- google_auth

---

# Dependencies

Required

- Google Calendar API
- Google OAuth Credentials
- Local LLM

Configuration Files

- google_credentials.json
- token.json

---

# Configuration

Google Calendar authentication requires:

```
backend/config/

google_credentials.json

token.json
```

Jarvis automatically authenticates using OAuth and securely stores the user's access token.

---

# Design Decisions

## Why Use the Local LLM?

Rather than forcing users to memorize rigid voice commands, the Local LLM converts natural speech into structured calendar actions.

This allows conversations such as:

> Move my meeting with John to Friday afternoon.

without requiring complex rule-based parsing.

---

## Why Use Google Calendar?

Google Calendar provides:

- Reliable synchronization
- OAuth authentication
- Cross-device compatibility
- Industry-standard APIs

---

## Why Maintain Context?

Users naturally refer to previous appointments.

Supporting phrases like:

- that meeting
- it
- my appointment

creates a far more conversational experience.

---

## Why Cache Calendar Summaries?

The UI frequently requests calendar data.

Caching reduces unnecessary Google API calls while keeping the dashboard responsive.

---

# Error Handling

The Calendar Agent automatically handles:

- Missing credentials
- OAuth failures
- Unknown appointments
- Invalid dates
- Invalid times
- Google API failures
- Network interruptions

Whenever possible, Jarvis returns a conversational response instead of exposing technical errors.

---



# Related Documentation

- installation.md
- local_llm.md
- wake_word.md
- voice.md
- intent_router.md
- configuration.md