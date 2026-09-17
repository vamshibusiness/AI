# Configuration

## Purpose

The Configuration System centralizes all settings used by Jarvis.

Configuration is split into two layers:

- **.env** – User-editable settings
- **jarvis_config.py** – Developer defaults, validation, and typed configuration

This architecture allows users to customize Jarvis without modifying Python source code.

---

## User Experience

Most users only configure Jarvis once.

Typical configuration tasks include:

- Setting a preferred greeting
- Choosing a home city
- Selecting AI models
- Enabling Beast Mode
- Adjusting feature settings

Once configured, every Jarvis subsystem automatically loads these settings.

---

# Architecture

```
.env

↓

python-dotenv

↓

jarvis_config.py

↓

Typed Configuration

↓

Jarvis Modules
```

---

## Features

### User Personalization

Users can customize:

- Greeting
- Preferred title
- Home location

Example:

```
USER_TITLE=sir

WAKE_RESPONSE=Hello sir, how can I help you.
```

---

### Hardware Configuration

Users choose whether Jarvis operates in:

Standard Mode

or

Beast Mode

Example

```
BEAST_MODE=true
```

This automatically enables GPU acceleration where supported.

---

### AI Model Selection

The Local LLM model is configurable.

Example:

```
CHAT_MODEL=gemma4:e4b

RESEARCH_MODEL=qwen3.6:27b
```

This allows users to experiment with different Ollama models without changing code.

---

### Weather Defaults

If the user does not specify a location, Jarvis automatically uses:

```
USER_CITY

USER_STATE
```

---

### Gmail Settings

Email retention is configurable.

```
KEEP_GMAIL_DAYS
```

Old summarized emails are automatically removed after the configured number of days.

---


# Module Breakdown

## .env

### Purpose

Stores user-editable configuration.

### Responsibilities

- Personal settings
- AI models
- Feature flags
- Runtime configuration

---

## jarvis_config.py

### Purpose

Loads and validates configuration.

### Responsibilities

- Load environment variables
- Apply defaults
- Convert strings into proper Python types
- Expose typed configuration to the application

---


# Current Configuration

## User

```
USER_TITLE

WAKE_RESPONSE

USER_CITY

USER_STATE
```

---

## AI

```
OLLAMA_URL

CHAT_MODEL

RESEARCH_MODEL
```

---

## Gmail

```
KEEP_GMAIL_DAYS
```

---

## Performance

```
BEAST_MODE
```

---

## Future RAG

```
RAG_TOP_K

RAG_SCORE_THRESHOLD
```

---

## Future UI

```
BACKEND_PORT

FRONTEND_PORT
```

---

# Python Files

```
backend/config/

jarvis_config.py

.env


```

---

# Python Packages

Configuration

- python-dotenv

Standard Library

- os

Internal Modules

- jarvis_config

---

# Dependencies

Required

- python-dotenv

No cloud services are required.

---

# Design Decisions

## Why Use .env?

Users should not need to modify Python files to customize Jarvis.

The .env file provides a familiar configuration experience used by many open-source projects.

---

## Why Keep jarvis_config.py?

Environment variables are always strings.

jarvis_config.py converts them into proper Python types such as:

- bool
- int
- float
- string

It also provides safe defaults when values are missing.

---

## Why Separate User and Developer Configuration?

User settings change frequently.

Developer constants rarely change.

Separating them keeps the project easier to maintain.

---

## Why Use Defaults?

Jarvis can still start even if optional configuration values are missing.

This simplifies installation for new users.

---

# Error Handling

If configuration values are missing:

- Default values are used whenever possible.
- Invalid values fall back to safe defaults.
- Individual modules report meaningful configuration errors.

---

# Example .env

```env
#######################################
# User
#######################################

USER_TITLE=sir

WAKE_RESPONSE=Hello sir, how can I help you?

USER_CITY=New York

USER_STATE=NY

#######################################
# AI
#######################################

OLLAMA_URL=http://localhost:11434/api/chat

CHAT_MODEL=gemma4:e4b

RESEARCH_MODEL=qwen3.6:27b

#######################################
# Gmail
#######################################

KEEP_GMAIL_DAYS=7

#######################################
# Performance
#######################################

BEAST_MODE=true

#######################################
# Future RAG
#######################################

RAG_TOP_K=3

RAG_SCORE_THRESHOLD=0.72
```

---



# Related Documentation

- installation.md
- local_llm.md
- voice.md
- wake_word.md
