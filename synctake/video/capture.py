import time
import subprocess
from pathlib import Path
from typing import Optional
from ..schema import SyncTakeConfig


def capture_walkthrough_playwright(
    url: str,
    output_webm: str | Path,
    config: SyncTakeConfig,
    headless: bool = True,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """
    Automated browser capture using Playwright.
    Launches browser, records video, executes scene navigations and callouts,
    and saves output WebM when duration_seconds is reached.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "Playwright is required for automated headless capture. "
            "Install it with: pip install playwright && playwright install chromium"
        )

    out_p = Path(output_webm).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    temp_rec_dir = out_p.parent / ".temp_recordings"
    temp_rec_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(temp_rec_dir),
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()

        print(f"[SyncTake Capture] Navigating to {url}...")
        page.goto(url, wait_until="networkidle")

        # Inject SyncTake client script and styles if not already present
        client_dir = Path(__file__).resolve().parents[1] / "client"
        js_code = (client_dir / "synctake.js").read_text(encoding="utf-8")
        css_code = (client_dir / "synctake.css").read_text(encoding="utf-8")

        page.add_style_tag(content=css_code)
        page.add_script_tag(content=js_code)

        # Inject config and start tour
        import json
        config_json = json.dumps(config.raw_config)
        page.evaluate(f"window.SyncTake.init({config_json});")

        print(f"[SyncTake Capture] Running automated walkthrough ({config.duration_seconds}s)...")
        start_time = time.time()
        scenes = config.scenes
        scene_idx = 0

        while (time.time() - start_time) < config.duration_seconds:
            elapsed = time.time() - start_time
            if scene_idx < len(scenes) and elapsed >= scenes[scene_idx].at:
                s = scenes[scene_idx]
                print(f"[SyncTake Capture] [{elapsed:.1f}s] Scene {s.id}: focus='{s.focus}'")
                if s.focus:
                    try:
                        page.locator(s.focus).first.scroll_into_view_if_needed(timeout=2000)
                    except Exception:
                        pass
                scene_idx += 1
            time.sleep(0.1)

        print("[SyncTake Capture] Walkthrough complete. Finalizing video...")
        page.close()
        context.close()
        browser.close()

        # Find the video recorded by Playwright
        videos = list(temp_rec_dir.glob("*.webm"))
        if not videos:
            raise RuntimeError("Playwright recording completed but no .webm file was found.")
        
        # Move the latest recording to out_p
        latest_video = max(videos, key=lambda f: f.stat().st_mtime)
        import shutil
        shutil.move(str(latest_video), str(out_p))
        shutil.rmtree(temp_rec_dir, ignore_errors=True)
        print(f"[SyncTake Capture] Video saved to: {out_p}")
        return out_p
