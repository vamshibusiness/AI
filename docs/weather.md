# Weather 

## Purpose

The Weather provides current weather conditions and weather forecasts for locations throughout the United States.

It supports current conditions, today's weather, tomorrow's forecast, weekly forecasts, and specific calendar dates using the Open-Meteo APIs.

---

## User Experience

Typical conversation flow:

1. User asks for weather.
2. Jarvis determines the request is weather-related.
3. Jarvis extracts the city, state, and requested timeframe.
4. The Weather Agent converts the location into GPS coordinates.
5. Current weather or forecast information is retrieved.
6. Jarvis summarizes the results using natural speech.

Example commands:

- What's the weather?
- What's the weather in Pittsburgh PA?
- What's the weather in Pittsburgh Pennsylvania?
- What's the weather tomorrow?
- What's the weather this week?
- What's the weather on July 4th?
- What's the weather in Orlando Florida tomorrow?

---

## Features

### Current Weather

Provides:

- Current temperature
- Weather conditions
- Humidity
- Wind speed

---

### Forecasts

Supports:

- Today
- Tomorrow
- Weekly forecast
- Specific calendar dates
- Relative dates

---

### Natural Language Processing

Automatically understands:

- State abbreviations
- Full state names
- Multiple date formats
- Follow-up weather questions

Examples:

- PA
- Pennsylvania
- July 4
- 7/4
- 2026-07-04

---

### Context Memory

The Weather Agent remembers the most recently requested location.

Example:

User:

> What's the weather in Pittsburgh?

Later:

> What about tomorrow?

Jarvis automatically continues using Pittsburgh until another city is provided.

---

# Architecture

```
User

↓

Intent Router

↓

Weather Intent

↓

Extract City / State

↓

Extract Timeframe

↓

Geocoding

↓

Weather API

↓

Natural Language Response

↓

Speech Output
```

---

# Module Breakdown

## weather_intent.py

### Purpose

Processes weather requests after they are identified by the Intent Router.

### Responsibilities

- Detect weather-related commands
- Extract city and state
- Parse requested timeframe
- Maintain short-term location memory
- Call the Weather Tool

---

## weather_tool.py

### Purpose

Retrieves weather information from Open-Meteo services.

### Responsibilities

- Convert city/state into GPS coordinates
- Retrieve current weather
- Retrieve forecasts
- Convert weather codes into natural language
- Format responses for speech

---

# Supported Timeframes

Current

- Current weather
- Right now
- Today

Forecast

- Tomorrow
- This week
- Seven day forecast

Specific Dates

- YYYY-MM-DD
- MM/DD
- July 4
- December 25

---

# Location Handling

Supported formats include:

- Pittsburgh PA
- Pittsburgh Pennsylvania
- Orlando FL
- Orlando Florida

The Weather Agent first converts the location into latitude and longitude using the Open-Meteo Geocoding API before requesting weather data.

---

# APIs Used

## Open-Meteo Geocoding API

Purpose

Converts city/state information into geographic coordinates.

---

## Open-Meteo Forecast API

Purpose

Retrieves:

- Current weather
- Hourly forecasts
- Daily forecasts

---

# Python Files

```
backend/modules/weather/

weather_intent.py

weather_tool.py
```

---

# Python Packages

Weather

- requests

Date Handling

- datetime

Pattern Matching

- re

Standard Library

- datetime
- re

---

# Dependencies

Required

- Internet connection
- Open-Meteo API

No API key is required.

---

# Configuration

Weather defaults are stored in:

```
jarvis_config.py
```

Important settings include:

- USER_CITY
- USER_STATE

These values are used whenever a weather request does not specify a location.

---

# Design Decisions

## Why Open-Meteo?

- Free for personal projects
- No API key required
- Reliable forecast data
- Excellent documentation

---

## Why Geocoding First?

Using latitude and longitude produces more accurate forecasts than relying solely on city names.

---

## Why Context Memory?

Users naturally ask follow-up questions.

Example:

> What's the weather in Pittsburgh?

followed by

> What about tomorrow?

The Weather Agent remembers the previous location to create a more natural conversation.

---

## Why Natural Language Parsing?

Users should not have to memorize specific commands.

The Weather Agent accepts multiple date formats, state abbreviations, and conversational phrasing.

---

# Error Handling

The Weather Agent gracefully handles:

- Unknown cities
- Invalid states
- Missing locations
- Unsupported forecast dates
- Network failures
- API failures

Natural responses are returned whenever possible instead of technical errors.

---



# Related Documentation

- architecture.md
- intent_router.md
- voice.md
- configuration.md