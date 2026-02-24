#!/usr/bin/env python3
"""Update README latest-posts section from an RSS feed."""

from __future__ import annotations

import argparse
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

START_MARKER = "<!-- BLOG-POST-LIST:START -->"
END_MARKER = "<!-- BLOG-POST-LIST:END -->"


def escape_markdown(text: str) -> str:
    return text.replace("[", r"\[").replace("]", r"\]")


def format_pub_date(raw_value: str) -> str:
    if not raw_value:
        return ""

    try:
        return parsedate_to_datetime(raw_value).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return raw_value.strip()


def fetch_feed_entries(feed_url: str, max_posts: int) -> list[str]:
    request = urllib.request.Request(
        feed_url, headers={"User-Agent": "readme-rss-updater/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        feed_xml = response.read()

    root = ET.fromstring(feed_xml)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Could not find RSS channel in feed response.")

    lines: list[str] = []
    for item in channel.findall("item")[:max_posts]:
        title = escape_markdown((item.findtext("title") or "Untitled").strip())
        link = (item.findtext("link") or "").strip()
        pub_date = format_pub_date((item.findtext("pubDate") or "").strip())

        if not link:
            continue

        line = f"- [{title}]({link})"
        if pub_date:
            line += f" ({pub_date})"
        lines.append(line)

    if not lines:
        lines.append("- No posts found in RSS feed.")

    return lines


def update_readme(readme_path: Path, entries: list[str]) -> None:
    content = readme_path.read_text(encoding="utf-8")

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}", re.DOTALL
    )
    if not pattern.search(content):
        raise ValueError(
            f"README is missing markers: {START_MARKER} ... {END_MARKER}"
        )

    replacement = "\n".join([START_MARKER, *entries, END_MARKER])
    updated_content = pattern.sub(replacement, content)
    readme_path.write_text(updated_content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update README latest-posts section from RSS."
    )
    parser.add_argument(
        "--readme-path", default="README.md", help="Path to README file."
    )
    parser.add_argument(
        "--feed-url",
        default="https://www.andrefiedler.de/feed/",
        help="RSS feed URL.",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=5,
        help="Maximum number of posts to render in README.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    entries = fetch_feed_entries(args.feed_url, args.max_posts)
    update_readme(Path(args.readme_path), entries)


if __name__ == "__main__":
    main()
