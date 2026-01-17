#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


API = "https://en.wikisource.org/w/api.php"
BASE = "https://en.wikisource.org/wiki/"


def _http_get_json(params: dict[str, str], *, timeout_s: int = 30) -> dict[str, Any]:
    url = API + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "saki_short-fiction/1.0 (wikisource url mapping)"})
    with urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wiki_url(page_title: str) -> str:
    return BASE + quote(page_title.replace(" ", "_"), safe=":/()'_-")


def _strip_outer_quotes(s: str) -> str:
    s = s.strip()
    # common straight/curly quotes
    return re.sub(r'^[\'"“”]+|[\'"“”]+$', "", s).strip()


def _norm_basic(s: str) -> str:
    s = _strip_outer_quotes(s)
    s = (
        s.replace("’", "'")
        .replace("‘", "'")
        .replace("—", "-")
        .replace("–", "-")
        .replace("\u00a0", " ")
    )
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


def _norm_loose(s: str) -> str:
    s = _norm_basic(s)
    # remove punctuation; keep alnum and spaces
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _norm_nospace(s: str) -> str:
    s = _norm_basic(s)
    return re.sub(r"[^a-z0-9]+", "", s)


@dataclass(frozen=True)
class Match:
    wikisource_title: str
    wikisource_url: str
    match_source: str  # author_page | search
    match_kind: str  # exact_segment | loose_segment | exact_full | loose_full | search_exact | search_loose
    confidence: str  # high | medium | low


def _author_page_ns0_titles() -> list[str]:
    data = _http_get_json(
        {
            "action": "parse",
            "page": "Author:Hector_Hugh_Munro",
            "prop": "links",
            "format": "json",
        }
    )
    links = data.get("parse", {}).get("links", [])
    return [l["*"] for l in links if l.get("ns") == 0 and "*" in l]


def _match_from_author_page(story_title: str, ns0_titles: list[str]) -> Match | None:
    """
    Match using the Author page outbound links.

    Important: the Author page often links to collection subpages like
    `The Chronicles of Clovis/Hermann the Irascible—A Story of the Great Weep`.
    We treat “segment starts with story title” as a valid match.
    """

    target_basic = _norm_basic(story_title)
    target_loose = _norm_loose(story_title)
    target_nospace = _norm_nospace(story_title)

    best: tuple[int, str] | None = None
    for full_title in ns0_titles:
        seg = _strip_outer_quotes(full_title.split("/")[-1])
        seg_basic = _norm_basic(seg)
        seg_loose = _norm_loose(seg)
        seg_nospace = _norm_nospace(seg)

        score = 0
        if seg_basic == target_basic:
            score = 300
        elif seg_loose == target_loose:
            score = 250
        elif seg_nospace == target_nospace:
            score = 240
        elif seg_nospace.startswith(target_nospace) and target_nospace:
            score = 200
        else:
            continue

        # Prefer “closer” titles (shorter segment, then shorter full title).
        score -= min(len(seg), 80) // 10
        score -= min(len(full_title), 200) // 50

        if best is None or score > best[0]:
            best = (score, full_title)

    if best is None:
        return None

    score, chosen = best
    kind = "author_exact" if score >= 240 else "author_prefix"
    confidence = "high" if kind == "author_exact" else "medium"
    return Match(
        wikisource_title=chosen,
        wikisource_url=_wiki_url(chosen),
        match_source="author_page",
        match_kind=kind,
        confidence=confidence,
    )


def _resolve_redirect(title: str) -> str:
    data = _http_get_json(
        {
            "action": "query",
            "titles": title,
            "redirects": "1",
            "format": "json",
        }
    )
    redirects = data.get("query", {}).get("redirects") or []
    if not redirects:
        return title
    # 'to' is the resolved title
    return redirects[0].get("to") or title


def _page_looks_like_saki(title: str) -> bool:
    # Best-effort verification: look for author markers (avoid false positives).
    resolved = _resolve_redirect(title)
    data = _http_get_json(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": resolved,
            "redirects": "1",
            "format": "json",
        }
    )
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    revisions = page.get("revisions") or []
    if not revisions:
        return False
    content = revisions[0].get("slots", {}).get("main", {}).get("*", "") or ""
    hay = content.lower()
    if "#redirect" in hay or "#redirect" in hay.replace(" ", ""):
        return False

    # Typical Wikisource headers / author templates.
    if re.search(r"author\\s*=\\s*saki\\b", hay):
        return True
    if re.search(r"author\\s*=\\s*hector\\s+hugh\\s+munro\\b", hay):
        return True
    if "{{author|saki" in hay:
        return True
    if "[[category:saki" in hay:
        return True
    if re.search(r"\\|\\s*author\\s*=\\s*saki\\b", hay):
        return True

    return False


