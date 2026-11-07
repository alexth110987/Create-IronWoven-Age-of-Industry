import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from update_mod_information import classify_status, CurseForgeError, load_manifest


class CatalogueStatusTests(unittest.TestCase):
    def test_exact_latest_stable_file_matches(self):
        installed = {"id": 10, "releaseType": 1, "fileDate": "2026-01-01T00:00:00Z"}
        latest = {"id": 10, "fileDate": "2026-01-01T00:00:00Z"}
        self.assertEqual(classify_status(installed, latest), "Matches latest stable listing")

    def test_newer_stable_file_requires_review(self):
        installed = {"id": 10, "releaseType": 1, "fileDate": "2026-01-01T00:00:00Z"}
        latest = {"id": 11, "fileDate": "2026-02-01T00:00:00Z"}
        self.assertEqual(
            classify_status(installed, latest),
            "Newer stable file found — review required",
        )

    def test_different_file_without_newer_date_needs_manual_review(self):
        installed = {"id": 10, "releaseType": 1, "fileDate": "2026-03-01T00:00:00Z"}
        latest = {"id": 11, "fileDate": "2026-02-01T00:00:00Z"}
        self.assertTrue(classify_status(installed, latest).startswith("Manual review required"))

    def test_prerelease_is_never_treated_as_approved(self):
        installed = {"id": 10, "releaseType": 2}
        latest = {"id": 11, "fileDate": "2026-02-01T00:00:00Z"}
        self.assertIn("pre-release", classify_status(installed, latest))

    def test_no_stable_file_is_explicit(self):
        installed = {"id": 10, "releaseType": 1}
        self.assertEqual(
            classify_status(installed, None),
            "No stable file found for the target version and loader",
        )

    def test_manifest_requires_neoforge(self):
        import json
        import tempfile
        manifest = {
            "manifestType": "minecraftModpack",
            "minecraft": {"version": "1.21.1", "modLoaders": [{"id": "fabric-1.21.1"}]},
            "files": [{"projectID": 1, "fileID": 2, "required": True}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(CurseForgeError):
                load_manifest(path)


if __name__ == "__main__":
    unittest.main()
