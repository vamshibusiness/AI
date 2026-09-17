# Memory System

## Purpose

The Memory System allows Jarvis to remember useful information across conversations while maintaining user privacy.

Rather than storing entire conversations, Jarvis extracts only important user facts, preferences, schedules, and long-term information that improve future interactions.

Memory is stored locally and never requires a cloud service.

---

## User Experience

Typical workflow:

1. User has a conversation with Jarvis.
2. Conversation ends.
3. Jarvis analyzes the conversation.
4. New facts are extracted.
5. Duplicate facts are removed.
6. Updated memory is saved locally.
7. Future conversations automatically use this information.

Example:

User

> My favorite airline is Delta.

↓

Jarvis stores:

- Preferred airline is Delta.

Later:

User

> Book me a flight to Florida.

Jarvis already knows the preferred airline.

---

## Features

### Long-Term Memory

Jarvis remembers useful information including:

- User preferences
- Favorite locations
- Frequently used contacts
- Personal reminders
- Schedules
- Long-term project information

---

### Automatic Memory Extraction

After every conversation, the Local LLM determines whether any new information should be remembered.

Examples:

- Favorite airline
- Home city
- Upcoming vacation
- Preferred golf clubs
- Frequently contacted people

Only explicit information is stored.

---

### Duplicate Protection

Before saving new memories:

- Existing memories are loaded.
- Duplicate entries are removed.
- Only new facts are saved.

This prevents memory from growing unnecessarily.

---

### Relative Date Conversion

Relative dates are converted into real calendar dates.

Example:

Conversation Date:

June 17

User

> Tomorrow I have a dentist appointment.

Stored Memory

June 18, 2026 — Dentist appointment.

---

### Local Storage

All memory is stored locally.

No conversation history or user profile is transmitted to external services.

---

# Architecture

```
Conversation

↓

Conversation Ends

↓

Memory Extraction

↓

JSON Facts

↓

Duplicate Removal

↓

User Profile

↓

Future Conversations
```

---

# Module Breakdown

## memory_manager.py

### Purpose

Maintains Jarvis's long-term memory.

### Responsibilities

- Load existing memories
- Extract new facts
- Normalize dates
- Merge memories
- Remove duplicates
- Save updated profile

---

## user_profile.json

### Purpose

Stores long-term user information.

Examples include:

- Preferences
- Personal facts
- Projects
- Schedules
- Reminders

---

# Memory Workflow

Conversation Ends

↓

Conversation History

↓

Local LLM

↓

Extract New Facts

↓

Convert to JSON

↓

Merge with Existing Memory

↓

Save Profile

---

# Stored Information

Jarvis remembers information such as:

Preferences

- Favorite airline
- Preferred voice
- Favorite sports

Projects

- Current development projects
- Research topics
- Long-term goals

Scheduling

- Future appointments
- Planned vacations
- Important dates

Relationships

- Frequently contacted people
- Family members
- Team members

General Facts

- User interests
- Frequently visited locations
- Recurring habits

---

# Memory Rules

Jarvis stores information only when:

- The user explicitly states a fact.
- The information is useful later.
- The information is not already stored.

Jarvis intentionally avoids storing:

- Entire conversations
- Temporary chat context
- Duplicate information

---

# Local Storage

Memory is stored in:

```
backend/assets/

user_profile.json
```

Memory is loaded automatically at the beginning of every conversation.

---

# Python Files

```
backend/modules/llm/

memory_manager.py

backend/assets/

user_profile.json
```

---

# Python Packages

JSON

- json

HTTP

- requests

Date & Time

- datetime

Filesystem

- pathlib

Internal Modules

- local_llm

---

# Dependencies

Required

- Local LLM

No external APIs are required.

---

# Configuration

Memory storage location:

```
backend/assets/user_profile.json
```

Memory extraction occurs automatically after each completed conversation.

---

# Design Decisions

## Why Store Facts Instead of Conversations?

Entire conversations consume unnecessary storage and frequently contain temporary information.

Extracting only useful facts produces a cleaner long-term memory.

---

## Why Use the Local LLM?

Natural language allows users to share information conversationally.

The Local LLM determines what is important enough to remember.

---

## Why Convert Relative Dates?

Users naturally speak using terms such as:

- Tomorrow
- Next week
- Friday

Converting these into explicit calendar dates prevents ambiguity in future conversations.

---

## Why Merge in Python?

The Local LLM identifies new facts.

Python performs duplicate detection and safely merges memories.

This keeps memory deterministic and prevents accidental overwrites.

---

## Why Store Memory Locally?

Privacy is a core design goal of Jarvis.

User memories remain on the local computer and are never transmitted to external AI services.

---

# Error Handling

The Memory System automatically handles:

- Missing profile files
- Invalid JSON
- Duplicate memories
- Invalid LLM responses
- Date conversion failures

If memory cannot be updated, Jarvis continues operating normally.

---



# Planned Memory Architecture

Current

```
Conversation

↓

Extract Facts

↓

user_profile.json
```

Future

```
Conversation

↓

Extract Facts

↓

Long-Term Memory

↓

Vector Database

↓

RAG Search

↓

Future Conversations
```

This future architecture will allow Jarvis to retrieve relevant memories instead of loading every stored fact into each prompt.

---

# Related Documentation

- local_llm.md
- research.md
- architecture.md
- wake_word.md
- configuration.mdS