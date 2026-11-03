import subprocess
from pathlib import Path
from typing import Optional
import imageio_ffmpeg
from ..schema import SyncTakeConfig


def export_video(
    source_webm: str | Path,
    output_mp4: str | Path,
    config: SyncTakeConfig,
    pad_tail: float = 0.0,
    force: bool = False,
) -> Path:
    """
    Converts a captured silent screen recording (.webm) into a standard 1080p 30fps H.264 MP4.
    Preserves aspect ratio with letterboxing and clamps duration to config.duration_seconds.
    """
    src = Path(source_webm).resolve()
    out = Path(output_mp4).resolve()

    if not src.is_file():
        raise FileNotFoundError(f"Source recording does not exist: {src}")
    if out.exists() and not force:
        raise FileExistsError(f"Output file already exists: {out}. Choose a new path or set force=True.")

    out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    video_filter = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x111116,setsar=1"
    )
    if pad_tail > 0:
        video_filter += f",tpad=stop_mode=clone:stop_duration={pad_tail}"

    cmd = [
        ffmpeg, "-hide_banner", "-y" if force else "-n",
        "-i", str(src),
        "-map", "0:v:0",
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-t", str(config.duration_seconds),
        "-movflags", "+faststart",
        str(out),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg video export failed:\n{res.stderr}")

    return out
