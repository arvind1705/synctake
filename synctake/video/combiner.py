import re
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Optional
import imageio_ffmpeg
from ..schema import SyncTakeConfig


def combine_video_audio(
    video_path: str | Path,
    voiceover_path: str | Path,
    output_path: str | Path,
    config: SyncTakeConfig,
    force: bool = False,
    check_timing_hash: bool = True,
) -> Path:
    """
    Combines calibrated MP4 video with assembled voiceover WAV into the final MP4.
    Performs integrity checks against timing manifests, verifies duration, and normalizes audio.
    """
    vid = Path(video_path).resolve()
    audio = Path(voiceover_path).resolve()
    out = Path(output_path).resolve()

    if not vid.is_file():
        raise FileNotFoundError(f"Missing video file: {vid}")
    if not audio.is_file():
        raise FileNotFoundError(f"Missing voiceover audio file: {audio}")
    if out.exists() and not force:
        raise FileExistsError(f"Output already exists: {out}. Use a new path or force=True.")

    out.parent.mkdir(parents=True, exist_ok=True)
    timing_file = audio.with_suffix(".timing.json")

    if check_timing_hash and timing_file.is_file():
        timing_data = json.loads(timing_file.read_text(encoding="utf-8"))
        if timing_data.get("config_sha256") != config.config_sha256:
            raise ValueError(
                "Voiceover was assembled against a different config! Re-assemble before combining."
            )
        audio_hash = hashlib.sha256(audio.read_bytes()).hexdigest()
        if timing_data.get("output_sha256") != audio_hash:
            raise ValueError("Voiceover audio file was modified after assembly! Re-assemble first.")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    # Probe video duration
    probe = subprocess.run([ffmpeg, "-hide_banner", "-i", str(vid)], capture_output=True, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):([0-9.]+)", probe.stderr)
    if match:
        actual_dur = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])
        if abs(actual_dur - config.duration_seconds) > 1.0:
            print(
                f"[SyncTake Warning] Video duration ({actual_dur:.1f}s) differs from target "
                f"({config.duration_seconds}s). It will be aligned to target duration."
            )

    cmd = [
        ffmpeg, "-hide_banner", "-y" if force else "-n",
        "-i", str(vid),
        "-i", str(audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-af", "loudnorm=I=-16:LRA=7:TP=-1.5",
        "-t", str(config.duration_seconds),
        "-movflags", "+faststart",
        str(out),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg muxing failed:\n{res.stderr}")

    return out
