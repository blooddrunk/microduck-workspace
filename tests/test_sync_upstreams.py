"""Offline, network-free tests; no real git fetch, writes or hardware access."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sync_upstreams as upstreams  # noqa: E402


class CatalogTests(unittest.TestCase):
    def test_catalog_is_pinned_and_named(self) -> None:
        catalog = upstreams.read_catalog()
        self.assertEqual(catalog["schema_version"], 1)
        self.assertIn("hd1910-rl", {s["name"] for s in catalog["sources"]})
        self.assertIn("kissqy-runtime", {s["name"] for s in catalog["sources"]})

    def test_duplicate_source_fails(self) -> None:
        text = '{"schema_version":1,"sources":[' + (
            '{"name":"duplicate","repo":"test/example","branch":"main","sha":"' + "0" * 40 + '"},'
            '{"name":"duplicate","repo":"test/example","branch":"main","sha":"' + "1" * 40 + '"}]}'
        )
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "sources.json"
            p.write_text(text, encoding="utf-8")
            with self.assertRaises(upstreams.SyncError):
                upstreams.read_catalog(p)

    def test_unknown_source_is_rejected(self) -> None:
        catalog = upstreams.read_catalog()
        with self.assertRaises(upstreams.SyncError):
            upstreams.select_sources(catalog["sources"], ["typo"], False)

    def test_fetch_requires_explicit_selection(self) -> None:
        catalog = upstreams.read_catalog()
        with self.assertRaises(upstreams.SyncError):
            upstreams.select_sources(catalog["sources"], [], False)

    def test_remote_head_has_exact_ref(self) -> None:
        source = {"name":"demo", "repo":"test/example", "branch":"main", "sha":"a"*40}
        with patch.object(upstreams, "git", return_value="a"*40 + "\trefs/heads/main") as mocked:
            self.assertEqual(upstreams.remote_head(source), "a"*40)
            mocked.assert_called_once()
        with patch.object(upstreams, "git", return_value="a"*40 + "\trefs/heads/other"):
            with self.assertRaises(upstreams.SyncError):
                upstreams.remote_head(source)


if __name__ == "__main__":
    unittest.main()
