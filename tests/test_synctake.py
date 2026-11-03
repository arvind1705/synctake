import unittest
import tempfile
import json
from pathlib import Path
import numpy as np
import soundfile as sf

from synctake.schema import SyncTakeConfig, Scene
from synctake.cues import generate_cues
from synctake.voice.assembler import assemble_voiceover
from synctake.voice.preparer import prepare_clips
from synctake.voice.generator import generate_clips


class TestSyncTake(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp_dir.name)

        self.sample_config_data = {
            "title": "Unit Test Walkthrough",
            "duration_seconds": 10.0,
            "scenes": [
                {
                    "id": "scene-01",
                    "at": 0.0,
                    "title": "Intro",
                    "callout": "Intro callout",
                    "focus": "#header",
                    "text": "Hello and welcome to this test walkthrough.",
                },
                {
                    "id": "scene-02",
                    "at": 4.5,
                    "title": "Middle",
                    "callout": "Middle callout",
                    "focus": "#main",
                    "text": "Here is the second feature.",
                },
            ],
        }
        self.config_file = self.dir / "synctake.json"
        self.config_file.write_text(json.dumps(self.sample_config_data), encoding="utf-8")
        self.config = SyncTakeConfig.load(self.config_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_schema_slots(self):
        slots = self.config.get_slot_map()
        self.assertEqual(slots["scene-01"], 4.5)
        self.assertEqual(slots["scene-02"], 5.5)
        self.assertEqual(len(self.config.scenes), 2)

    def test_cue_generation(self):
        cues_dir = self.dir / "cues"
        res = generate_cues(self.config, cues_dir)
        self.assertTrue(Path(res["csv"]).is_file())
        self.assertTrue(Path(res["markdown"]).is_file())
        self.assertTrue((cues_dir / "sections" / "scene-01.txt").is_file())

    def test_voice_mock_and_assembly(self):
        raw_dir = self.dir / "raw"
        clips_dir = self.dir / "clips"
        out_wav = self.dir / "master.wav"

        # 1. Generate mock clips
        generate_clips(self.config, raw_dir, mock=True)
        self.assertTrue((raw_dir / "scene-01.wav").is_file())
        self.assertTrue((raw_dir / "scene-02.wav").is_file())

        # 2. Prepare & Level
        prep_results = prepare_clips(raw_dir, clips_dir, self.config)
        self.assertIn("scene-01", prep_results)
        self.assertIn("scene-02", prep_results)

        # 3. Assemble onto timeline
        report = assemble_voiceover(clips_dir, out_wav, self.config, sample_rate=48000)
        self.assertTrue(out_wav.is_file())
        self.assertTrue(out_wav.with_suffix(".timing.json").is_file())

        data, sr = sf.read(str(out_wav))
        self.assertEqual(sr, 48000)
        # Check stereo
        self.assertEqual(data.shape[1], 2)
        # Check exact duration in samples
        expected_samples = int(10.0 * 48000)
        self.assertEqual(len(data), expected_samples)
        self.assertEqual(report["duration_seconds"], 10.0)


if __name__ == "__main__":
    unittest.main()
