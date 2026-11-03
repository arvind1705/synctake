import sys
import json
import argparse
import shutil
from pathlib import Path

from .schema import SyncTakeConfig
from .cues import generate_cues
from .voice.generator import generate_clips
from .voice.preparer import prepare_clips
from .voice.assembler import assemble_voiceover
from .video.exporter import export_video
from .video.combiner import combine_video_audio
from .agent.director import direct_walkthrough, auto_inject_client


def cmd_plan(args):
    """Agent Director: inspects UI and generates walkthrough from user guidance."""
    print(f"[SyncTake Agent] Inspecting UI source: {args.ui}...")
    plan = direct_walkthrough(
        user_guidance=args.prompt,
        ui_source=args.ui,
        target_duration=args.duration,
    )

    out_file = Path(args.out).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    print(f"[SyncTake Agent] Generated plan saved to: {out_file}")
    print(f"  • Title: {plan.get('title')}")
    print(f"  • Duration: {plan.get('duration_seconds')}s")
    print(f"  • Scenes: {len(plan.get('scenes', []))}")
    for s in plan.get("scenes", []):
        print(f"    - [{s.get('at'):.1f}s] {s.get('id')}: focus='{s.get('focus')}' -> \"{s.get('title')}\"")

    if args.inject and Path(args.ui).is_file():
        # Copy client files next to HTML
        client_dir = Path(__file__).resolve().parent / "client"
        dest_dir = Path(args.ui).parent
        shutil.copy(client_dir / "synctake.js", dest_dir / "synctake.js")
        shutil.copy(client_dir / "synctake.css", dest_dir / "synctake.css")
        auto_inject_client(args.ui, config_path=f"./{out_file.name}")


def cmd_inject(args):
    """Injects SyncTake player into an existing HTML file."""
    client_dir = Path(__file__).resolve().parent / "client"
    dest_dir = Path(args.html).parent
    shutil.copy(client_dir / "synctake.js", dest_dir / "synctake.js")
    shutil.copy(client_dir / "synctake.css", dest_dir / "synctake.css")
    auto_inject_client(args.html, config_path=args.config)


