import os
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class Scene:
    id: str
    at: float
    title: str = ""
    callout: str = ""
    focus: Optional[str] = None
    view: Optional[str] = None
    text: str = ""
    duration: float = 0.0

    @property
    def clean_text(self) -> str:
        return " ".join(self.text.split())


@dataclass
class SyncTakeConfig:
    title: str
    duration_seconds: float
    scenes: List[Scene] = field(default_factory=list)
    voice: Dict[str, Any] = field(default_factory=dict)
    raw_config: Dict[str, Any] = field(default_factory=dict)
    config_sha256: str = ""

    @classmethod
    def load(cls, config_path: str | Path) -> "SyncTakeConfig":
        path = Path(config_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")

        raw_bytes = path.read_bytes()
        config_hash = hashlib.sha256(raw_bytes).hexdigest()
        data = json.loads(raw_bytes.decode("utf-8"))

        duration = float(data.get("duration_seconds", 0))
        if duration <= 0:
            raise ValueError("duration_seconds must be a positive number")

        raw_scenes = data.get("scenes", [])
        if not raw_scenes:
            raise ValueError("Configuration must contain at least one scene")

        scenes: List[Scene] = []
        last_at = -1.0

        for i, s in enumerate(raw_scenes):
            scene_id = s.get("id")
            if not scene_id:
                raise ValueError(f"Scene at index {i} is missing an 'id'")

            at = float(s.get("at", 0.0))
            if at <= last_at and i > 0:
                raise ValueError(
                    f"Scene '{scene_id}' has timestamp {at}s, which is not strictly greater than previous {last_at}s"
                )
            if at >= duration:
                raise ValueError(
                    f"Scene '{scene_id}' starts at {at}s, exceeding total duration of {duration}s"
                )
            last_at = at

            scenes.append(
                Scene(
                    id=scene_id,
                    at=at,
                    title=s.get("title", ""),
                    callout=s.get("callout", ""),
                    focus=s.get("focus"),
                    view=s.get("view"),
                    text=s.get("text", "").strip(),
                )
            )

        # Calculate slot durations
        for i, scene in enumerate(scenes):
            next_at = scenes[i + 1].at if i + 1 < len(scenes) else duration
            scene.duration = round(next_at - scene.at, 3)

        return cls(
            title=data.get("title", "SyncTake Walkthrough"),
            duration_seconds=duration,
            scenes=scenes,
            voice=data.get("voice", {}),
            raw_config=data,
            config_sha256=config_hash,
        )

    def get_slot_map(self) -> Dict[str, float]:
        return {scene.id: scene.duration for scene in self.scenes}
