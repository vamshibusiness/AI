# User Interface

## Purpose

The User Interface provides a real-time visual representation of Jarvis.

Rather than acting as a control panel, the UI reflects Jarvis's current state, displays active information, and provides access to completed research and dashboard summaries.

The interface communicates with the backend through WebSockets and lightweight REST endpoints.

---

## User Experience

The interface automatically updates while Jarvis is running.

Typical flow:

1. Jarvis starts.
2. UI connects to the backend.
3. Current status is displayed.
4. Voice interactions update the UI in real time.
5. Dashboard cards refresh automatically.
6. Research reports can be viewed from the interface.

The UI requires no user interaction during normal voice conversations.

---

## Features

### Real-Time Status

The UI reflects Jarvis's current operating state.

Supported states include:

- Idle
- Listening
- Thinking
- Speaking
- Checking Email

Status changes occur automatically through WebSocket events.

---

### Research Dashboard

Displays:

- Active research count
- Completed research count
- Active research topic

Users can also browse completed research reports.

---

### Completed Research Viewer

Completed reports include:

- Topic
- Summary
- Full report
- Supporting facts
- Sources
- Creation date

Reports can be opened directly from the dashboard.

---

### Calendar Dashboard

Displays:

- Upcoming event count
- Today's appointments
- Event summaries

The dashboard refreshes automatically whenever calendar events change.

---

### Gmail Dashboard

Displays:

- Unread important email count

The badge updates automatically after Gmail polling or when emails are read.

---

### Reactive Updates

The UI automatically reacts to backend events.

Examples:

Research completed

↓

Research counter updates

↓

Research report becomes available

Calendar updated

↓

Calendar badge refreshes

Email received

↓

Unread badge updates

---

# Architecture

```
React

↓

WebSocket

↓

FastAPI Backend

↓

Jarvis

↓

Dashboard Updates
```

---

# Module Breakdown

## App.jsx

### Purpose

Acts as the primary UI controller.

### Responsibilities

- Maintain application state
- Receive WebSocket events
- Display dashboard information
- Switch between views
- Render research reports

---

## main.jsx

### Purpose

Initializes the React application.

### Responsibilities

- Load App component
- Mount React application
- Load global styles

---

# UI Views

## Home

Displays:

- Jarvis animation
- Current state
- Dashboard widgets

---

## Completed Research

Displays:

- List of completed reports
- Research summaries
- Detailed report viewer

---

# WebSocket Events

The UI listens for real-time events.

Examples:

Status Updates

```
idle

listening

thinking

speaking

checking-email
```

Research

```
show_completed_research

research_summary

home
```

Dashboard

```
calendar_summary

gmail_summary
```

---

# REST Endpoints

The UI communicates with the backend using lightweight REST endpoints.

Examples include:

Status

```
/status
```

Research

```
/research/summary

/research/show-completed

/research/close
```

Calendar

```
/calendar/summary

/calendar/refresh-summary
```

Gmail

```
/gmail/summary

/gmail/refresh-summary
```

---

# State Management

The UI maintains several pieces of application state.

Examples:

- Current Jarvis status
- Current view
- Completed research
- Selected research report
- Research summary
- Calendar summary
- Gmail summary

State updates automatically as backend events arrive.

---

# Python / JavaScript Files

```
frontend/src/

App.jsx

main.jsx

App.css

index.css
```

---

# Technologies

Frontend

- React
- Vite

Communication

- WebSocket
- REST

Backend

- FastAPI

---

# Dependencies

Required

- React
- Vite
- FastAPI Backend

Optional

- Modern web browser
- GPU animation support

---

# Configuration

The frontend connects to the local backend.

Default WebSocket

```
ws://localhost:8000/ws
```

REST endpoints communicate with the same backend server.

---

# Design Decisions

## Why React?

React provides efficient state management and automatic UI updates with very little code.

---

## Why WebSockets?

WebSockets allow Jarvis to push updates immediately.

The frontend never has to poll continuously for status changes.

---

## Why Separate Dashboard Cards?

Each subsystem owns its own summary.

Examples:

- Gmail
- Calendar
- Research

This allows individual features to refresh without reloading the entire interface.

---

## Why Minimal User Interaction?

Jarvis is designed as a voice-first assistant.

The UI acts primarily as a live dashboard instead of requiring constant mouse interaction.

---

## Why REST and WebSockets?

WebSockets provide instant event updates.

REST endpoints are used for retrieving structured information and refreshing dashboard data.

Using both keeps communication simple and efficient.

---

# Error Handling

The UI automatically handles:

- Lost WebSocket connections
- Backend restarts
- Missing dashboard data
- Invalid research reports
- Empty calendar
- Empty Gmail inbox

Whenever possible, the UI reconnects automatically and continues displaying the latest information.

---


# Related Documentation

- architecture.md
- wake_word.md
- voice.md
- research.md
- calendar.md
- gmail.md
- local_llm.md