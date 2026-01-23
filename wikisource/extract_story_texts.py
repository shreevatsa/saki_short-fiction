#!/usr/bin/env python3
"""Extract and normalize repo/Wikisource text for a story, and write to files."""

import html as html_lib
import json
import re
import sys
import hashlib
import urllib.error
import urllib.request
import time
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


PARA_TAGS = {"p", "dd", "li"}


class WikiParagraphExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self._buf = []
        self._para_tag = None
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

        if tag in PARA_TAGS and not cur_skip and self._para_tag is None:
            self._para_tag = tag
            self._buf = []
        elif self._para_tag and tag == "br":
            self._buf.append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == self._para_tag:
            text = "".join(self._buf).strip()
            if text:
                self.paragraphs.append(text)
            self._para_tag = None
            self._buf = []
        elif self._para_tag and tag == "p":
            self._buf.append("\n\n")

        if tag not in VOID_TAGS and self._skip_stack:
            self._skip_stack.pop()

    def handle_data(self, data):
        if not self._para_tag:
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


def title_key(text):
    text = text.strip()
    text = re.sub(r"[\"'’“”]", "", text)
    text = re.sub(r"[^0-9A-Za-z]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def is_titleish(text):
    text = text.strip()
    if not text or len(text) > 80:
        return False
    if re.search(r"[.!?]", text):
        return False
    words = re.findall(r"[A-Za-z0-9]+", text)
    return len(words) <= 12


def strip_wikisource_title(text, title, wikisource_title=None):
    parts = [p for p in re.split(r"\n{2,}", text) if p.strip()]
    if not parts:
        return text
    candidates = [title]
    if wikisource_title:
        candidates.append(wikisource_title.split("/")[-1])
    cand_keys = {title_key(c) for c in candidates if c}

    first = parts[0]
    second = parts[1] if len(parts) > 1 else ""
    combined = (first + " " + second).strip()

    if cand_keys and title_key(combined) in cand_keys:
        parts = parts[2:]
    elif cand_keys and title_key(first) in cand_keys:
        parts = parts[1:]
    elif len(parts) > 1 and cand_keys and title_key(second) in cand_keys and is_titleish(first):
        parts = parts[2:]

    return "\n\n".join(parts)


def extract_repo_text(xhtml_path):
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    tree = ET.parse(xhtml_path)
    root = tree.getroot()
    paragraphs = []
    ns_url = ns["x"]
    tag = lambda t: f"{{{ns_url}}}{t}"
    p_tag = tag("p")
    li_tag = tag("li")
    tr_tag = tag("tr")
    td_tag = tag("td")
    th_tag = tag("th")
    br_tag = tag("br")

    def text_with_breaks(node):
        parts = []

        def walk(el):
            if el.text:
                parts.append(el.text)
            for child in list(el):
                if child.tag == br_tag:
                    parts.append("\n")
                else:
                    walk(child)
                if child.tail:
                    parts.append(child.tail)

        walk(node)
        return "".join(parts)

    for el in root.iter():
        if el.tag == tr_tag:
            cells = []
            for cell in el:
                if cell.tag not in (td_tag, th_tag):
                    continue
                cell_text = " ".join(text_with_breaks(cell).split())
                if cell_text:
                    cells.append(cell_text)
            if cells:
                if len(cells) >= 2:
                    line = f"{cells[0]}: {cells[1]}"
                    if len(cells) > 2:
                        line += " " + " ".join(cells[2:])
                else:
                    line = cells[0]
                paragraphs.append(line)
            continue

        if el.tag == p_tag:
            txt = text_with_breaks(el).strip()
            if txt:
                paragraphs.append(txt)
            continue

        if el.tag == li_tag:
            if el.find(".//x:p", ns) is not None:
                continue
            txt = text_with_breaks(el).strip()
            if txt:
                paragraphs.append(txt)
    return "\n\n".join(paragraphs)


def cache_path_for(url):
    cache_dir = Path("wikisource/http_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.html"


def fetch_wikisource_html(url, refresh=False, max_retries=5, base_delay=1.0):
    if "?" in url:
        fetch_url = f"{url}&action=render"
    else:
        fetch_url = f"{url}?action=render"
    cache_path = cache_path_for(fetch_url)
    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(fetch_url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            cache_path.write_text(html, encoding="utf-8")
            return html
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt >= max_retries:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)


def extract_wikisource_text(url, refresh=False):
    html = fetch_wikisource_html(url, refresh=refresh)
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
        print("Usage: wikisource/extract_story_texts.py [--refresh] <story title>")
        return 2

    args = sys.argv[1:]
    refresh = False
    if "--refresh" in args:
        refresh = True
        args = [a for a in args if a != "--refresh"]

    title = " ".join(args)
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
    wiki_text = normalize_text(extract_wikisource_text(entry["wikisource_url"], refresh=refresh))
    wiki_text = strip_wikisource_title(
        wiki_text,
        entry["title"],
        wikisource_title=entry.get("wikisource_title"),
    )

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
