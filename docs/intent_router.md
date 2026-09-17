# Intent Router

## Purpose

The Intent Router is responsible for determining which Jarvis feature should process a user's spoken request.

Rather than every module inspecting every command, the Intent Router evaluates each registered handler in priority order until one claims responsibility for the request.

This provides a modular architecture where new features can be added without changing the routing logic.

---

## User Experience

Typical routing flow:

1. User asks a question.
2. Speech is converted to text.
3. The Intent Router evaluates every registered handler.
4. The first matching handler executes.
5. Jarvis returns the response.

Example:

User

> What's the weather tomorrow?

↓

Weather Handler

↓

Weather Agent

↓

Voice Response

---

## Features

### Modular Routing

Each feature implements its own handler.

Current handlers include:

- Morning Briefing
- Calendar
- Gmail
- Research
- Weather
- General Chat

The router does not know how these features work.

It simply asks each handler:

> "Is this your request?"

---

### Priority-Based Evaluation

Handlers are evaluated in order.

The first handler that claims a request becomes responsible for it.

Current evaluation order:

1. Morning Briefing
2. Calendar
3. Gmail
4. Research
5. Weather
6. Chat

This allows specialized features to take priority over general conversation.

---

### Conversation History

The router passes the active conversation history to each handler.

This allows handlers to:

- Remember previous questions
- Continue conversations
- Maintain context

---

### Extensible Design

Adding a new feature requires only:

1. Create a new handler.
2. Register the handler.

No router logic needs to change.

---

# Architecture

```
Speech Recognition

↓

Intent Router

↓

Registered Handlers

↓

Feature Module

↓

Voice Response
```

---

# Module Breakdown

## intent_router.py

### Purpose

Routes user requests to the correct handler.

### Responsibilities

- Evaluate handlers
- Pass conversation history
- Return handler response
- Stop evaluation after first match

---

## registry.py

### Purpose

Maintains the ordered list of available handlers.

### Responsibilities

- Register handlers
- Control evaluation order
- Initialize feature modules

---

# Current Routing Order

```
Morning Briefing

↓

Calendar

↓

Gmail

↓

Research

↓

Weather

↓

General Chat
```

The Chat Handler is intentionally last because it serves as the fallback for requests that are not handled by specialized features.

---

# Handler Interface

Every handler implements a common interface.

Required methods:

```
is_related(command)

handle(command, history)
```

Some handlers optionally support:

```
execute_interactive()
```

This allows the handler to temporarily take control of the microphone for conversational workflows.

Example:

Send Email

↓

Who would you like to email?

↓

What is the subject?

↓

What is your message?

---

# Interactive Sessions

Some features require multiple conversational steps.

Examples:

- Send Email
- Research Q&A
- Future Settings Wizard

During these sessions the handler temporarily owns the conversation until the workflow completes.

---

# Python Files

```
backend/router/

intent_router.py

registry.py
```

---

# Python Packages

Internal Modules

- calendar_intent
- gmail_intent
- weather_intent
- research_intent
- morning_briefing_intent
- chat_intent

---

# Dependencies

Required

- Voice Engine
- Registered Intent Handlers

No external APIs are used directly by the Intent Router.

---

# Configuration

The routing order is controlled by:

```
registry.py
```

Adding a new feature requires registering a new handler in the handler list.

---

# Design Decisions

## Why a Handler Registry?

The router never imports feature-specific logic.

Instead, every feature is self-contained and simply registers itself.

This keeps the router extremely small and easy to maintain.

---

## Why First-Match Wins?

Most requests should only be handled once.

Stopping after the first match prevents duplicate responses and unnecessary processing.

---

## Why Separate Routing from Features?

Each feature is responsible only for understanding its own commands.

The router remains completely independent of feature implementations.

---

## Why Pass Conversation History?

Many requests depend on previous context.

Passing history allows features to maintain natural conversations without relying on global variables.

---

# Error Handling

The Intent Router automatically handles:

- No matching handler
- Missing handlers
- Invalid routing requests

If no specialized handler accepts the request, the Chat Handler serves as the fallback conversational interface.

---



# Related Documentation

- architecture.md
- wake_word.md
- voice.md
- local_llm.md
- research.md
- weather.md
- calendar.md
- gmail.md