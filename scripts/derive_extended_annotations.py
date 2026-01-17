#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def detect_recurring(text: str, title: str, notes: str) -> list[str]:
    hay = f"{title}\n{notes}\n{text}".lower()
    out: list[str] = []
    for name in ["clovis", "reginald", "comus"]:
        if re.search(rf"\b{name}\b", hay):
            out.append(name)
    return out


def detect_setting(text: str, title: str, themes: dict, notes: str) -> str:
    hay = f"{title}\n{notes}\n{text}".lower()

    # Very strict historical-pastiche detection (avoid metaphorical “Caesar”, etc.).
    if (
        "an unrecorded episode in roman history" in hay
        or "placidus superbus" in hay
        or ("imperial circus" in hay and "suffragetae" in hay)
    ):
        return "historical_pastiche"
    if title.lower().startswith("the story of st. "):
        return "historical_pastiche"

    # Colonial/outpost markers.
    if any(
        w in hay
        for w in [
            "verandah",
            "syce",
            "upcountry",
            "mission-house",
            "bequar",
            "ponies only fetlock",
        ]
    ):
        return "colonial_outpost"

    # Country-house weekend politics.
    if themes.get("theme_country_house_politics"):
        return "country_house"

    # Rural village/parish/rectory.
    if any(
        w in hay
        for w in [
            "st. chuddocks",
            "st chuddocks",
            "rectory",
            "parish",
            "vicar",
            "hamlet",
            "village",
            "yondershire",
        ]
    ):
        return "rural_village"

    # Explicit London markers.
    if any(
        w in hay
        for w in [
            "mayfair",
            "berkeley-square",
            "berkeley square",
            "piccadilly",
            "regent street",
            "kensington",
            "kensal green",
            "tube",
            "harrod",
            "selfridge",
            "st. james’s park",
            "st. james's park",
            "london",
        ]
    ):
        return "london_town"

    # Foreign “elsewhere”.
    if themes.get("theme_exotic_elsewhere_disruption"):
        return "foreign_abroad"

    # Default.
    return "country_house" if any(w in hay for w in ["hall", "manor", "house-party", "house party"]) else "rural_village"


def detect_body_count(notes: str) -> int:
    n = (notes or "").lower()
    if re.search(r"\btwo men die\b", n) or re.search(r"\btwo\b.*\bdie\b", n):
        return 2
    if any(w in n for w in ["dies", "die ", "killed", "death", "lost their lives", "murder"]):
        return 1
    return 0


def detect_animals_triumph(themes: dict, notes: str, text: str) -> bool:
    if not themes.get("theme_animals"):
        return False
    n = (notes or "").lower()
    t = (text or "").lower()
    if any(w in n for w in ["kills", "devours", "eating a goat", "mauls", "eaten"]):
        return True
    if themes.get("theme_sudden_darkness_punchline") and any(
        w in t for w in ["wolf", "ferret", "hyena", "hyaena", "leopard", "tiger", "panther", "boar"]
    ):
        return True
    return False


def detect_ending_type(themes: dict, notes: str) -> str:
    n = (notes or "").lower()
    if themes.get("theme_sudden_darkness_punchline"):
        if any(p in n for p in ["only for", "turns out", "reveal", "only to"]):
            return "twist_reveal"
        return "dark_punchline"
    if any(p in n for p in ["only for", "turns out", "reveal", "only to"]):
        return "twist_reveal"
    if themes.get("theme_comeuppance"):
        return "ironic_reversal"
    if themes.get("tone") == "funny":
        return "comic_deflation"
    return "open_ended"


def detect_darkness_level(themes: dict, body_count: int) -> int:
    if body_count >= 2:
        return 5
    if body_count == 1:
        return 4
    if themes.get("theme_sudden_darkness_punchline"):
        return 4
    if themes.get("tone") == "serious":
        return 3
    return 2 if themes.get("tone") == "mixed" else 1


def detect_central_mechanism(themes: dict, notes: str, title: str) -> str:
    n = (notes or "").lower()
    if themes.get("theme_hoax_practical_joke"):
        return "hoax"
    if themes.get("theme_gossip_scandal_reputation"):
        if "blackmail" in n or "compromise" in n or "threat" in n:
            return "blackmail_reputation"
        return "misunderstanding"
    if themes.get("theme_animals") and themes.get("theme_animals_triumph"):
        return "animal_intrusion"
    if "derby" in n or "bet" in n or "wager" in n:
        return "wager_bet"
    if title.lower().startswith("clovis on") or "argues that" in n:
        return "monologue_essay"
    return "misunderstanding"


