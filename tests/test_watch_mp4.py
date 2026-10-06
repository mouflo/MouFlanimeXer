import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mouflanimexer as m


class WatchMp4Seed(unittest.TestCase):
    def test_mp4_existants_connus_au_premier_passage(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "Serie" / "Specials"
            root.mkdir(parents=True)
            old = root / "ep1.mp4"
            old.write_bytes(b"x")
            os.utime(old, (1000, 1000))
            saved = (m.SONARR_WATCH_DIRS, m.SONARR_STATE_PATH, m.WATCH_MP4, m.WORK_ROOT, m.WATCH_LOCK_PATH, m.SONARR_FAIL_PATH)
            calls = []
            try:
                m.SONARR_WATCH_DIRS = [Path(t)]
                m.SONARR_STATE_PATH = Path(t) / "state.json"
                m.WATCH_LOCK_PATH = Path(t) / "w.lock"
                m.SONARR_FAIL_PATH = Path(t) / "f.json"
                m.WATCH_MP4 = True
                m.WORK_ROOT = Path(t)
                orig = m.auto_process_file
                m.auto_process_file = lambda *a, **k: calls.append(a) or ("done", "ok", None)
                m.run_sonarr_watch_once()
                m.auto_process_file = orig
                self.assertEqual(calls, [])
                self.assertIn(str(old), m._load_sonarr_state())
            finally:
                (m.SONARR_WATCH_DIRS, m.SONARR_STATE_PATH, m.WATCH_MP4, m.WORK_ROOT, m.WATCH_LOCK_PATH, m.SONARR_FAIL_PATH) = saved


if __name__ == "__main__":
    unittest.main()
