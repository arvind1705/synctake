import math
import re
from typing import List, Dict, Any


DEFAULT_WORDS_PER_MINUTE = 145.0
WORDS_PER_SECOND = DEFAULT_WORDS_PER_MINUTE / 60.0  # ~2.42 words/sec


def count_words(text: str) -> int:
    """Accurately counts words in a script, handling punctuation and whitespace."""
    clean = re.sub(r"[^\w\s]", "", text)
    words = [w for w in clean.split() if w.strip()]
    return len(words)


def estimate_speech_duration(text: str, wpm: float = DEFAULT_WORDS_PER_MINUTE) -> float:
    """Estimates spoken duration in seconds for a given narration text."""
    words = count_words(text)
    if words == 0:
        return 0.0
    return round(words / (wpm / 60.0), 2)


def balance_timeline(scenes: List[Dict[str, Any]], target_duration: float, min_scene_pause: float = 1.0) -> List[Dict[str, Any]]:
    """
    Adjusts scene start timestamps and slot durations so speech fits comfortably
    with natural pauses and sums to the exact target duration.
    """
    if not scenes:
        return []

    # 1. Calculate raw speech durations
    speech_durations = [estimate_speech_duration(s.get("text", "")) for s in scenes]
    raw_total_speech = sum(speech_durations)

    # 2. Check if text fits inside target duration
    min_required = raw_total_speech + (len(scenes) * min_scene_pause)
    if min_required > target_duration:
        scale = target_duration / min_required
        print(
            f"[SyncTake Pacing Warning] Script has {sum(count_words(s.get('text', '')) for s in scenes)} words, "
            f"which is tight for {target_duration}s. Pacing will be dense."
        )

    # 3. Distribute time slots proportionally
    remaining_time = target_duration - raw_total_speech
    pause_per_scene = max(0.5, remaining_time / len(scenes))

    current_at = 0.0
    balanced = []

    for i, scene in enumerate(scenes):
        speech_dur = speech_durations[i]
        # Slot duration is speech duration plus fair share of padding
        slot_duration = speech_dur + pause_per_scene if i < len(scenes) - 1 else (target_duration - current_at)
        slot_duration = round(slot_duration, 2)

        balanced_scene = dict(scene)
        balanced_scene["at"] = round(current_at, 2)
        balanced.append(balanced_scene)

        current_at += slot_duration

    return balanced
