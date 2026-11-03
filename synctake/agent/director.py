import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from .inspector import inspect_ui_source
from .pacing import balance_timeline, estimate_speech_duration
from ..schema import SyncTakeConfig


DIRECTOR_SYSTEM_PROMPT = """You are SyncTake Director, an expert AI video producer and technical narrator.
Your job is to translate a developer's UI and product guidance into a perfectly timed, engaging walkthrough script.

Rules:
1. Pacing & Time: Total duration must match the requested seconds. Conversational speech is ~2.4 words per second (145 WPM).
2. Focus: Choose real CSS selectors from the provided UI landmarks for each scene.
3. Engaging Script: Write natural, professional narration. Do not read UI selectors or timestamps aloud.
4. Output JSON: Return ONLY a valid JSON object matching the SyncTake format.

JSON Schema:
{
  "title": "Title of Demo",
  "duration_seconds": 30,
  "scenes": [
    {
      "id": "01-scene-name",
      "title": "Short on-screen heading",
      "callout": "Subtitle or takeaway text",
      "focus": "#target-css-selector",
      "text": "Natural narration text to be spoken in this scene."
    }
  ]
}
"""


def build_director_prompt(user_guidance: str, ui_blueprint: Dict[str, Any], target_duration: float = 30.0) -> str:
    """Builds the prompt given user guidance and the extracted UI landmarks."""
    landmarks_text = json.dumps(ui_blueprint.get("landmarks", []), indent=2)
    return f"""Target Duration: {target_duration} seconds

User Guidance / Instructions:
{user_guidance}

UI Landmarks & Available Selectors:
{landmarks_text}

Generate the complete walkthrough JSON with scenes, focus selectors, on-screen callouts, and natural narration."""


def fallback_director(user_guidance: str, ui_blueprint: Dict[str, Any], target_duration: float = 30.0) -> Dict[str, Any]:
    """
    Deterministic rule-based director when no LLM API key is configured.
    Creates a clean 3-act narrative using available UI landmarks.
    """
    landmarks = ui_blueprint.get("landmarks", [])
    primary_focus = landmarks[0]["selector"] if landmarks else "body"
    secondary_focus = landmarks[1]["selector"] if len(landmarks) > 1 else primary_focus
    tertiary_focus = landmarks[2]["selector"] if len(landmarks) > 2 else secondary_focus

    # Extract intent keywords
    title = "Product Walkthrough"
    if "dashboard" in user_guidance.lower():
        title = "Dashboard Walkthrough"
    elif "signup" in user_guidance.lower():
        title = "User Onboarding Walkthrough"

    scenes = [
        {
            "id": "01-overview",
            "title": f"Welcome to {title}",
            "callout": "Overview of key capabilities and architecture",
            "focus": primary_focus,
            "text": f"Welcome! In this walkthrough, we will explore the core features based on your goals: {user_guidance[:100]}."
        },
        {
            "id": "02-features",
            "title": "Deep Dive & Core Flow",
            "callout": "Real-time interactions and operational highlights",
            "focus": secondary_focus,
            "text": "Here you can see the primary workflow in action. Real-time updates and clear visual landmarks make navigation seamless."
        },
        {
            "id": "03-outcome",
            "title": "Summary & Next Steps",
            "callout": "Verified outcome with zero-drift synchronization",
            "focus": tertiary_focus,
            "text": "Everything is synchronized from code. Changes can be verified instantly with code-level assurance."
        }
    ]

    balanced_scenes = balance_timeline(scenes, target_duration)
    return {
        "title": title,
        "duration_seconds": target_duration,
        "scenes": balanced_scenes,
    }


def direct_walkthrough(
    user_guidance: str,
    ui_source: str | Path,
    target_duration: float = 30.0,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    The Agent Director:
    1. Inspects UI source for landmarks.
    2. Authors scenes, selectors, callouts, and narration from user guidance.
    3. Calculates speech pacing and balances the timeline.
    """
    ui_blueprint = inspect_ui_source(ui_source)
    api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")

    if not api_key:
        print("[SyncTake Agent] No LLM API key detected. Using built-in heuristic Director.")
        return fallback_director(user_guidance, ui_blueprint, target_duration)

    try:
        import urllib.request
        prompt = build_director_prompt(user_guidance, ui_blueprint, target_duration)
        endpoint = base_url or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        if not endpoint.endswith("/chat/completions"):
            endpoint = endpoint.rstrip("/") + "/chat/completions"

        req_body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4,
            "response_format": {"type": "json_object"}
        }).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=req_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            # Rebalance with pacing engine
            result["scenes"] = balance_timeline(result.get("scenes", []), target_duration)
            result["duration_seconds"] = target_duration
            return result
    except Exception as e:
        print(f"[SyncTake Agent] LLM direct call failed ({e}). Falling back to heuristic director.")
        return fallback_director(user_guidance, ui_blueprint, target_duration)


def auto_inject_client(html_path: str | Path, config_path: str = "./synctake.json") -> bool:
    """
    Automatically injects synctake.css and synctake.js before </body> in an HTML file.
    """
    path = Path(html_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"HTML file not found: {path}")

    content = path.read_text(encoding="utf-8")
    if "synctake.js" in content:
        print(f"[SyncTake Agent] Client already injected into {path.name}")
        return False

    tags = f"""
  <!-- SyncTake Automated Walkthrough Agent -->
  <link rel="stylesheet" href="./synctake.css">
  <script src="./synctake.js"></script>
  <script>SyncTake.autoInit("{config_path}");</script>
"""
    if "</body>" in content:
        new_content = content.replace("</body>", f"{tags}\n</body>")
    else:
        new_content = content + tags

    path.write_text(new_content, encoding="utf-8")
    print(f"[SyncTake Agent] Successfully injected SyncTake into {path.name}")
    return True