def _search_best(title: str) -> Match | None:
    # Use MediaWiki search in main namespace.
    query = f'intitle:"{title}" (Saki OR Munro OR "H. H. Munro")'
    data = _http_get_json(
        {
            "action": "query",
            "list": "search",
            "srnamespace": "0",
            "srlimit": "10",
            "srsearch": query,
            "format": "json",
        }
    )
    results = data.get("query", {}).get("search", [])
    if not results:
        return None

    title_loose = _norm_loose(title)
    title_basic = _norm_basic(title)
    title_nospace = _norm_nospace(title)

    scored: list[tuple[int, str]] = []
    for r in results:
        cand = r.get("title")
        if not cand:
            continue
        seg = _strip_outer_quotes(cand.split("/")[-1])
        seg_basic = _norm_basic(seg)
        seg_loose = _norm_loose(seg)
        seg_nospace = _norm_nospace(seg)
        cand_nospace = _norm_nospace(cand)

        score = 0
        if seg_basic == title_basic:
            score += 100
        if seg_loose == title_loose:
            score += 80
        if seg_nospace == title_nospace:
            score += 75
        if seg_nospace.startswith(title_nospace) and title_nospace:
            score += 60
        if _norm_basic(cand) == title_basic:
            score += 60
        if _norm_loose(cand) == title_loose:
            score += 40
        if cand_nospace == title_nospace:
            score += 35
        # Prefer subpages from known Saki collections (heuristic).
        if "/" in cand and any(
            cand.startswith(prefix)
            for prefix in [
                "Reginald/",
                "Reginald in Russia/",
                "The Chronicles of Clovis/",
                "Beasts and Super-Beasts/",
                "The Toys of Peace and Other Papers/",
            ]
        ):
            score += 10
        scored.append((score, cand))

    scored.sort(reverse=True)

    for score, cand in scored[:5]:
        # Avoid very weak matches.
        if score < 60:
            continue
        # Verify it looks like a Saki page.
        time.sleep(0.05)
        resolved = _resolve_redirect(cand)
        if not _page_looks_like_saki(resolved):
            continue
        confidence = "high" if score >= 100 else ("medium" if score >= 80 else "low")
        kind = "search_exact" if score >= 100 else "search_loose"
        return Match(
            wikisource_title=resolved,
            wikisource_url=_wiki_url(resolved),
            match_source="search",
            match_kind=kind,
            confidence=confidence,
        )

    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", default="annotations/stories.json")
    parser.add_argument("--out", default="annotations/wikisource_urls.json")
    parser.add_argument("--sleep", type=float, default=0.05, help="sleep seconds between network calls")
    args = parser.parse_args()

    stories = json.loads(Path(args.stories).read_text(encoding="utf-8"))
    ns0_titles = _author_page_ns0_titles()

    out: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for s in stories:
        title = s["title"]
        key_basic = _norm_basic(title)
        key_loose = _norm_loose(title)
        _ = key_basic, key_loose  # keep for debugging parity; matching uses author-page scanning now.

        match = _match_from_author_page(title, ns0_titles)
        if match is None:
            time.sleep(args.sleep)
            match = _search_best(title)

        entry: dict[str, Any] = {
            "index": s["index"],
            "title": title,
            "href": s["href"],
            "wikisource_title": match.wikisource_title if match else None,
            "wikisource_url": match.wikisource_url if match else None,
            "match_source": match.match_source if match else "missing",
            "match_kind": match.match_kind if match else "missing",
            "confidence": match.confidence if match else "none",
        }
        out.append(entry)
        if match is None:
            missing.append(entry)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"wrote {out_path} ({len(out)} entries)")
    print(f"found: {len(out) - len(missing)}, missing: {len(missing)}")
    if missing:
        print("missing sample:")
        for m in missing[:25]:
            print(f"  - {m['index']}: {m['title']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
