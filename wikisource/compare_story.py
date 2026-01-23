#!/usr/bin/env python3
"""Download a Wikisource story, normalize it against repo XHTML, and report diffs."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, List, Optional
from itertools import zip_longest
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from difflib import SequenceMatcher


REPO_ROOT = Path(__file__).resolve().parents[1]
WIKISOURCE_URLS = REPO_ROOT / "wikisource" / "wikisource_urls.json"
DEFAULT_REPORT_DIR = REPO_ROOT / "wikisource" / "reports"
DEFAULT_DOWNLOAD_DIR = REPO_ROOT / "wikisource" / "downloads"
DEFAULT_TEXTS_DIR = REPO_ROOT / "wikisource" / "texts"
DEFAULT_NORMALIZED_DIR = REPO_ROOT / "wikisource" / "normalized"


class TextExtractor(HTMLParser):
    """Extract text from HTML while preserving spacing between block elements."""

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: List[str] = []
        self.in_style_or_script = False

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self.in_style_or_script = True

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.in_style_or_script = False
        if tag in {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self.in_style_or_script:
            self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts)


class WikisourceExtractor(HTMLParser):
    """Extract text from Wikisource HTML within a target container class."""

    def __init__(self, target_classes: Iterable[str]) -> None:
        super().__init__()
        self.target_classes = set(target_classes)
        self.text_parts: List[str] = []
        self.in_style_or_script = False
        self.capture_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self.in_style_or_script = True
        attrs_dict = dict(attrs)
        if tag == "div":
            class_attr = attrs_dict.get("class", "")
            classes = set(class_attr.split()) if isinstance(class_attr, str) else set(class_attr or [])
            if self.capture_depth == 0 and self.target_classes.intersection(classes):
                self.capture_depth = 1
                return
        if self.capture_depth > 0:
            self.capture_depth += 1

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.in_style_or_script = False
        if self.capture_depth > 0:
            self.capture_depth -= 1
        if tag in {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self.capture_depth > 0 and not self.in_style_or_script:
            self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts)


@dataclass
class StorySource:
    title: str
    wikisource_title: Optional[str]
    wikisource_url: str
    xhtml_path: Path


ROMAN_NUMERAL_RE = re.compile(r"^(?=[IVXLCDM])M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")


def load_story_source(title: str) -> StorySource:
    data = json.loads(WIKISOURCE_URLS.read_text(encoding="utf-8"))
    for item in data:
        if item.get("title") == title:
            href = item["href"].lstrip("/")
            xhtml_path = REPO_ROOT / href
            if not xhtml_path.exists():
                xhtml_path = REPO_ROOT / "src" / "epub" / href
            return StorySource(
                title=title,
                wikisource_title=item.get("wikisource_title"),
                wikisource_url=item["wikisource_url"],
                xhtml_path=xhtml_path,
            )
    raise ValueError(f"Title not found in {WIKISOURCE_URLS}: {title}")


def fetch_wikisource_html(title: str) -> str:
    """Fetch rendered HTML for a Wikisource page."""
    params = {
        "action": "parse",
        "format": "json",
        "page": title,
        "prop": "text",
        "formatversion": 2,
    }
    url = f"https://en.wikisource.org/w/api.php?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    if "error" in data:
        raise RuntimeError(f"Wikisource API error: {data['error']}")
    return data["parse"]["text"]


def extract_text_from_wikisource(html: str) -> str:
    """Extract clean text from Wikisource HTML."""
    parser = WikisourceExtractor(target_classes=["prose", "mw-parser-output"])
    parser.feed(html)
    text = parser.get_text()
    if text.strip():
        return text

    fallback = TextExtractor()
    fallback.feed(html)
    return fallback.get_text()


def extract_text_from_xhtml(xhtml_path: Path) -> str:
    """Extract story body text from repo XHTML."""
    content = xhtml_path.read_text(encoding="utf-8")
    match = re.search(r"<article[^>]*>.*?<h2[^>]*>([^<]*)</h2>\s*(.*?)</article>", content, re.DOTALL)
    if match:
        story_body = match.group(2)
    else:
        story_body = content

    parser = TextExtractor()
    parser.feed(story_body)
    text = parser.get_text()
    return unescape(text)


def strip_wikisource_header(text: str, title: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    title_lower = title.lower()
    trimmed_lines = [line.strip() for line in lines]
    candidate_indexes = [i for i, line in enumerate(trimmed_lines) if line.lower() == title_lower]
    for index in reversed(candidate_indexes):
        next_index = index + 1
        if next_index >= len(trimmed_lines):
            continue
        next_line = trimmed_lines[next_index]
        if next_line == "I" or ROMAN_NUMERAL_RE.match(next_line):
            start = next_index + 1
            return "\n".join(lines[start:])
        if next_line[:2].lower() in {"it", "t "}:
            return "\n".join(lines[next_index:])

    for i, line in enumerate(trimmed_lines):
        if line[:2].lower() in {"it", "t "}:
            return "\n".join(lines[i:])

    return "\n".join(lines)


def normalize_text(text: str) -> str:
    """Normalize text for comparison with minimal transformation."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u200b", "").replace("\ufeff", "").replace("\u2060", "")
    text = text.replace("\u00a0", " ")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")

    lines = text.split("\n")
    normalized_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]

    paragraphs: List[str] = []
    current_lines: List[str] = []
    for line in normalized_lines:
        if line == "":
            if current_lines:
                paragraphs.append(" ".join(current_lines).strip())
                current_lines = []
            elif paragraphs and paragraphs[-1] != "":
                paragraphs.append("")
            continue
        current_lines.append(line)

    if current_lines:
        paragraphs.append(" ".join(current_lines).strip())

    cleaned: List[str] = []
    for paragraph in paragraphs:
        if paragraph == "" and (not cleaned or cleaned[-1] == ""):
            continue
        cleaned.append(paragraph)

    text = "\n\n".join(cleaned).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def diff_summary(a: str, b: str) -> int:
    matcher = SequenceMatcher(None, a, b)
    return sum(1 for tag, *_ in matcher.get_opcodes() if tag != "equal")


