import contextlib
import io
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import update_readme_from_rss as updater


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload


class UpdateReadmeFromRssTests(unittest.TestCase):
    def test_fetch_feed_entries_retries_timeout_and_succeeds(self) -> None:
        feed_xml = textwrap.dedent(
            """\
            <rss>
              <channel>
                <item>
                  <title>Hello</title>
                  <link>https://example.com/post</link>
                  <pubDate>Tue, 01 Apr 2026 12:00:00 +0000</pubDate>
                </item>
              </channel>
            </rss>
            """
        ).encode("utf-8")
        timeout_error = urllib.error.URLError(TimeoutError("timed out"))

        with mock.patch(
            "update_readme_from_rss.urllib.request.urlopen",
            side_effect=[timeout_error, FakeResponse(feed_xml)],
        ) as urlopen, mock.patch("update_readme_from_rss.time.sleep") as sleep:
            entries = updater.fetch_feed_entries("https://example.com/feed.xml", 1)

        self.assertEqual(
            entries, ["- [Hello](https://example.com/post) (2026-04-01)"]
        )
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(5)

    def test_main_keeps_existing_readme_when_feed_fetch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            readme_path = Path(tmpdir) / "README.md"
            original = textwrap.dedent(
                """\
                # Demo

                <!-- BLOG-POST-LIST:START -->
                - Existing post
                <!-- BLOG-POST-LIST:END -->
                """
            )
            readme_path.write_text(original, encoding="utf-8")
            stderr = io.StringIO()

            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "update_readme_from_rss.py",
                        "--readme-path",
                        str(readme_path),
                        "--feed-url",
                        "https://example.com/feed.xml",
                    ],
                ),
                mock.patch(
                    "update_readme_from_rss.urllib.request.urlopen",
                    side_effect=urllib.error.URLError(TimeoutError("timed out")),
                ),
                mock.patch("update_readme_from_rss.time.sleep"),
                contextlib.redirect_stderr(stderr),
            ):
                updater.main()

            self.assertEqual(readme_path.read_text(encoding="utf-8"), original)
            self.assertIn("Skipping README update", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
