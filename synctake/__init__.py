"""
SyncTake: Walkthrough-as-Code
Automated, perfectly synchronized product walkthrough videos with zero-shot voice cloning.
"""

from .schema import SyncTakeConfig, Scene
from .cues import generate_cues
from .voice.assembler import assemble_voiceover
from .voice.preparer import prepare_clips
from .voice.generator import generate_clips
from .video.exporter import export_video
from .video.combiner import combine_video_audio

__version__ = "0.1.0"

__all__ = [
    "SyncTakeConfig",
    "Scene",
    "generate_cues",
    "generate_clips",
    "prepare_clips",
    "assemble_voiceover",
    "export_video",
    "combine_video_audio",
]