def detect_protagonist_type(themes: dict, recurring: list[str], notes: str, text: str) -> str:
    if themes.get("theme_children_triumph") or themes.get("theme_child_lies"):
        return "child"
    n = (notes or "").lower()
    if any(w in n for w in ["rector", "canon", "bishop", "major", "colonel", "rev."]):
        return "professional_clergy_military"
    if recurring:
        return "trickster"
    if themes.get("theme_trickster"):
        return "trickster"
    if any(w in n for w in ["sheltered", "naive", "outsider"]):
        return "outsider_naif"
    if (text or "").count("<p>“") >= 10:
        return "ensemble"
    return "society_adult"


def detect_agency_driver(themes: dict, protagonist_type: str) -> str:
    if themes.get("theme_children_triumph"):
        return "child"
    if themes.get("theme_animals_triumph"):
        return "animal"
    if protagonist_type == "trickster" or themes.get("theme_trickster"):
        return "trickster"
    if themes.get("theme_meddling_aunt_guardian"):
        return "adult_authority"
    return "chance"


def detect_social_target(themes: dict, notes: str) -> list[str]:
    out: list[str] = []
    n = (notes or "").lower()
    if themes.get("theme_snobbery_status_anxiety"):
        out.append("snobbery")
    if themes.get("theme_philanthropy_backfires"):
        out.append("philanthropy")
    if themes.get("theme_country_house_politics") or "parliament" in n or "election" in n:
        out.append("politics")
    if any(w in n for w in ["bishop", "rector", "canon"]):
        out.append("religion")
    if themes.get("theme_meddling_aunt_guardian"):
        out.append("domesticity")
    if themes.get("theme_hypocrisy_respectability"):
        out.append("respectability")
    if themes.get("theme_social_satire") and not out:
        out.append("respectability")
    # stable unique
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def detect_constraint_pressure(themes: dict, notes: str) -> list[str]:
    out: list[str] = []
    n = (notes or "").lower()
    if themes.get("theme_etiquette_weapon"):
        out.append("etiquette")
    if themes.get("theme_snobbery_status_anxiety") or themes.get("theme_gossip_scandal_reputation"):
        out.append("reputation")
    if themes.get("theme_meddling_aunt_guardian"):
        out.append("family_guardianship")
    if themes.get("theme_country_house_politics") or "parliament" in n or "election" in n:
        out.append("career_politics")
    if any(w in n for w in ["legacy", "inherit", "money"]):
        out.append("money")
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="annotations/stories.json")
    parser.add_argument("--out", dest="out_path", default="annotations/stories.json")
    parser.add_argument("--epub-root", dest="epub_root", default="src/epub")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    epub_root = Path(args.epub_root)

    stories = json.loads(in_path.read_text(encoding="utf-8"))

    text_cache: dict[int, str] = {}
    for s in stories:
        p = epub_root / s["href"]
        try:
            text_cache[s["index"]] = p.read_text(encoding="utf-8")
        except FileNotFoundError:
            text_cache[s["index"]] = ""

    new_stories: list[dict] = []
    for s in stories:
        idx = s["index"]
        text = text_cache.get(idx, "")
        notes = s.get("notes") or ""

        themes = {k: s.get(k) for k in s.keys() if k.startswith("theme_")}
        themes["tone"] = s.get("tone")

        recurring = detect_recurring(text, s.get("title", ""), notes)
        animals_triumph = detect_animals_triumph(themes, notes, text)

        setting = detect_setting(text, s.get("title", ""), themes, notes)
        body_count = detect_body_count(notes)
        ending_type = detect_ending_type(themes, notes)
        darkness_level = detect_darkness_level(themes, body_count)
        central_mechanism = detect_central_mechanism({**themes, "theme_animals_triumph": animals_triumph}, notes, s.get("title", ""))
        protagonist_type = detect_protagonist_type(themes, recurring, notes, text)
        agency_driver = detect_agency_driver({**themes, "theme_animals_triumph": animals_triumph}, protagonist_type)
        social_target = detect_social_target(themes, notes)
        constraint_pressure = detect_constraint_pressure(themes, notes)

        out: dict = {}
        for key in ["index", "title", "href", "rating_story", "tone"]:
            out[key] = s.get(key)

        out["setting"] = setting
        out["ending_type"] = ending_type
        out["darkness_level"] = darkness_level
        out["body_count"] = body_count
        out["central_mechanism"] = central_mechanism
        out["protagonist_type"] = protagonist_type
        out["agency_driver"] = agency_driver
        out["recurring_character"] = recurring
        out["social_target"] = social_target
        out["constraint_pressure"] = constraint_pressure

        out["themes_other"] = s.get("themes_other")
        out["notes"] = s.get("notes")

        theme_order = [
            "theme_children_triumph",
            "theme_animals",
            "theme_animals_triumph",
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
        ]
        for k in theme_order:
            out[k] = animals_triumph if k == "theme_animals_triumph" else s.get(k)

        new_stories.append(out)

    out_path.write_text(json.dumps(new_stories, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
