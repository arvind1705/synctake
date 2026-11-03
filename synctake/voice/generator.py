import sys
import os
import time
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
import numpy as np
import soundfile as sf
from ..schema import SyncTakeConfig


DEFAULT_MLX_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16"
DEFAULT_SYSTEM_VOICE = "Samantha"  # macOS natural voice


def generate_system_clip(text: str, voice_name: str = DEFAULT_SYSTEM_VOICE) -> tuple[np.ndarray, int]:
    """Generates real spoken English audio using the system TTS engine (macOS 'say' or Linux 'espeak')."""
    if shutil.which("say"):
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            cmd = ["say"]
            if voice_name:
                cmd.extend(["-v", voice_name])
            cmd.extend(["-o", tmp_path, text])
            subprocess.run(cmd, check=True)
            data, sr = sf.read(tmp_path)
            return np.array(data, dtype=np.float32), sr
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    elif shutil.which("espeak-ng") or shutil.which("espeak"):
        exe = shutil.which("espeak-ng") or shutil.which("espeak")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.run([exe, "-w", tmp_path, text], check=True)
            data, sr = sf.read(tmp_path)
            return np.array(data, dtype=np.float32), sr
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    else:
        raise RuntimeError("No system speech synthesizer ('say' or 'espeak') found.")


def generate_mock_clip(text: str, duration: float, sample_rate: int = 24000) -> np.ndarray:
    """Generates a soft harmonic tone indicating synthetic test speech."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    freq = 220.0 + 30.0 * np.sin(2 * np.pi * 3.0 * t)
    audio = 0.15 * np.sin(2 * np.pi * freq * t)
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
    voice_name: Optional[str] = None,
    only_scenes: Optional[List[str]] = None,
    force: bool = False,
    mock: bool = False,
) -> dict:
    """
    Generates narration clips for configured scenes.
    - If reference_audio is provided: uses Apple Silicon MLX zero-shot voice cloning.
    - Otherwise (default): uses natural system speech synthesis (macOS 'say' / Linux).
    - If mock=True: generates test tone.
    """
    out_dir = Path(output_raw_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    slots = config.get_slot_map()
    wanted_ids = set(only_scenes) if only_scenes else {s.id for s in config.scenes}
    results = {}
    use_mlx = False
    model = None

    if reference_audio and not mock:
        try:
            from mlx_audio.tts.utils import load_model  # type: ignore
            print(f"[SyncTake Voice] Loading MLX TTS model for voice cloning: {model_name}...")
            model = load_model(model_name)
            use_mlx = True
        except (ImportError, Exception) as e:
            print(f"[SyncTake Voice] MLX TTS not available ({e}). Using system speech synthesis.")

    for scene in config.scenes:
        if scene.id not in wanted_ids:
            continue
        if not scene.text:
            continue

        clip_dest = out_dir / f"{scene.id}.wav"
        if clip_dest.exists() and not force:
            print(f"[SyncTake Voice] Skipping existing clip: {clip_dest.name} (use force=True to overwrite)")
            results[scene.id] = str(clip_dest)
            continue

        print(f"[SyncTake Voice] Synthesizing scene '{scene.id}' (slot: {scene.duration:.2f}s)...")

        if mock:
            word_count = len(scene.text.split())
            est_duration = min(scene.duration - 0.2, max(1.0, word_count / 2.5))
            audio = generate_mock_clip(scene.text, est_duration)
            sr = 24000
            sf.write(str(clip_dest), audio, sr)
        elif use_mlx and model:
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
        else:
            # Natural system speech synthesis
            try:
                selected_voice = voice_name or DEFAULT_SYSTEM_VOICE
                audio, sr = generate_system_clip(scene.text, voice_name=selected_voice)
                sf.write(str(clip_dest), audio, sr)
            except Exception as e:
                print(f"[SyncTake Voice Warning] System speech failed ({e}). Falling back to mock tone.")
                word_count = len(scene.text.split())
                est_duration = min(scene.duration - 0.2, max(1.0, word_count / 2.5))
                audio = generate_mock_clip(scene.text, est_duration)
                sf.write(str(clip_dest), audio, 24000)

        results[scene.id] = str(clip_dest)

    return results
