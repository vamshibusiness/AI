# Wake Word Engine

## Purpose

The Wake Word Engine is the entry point into Jarvis.

It continuously listens for the wake phrase, manages active voice conversations, coordinates background agents, updates the user interface, and routes requests to the appropriate modules.

Unlike a simple wake word detector, this engine acts as the central orchestrator for all voice interactions.

---

## User Experience

Typical conversation flow:

1. Jarvis waits silently for the wake phrase.
2. User says "Hey Jarvis."
3. Jarvis acknowledges the request.
4. The user asks a question.
5. Jarvis determines the appropriate action.
6. Jarvis speaks the response.
7. Jarvis continues listening for follow-up questions.
8. Conversation ends after silence or an exit phrase.

Example:

User

> Hey Jarvis

Jarvis

> Good morning, sir.

User

> What's the weather tomorrow?

Jarvis

> Tomorrow will be partly cloudy with a high of 74 degrees.

User

> What meetings do I have?

Jarvis answers without requiring the wake word again.

---

## Features

### Wake Word Detection

Continuously monitors microphone input for:

- Hey Jarvis

Detection uses OpenWakeWord running locally.

---

### Continuous Conversation

After activation, Jarvis remains in an active conversation.

Users may ask multiple follow-up questions without repeating the wake phrase.

Conversation automatically ends after:

- Prolonged silence
- Goodbye
- Bye
- Thank you
- That's all
- Stop
- Never mind

---

### Background Event Processing

The Wake Word Engine receives events from background agents.

Examples:

- Research completed
- Calendar reminders

These events are queued and announced only after Jarvis is no longer busy.

---

### Interactive Sessions

Some features temporarily take exclusive control of the microphone.

Examples:

- Sending Email
- Research Question & Answer

During these sessions normal routing is paused until the workflow completes.

---

### User Memory

At the beginning of every conversation:

- User profile is loaded
- Preferences are injected into the LLM
- Conversation history begins

At the end of every conversation:

- New facts are extracted
- User profile is updated

---

### UI Synchronization

The Wake Word Engine continuously updates the UI.

Supported states include:

- Idle
- Listening
- Thinking
- Speaking
- Checking Email

---

# Architecture

```
Microphone

↓

OpenWakeWord

↓

Wake Queue

↓

Action Worker

↓

Speech-to-Text

↓

Intent Router

↓

Feature Handler

↓

LLM / Tool

↓

Text-to-Speech

↓

Speaker
```

---

# Module Breakdown

## listener.py

### Purpose

Acts as the central controller for all voice interactions.

### Responsibilities

- Listen for wake word
- Manage conversation sessions
- Coordinate microphone usage
- Route commands
- Handle background events
- Update the UI
- Maintain conversation history
- Save user memory

---

## Wake Queue

### Purpose

Coordinates all wake word events.

Responsibilities:

- Queue wake events
- Queue background agent events
- Prevent overlapping conversations

---

## Action Worker

### Purpose

Runs the active conversation session.

Responsibilities

- Play wake response
- Listen for questions
- Route commands
- Speak responses
- Continue conversation
- End conversation gracefully

---

## Event Watcher

### Purpose

Monitors background agents.

Supported events include:

- Research complete
- Calendar reminders

Background events are queued until Jarvis becomes available.

---

## Callback

### Purpose

Processes microphone audio.

Responsibilities

- Detect wake word
- Route audio to Speech-to-Text
- Ignore audio while Jarvis is speaking
- Prevent duplicate wake events

---

# Conversation Lifecycle

Idle

↓

Wake Word

↓

Greeting

↓

Conversation Loop

↓

Speech Recognition

↓

Intent Routing

↓

Response

↓

Continue Listening

↓

Conversation Ends

↓

Return to Idle

---

# Background Event Flow

Background Agent

↓

Jarvis Event

↓

Event Queue

↓

Wake Engine

↓

Voice Notification

↓

Interactive Flow (optional)

---

# Python Files

```
backend/modules/wakeword/

listener.py
```

---

# Python Packages

Wake Word

- openwakeword

Audio

- sounddevice
- numpy

Networking

- requests

Threading

- threading
- queue

Filesystem

- pathlib

Date & Time

- datetime
- time

Pattern Matching

- re

Standard Library

- sys

Internal Modules

- stt_whisper
- tts
- intent_router
- memory_manager
- jarvis_events
- calendar_reminder_agent

---

# Dependencies

Required

- OpenWakeWord
- ONNX Runtime
- Microphone
- Voice Engine


---

# Configuration

Configuration is managed through:

```
jarvis_config.py
```

Important settings include:

- WAKE_RESPONSE
- BEAST_MODE
- SAMPLE_RATE
- CHUNK_SIZE
- TRIGGER_COOLDOWN_SECONDS

---

# Design Decisions

## Why OpenWakeWord?

- Fully local
- No cloud dependency
- Low CPU usage
- Fast detection
- Open source

---

## Why a Conversation Loop?

Users naturally ask follow-up questions.

Keeping the microphone active creates a more conversational experience and removes the need to repeatedly say the wake phrase.

---

## Why Queue Background Events?

Jarvis should never interrupt itself while speaking.

Background notifications are delayed until the current conversation finishes.

---

## Why Separate Worker Threads?

Separating wake detection, conversation handling, and event monitoring prevents audio dropouts while keeping the interface responsive.

---

## Why Update the UI?

The interface always reflects Jarvis's current state.

This provides visual feedback while:

- Listening
- Thinking
- Speaking
- Performing background work

---

# Error Handling

The Wake Word Engine automatically handles:

- Audio device errors
- Duplicate wake words
- Conversation timeouts
- UI communication failures
- Interrupted conversations
- Background event queuing

Whenever possible, Jarvis returns to the idle listening state automatically.

---


# Related Documentation

- voice.md
- architecture.md
- local_llm.md
- research.md
- calendar.md
- email.md
- configuration.md