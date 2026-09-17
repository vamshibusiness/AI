# Local LLM Engine

## Purpose

The Local LLM Engine gives Jarvis its conversational intelligence.

It connects Jarvis to a locally running Ollama model, streams responses for fast voice playback, supports background LLM tasks, powers general conversation, assists research workflows, and extracts useful user memory after conversations.

The Local LLM Engine is designed to keep Jarvis private, responsive, and independent from cloud AI APIs.

---

## User Experience

Typical conversation flow:

1. User asks a question.
2. Jarvis routes the request to the Chat Handler if no specialized feature handles it.
3. The Local LLM generates a response through Ollama.
4. The response streams token by token.
5. Complete sentences are spoken as soon as they are available.
6. The final response is saved into conversation history.
7. At the end of the session, useful user facts are extracted and saved.

Example commands:

- Explain how local LLMs work.
- What can Jarvis do?
- Tell me a joke.
- Start a research project.

---

## Features

### Local Conversation

General chat is handled by the local Ollama model.

If no specialized handler claims the request, the Chat Handler becomes the fallback response system.

---

### Streaming Responses

The Local LLM streams tokens as they are generated.

Jarvis does not wait for the full answer before speaking.

Instead, it buffers text until a sentence is complete, then sends that sentence to Text-to-Speech.

---

### Voice-Friendly Output

Responses are optimized for speech.

The Chat Handler speaks sentence chunks as they become available, which reduces perceived latency and makes Jarvis feel more responsive.

---

### Background LLM Calls

Some modules need complete responses instead of streamed speech.

Examples:

- Email summarization
- Calendar parsing
- Research planning
- Research report generation
- Memory extraction

For these tasks, Jarvis uses non-streaming wrappers around the same local Ollama API.

---

### Research Model Selection

Research can use a larger model when Beast Mode is enabled.

In Beast Mode, research requests use a more powerful model for higher-quality planning and summarization.

In Standard Mode, research falls back to the default local model.

---

### User Memory Extraction

At the end of a conversation, Jarvis analyzes the session and extracts new facts, preferences, reminders, schedules, and useful details.

These are stored locally and injected into future conversations.

---

# Architecture

```
User Question

↓

Intent Router

↓

Chat Handler

↓

Local LLM

↓

Streaming Tokens

↓

Sentence Buffer

↓

Text-to-Speech

↓

Spoken Response

↓

Conversation Memory Update
```

---

# Module Breakdown

## local_llm.py

### Purpose

Provides the core Ollama API interface.

### Responsibilities

- Send chat messages to Ollama
- Stream tokens
- Return complete responses
- Select alternate models for research
- Handle Ollama errors

---

## chat_intent.py

### Purpose

Provides the fallback general conversation handler.

### Responsibilities

- Accept unhandled user requests
- Stream LLM responses
- Buffer complete sentences
- Speak sentences as they finish
- Mark responses as already spoken

---

## memory_manager.py

### Purpose

Maintains long-term user profile memory.

### Responsibilities

- Load saved user facts
- Extract new facts from conversations
- Convert relative dates into explicit dates
- Merge new facts with existing memory
- Save memory locally

---

# LLM Workflow

Conversation History

↓

Ollama Chat API

↓

Streaming Token Response

↓

Sentence Detection

↓

Speech Queue

↓

TTS Playback

↓

Final Response Saved

---

# Streaming Workflow

Ollama Token

↓

Append to Buffer

↓

Detect Sentence Boundary

↓

Send Sentence to Speech Queue

↓

Continue Streaming

↓

Speak Remaining Text

---

# Memory Workflow

Conversation Ends

↓

Session History Sent to Local LLM

↓

New Facts Extracted

↓

Facts Parsed as JSON

↓

Duplicates Removed

↓

Saved to User Profile

↓

Loaded into Future Sessions

---

# Python Files

```
backend/modules/llm/

local_llm.py

chat_intent.py

memory_manager.py
```

---

# Python Packages

HTTP

- requests

JSON

- json

Threading

- threading
- queue

Pattern Matching

- re

Date & Time

- datetime

Filesystem

- pathlib

Internal Modules

- tts
- jarvis_config

---

# Dependencies

Required

- Ollama
- Local model pulled in Ollama
- Voice Engine

Optional

- Beast Mode GPU acceleration
- Larger research model

---

# Configuration

The Local LLM Engine uses:

```
local_llm.py
```

Important settings include:

- OLLAMA_URL
- MODEL_NAME

Current defaults:

```
OLLAMA_URL = "http://localhost:11434/api/chat"

MODEL_NAME = "gemma4:e4b"
```

Research model selection is controlled by:

```
BEAST_MODE
```

When Beast Mode is enabled, research uses:

```
qwen3.6:27b
```

When Beast Mode is disabled, research uses the default model.

---

# Design Decisions

## Why Ollama?

Ollama allows Jarvis to run local language models without depending on a cloud AI provider.

This keeps conversations private and allows the system to run offline once models are installed.

---

## Why Streaming?

Streaming reduces perceived delay.

Jarvis can begin speaking after the first complete sentence instead of waiting for the entire response.

---

## Why Sentence Chunking?

Speaking token-by-token sounds unnatural.

Sentence chunking provides a smoother voice experience while still keeping latency low.

---

## Why a Chat Handler Fallback?

Not every request maps to a tool.

The Chat Handler ensures Jarvis can always respond conversationally even when no specialized feature matches.

---

## Why Separate Research Calls?

Research benefits from larger models and longer outputs.

Using a separate research wrapper allows Jarvis to use a stronger model without slowing down everyday conversation.

---

## Why Local Memory Extraction?

Memory allows Jarvis to personalize future conversations.

Instead of remembering everything blindly, the memory system extracts only useful explicit facts and stores them locally.

---

# Error Handling

The Local LLM Engine automatically handles:

- Ollama connection failures
- Streaming interruptions
- Invalid model responses
- Memory JSON parsing failures
- Missing user profile files

If Ollama is unavailable, Jarvis returns a local engine error message.

---



# Related Documentation

- architecture.md
- intent_router.md
- wake_word.md
- voice.md
- research.md
- configuration.md
- memory.md