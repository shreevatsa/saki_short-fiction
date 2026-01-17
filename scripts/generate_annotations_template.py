#!/usr/bin/env python3

import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path


EXCLUDE_HREFS = {
    "text/titlepage.xhtml",
    "text/imprint.xhtml",
    "text/endnotes.xhtml",
    "text/colophon.xhtml",
    "text/uncopyright.xhtml",
}


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_toc_items(toc_path: Path) -> list[tuple[str, str]]:
    root = ET.fromstring(toc_path.read_text(encoding="utf-8"))

    nav_toc = None
    for el in root.iter():
        if _localname(el.tag) != "nav":
            continue
        if el.get("id") == "toc":
            nav_toc = el
            break

    if nav_toc is None:
        raise RuntimeError(f"Could not find TOC nav in {toc_path}")

    items: list[tuple[str, str]] = []
    for el in nav_toc.iter():
        if _localname(el.tag) != "a":
            continue
        href = el.get("href")
        if not href or not href.startswith("text/"):
            continue
        title = " ".join("".join(el.itertext()).split())
        items.append((href, title))

    return items


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a blank annotation CSV from src/epub/toc.xhtml."
    )
    parser.add_argument(
        "--toc",
        default="src/epub/toc.xhtml",
        help="Path to toc.xhtml (default: %(default)s)",
    )
    parser.add_argument(
        "--out",
        default="annotations/stories.csv",
        help="Output CSV path (default: %(default)s)",
    )
    args = parser.parse_args()

    toc_path = Path(args.toc)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    items = parse_toc_items(toc_path)
    stories = [(href, title) for href, title in items if href not in EXCLUDE_HREFS]

    # Safety check: ensure TOC entries exist on disk.
    missing = [href for href, _ in stories if not (toc_path.parent / href).exists()]
    if missing:
        missing_list = "\n".join(missing[:20])
        raise RuntimeError(
            f"{len(missing)} TOC entries are missing under {toc_path.parent}:\n{missing_list}"
        )

    fieldnames = [
        "index",
        "title",
        "href",
        "rating_story",
        "tone",
        "theme_children_triumph",
        "theme_animals",
        "theme_child_lies",
        "theme_trickster",
        "theme_comeuppance",
        "theme_supernatural",
        "theme_social_satire",
        "theme_meddling_aunt_guardian",
        "theme_hoax_practical_joke",
        "theme_etiquette_weapon",
        "theme_snobbery_status_anxiety",
        "theme_hypocrisy_respectability",
        "theme_philanthropy_backfires",
        "theme_country_house_politics",
        "theme_gossip_scandal_reputation",
        "theme_exotic_elsewhere_disruption",
        "theme_sudden_darkness_punchline",
        "themes_other",
        "notes",
    ]

    existing_by_href: dict[str, dict[str, str]] = {}
    existing_fieldnames: list[str] = []
    if out_path.exists():
        with out_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            existing_fieldnames = list(reader.fieldnames or [])
            for row in reader:
                href = (row.get("href") or "").strip()
                if href:
                    existing_by_href[href] = row

    extra_fieldnames = [
        name for name in existing_fieldnames if name and name not in fieldnames
    ]
    all_fieldnames = fieldnames + extra_fieldnames

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
        writer.writeheader()
        for i, (href, title) in enumerate(stories, start=1):
            existing = existing_by_href.get(href, {})
            row: dict[str, str] = {k: "" for k in all_fieldnames}
            row.update({k: (existing.get(k) or "") for k in all_fieldnames})
            row.update({"index": str(i), "title": title, "href": href})
            writer.writerow(row)

    print(f"Wrote {len(stories)} stories to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
