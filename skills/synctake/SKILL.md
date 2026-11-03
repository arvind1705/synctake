---
name: synctake
description: Use SyncTake to plan, script, record, and voice automated video walkthroughs and demos of web applications with zero-shot voice cloning.
---

# SyncTake Coding Agent Skill

This skill empowers coding agents (Claude Code, Cursor, Antigravity, OpenCode, Codex) to autonomously produce polished, narrated video walkthroughs of web applications.

## When to Use This Skill

Activate this workflow when the user asks to:
- *"Create a demo video / walkthrough of this project / feature"*
- *"Record a narrated video showing the new dashboard / signup flow"*
- *"Make a 30s/60s video showcasing the app in my voice"*
- *"Generate a video presentation for our launch / submission"*

---

## 5-Step Agent Production Pipeline

```
[1. Inspect Codebase & UI] ──> [2. Author Script & synctake.json] ──> [3. Capture Screen] ──> [4. Synthesize Voice] ──> [5. Mux Video]
```

### Step 1: Inspect Codebase & UI Landmarks
1. Search the workspace for routes, components, and HTML views (e.g. `src/`, `pages/`, `app/`, `public/index.html`).
2. Identify the visual landmarks you want to feature:
   - Header, navigation, or hero sections (`#hero`, `header`)
   - Interactive components, forms, buttons (`#deploy-btn`, `button[type='submit']`)
   - Cards, metrics, or graphs (`[data-testid='metrics']`, `.analytics-card`)
3. Alternatively, run the built-in UI inspector:
   ```bash
   synctake plan <path-to-html> --prompt "<user guidance>" --duration <seconds>
   ```

### Step 2: Author the Walkthrough Specification (`synctake.json`)
Create `synctake.json` in the project root.

**Rules for Natural Pacing:**
- **Words-Per-Minute:** Target **140–150 WPM** (~2.4 words per second). A 10-second scene should contain roughly 20–24 words.
- **Scene Timestamps (`at`):** Must be strictly increasing.
- **On-Screen Callout:** Keep `title` and `callout` short and punchy (they appear as floating badges).
- **Focus:** Use valid CSS selectors (`#id`, `.class`, `[data-testid='...']`).

```json
{
  "title": "Feature Walkthrough",
  "duration_seconds": 30,
  "voice": {
    "provider": "mlx",
    "reference_audio": "./voice-sample.wav"
  },
  "scenes": [
    {
      "id": "01-intro",
      "at": 0.0,
      "title": "Overview",
      "callout": "Live health metrics and telemetry",
      "focus": "#metrics-card",
      "text": "Welcome! In this walkthrough, we'll demonstrate how real-time telemetry tracks cluster health across regions."
    },
    {
      "id": "02-action",
      "at": 14.5,
      "title": "Instant Action",
      "callout": "Verified deployment with zero downtime",
      "focus": "#deploy-btn",
      "text": "With a single click, our automated pipeline validates configuration changes and applies rolling updates."
    }
  ]
}
```

### Step 3: Capture the Screen Recording
Choose between automated headless capture or user-interactive capture:

#### Option A: Fully Automated (Playwright)
Run the headless capture command:
```bash
synctake capture --url http://localhost:3000 --config synctake.json --out build/capture.webm
```

#### Option B: User-Interactive (In-Browser Tab Capture)
Inject the floating recorder into the frontend:
```bash
synctake inject ./public/index.html --config ./synctake.json
```
Prompt the user:
> *"I've injected the SyncTake recorder into your app at http://localhost:3000. Click **Record Take** and select this tab. The tour will run automatically and download `synctake-take.webm`."*

### Step 4: Synthesize Zero-Shot Voiceover
Run the timeline voice generator:
```bash
# Using a reference audio sample for voice cloning:
synctake voice synctake.json --ref-audio ./voice-sample.wav --out build/voice

# Or test instantly with synthetic speech tone (no GPU needed):
synctake voice synctake.json --mock --out build/voice
```
*Note: If speech in any scene exceeds its slot, SyncTake will warn you with the exact second overrun so you can trim words.*

### Step 5: Mux into Final MP4 Video
Convert the WebM capture to calibrated 1080p and mux with the assembled voiceover:
```bash
# 1. Convert WebM to 1080p H.264
synctake export-video build/capture.webm synctake.json --out build/visual.mp4

# 2. Lossless mux with AAC audio
synctake combine build/visual.mp4 build/voice/voiceover.wav synctake.json --out demo.mp4
```

Deliver `demo.mp4` to the user!
