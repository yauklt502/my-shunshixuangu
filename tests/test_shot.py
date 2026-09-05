import unittest
import zipfile
from io import BytesIO

from PIL import Image

from dragon.engine import analyze
from dragon.pack import build_zip
from dragon.shot import render_png
from tests.test_score import CONCEPTS, sample_rows


class ShotTest(unittest.TestCase):
    def test_png_header_and_name(self):
        result = analyze(
            sample_rows(),
            popularity={"000592": 1, "600108": 3, "001366": 8},
            concepts=CONCEPTS,
            mode="盘后",
        )
        snap = {
            "date": "20260904",
            "mode": "盘后",
            "stats": {"zt": 8},
            "watch": result["watch"].to_dict() if result["watch"] else None,
            "watch_hat": result["decision"].watch_hat,
            "reason": result["decision"].reason,
            "action": result["action"],
            "notes": result["decision"].notes,
            "mainline": result["mainline"],
            "picks": {
                "locomotive": result["decision"].locomotive.to_dict() if result["decision"].locomotive else None,
                "sentiment": result["decision"].sentiment.to_dict() if result["decision"].sentiment else None,
                "height": result["decision"].height.to_dict() if result["decision"].height else None,
            },
            "steps": result["steps"],
        }
        raw, fname = render_png(snap)
        self.assertTrue(raw.startswith(b"\x89PNG"))
        self.assertGreater(len(raw), 8000)
        self.assertIn("600108", fname)
        self.assertIn("亚盛", fname)
        img = Image.open(BytesIO(raw))
        self.assertEqual(img.getpixel((2, 2)), (255, 255, 255))

    def test_empty_watch_still_png(self):
        raw, fname = render_png({"date": "20260905", "mode": "盘后", "reason": "今日无龙", "stats": {"zt": 0}})
        self.assertTrue(raw.startswith(b"\x89PNG"))
        self.assertIn("none", fname)


class PackTest(unittest.TestCase):
    def test_zip_has_launcher(self):
        raw = build_zip()
        zf = zipfile.ZipFile(BytesIO(raw))
        names = zf.namelist()
        self.assertIn("launch.py", names)
        self.assertIn("server.py", names)
        self.assertIn("一键启动.bat", names)
        self.assertTrue(all(not n.startswith(".venv/") for n in names))
        self.assertTrue(all("/__pycache__/" not in n for n in names))


if __name__ == "__main__":
    unittest.main()
