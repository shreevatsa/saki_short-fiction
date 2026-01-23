#!/usr/bin/env python3
"""Fetch a Wikisource page, normalize, and produce inline diffs vs repo XHTML."""

import difflib
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

    def _is_skip(self, attrs):
        cls = ""
        for key, value in attrs:
            if key == "class" and value:
                cls = value
                break
        if not cls:
            return False
        classes = set(cls.split())
        return bool(classes & SKIP_CLASSES)

    def handle_starttag(self, tag, attrs):
        parent_skip = self._skip_stack[-1] if self._skip_stack else False
        cur_skip = parent_skip or self._is_skip(attrs)
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


def inline_diff_tokens(repo_text, wiki_text):
    token_re = re.compile(r"\s+|\w+(?:['’]\w+)*|[^\w\s]", re.UNICODE)
    repo_tokens = token_re.findall(repo_text)
    wiki_tokens = token_re.findall(wiki_text)
    matcher = difflib.SequenceMatcher(None, repo_tokens, wiki_tokens, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out.append("".join(repo_tokens[i1:i2]))
        elif tag == "replace":
            out.append("{" + "".join(repo_tokens[i1:i2]) + "}{" + "".join(wiki_tokens[j1:j2]) + "}")
        elif tag == "delete":
            out.append("{" + "".join(repo_tokens[i1:i2]) + "}{}")
        elif tag == "insert":
            out.append("{}{" + "".join(wiki_tokens[j1:j2]) + "}")
    return "".join(out)


def paragraphize(text):
    text = text.strip()
    if not text:
        return []
    return re.split(r"\n{2,}", text)


def paragraph_signature(text):
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def inline_diff(repo_text, wiki_text):
    repo_paras = paragraphize(repo_text)
    wiki_paras = paragraphize(wiki_text)
    repo_sigs = [paragraph_signature(p) for p in repo_paras]
    wiki_sigs = [paragraph_signature(p) for p in wiki_paras]

    matcher = difflib.SequenceMatcher(None, repo_sigs, wiki_sigs, autojunk=False)
    out_paras = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal" or (tag == "replace" and (i2 - i1) == (j2 - j1)):
            for a, b in zip(repo_paras[i1:i2], wiki_paras[j1:j2]):
                out_paras.append(inline_diff_tokens(a, b))
        elif tag == "replace":
            out_paras.append(
                "{" + "\n\n".join(repo_paras[i1:i2]) + "}{" + "\n\n".join(wiki_paras[j1:j2]) + "}"
            )
        elif tag == "delete":
            out_paras.append("{" + "\n\n".join(repo_paras[i1:i2]) + "}{}")
        elif tag == "insert":
            out_paras.append("{}{" + "\n\n".join(wiki_paras[j1:j2]) + "}")

    return "\n\n".join(out_paras)


def load_story_texts(stem):
    base = Path("wikisource/story_texts") / stem
    repo_path = base / "repo.txt"
    wiki_path = base / "wikisource.txt"
    if repo_path.exists() and wiki_path.exists():
        return (
            repo_path.read_text(encoding="utf-8"),
            wiki_path.read_text(encoding="utf-8"),
        )
    return None


def load_entry(title):
    with open("wikisource/wikisource_urls.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        if item.get("title", "").lower() == title.lower():
            return item
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: wikisource/inline_diff.py [--refresh] <story title>")
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

    texts = None
    stem = Path(href).stem
    if not refresh:
        texts = load_story_texts(stem)
        if texts:
            print(f"Using cached texts: wikisource/story_texts/{stem}")

    if texts:
        repo_text, wiki_text = texts
    else:
        repo_text = normalize_text(extract_repo_text(repo_path))
        wiki_text = normalize_text(extract_wikisource_text(entry["wikisource_url"]))

    diff_text = inline_diff(repo_text, wiki_text)

    out_dir = Path("wikisource/inline_diffs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (Path(href).stem + "_inline_diff.txt")
    out_path.write_text(diff_text, encoding="utf-8")

    print(f"Wrote inline diff: {out_path}")
    print(f"Repo chars: {len(repo_text)} | Wiki chars: {len(wiki_text)} | Diff chars: {len(diff_text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
