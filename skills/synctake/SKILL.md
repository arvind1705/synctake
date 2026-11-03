---
name: synctake
description: Autonomously plan, script, capture, and voice perfectly synchronized product walkthrough videos with zero audio drift.
---

# SyncTake Coding Agent Skill

This skill instructs coding agents (Claude Code, Cursor, Antigravity, OpenCode, Codex) on how to autonomously produce polished, narrated video walkthroughs of web applications.

---

## 🎯 When to Activate This Skill

Activate this workflow whenever the user requests:
- *"Create a demo video / walkthrough of this project / feature"*
- *"Record a video showing how the app works"*
- *"Make a 30s/60s walkthrough video of this new UI"*
- *"Showcase this feature in video with narration"*

---

## 🛠️ Step 0: Environment & Dependency Check

Before running the workflow, verify the necessary tools are installed:

1. **Verify SyncTake CLI:**
   ```bash
   synctake --help || pip install -e /path/to/synctake
   ```
2. **Verify Playwright (for autonomous headless capture):**
   ```bash
   python -c "import playwright" 2>/dev/null || (pip install playwright && playwright install chromium)
   ```

---

## 📋 The 5-Step Autonomous Agent Playbook

```
[1. Inspect UI] ──> [2. Author synctake.json] ──> [3. Start Dev Server] ──> [4. Run Autonomous Pipeline] ──> [5. Deliver Video]
```

### Step 1: Inspect Codebase & UI Landmarks
1. Search the workspace for routes, components, and HTML views (e.g. `src/`, `pages/`, `app/`, `public/index.html`).
2. Identify the key visual landmarks for the video:
   - Header, navigation, hero (`#hero`, `header`, `.brand`)
   - Interactive components, forms, buttons (`#deploy-btn`, `button[type='submit']`, `select`)
   - Cards, metrics, graphs (`[data-testid='metrics']`, `.card`, `.recommendation-grid`)
3. Alternatively, run the built-in UI inspector:
   ```bash
   synctake plan ./public/index.html --prompt "<user guidance>" --duration <seconds>
   ```

---

### Step 2: Author the Walkthrough Specification (`synctake.json`)
Create `synctake.json` in the project root.

**Pacing & Scripting Rules:**
- **Words-Per-Minute:** Target **140–150 WPM** (~2.4 words per second). A 10-second scene should contain roughly 20–24 words.
- **Scene Timestamps (`at`):** Must be strictly increasing.
- **On-Screen Callout:** Keep `title` and `callout` short and punchy (they appear as native floating cards).
- **Focus:** Use real, valid CSS selectors (`#id`, `.class`, `[data-testid='...']`).
- **Narration:** Write natural, conversational speech. Never read raw code symbols, selectors, or timestamps aloud.

```json
{
  "title": "Feature Walkthrough",
  "duration_seconds": 30.0,
  "voice": {
    "provider": "system"
  },
  "scenes": [
    {
      "id": "01-overview",
      "at": 0.0,
      "title": "Live Cluster Overview",
      "callout": "Real-time health and telemetry metrics across regions",
      "focus": "#metrics-card",
      "text": "Welcome! In this walkthrough, we will explore real-time cluster health and automated remediation."
    },
    {
      "id": "02-actions",
      "at": 12.0,
      "title": "One-Click Deployments",
      "callout": "Automated validation with human approval",
      "focus": "#deploy-btn",
      "text": "With a single click, our pipeline validates configuration changes and applies rolling updates."
    }
  ]
}
```

---

### Step 3: Ensure Dev Server is Running
Check if the web application's dev server is already listening on a local port:
```bash
lsof -i :3000 -i :5173 -i :8000 || true
```
If not running, launch it in the background:
- For static HTML: `python3 -m http.server 5173 --bind 127.0.0.1`
- For Vite: `npm run dev`
- For Next.js: `npm run dev`

---

### Step 4: Run the Autonomous Pipeline

Run the all-in-one autonomous execution command:

```bash
synctake run \
  --url http://127.0.0.1:5173 \
  --config ./synctake.json \
  --out ./demo.mp4
```

*If the user provided a voice reference clip (e.g. `voice.wav`), pass `--ref-audio ./voice.wav` to clone their voice.*

**What `synctake run` does automatically:**
1. **Headless Screen Capture:** Launches Chromium via Playwright, steps through scene cues, highlights elements with host-adaptive focus rings, shows native callout badges, and saves calibrated WebM.
2. **Speech Synthesis:** Synthesizes clear spoken English (or clones the user's voice).
3. **Pacing & Slot Validation:** Verifies no audio clip exceeds its allocated scene duration.
4. **Master Canvas Assembly:** Places clips at exact cues, fills pauses with digital silence, and outputs calibrated 48 kHz stereo audio.
5. **Lossless Muxing:** Normalizes audio to broadcast standard (-16 LUFS) and muxes into 1080p H.264 MP4 with zero generational video loss.

---

### Step 5: Deliver the Finished Video

Once `synctake run` completes:
1. Verify the output video exists and is non-empty (`ls -lh ./demo.mp4`).
2. Present the finished video deliverable to the user with its absolute file path link:
   > *"Here is your completed walkthrough video: [demo.mp4](file:///path/to/demo.mp4)!"*
