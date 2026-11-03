from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from ..schema import SyncTakeConfig


def trim_silence(audio: np.ndarray, sample_rate: int, threshold: float = 0.005) -> np.ndarray:
    """Trims leading and trailing silence from an audio array."""
    loud = np.where(np.abs(audio) > threshold)[0]
    if len(loud) == 0:
        return audio
    start = max(0, int(loud[0] - 0.05 * sample_rate))
    end = min(len(audio), int(loud[-1] + 0.08 * sample_rate))
    return audio[start:end]


def prepare_clips(
    raw_dir: str | Path,
    clips_dir: str | Path,
    config: SyncTakeConfig,
    target_loudness: float = -20.0,
) -> Dict[str, dict]:
    """
    Trims, levels, and validates raw scene clips against slot allocations in config.
    Returns a dictionary of per-scene clip stats.
    Fails if any clip duration exceeds its configured scene slot.
    """
    raw_p = Path(raw_dir).resolve()
    clips_p = Path(clips_dir).resolve()
    clips_p.mkdir(parents=True, exist_ok=True)

    meter = pyln.Meter(24000)
    slots = config.get_slot_map()
    results = {}

    for scene in config.scenes:
        if not scene.text:
            continue

        # Look for matching raw file with supported extensions
        raw_candidates = list(raw_p.glob(f"{scene.id}.*"))
        if not raw_candidates:
            raise FileNotFoundError(f"Missing raw audio clip for scene '{scene.id}' in {raw_p}")

        raw_file = raw_candidates[0]
        data, sr = sf.read(str(raw_file))

        # Convert to mono if needed
        if data.ndim > 1:
            data = data.mean(axis=1)

        data = trim_silence(data, sr)
        actual_duration = len(data) / sr
        allowed_slot = slots[scene.id]

        if actual_duration > allowed_slot:
            raise ValueError(
                f"Scene '{scene.id}' audio duration ({actual_duration:.2f}s) exceeds "
                f"allocated slot ({allowed_slot:.2f}s) by {actual_duration - allowed_slot:.2f}s! "
                f"Shorten the text or re-record to avoid audio overlap."
            )

        # Normalize loudness
        meter.rate = sr
        try:
            current_loudness = meter.integrated_loudness(data)
            if not np.isinf(current_loudness) and not np.isnan(current_loudness):
                data = pyln.normalize.loudness(data, current_loudness, target_loudness)
        except Exception:
            # Fallback peak normalization if audio is too short for LUFS meter
            peak = np.max(np.abs(data))
            if peak > 0:
                data = data / peak * 0.8

        out_clip_path = clips_p / f"{scene.id}.wav"
        sf.write(str(out_clip_path), data, sr)

        results[scene.id] = {
            "path": str(out_clip_path),
            "sample_rate": sr,
            "duration": actual_duration,
            "slot": allowed_slot,
            "padding": round(allowed_slot - actual_duration, 3),
        }

    return results
