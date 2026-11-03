import sys
import time
import argparse
from pathlib import Path
from typing import List, Optional
import numpy as np
import soundfile as sf
from ..schema import SyncTakeConfig


DEFAULT_MLX_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16"


def generate_mock_clip(text: str, duration: float, sample_rate: int = 24000) -> np.ndarray:
    """Generates a soft pleasant harmonic tone indicating synthetic test speech."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Gentle modulated carrier simulating voice formant frequencies
    freq = 220.0 + 30.0 * np.sin(2 * np.pi * 3.0 * t)
    audio = 0.15 * np.sin(2 * np.pi * freq * t)
    # Apply fade in / fade out
    envelope = np.ones_like(audio)
    fade = int(sample_rate * 0.05)
    if len(audio) > 2 * fade:
        envelope[:fade] = np.linspace(0, 1, fade)
        envelope[-fade:] = np.linspace(1, 0, fade)
    return (audio * envelope).astype(np.float32)


def generate_clips(
    config: SyncTakeConfig,
    output_raw_dir: str | Path,
    reference_audio: Optional[str | Path] = None,
    reference_text: Optional[str] = None,
    model_name: str = DEFAULT_MLX_MODEL,
    only_scenes: Optional[List[str]] = None,
    force: bool = False,
    mock: bool = False,
) -> dict:
    """
    Generates zero-shot narration clips for configured scenes.
    Uses MLX on Apple Silicon if available, or mock mode for fast local verification.
    """
    out_dir = Path(output_raw_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    slots = config.get_slot_map()
    wanted_ids = set(only_scenes) if only_scenes else {s.id for s in config.scenes}
    results = {}

    if not mock:
        try:
            from mlx_audio.tts.utils import load_model  # type: ignore
            print(f"[SyncTake] Loading MLX TTS model: {model_name}...")
            model = load_model(model_name)
        except (ImportError, Exception) as e:
            print(f"[SyncTake] MLX TTS not available ({e}). Falling back to mock generator.")
            mock = True

    for scene in config.scenes:
        if scene.id not in wanted_ids:
            continue
        if not scene.text:
            continue

        clip_dest = out_dir / f"{scene.id}.wav"
        if clip_dest.exists() and not force:
            print(f"[SyncTake] Skipping existing clip: {clip_dest.name} (use force=True to overwrite)")
            results[scene.id] = str(clip_dest)
            continue

        print(f"[SyncTake] Synthesizing scene '{scene.id}' (slot: {scene.duration:.2f}s)...")

        if mock:
            # Estimate speech length: approx 150 words per minute ~ 2.5 words per second
            word_count = len(scene.text.split())
            est_duration = min(scene.duration - 0.2, max(1.0, word_count / 2.5))
            audio = generate_mock_clip(scene.text, est_duration)
            sr = 24000
            sf.write(str(clip_dest), audio, sr)
        else:
            # Generate via MLX TTS
            kwargs = {}
            if reference_audio and Path(reference_audio).is_file():
                kwargs["ref_audio"] = str(reference_audio)
                if reference_text:
                    kwargs["ref_text"] = reference_text
            
            output = model.generate(scene.text, **kwargs)
            audio = output.audio if hasattr(output, "audio") else output
            sr = getattr(output, "sample_rate", 24000)
            if hasattr(audio, "asnumpy"):
                audio = audio.asnumpy()
            sf.write(str(clip_dest), np.array(audio, dtype=np.float32), sr)

        results[scene.id] = str(clip_dest)

    return results
