#!/usr/bin/env python3
"""Extract and normalize repo/Wikisource text for a story, and write to files."""

import html as html_lib
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET


SKIP_CLASSES = {
    "ws-noexport",
    "wst-header",
    "wst-header-mainblock",
    "mw-editsection",
    "reference",
    "reflist",
    "mw-references-wrap",
    "printonly",
    "metadata",
    "pagenum",
    "ws-pagenum",
}

SKIP_TAGS = {"script", "style", "noscript"}

VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class WikiParagraphExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self._buf = []
        self._in_p = False
        self._skip_stack = []

    def _is_skip(self, tag, attrs):
        if tag in SKIP_TAGS:
            return True
        cls = ""
        style = ""
        elem_id = ""
        for key, value in attrs:
            if key == "class" and value:
                cls = value
            elif key == "style" and value:
                style = value
            elif key == "id" and value:
                elem_id = value
        if elem_id == "dynamic_layout_overrider":
            return True
        if "display:none" in style.replace(" ", ""):
            return True
        if not cls:
            return False
        classes = set(cls.split())
        return bool(classes & SKIP_CLASSES)

    def handle_starttag(self, tag, attrs):
        parent_skip = self._skip_stack[-1] if self._skip_stack else False
        cur_skip = parent_skip or self._is_skip(tag, attrs)
        if tag not in VOID_TAGS:
            self._skip_stack.append(cur_skip)

        if tag == "p" and not cur_skip:
            self._in_p = True
            self._buf = []
        elif self._in_p and tag == "br":
            self._buf.append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "p" and self._in_p:
            text = "".join(self._buf).strip()
            if text:
                self.paragraphs.append(text)
            self._in_p = False
            self._buf = []

        if tag not in VOID_TAGS and self._skip_stack:
            self._skip_stack.pop()

    def handle_data(self, data):
        if not self._in_p:
            return
        if self._skip_stack and self._skip_stack[-1]:
            return
        self._buf.append(data)


def normalize_text(text):
    text = html_lib.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\u2060", "")
    text = text.replace("\ufeff", "")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u2013", "\u2014")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_repo_text(xhtml_path):
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    tree = ET.parse(xhtml_path)
    root = tree.getroot()
    paragraphs = []
    for p in root.findall(".//x:p", ns):
        txt = "".join(p.itertext()).strip()
        if txt:
            paragraphs.append(txt)
    return "\n\n".join(paragraphs)


def fetch_wikisource_html(url):
    if "?" in url:
        fetch_url = f"{url}&action=render"
    else:
        fetch_url = f"{url}?action=render"
    req = urllib.request.Request(fetch_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_wikisource_text(url):
    html = fetch_wikisource_html(url)
    parser = WikiParagraphExtractor()
    parser.feed(html)
    return "\n\n".join(parser.paragraphs)


def load_entry(title):
    with open("wikisource/wikisource_urls.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        if item.get("title", "").lower() == title.lower():
            return item
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: wikisource/extract_story_texts.py <story title>")
        return 2

    title = " ".join(sys.argv[1:])
    entry = load_entry(title)
    if not entry:
        print(f"Story not found in wikisource_urls.json: {title}")
        return 1
    if not entry.get("wikisource_url"):
        print(f"No Wikisource URL for: {title}")
        return 1

    href = entry["href"]
    repo_path = Path("src/epub") / href
    if not repo_path.exists():
        print(f"Repo file not found: {repo_path}")
        return 1

    repo_text = normalize_text(extract_repo_text(repo_path))
    wiki_text = normalize_text(extract_wikisource_text(entry["wikisource_url"]))

    out_dir = Path("wikisource/story_texts") / Path(href).stem
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "repo.txt").write_text(repo_text, encoding="utf-8")
    (out_dir / "wikisource.txt").write_text(wiki_text, encoding="utf-8")

    print(f"Wrote: {out_dir / 'repo.txt'}")
    print(f"Wrote: {out_dir / 'wikisource.txt'}")
    print(f"Repo chars: {len(repo_text)} | Wiki chars: {len(wiki_text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
