import json
from pathlib import Path
from typing import List

PROGRAMS_JSON_PATH = Path(__file__).parent.parent.parent / "programs.json"


def load_programs():
    """Load programs from programs.json file."""
    if PROGRAMS_JSON_PATH.exists():
        try:
            with open(PROGRAMS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def list_programs_by_difficulty(difficulty: str) -> List[dict]:
    """Return programs filtered by difficulty (beginner/intermediate/advanced)."""
    difficulty = difficulty.lower()
    programs = load_programs()
    return [p for p in programs if p.get("difficulty") == difficulty]


def get_all_programs() -> List[dict]:
    """Return all available open-source programs."""
    return load_programs()


# Try to import the real ADK Agent. If it's not available in this environment,
# provide a lightweight fallback so the API still starts and the frontend can
# fetch program data. This keeps the app usable locally without ADK installed.
try:
    from google_adk.agents import Agent  # package name is `google-adk` on pip

    open_source_mentor_agent = Agent(
        name="open_source_mentor_agent",
        model="gemini-1.5-flash",
        description="Helps students choose suitable open-source programs and understand timelines.",
        instruction=(
            "You are an OpenSource Mentor Agent. "
            "Use the provided tools to inspect the program list and recommend programs based on user profile, "
            "difficulty preferences, and timelines. Explain reasoning briefly in friendly language."
        ),
        tools=[list_programs_by_difficulty, get_all_programs],
    )
except Exception:
    class _FallbackAgent:
        """Minimal fallback agent with an `execute` method used when ADK isn't installed."""

        def execute(self, payload: dict) -> dict:
            # Return a harmless default response; the frontend will still be able
            # to fetch program data from the /programs endpoint.
            return {"output": "OpenSource Mentor agent is not available in this environment."}

    open_source_mentor_agent = _FallbackAgent()
