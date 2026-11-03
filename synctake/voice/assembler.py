import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import soundfile as sf
import librosa
from ..schema import SyncTakeConfig


SUPPORTED_EXTS = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus")


def resample_if_needed(data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return data
    return librosa.resample(data, orig_sr=orig_sr, target_sr=target_sr)


def assemble_voiceover(
    clips_dir: str | Path,
    output_wav: str | Path,
    config: SyncTakeConfig,
    sample_rate: int = 48000,
    max_padding_warning: float = 3.0,
) -> Dict[str, Any]:
    """
    Places each scene's audio clip onto the master timeline at scene.at.
    Pads pauses with silence and ensures overall duration is exactly config.duration_seconds.
    Writes output WAV (stereo, 48kHz) and companion .timing.json file.
    """
    clips_p = Path(clips_dir).resolve()
    out_wav_p = Path(output_wav).resolve()
    out_wav_p.parent.mkdir(parents=True, exist_ok=True)
    timing_p = out_wav_p.with_suffix(".timing.json")

    total_samples = int(round(config.duration_seconds * sample_rate))
    canvas = np.zeros(total_samples, dtype=np.float32)

    scene_reports = []
    slots = config.get_slot_map()

    for scene in config.scenes:
        if not scene.text:
            scene_reports.append({
                "id": scene.id,
                "at": scene.at,
                "clip_duration": 0.0,
                "slot_duration": slots[scene.id],
                "padding": slots[scene.id],
                "status": "silent",
            })
            continue

        # Find matching clip
        matched = None
        for ext in SUPPORTED_EXTS:
            cand = clips_p / f"{scene.id}{ext}"
            if cand.is_file():
                matched = cand
                break

        if not matched:
            raise FileNotFoundError(f"No audio file found for scene '{scene.id}' in {clips_p}")

        data, sr = sf.read(str(matched))
        if data.ndim > 1:
            data = data.mean(axis=1)

        data = resample_if_needed(data, sr, sample_rate)
        clip_duration = len(data) / sample_rate
        slot_duration = slots[scene.id]

        if clip_duration > slot_duration:
            raise ValueError(
                f"Scene '{scene.id}' ({clip_duration:.2f}s) exceeds allocated slot ({slot_duration:.2f}s)!"
            )

        start_sample = int(round(scene.at * sample_rate))
        end_sample = start_sample + len(data)

        if end_sample > total_samples:
            raise ValueError(
                f"Scene '{scene.id}' ends at sample {end_sample}, exceeding canvas limit {total_samples}!"
            )

        canvas[start_sample:end_sample] = data.astype(np.float32)

        padding = round(slot_duration - clip_duration, 3)
        scene_reports.append({
            "id": scene.id,
            "at": scene.at,
            "clip_duration": round(clip_duration, 3),
            "slot_duration": slot_duration,
            "padding": padding,
            "source_clip": matched.name,
            "status": "placed",
        })

    # Convert canvas to stereo
    stereo_canvas = np.column_stack([canvas, canvas])
    sf.write(str(out_wav_p), stereo_canvas, sample_rate, subtype="PCM_16")

    output_bytes = out_wav_p.read_bytes()
    output_hash = hashlib.sha256(output_bytes).hexdigest()

    timing_report = {
        "title": config.title,
        "duration_seconds": config.duration_seconds,
        "sample_rate": sample_rate,
        "config_sha256": config.config_sha256,
        "output_sha256": output_hash,
        "scene_count": len(config.scenes),
        "scenes": scene_reports,
    }

    timing_p.write_text(json.dumps(timing_report, indent=2), encoding="utf-8")
    return timing_report
