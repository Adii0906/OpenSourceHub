import os
from typing import List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import json
from pathlib import Path
import requests
import asyncio
from datetime import datetime, timedelta
import os

try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

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
async def get_programs(difficulty: str | None = None, tech: str | None = None):
    """
    Return list of programs.
    Optional query params: 
    - difficulty=beginner|intermediate|advanced
    - tech=security|ai|web|mobile|cloud|devops
    """
    programs_data = get_programs_data()
    filtered = programs_data
    
    # Filter by difficulty
    if difficulty:
        difficulty = difficulty.lower()
        filtered = [p for p in filtered if p.get("difficulty") == difficulty]
    
    # Filter by tech category
    if tech:
        tech = tech.lower()
        filtered = [p for p in filtered if 
                   p.get("tech", "").lower() == tech or 
                   any(tech in tag.lower() for tag in p.get("tags", []))]
    
    # Return all programs with proper model validation
    return [Program(**p) for p in filtered]


# In a real app, you would persist these to a DB or mailing service.
SUBSCRIBED_EMAILS: List[str] = []

# Subscriptions persistence
SUBSCRIPTIONS_STORE = Path(__file__).parent.parent / "backend" / "subscriptions.json"


def load_subscriptions():
    if SUBSCRIPTIONS_STORE.exists():
        try:
            with open(SUBSCRIPTIONS_STORE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            return []
    return []


def save_subscriptions(emails: List[str]):
    try:
        SUBSCRIPTIONS_STORE.parent.mkdir(parents=True, exist_ok=True)
        with open(SUBSCRIPTIONS_STORE, "w", encoding="utf-8") as f:
            json.dump(list(dict.fromkeys(emails)), f)
    except Exception as e:
        print(f"Error saving subscriptions: {e}")

# Persisted notifications to avoid re-sending same program to same user
NOTIFICATIONS_STORE = Path(__file__).parent.parent / "backend" / "sent_notifications.json"

# Kestra integration configuration (can be overridden via env)
KESTRA_BASE = os.getenv("KESTRA_BASE", "http://localhost:8080")
KESTRA_NAMESPACE = os.getenv("KESTRA_NAMESPACE", "opensource")
KESTRA_FLOW_SUBSCRIBE = os.getenv("KESTRA_FLOW_SUBSCRIBE", "subscription-success")
KESTRA_FLOW_DAILY = os.getenv("KESTRA_FLOW_DAILY", "daily-reminder")


def load_sent_notifications():
    if NOTIFICATIONS_STORE.exists():
        try:
            with open(NOTIFICATIONS_STORE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_sent_notifications(data):
    try:
        NOTIFICATIONS_STORE.parent.mkdir(parents=True, exist_ok=True)
        with open(NOTIFICATIONS_STORE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving notifications store: {e}")


def start_kestra_execution(flow_id: str, inputs: dict):
    """Start a Kestra flow execution via its REST API.

    This function is best called in a background thread/task because it issues a blocking HTTP request.
    Make sure you have a flow with the given id in the configured namespace.
    """
    url = f"{KESTRA_BASE}/api/v1/main/executions/{KESTRA_NAMESPACE}/{flow_id}"
    
    # Kestra requires multipart/form-data with inputs as form fields
    files = {}
    for key, value in inputs.items():
        files[key] = (None, str(value))
    
    try:
        # Add basic auth credentials for Kestra
        auth = ("cybterrior@gmail.com", "Heythere123321")
        resp = requests.post(url, files=files, timeout=10, auth=auth)
        if resp.status_code >= 300:
            print(f"Kestra execution failed ({resp.status_code}): {resp.text}")
        else:
            print(f"Kestra execution started for flow {flow_id}")
    except Exception as e:
        print(f"Error starting Kestra flow {flow_id}: {e}")


async def daily_reminder_loop():
    """Background loop that runs once a day and triggers Kestra reminders.

    It finds programs that are urgent (deadline within 7 days) or tagged high-priority.
    For each subscribed email, it sends only new program notifications using the Kestra daily flow.
    """
    print("Starting daily reminder loop")
    while True:
        try:
            # Wait until next 03:00 UTC to run (or run immediately on startup)
            now = datetime.utcnow()
            # Run every 24 hours; sleep until next run time
            # We'll run once immediately on start, then sleep 24h.
            programs = get_programs_data()

            # Determine urgent programs (deadline within 7 days) and high-priority heuristics
            urgent_programs = []
            for p in programs:
                added = False
                # try to parse deadline
                deadline = None
                dl = p.get("deadline") or ""
                if date_parser:
                    try:
                        deadline = date_parser.parse(dl, fuzzy=True)
                    except Exception:
                        deadline = None
                # if parsed and within 7 days
                if isinstance(deadline, datetime):
                    if 0 <= (deadline - datetime.utcnow()).days <= 7:
                        urgent_programs.append(p)
                        added = True

                # Heuristic: tags containing 'Paid' or 'Urgent' are high-priority
                tags = [t.lower() for t in (p.get("tags") or [])]
                if ("paid" in tags or "urgent" in tags or p.get("program_type", "").lower() == "internship") and not added:
                    urgent_programs.append(p)

            # prepare notifications store
            sent = load_sent_notifications()

            # For each subscribed email, prepare list of programs not yet sent
            for email in SUBSCRIBED_EMAILS:
                email_sent_ids = set(sent.get(email, []))
                to_send = [p for p in urgent_programs if p.get("id") not in email_sent_ids]
                if not to_send:
                    continue

                # Trigger Kestra daily reminder flow in background thread
                inputs = {
                    "email": email,
                    "programs": to_send,
                    "note": "Daily urgent programs reminder",
                }
                # run blocking HTTP call in thread
                asyncio.create_task(asyncio.to_thread(start_kestra_execution, KESTRA_FLOW_DAILY, inputs))

                # update sent store with ids we've just notified
                email_sent_ids.update([p.get("id") for p in to_send if p.get("id") is not None])
                sent[email] = list(email_sent_ids)

            save_sent_notifications(sent)

        except Exception as e:
            print(f"Error in daily_reminder_loop: {e}")

        # Sleep 24 hours
        await asyncio.sleep(24 * 60 * 60)


@app.on_event("startup")
async def startup_event():
    # Ensure sent notifications file exists
    if not NOTIFICATIONS_STORE.exists():
        save_sent_notifications({})
    # Start background daily loop
    # Load persisted subscriptions into memory
    global SUBSCRIBED_EMAILS
    loaded = load_subscriptions()
    if loaded:
        SUBSCRIBED_EMAILS = loaded
    else:
        SUBSCRIBED_EMAILS = []

    # Ensure subscriptions file exists (write current in-memory list)
    save_subscriptions(SUBSCRIBED_EMAILS)

    asyncio.create_task(daily_reminder_loop())


@app.post("/api/subscribe")
async def subscribe_email(payload: EmailSubscription, background_tasks: BackgroundTasks):
    email = payload.email
    if email in SUBSCRIBED_EMAILS:
        return {"status": "already_subscribed", "email": email}
    SUBSCRIBED_EMAILS.append(email)

    # Persist subscriptions
    try:
        save_subscriptions(SUBSCRIBED_EMAILS)
    except Exception as e:
        print(f"Error persisting subscription: {e}")

    # Trigger Kestra workflow to send confirmation email
    background_tasks.add_task(
        start_kestra_execution,
        KESTRA_FLOW_SUBSCRIBE,
        {
            "email": email,
            "status": "subscribed",
            "note": "New subscription from website"
        }
    )

    return {"status": "subscribed", "email": email}


@app.post("/api/agent/chat")
async def agent_chat(query: AgentQuery):
    """
    Chat with AI mentor about open source programs and contributions.
    """
    try:
        if not query.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Get programs data for context
        programs_data = get_programs_data()

        # Call the updated async mentor function
        reply_text = await open_source_mentor_agent(query.message, programs_data)

        # Filter programs based on difficulty if specified
        if query.difficulty_filter:
            suggested_programs = [
                p for p in programs_data
                if p.get("difficulty", "").lower() == query.difficulty_filter.lower()
            ]
        else:
            # Return top 5 programs as suggestions
            suggested_programs = programs_data[:5]

        return {
            "reply": reply_text,
            "suggested_programs": suggested_programs
        }

    except Exception as e:
        print(f"Agent chat error: {e}")
        return {
            "reply": "Sorry, I'm having trouble right now. Please try again later.",
            "suggested_programs": []
        }


@app.get("/subscribers", response_model=List[str])
async def get_subscribers():
    """Return list of all subscriber emails for Kestra workflows."""
    return SUBSCRIBED_EMAILS


@app.get("/admin/latest-additions")
async def get_latest_additions():
    """
    Return programs added in the last 24 hours for reminder emails.
    For now, returns last 3 programs (sorted by ID descending).
    """
    programs_data = get_programs_data()
    # Sort by ID descending and take last 3
    sorted_programs = sorted(programs_data, key=lambda p: p.get('id', 0), reverse=True)
    return sorted_programs[:3]


@app.post("/admin/update-programs")
async def update_programs(programs: List[dict]):
    """
    Admin endpoint for Kestra AI workflow to update programs.json
    with newly scraped & categorized programs.
    """
    try:
        with open(PROGRAMS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(programs, f, indent=2, ensure_ascii=False)
        
        # Also update frontend cache
        frontend_cache = Path(__file__).parent.parent / "frontend" / "programs-cache.json"
        with open(frontend_cache, "w", encoding="utf-8") as f:
            json.dump(programs, f, indent=2, ensure_ascii=False)
        
        return {"status": "success", "total_programs": len(programs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/add-programs")
async def add_programs(data: dict):
    """
    Admin endpoint for AI workflow to ADD new programs to existing programs.json
    Includes duplicate detection based on name, slug, and official_site URL
    """
    try:
        new_programs = data.get('programs', [])
        if not new_programs:
            return {"status": "error", "message": "No programs provided"}
        
        # Load existing programs
        existing_programs = get_programs_data()
        
        # Create lookup sets for duplicate detection
        existing_names = {p.get('name', '').lower().strip() for p in existing_programs}
        existing_slugs = {p.get('slug', '').lower().strip() for p in existing_programs}
        existing_sites = {p.get('official_site', '').lower().strip() for p in existing_programs}
        
        # Filter out duplicates
        actually_new = []
        duplicates = []
        
        for program in new_programs:
            program_name = program.get('name', '').lower().strip()
            program_slug = program.get('slug', '').lower().strip()
            program_site = program.get('official_site', '').lower().strip()
            
            # Check if duplicate based on name, slug, or site
            if (program_name in existing_names or 
                program_slug in existing_slugs or 
                program_site in existing_sites):
                duplicates.append(program.get('name', 'Unknown'))
                print(f"⚠️ Skipping duplicate: {program.get('name')}")
            else:
                actually_new.append(program)
                # Add to sets to prevent duplicates within the same batch
                existing_names.add(program_name)
                existing_slugs.add(program_slug)
                existing_sites.add(program_site)
        
        # Only add truly new programs
        all_programs = existing_programs + actually_new
        
        # Save to programs.json
        with open(PROGRAMS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(all_programs, f, indent=2, ensure_ascii=False)
        
        # Also update frontend cache
        frontend_cache = Path(__file__).parent.parent / "frontend" / "programs-cache.json"
        with open(frontend_cache, "w", encoding="utf-8") as f:
            json.dump(all_programs, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "programs_added": len(actually_new),
            "duplicates_skipped": len(duplicates),
            "duplicate_names": duplicates,
            "total_programs": len(all_programs),
            "new_program_names": [p.get('name') for p in actually_new]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# NOTE: Frontend is served separately during development (e.g., npm serve, or LiveServer)
# or via a reverse proxy in production. Do NOT mount at "/" with StaticFiles(html=True)
# as it shadows API routes.

# Frontend files directory (used to serve index.html and static assets)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# Mount the frontend static files at the root path AFTER API routes so that
# API endpoints (defined above) take precedence. This serves `index.html`
# for the home route and provides the JS/CSS files under `/` paths used by
# the existing frontend (e.g. `/app.js`, `/styles.css`, `/programs-cache.json`).
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    print(f"Warning: frontend directory not found at {FRONTEND_DIR}. Home route will not serve index.html")
