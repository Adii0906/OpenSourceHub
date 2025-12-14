import os
import google.generativeai as genai
import logging
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
        # Configure Gemini with hardcoded API key
        logger = logging.getLogger(__name__)
        api_key = "AIzaSyDxi2Xt5sJvsrH1DoiEDj2dZ8F2FmUp67c"
        genai.configure(api_key=api_key)

        # Select model (default to Gemini 2.5 Flash but allow override via GENAI_MODEL)
        model_name = os.getenv("GENAI_MODEL", "gemini-2.5-flash")
        try:
            model = genai.GenerativeModel(model_name)
            logger.info(f"Using generative model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize model {model_name}: {e}")
            try:
                # fallback to a known-stable model
                model = genai.GenerativeModel('gemini-1.5-pro')
                logger.info("Using fallback model: gemini-1.5-pro")
            except Exception as e2:
                logger.error(f"All model initializations failed: {e2}")
                return (
                    "AI mentor is temporarily unavailable due to model initialization issues. "
                    "Please try again later."
                )

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

        print(f"🤖 AI Request: {message[:100]}...")
        response = model.generate_content(prompt)
        result = response.text.strip()
        print(f"🤖 AI Response length: {len(result)} characters")
        return result

    except Exception as e:
        print(f"❌ AI Mentor Error: {str(e)}")
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