def cmd_init(args):
    dest = Path(args.dest or ".").resolve()
    dest.mkdir(parents=True, exist_ok=True)

    sample_config = {
        "title": "My Product Walkthrough",
        "duration_seconds": 30,
        "voice": {
            "provider": "mlx",
            "reference_audio": "./voice-reference.wav",
            "reference_text": "Hello, this is a test reference of my voice."
        },
        "scenes": [
            {
                "id": "01-welcome",
                "at": 0.0,
                "title": "Welcome to SyncTake",
                "callout": "Automated, perfectly synchronized product walkthroughs",
                "focus": "#hero-section",
                "text": "Welcome! In this quick walkthrough, we'll show you how easily you can build product tours driven by code."
            },
            {
                "id": "02-features",
                "at": 10.5,
                "title": "Key Features",
                "callout": "Zero-shot voice cloning with perfect timeline sync",
                "focus": "#features-grid",
                "text": "Every scene is locked to a specific timestamp, guaranteeing zero audio drift and effortless re-takes."
            },
            {
                "id": "03-cta",
                "at": 20.0,
                "title": "Get Started",
                "callout": "Open-source and developer-first",
                "focus": "#cta-box",
                "text": "Try it on your own web application today and create high-production demo videos in minutes."
            }
        ]
    }

    cfg_file = dest / "synctake.json"
    cfg_file.write_text(json.dumps(sample_config, indent=2), encoding="utf-8")

    # Copy client assets
    client_dir = Path(__file__).resolve().parent / "client"
    shutil.copy(client_dir / "synctake.js", dest / "synctake.js")
    shutil.copy(client_dir / "synctake.css", dest / "synctake.css")

    # Write a clean demo index.html
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SyncTake Demo Showcase</title>
  <link rel="stylesheet" href="synctake.css">
  <style>
    body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
    .container { max-width: 800px; margin: 0 auto; }
    .card { background: #1e293b; padding: 24px; border-radius: 12px; margin-bottom: 24px; border: 1px solid #334155; }
    h1 { color: #60a5fa; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card" id="hero-section">
      <h1>SyncTake Demo</h1>
      <p>This is a sample application showing automatic screen tour navigation and recording.</p>
    </div>
    <div class="card" id="features-grid">
      <h2>Synchronized Features</h2>
      <p>Automatic tab capture • Zero-shot local voice cloning • Lossless MP4 muxing</p>
    </div>
    <div class="card" id="cta-box">
      <h2>Ready to Build?</h2>
      <p>Use the floating controller at the bottom right to preview or record!</p>
    </div>
  </div>
  <script src="synctake.js"></script>
  <script>
    SyncTake.autoInit("./synctake.json");
  </script>
</body>
</html>
"""
    (dest / "index.html").write_text(html_content, encoding="utf-8")
    print(f"[SyncTake] Initialized starter project at: {dest}")
    print("Files created:")
    print("  • synctake.json  (Walkthrough scenes & timeline)")
    print("  • synctake.js    (Browser overlay & recorder)")
    print("  • synctake.css   (Callout styling)")
    print("  • index.html     (Showcase web app)")


def cmd_cues(args):
    config = SyncTakeConfig.load(args.config)
    res = generate_cues(config, args.out)
    print(f"[SyncTake] Generated cue sheets in {args.out}:")
    print(f"  • Script:   {res['markdown']}")
    print(f"  • CSV:      {res['csv']}")
    print(f"  • Sections: {res['sections_dir']}")


def cmd_voice(args):
    config = SyncTakeConfig.load(args.config)
    work_dir = Path(args.out).resolve()
    raw_dir = work_dir / "raw"
    clips_dir = work_dir / "clips"
    out_wav = work_dir / "voiceover.wav"

    print("[SyncTake] Step 1/3: Generating scene narration...")
    generate_clips(
        config=config,
        output_raw_dir=raw_dir,
        reference_audio=args.ref_audio,
        reference_text=args.ref_text,
        only_scenes=args.only.split(",") if args.only else None,
        force=args.force,
        mock=args.mock,
    )

    print("[SyncTake] Step 2/3: Trimming, leveling and verifying slots...")
    prepare_clips(raw_dir=raw_dir, clips_dir=clips_dir, config=config)

    print("[SyncTake] Step 3/3: Assembling master timeline audio...")
    report = assemble_voiceover(clips_dir=clips_dir, output_wav=out_wav, config=config)
    print(f"[SyncTake] Master voiceover assembled: {out_wav} ({report['duration_seconds']}s)")


def cmd_export_video(args):
    config = SyncTakeConfig.load(args.config)
    out = export_video(
        source_webm=args.webm,
        output_mp4=args.out,
        config=config,
        pad_tail=args.pad_tail,
        force=args.force,
    )
    print(f"[SyncTake] 1080p visual track exported: {out}")


def cmd_combine(args):
    config = SyncTakeConfig.load(args.config)
    out = combine_video_audio(
        video_path=args.video,
        voiceover_path=args.voiceover,
        output_path=args.out,
        config=config,
        force=args.force,
        check_timing_hash=not args.no_hash_check,
    )
    print(f"[SyncTake] Final video created successfully: {out}")


def main():
    parser = argparse.ArgumentParser(
        prog="synctake",
        description="SyncTake: Agent-First Walkthrough-as-Code — UI understanding, script generation, and synchronized recording.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # plan (Agent Director)
    p_plan = subparsers.add_parser("plan", help="Agent Director: inspect UI and generate walkthrough from user guidance")
    p_plan.add_argument("ui", help="Path to local HTML file or project directory")
    p_plan.add_argument("--prompt", required=True, help="User instructions / intent for the demo video")
    p_plan.add_argument("--duration", type=float, default=30.0, help="Target total duration in seconds (default: 30)")
    p_plan.add_argument("--out", default="./synctake.json", help="Output path for generated synctake.json")
    p_plan.add_argument("--inject", action="store_true", help="Auto-inject synctake.js and css into the HTML file")
    p_plan.set_defaults(func=cmd_plan)

    # inject
    p_inj = subparsers.add_parser("inject", help="Inject SyncTake client recorder into an HTML file")
    p_inj.add_argument("html", help="Path to target HTML file")
    p_inj.add_argument("--config", default="./synctake.json", help="Path to synctake.json configuration")
    p_inj.set_defaults(func=cmd_inject)

    # init
    p_init = subparsers.add_parser("init", help="Scaffold a new SyncTake walkthrough project")
    p_init.add_argument("dest", nargs="?", default=".", help="Target directory (default: current directory)")
    p_init.set_defaults(func=cmd_init)

    # cues
    p_cues = subparsers.add_parser("cues", help="Generate Markdown script and CSV cue sheets from config")
    p_cues.add_argument("config", help="Path to synctake.json")
    p_cues.add_argument("--out", default="./cues", help="Output directory for cues and scripts")
    p_cues.set_defaults(func=cmd_cues)

    # voice
    p_voice = subparsers.add_parser("voice", help="Generate, prepare, and assemble timeline narration")
    p_voice.add_argument("config", help="Path to synctake.json")
    p_voice.add_argument("--ref-audio", default=None, help="Reference audio sample for voice cloning")
    p_voice.add_argument("--ref-text", default=None, help="Exact transcript of the reference sample")
    p_voice.add_argument("--out", default="./build/voice", help="Output directory")
    p_voice.add_argument("--only", default=None, help="Comma-separated scene IDs for selective re-takes")
    p_voice.add_argument("--force", action="store_true", help="Overwrite existing clips")
    p_voice.add_argument("--mock", action="store_true", help="Generate synthetic test audio without GPU model")
    p_voice.set_defaults(func=cmd_voice)

    # export-video
    p_exp = subparsers.add_parser("export-video", help="Convert recorded WebM to calibrated 1080p MP4")
    p_exp.add_argument("webm", help="Path to downloaded screen recording (.webm)")
    p_exp.add_argument("config", help="Path to synctake.json")
    p_exp.add_argument("--out", default="./build/visual.mp4", help="Output path for calibrated MP4")
    p_exp.add_argument("--pad-tail", type=float, default=0.5, help="Seconds to freeze final frame before clamp")
    p_exp.add_argument("--force", action="store_true", help="Overwrite existing video")
    p_exp.set_defaults(func=cmd_export_video)

    # combine
    p_comb = subparsers.add_parser("combine", help="Mux calibrated video and assembled voiceover into final MP4")
    p_comb.add_argument("video", help="Calibrated video MP4")
    p_comb.add_argument("voiceover", help="Assembled voiceover WAV")
    p_comb.add_argument("config", help="Path to synctake.json")
    p_comb.add_argument("--out", default="./build/final.mp4", help="Output path for final MP4")
    p_comb.add_argument("--no-hash-check", action="store_true", help="Skip SHA256 timing hash validation")
    p_comb.add_argument("--force", action="store_true", help="Overwrite existing video")
    p_comb.set_defaults(func=cmd_combine)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
