import csv
from pathlib import Path
from typing import Optional
from .schema import SyncTakeConfig


def format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"


def generate_cues(config: SyncTakeConfig, output_dir: str | Path) -> dict:
    """Generates voiceover-script.md, voiceover-cues.csv, and per-scene text files."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sections_dir = out / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate CSV
    csv_path = out / "voiceover-cues.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Scene ID", "Start (s)", "End (s)", "Duration (s)", "Title", "Callout", "Focus"])
        for s in config.scenes:
            end_at = s.at + s.duration
            writer.writerow([s.id, f"{s.at:.2f}", f"{end_at:.2f}", f"{s.duration:.2f}", s.title, s.callout, s.focus or ""])

    # 2. Generate Markdown Script
    md_path = out / "voiceover-script.md"
    md_lines = [
        f"# {config.title}",
        "",
        f"> **Total Duration:** {format_timestamp(config.duration_seconds)} ({config.duration_seconds}s) | **Scenes:** {len(config.scenes)}",
        "",
        "---",
        "",
    ]

    for i, s in enumerate(config.scenes, start=1):
        end_at = s.at + s.duration
        md_lines.extend([
            f"### Scene {i:02d}: `{s.id}`",
            f"**Cues:** `{format_timestamp(s.at)}` → `{format_timestamp(end_at)}` ({s.duration:.2f}s slot)  ",
            f"**On-screen Callout:** *{s.callout or s.title or 'N/A'}*  ",
            f"**Focus Selector:** `{s.focus or 'full-screen'}`",
            "",
            "```text",
            s.text if s.text else "[Silent / No narration]",
            "```",
            "",
        ])

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # 3. Generate Speech Section Files
    for s in config.scenes:
        if s.text:
            scene_file = sections_dir / f"{s.id}.txt"
            scene_file.write_text(s.text + "\n", encoding="utf-8")

    return {
        "csv": str(csv_path),
        "markdown": str(md_path),
        "sections_dir": str(sections_dir),
    }
