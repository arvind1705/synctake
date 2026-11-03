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
from synctake.agent.inspector import inspect_html
from synctake.agent.pacing import estimate_speech_duration, balance_timeline
from synctake.agent.director import direct_walkthrough, auto_inject_client


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
        self.assertEqual(data.shape[1], 2)
        expected_samples = int(10.0 * 48000)
        self.assertEqual(len(data), expected_samples)
        self.assertEqual(report["duration_seconds"], 10.0)

    def test_agent_inspector_and_pacing(self):
        sample_html = """
        <html>
          <body>
            <header id="main-nav"><h1>Acme Cloud</h1></header>
            <main>
              <section id="metrics-card"><h2>Live Health</h2></section>
              <button id="deploy-btn">Deploy</button>
            </main>
          </body>
        </html>
        """
        blueprint = inspect_html(sample_html)
        selectors = [el["selector"] for el in blueprint["landmarks"]]
        self.assertIn("#main-nav", selectors)
        self.assertIn("#metrics-card", selectors)
        self.assertIn("#deploy-btn", selectors)

        # Test Pacing
        text = "Welcome to Acme Cloud. We provide instant deployments."
        dur = estimate_speech_duration(text)
        self.assertGreater(dur, 2.0)

    def test_agent_director_and_auto_inject(self):
        sample_html_file = self.dir / "app.html"
        sample_html_file.write_text("<html><body><div id='hero'>Hello</div></body></html>", encoding="utf-8")

        # 1. Direct walkthrough from guidance
        plan = direct_walkthrough(
            user_guidance="Give a 20-second product tour showing the hero section",
            ui_source=sample_html_file,
            target_duration=20.0,
        )
        self.assertEqual(plan["duration_seconds"], 20.0)
        self.assertTrue(len(plan["scenes"]) >= 2)

        # 2. Auto-inject client into HTML
        injected = auto_inject_client(sample_html_file, config_path="./synctake.json")
        self.assertTrue(injected)
        content = sample_html_file.read_text(encoding="utf-8")
        self.assertIn("synctake.js", content)
        self.assertIn("synctake.css", content)


if __name__ == "__main__":
    unittest.main()
