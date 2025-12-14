import os
import google.generativeai as genai
from typing import List, Dict, Any
import json
from pathlib import Path

# Load programs data
PROGRAMS_JSON_PATH = Path(__file__).parent.parent.parent / "programs.json"

def load_programs() -> List[Dict[str, Any]]:
    """Load programs from programs.json file."""
    if PROGRAMS_JSON_PATH.exists():
        try:
            with open(PROGRAMS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

async def open_source_mentor_agent(message: str, programs: List[Dict[str, Any]]) -> str:
    """
    AI mentor that helps with open-source programs and contribution guidance.
    Focuses on merge, pull request, commit processes and stays on topic.
    """
    try:
        # Configure Gemini
        api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyAb9AHy07_7AQhb4on2H5VugOUMM-uRyTk")
        genai.configure(api_key=api_key)

        # Use Gemini 2.0 Flash (closest to 2.5 Flash available)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Create context from programs
        programs_context = "\n".join([
            f"- {p['name']}: {p['description']} (Difficulty: {p['difficulty']}, Type: {p['program_type']}, Deadline: {p['deadline']})"
            for p in programs[:8]  # Limit to first 8 for context
        ])

        prompt = f"""
        You are an Open Source Contribution Mentor. You ONLY help with:

        1. **Open Source Programs**: Recommend programs from our database
        2. **Contribution Process**: How to contribute (Git workflow, pull requests, commits, merges)
        3. **Getting Started**: How to begin with open source

        **STRICT RULES:**
        - ONLY answer questions about open source programs and contributions
        - If asked about anything else (coding, tech stacks, careers, etc.), politely redirect to open source topics
        - Focus on practical contribution steps: fork → clone → branch → commit → pull request → merge
        - Be helpful, encouraging, and stay on topic

        **Available Programs:**
        {programs_context}

        **User Question:** {message}

        **Response Guidelines:**
        - Keep answers focused and practical
        - If they ask about contributing, explain the Git workflow clearly
        - If they ask about programs, recommend from our list
        - If off-topic, gently redirect to open source contributions
        - Be concise but helpful
        """

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        # Fallback response for contribution guidance
        contribution_help = """
        Here's how to contribute to open source projects:

        **Git Workflow:**
        1. **Fork** the repository on GitHub
        2. **Clone** your fork: `git clone your-fork-url`
        3. **Create branch**: `git checkout -b feature-name`
        4. **Make changes** and test them
        5. **Commit**: `git commit -m "Add feature description"`
        6. **Push**: `git push origin feature-name`
        7. **Pull Request**: Create PR on original repository
        8. **Merge**: Wait for maintainers to review and merge

        **Tips:**
        - Start with small issues labeled "good first issue"
        - Read contribution guidelines in README.md
        - Test your changes thoroughly
        - Write clear commit messages

        What specific part would you like help with?
        """
        return contribution_help.strip()
