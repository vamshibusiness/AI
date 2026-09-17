# Research Agent

## Purpose

The Research Agent performs long-running autonomous web research in the background while Jarvis continues responding to other requests.

Unlike normal question answering, research is designed for topics that require multiple searches, information gathering, fact extraction, summarization, and long-term storage.

Completed research is permanently saved and can later be queried through a conversational question-and-answer interface.

---

## User Experience

Typical workflow:

1. User starts a research task.
2. Jarvis plans multiple search queries.
3. Research runs in the background.
4. Jarvis remains available for other commands.
5. When research completes, Jarvis announces completion.
6. User can ask follow-up questions about the completed report.

Example commands:

- Start research on artificial intelligence
- Research why local LLMs are becoming popular
- Research the latest NVIDIA GPUs
- Research status
- Cancel research
- Continue unfinished research
- What did you find about AI?
- Show completed research

---

## Features

### Autonomous Planning

Before searching the internet, the Research Agent asks the local LLM to break a topic into multiple focused search queries.

Example:

Topic:

Artificial Intelligence

Generated searches might include:

- History of artificial intelligence
- Current AI trends
- Major AI companies
- Future of AI

---

### Background Execution

Research runs on a background thread.

Jarvis remains available while research is running.

Users may continue asking:

- Weather
- Email
- Calendar
- General questions

without interrupting the research process.

---

### Dynamic Research

The Research Agent is capable of generating additional follow-up searches while researching.

If the collected information indicates another important topic should be investigated, the agent automatically inserts another search into the queue.

---

### Fact Extraction

Each web search is analyzed by the local LLM.

The model extracts:

- Relevant facts
- Important findings
- Useful summaries

while ignoring irrelevant information.

---

### Report Generation

After all searches complete, the local LLM combines every collected fact into a single comprehensive report.

The report is written in natural language optimized for voice conversations.

---

### Long-Term Memory

Completed research is permanently stored.

Future requests on the same topic immediately return the saved report instead of repeating the research.

---

### Interactive Question & Answer

After research finishes, users can continue asking questions about the completed report.

Example:

Research completes.

User:

What did the research find?

User:

Tell me more about the third point.

User:

Can you explain that differently?

The Research Agent answers using only the completed report.

---

# Architecture

```
User

↓

Intent Router

↓

Research Intent

↓

Research Agent

↓

Research Planning (LLM)

↓

Web Searches

↓

Fact Extraction (LLM)

↓

Dynamic Follow-up Searches

↓

Report Generation (LLM)

↓

Long-Term Storage

↓

Research Complete Event

↓

Voice Q&A
```

---

# Module Breakdown

## research_intent.py

### Purpose

Processes all research-related voice commands.

### Responsibilities

- Detect research requests
- Start research
- Cancel research
- Resume unfinished research
- Return research status
- Launch research Q&A mode

---

## research_tool.py

### Purpose

Acts as the public interface between Jarvis and the Research Agent.

### Responsibilities

- Share the singleton Research Agent
- Start research
- Cancel research
- Return completed reports
- Answer questions about saved reports

---

## search_tool.py

### Purpose

Provides internet search capabilities for the Research Agent.

### Responsibilities

- Execute DuckDuckGo web searches
- Format search results for LLM consumption
- Return titles, summaries, and source URLs
- Handle search failures gracefully

The search tool returns structured text optimized for fact extraction by the local LLM.

## research_agent.py

### Purpose

Implements the autonomous research workflow.

### Responsibilities

- Plan research
- Generate search queries
- Perform web searches
- Extract facts
- Generate follow-up searches
- Build final reports
- Persist research
- Resume interrupted research

---

## main.py

### Purpose

Creates and manages the shared Research Agent during Jarvis startup.

### Responsibilities

- Initialize the Research Agent
- Resume unfinished research
- Broadcast research updates to the UI
- Display completed reports

---

# Research Workflow

Planning

↓

Generate Search Queries

↓

Execute Search

↓

Extract Facts

↓

Repeat

↓

Generate Report

↓

Save Report

↓

Notify User

↓

Research Q&A

---

# State Management

The Research Agent tracks its progress using several internal states.

Supported states:

- Idle
- Planning
- Researching
- Summarizing
- Error

If Jarvis shuts down unexpectedly, research automatically resumes the next time Jarvis starts.

---

# Memory

## Active Memory

Current research progress is continuously saved.

Stored information includes:

- Current topic
- Search queue
- Active search
- Collected facts
- Sources
- Progress

---

## Long-Term Memory

Completed reports include:

- Research topic
- Final report
- Collected facts
- Web sources
- Creation date

Repeated research requests reuse previously completed reports whenever possible.

---

# External Services

## DuckDuckGo Search

Purpose

Provides internet search capabilities without requiring an API key leveraged in search_tools.py.

The Research Agent uses the DDGS Python package to retrieve:

- Search result titles
- Summaries
- Source URLs

These results are passed to the local LLM for fact extraction and report generation.

No API key is required.

---

# Python Files

```

backend/modules/agents/
research_agent.py

backend/modules/research/
research_tool.py

research_intent.py

backend/main.py

backend\modules\web
search_tool.py
```

---

# Python Packages

Web Search

- ddgs

Threading

- threading

JSON

- json

Date & Time

- datetime
- time

Pattern Matching

- re

Filesystem

- pathlib

Typing

- typing

Internal Modules

- local_llm
- search_tool
- jarvis_events

# Dependencies

Required

- Local LLM
- Internet connection
- Web Search Tool


---

# Configuration

Research state is automatically stored in:

```
backend/assets/

active_research.json

completed_research.json
```

These files allow research to continue after Jarvis restarts.

---

# Design Decisions

## Why Background Threads?

Research may take several minutes.

Running in the background allows Jarvis to continue responding to voice commands.

---

## Why Planning First?

Breaking a topic into multiple focused searches produces significantly higher quality reports than performing a single search.

---

## Why Dynamic Follow-Up Searches?

Sometimes the initial searches reveal missing information.

The Research Agent can automatically investigate those gaps.

---

## Why Save Reports?

Research should only need to be performed once.

Previously completed reports become part of Jarvis's long-term knowledge.

---

## Why Interactive Q&A?

Instead of reading an entire report aloud, users can ask follow-up questions naturally.

This creates a conversational research experience.

---

# Error Handling

The Research Agent automatically handles:

- Network failures
- Empty search results
- Invalid LLM responses
- JSON parsing failures
- Interrupted research
- Duplicate research requests

Whenever possible, research resumes instead of restarting.

---



# Related Documentation

- architecture.md
- local_llm.md
- voice.md
- intent_router.md
- configuration.md