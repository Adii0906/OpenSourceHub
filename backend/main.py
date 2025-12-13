import os
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import json
from pathlib import Path

from backend.models import Program, AgentQuery, AgentResponse, EmailSubscription
from backend.agents.open_source_mentor import open_source_mentor_agent

# Optionally load environment variables for Gemini / ADK auth (e.g. GOOGLE_API_KEY)
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="OpenSource Programs Mentor")

# Path to programs.json file
PROGRAMS_JSON_PATH = Path(__file__).parent.parent / "programs.json"


def load_programs():
    """Load programs from programs.json file with fallback."""
    if PROGRAMS_JSON_PATH.exists():
        try:
            with open(PROGRAMS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and len(data) > 0:
                    return data
                else:
                    print("Warning: programs.json exists but is empty")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading programs.json: {e}")

    # Fallback: try to load from frontend cache
    frontend_cache = Path(__file__).parent.parent / "frontend" / "programs-cache.json"
    if frontend_cache.exists():
        try:
            with open(frontend_cache, "r", encoding="utf-8") as f:
                data = json.load(f)
                print("Using frontend cache as fallback")
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading frontend cache: {e}")

    # Last resort: return minimal fallback data
    print("Using minimal fallback programs data")
    return [
        {
            "id": 1,
            "name": "Google Summer of Code (GSoC)",
            "slug": "gsoc",
            "difficulty": "intermediate",
            "program_type": "Internship",
            "timeline": "Applications Feb–Apr, coding May–Aug (varies by year)",
            "opens_in": "March",
            "deadline": "April 2, 2025",
            "description": "Work with open source organizations on a 3-month programming project during your summer break.",
            "official_site": "https://summerofcode.withgoogle.com/",
            "tags": ["Paid", "Remote", "Global"],
        },
        {
            "id": 4,
            "name": "Hacktoberfest",
            "slug": "hacktoberfest",
            "difficulty": "intermediate",
            "program_type": "Open Source",
            "timeline": "October 1–31 every year",
            "opens_in": "October",
            "deadline": "October 31",
            "description": "Month-long celebration of open source focused on submitting pull requests to participating repositories.",
            "official_site": "https://hacktoberfest.com/",
            "tags": ["Remote", "Global"],
        }
    ]


def get_programs_data():
    """Get programs data, with fallback to empty list."""
    return load_programs()

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# NOTE: We mount the frontend static files *after* defining API routes
# to avoid the static mount from shadowing API endpoints (e.g. /programs).


@app.get("/programs", response_model=List[Program])
async def get_programs(difficulty: str | None = None):
    """
    Return list of programs.
    Optional query param: difficulty=beginner|intermediate|advanced.
    """
    programs_data = get_programs_data()
    if difficulty:
        difficulty = difficulty.lower()
        filtered = [Program(**p) for p in programs_data if p.get("difficulty") == difficulty]
        return filtered
    # Return all programs with proper model validation
    return [Program(**p) for p in programs_data]


# In a real app, you would persist these to a DB or mailing service.
SUBSCRIBED_EMAILS: List[str] = []


@app.post("/subscribe-email")
async def subscribe_email(payload: EmailSubscription):
    email = payload.email
    if email in SUBSCRIBED_EMAILS:
        return {"status": "already_subscribed", "email": email}
    SUBSCRIBED_EMAILS.append(email)
    return {"status": "subscribed", "email": email}


@app.post("/agent-chat", response_model=AgentResponse)
async def agent_chat(query: AgentQuery):
    """
    Forward user query to the ADK agent and optionally filter by difficulty.
    The agent uses tools to inspect available programs and returns suggestions.
    """
    if not query.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Prepare a structured payload for the ADK agent
    # How exactly you call .execute can vary by ADK version; this is a typical pattern. [web:16][web:14]
    payload = {
        "input": query.message,
        "context": {
            "difficulty_filter": query.difficulty_filter,
        },
    }

    # Execute the agent (async support depends on ADK; wrap sync call if needed)
    agent_result = open_source_mentor_agent.execute(payload)

    # Extract textual reply; adapt depending on actual schema of `agent_result`. [web:16]
    reply_text = str(agent_result.get("output", "Here are some programs that might fit you."))

    # Difficulty filtering on backend for deterministic behavior
    programs_data = get_programs_data()
    if query.difficulty_filter:
        programs = [
            Program(**p)
            for p in programs_data
            if p["difficulty"] == query.difficulty_filter.lower()
        ]
    else:
        programs = [Program(**p) for p in programs_data]

    return AgentResponse(
        reply=reply_text,
        suggested_programs=programs,
    )


# NOTE: Frontend is served separately during development (e.g., npm serve, or LiveServer)
# or via a reverse proxy in production. Do NOT mount at "/" with StaticFiles(html=True)
# as it shadows API routes.
