"""
SyncTake: Agent-First Walkthrough-as-Code
Automated, perfectly synchronized product walkthrough videos with zero-shot voice cloning.
"""

from .schema import SyncTakeConfig, Scene
from .cues import generate_cues
from .voice.assembler import assemble_voiceover
from .voice.preparer import prepare_clips
from .voice.generator import generate_clips
from .video.exporter import export_video
from .video.combiner import combine_video_audio
from .agent.director import direct_walkthrough, auto_inject_client, build_director_prompt
from .agent.inspector import inspect_ui_source, inspect_html
from .agent.pacing import balance_timeline, estimate_speech_duration

__version__ = "0.2.0"

__all__ = [
    "SyncTakeConfig",
    "Scene",
    "generate_cues",
    "generate_clips",
    "prepare_clips",
    "assemble_voiceover",
    "export_video",
    "combine_video_audio",
    "direct_walkthrough",
    "auto_inject_client",
    "build_director_prompt",
    "inspect_ui_source",
    "inspect_html",
    "balance_timeline",
    "estimate_speech_duration",
]
