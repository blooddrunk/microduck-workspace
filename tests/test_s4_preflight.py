import tempfile
import unittest
from pathlib import Path

from scripts.check_s4_environment import verify_snapshot_manifest


class SnapshotManifestTests(unittest.TestCase):
    def test_valid_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = root / "policy.onnx"
            payload.write_bytes(b"fixture")
            import hashlib

            digest = hashlib.sha256(b"fixture").hexdigest()
            (root / "SHA256SUMS").write_text(f"{digest}  policy.onnx\n", encoding="utf-8")
            result = verify_snapshot_manifest(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["checked_files"], 1)

    def test_missing_or_tampered_file_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "SHA256SUMS").write_text(f"{'0' * 64}  missing.bin\n", encoding="utf-8")
            result = verify_snapshot_manifest(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("missing file: missing.bin", result["failures"])


if __name__ == "__main__":
    unittest.main()