def diff_text_segment(repo_segment: str, ws_segment: str) -> str:
    if repo_segment == ws_segment:
        return repo_segment
    matcher = SequenceMatcher(None, repo_segment, ws_segment, autojunk=False)
    output_parts: List[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            output_parts.append(repo_segment[i1:i2])
            continue
        repo_chunk = repo_segment[i1:i2]
        ws_chunk = ws_segment[j1:j2]
        max_len = max(len(repo_chunk), len(ws_chunk))
        for index in range(max_len):
            repo_char = repo_chunk[index] if index < len(repo_chunk) else ""
            ws_char = ws_chunk[index] if index < len(ws_chunk) else ""
            output_parts.append(f"{{{repo_char}}}{{{ws_char}}}")
    return "".join(output_parts)


def split_sentences(text: str) -> List[str]:
    pattern = r"(?:(?<=[.!?])|(?<=[.!?][\"']))\s+(?=[\"'A-Z])"
    return [part for part in re.split(pattern, text) if part]


def diff_paragraph(repo_para: str, ws_para: str) -> str:
    repo_sentences = split_sentences(repo_para)
    ws_sentences = split_sentences(ws_para)
    matcher = SequenceMatcher(None, repo_sentences, ws_sentences, autojunk=False)
    output_sentences: List[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            output_sentences.extend(repo_sentences[i1:i2])
            continue
        repo_segment = repo_sentences[i1:i2]
        ws_segment = ws_sentences[j1:j2]
        max_len = max(len(repo_segment), len(ws_segment))
        for index in range(max_len):
            repo_sentence = repo_segment[index] if index < len(repo_segment) else ""
            ws_sentence = ws_segment[index] if index < len(ws_segment) else ""
            if repo_sentence == ws_sentence:
                output_sentences.append(repo_sentence)
            else:
                output_sentences.append(diff_text_segment(repo_sentence, ws_sentence))

    return " ".join(output_sentences)


def build_inline_diff_text(repo_text: str, ws_text: str) -> str:
    repo_paragraphs = repo_text.split("\n\n")
    ws_paragraphs = ws_text.split("\n\n")
    matcher = SequenceMatcher(None, repo_paragraphs, ws_paragraphs, autojunk=False)
    output_paragraphs: List[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            output_paragraphs.extend(repo_paragraphs[i1:i2])
            continue
        repo_segment = repo_paragraphs[i1:i2]
        ws_segment = ws_paragraphs[j1:j2]
        max_len = max(len(repo_segment), len(ws_segment))
        for index in range(max_len):
            repo_para = repo_segment[index] if index < len(repo_segment) else ""
            ws_para = ws_segment[index] if index < len(ws_segment) else ""
            if repo_para and ws_para:
                output_paragraphs.append(diff_paragraph(repo_para, ws_para))
            else:
                output_paragraphs.append(diff_text_segment(repo_para, ws_para))

    return "\n\n".join(output_paragraphs)


def generate_inline_diff(
    title: str,
    xhtml_path: Path,
    ws_path: Path,
    raw_repo_text: str,
    raw_ws_text: str,
    norm_repo_text: str,
    norm_ws_text: str,
    normalized_repo_path: Path,
    normalized_ws_path: Path,
    inline_diff_path: Path,
) -> None:
    normalized_repo_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_ws_path.parent.mkdir(parents=True, exist_ok=True)
    inline_diff_path.parent.mkdir(parents=True, exist_ok=True)

    inline_diff_text = build_inline_diff_text(norm_repo_text, norm_ws_text)

    normalized_repo_path.write_text(norm_repo_text, encoding="utf-8")
    normalized_ws_path.write_text(norm_ws_text, encoding="utf-8")

    header_lines = [
        f"# Inline diff: {title}",
        "",
        "## Inputs",
        f"- Repo XHTML: `{xhtml_path.relative_to(REPO_ROOT)}`",
        f"- Wikisource text: `{ws_path.relative_to(REPO_ROOT)}`",
        "",
        "## Normalization applied",
        "- Remove zero-width/BOM characters.",
        "- Normalize non-breaking spaces.",
        "- Normalize curly quotes to straight quotes.",
        "- Normalize line endings and collapse repeated blank lines.",
        "",
        "## Summary",
        f"- Raw diff hunks: {diff_summary(raw_repo_text, raw_ws_text)}",
        f"- Normalized diff hunks: {diff_summary(norm_repo_text, norm_ws_text)}",
        "",
        "## Outputs",
        f"- Normalized repo text: `{normalized_repo_path.relative_to(REPO_ROOT)}`",
        f"- Normalized Wikisource text: `{normalized_ws_path.relative_to(REPO_ROOT)}`",
        "",
        "## Inline diff",
        "- Inline markers use `{r}{w}` pairs (repo, wikisource); deletions show `{x}{}` and insertions show `{}{x}`.",
        "",
        inline_diff_text,
        "",
    ]

    inline_diff_path.write_text("\n".join(header_lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="Tobermory", help="Story title to compare")
    parser.add_argument("--download-dir", type=Path, default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--normalized-dir", type=Path, default=DEFAULT_NORMALIZED_DIR)
    parser.add_argument("--inline-diff", type=Path, help="Output path for inline diff text")
    args = parser.parse_args()

    source = load_story_source(args.title)
    if not source.xhtml_path.exists():
        raise FileNotFoundError(f"Missing XHTML file: {source.xhtml_path}")

    ws_title = source.wikisource_title or source.title
    ws_path: Path
    try:
        html = fetch_wikisource_html(ws_title)
        ws_text = extract_text_from_wikisource(html)
        args.download_dir.mkdir(parents=True, exist_ok=True)
        ws_filename = f"{source.xhtml_path.stem}_wikisource.txt"
        ws_path = args.download_dir / ws_filename
        ws_path.write_text(ws_text, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - fallback to cached text when offline
        fallback_path = DEFAULT_TEXTS_DIR / f"{source.xhtml_path.stem}.txt"
        if not fallback_path.exists():
            raise RuntimeError("Failed to download Wikisource text and no cached file found.") from exc
        ws_path = fallback_path
        ws_text = ws_path.read_text(encoding="utf-8")

    ws_story_text = strip_wikisource_header(ws_text, source.title)
    repo_text = extract_text_from_xhtml(source.xhtml_path)

    norm_repo_text = normalize_text(repo_text)
    norm_ws_text = normalize_text(ws_story_text)

    normalized_repo_path = args.normalized_dir / f"{source.xhtml_path.stem}_repo_normalized.txt"
    normalized_ws_path = args.normalized_dir / f"{source.xhtml_path.stem}_wikisource_normalized.txt"
    inline_diff_path = args.inline_diff or (DEFAULT_REPORT_DIR / f"{source.xhtml_path.stem}_inline_diff.txt")
    generate_inline_diff(
        source.title,
        source.xhtml_path,
        ws_path,
        repo_text,
        ws_story_text,
        norm_repo_text,
        norm_ws_text,
        normalized_repo_path,
        normalized_ws_path,
        inline_diff_path,
    )

    print(f"Inline diff written to {inline_diff_path}")


if __name__ == "__main__":
    main()
