# -*- coding: utf-8 -*-
"""Generate 情境對話: 10 two-person (M+F) American conversational dialogues per
listening category (20 categories = 200 dialogues, ~18-22 lines each).
Cached per call in tools/.cache/, resumable. Writes data/dialogues/<unit>.json + index."""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUTDIR = os.path.join(ROOT, "data", "dialogues")
CACHE = os.path.join(HERE, ".cache")
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

with open(os.path.join(ROOT, "data", "listening.json"), encoding="utf-8") as f:
    UNITS = [{"unit": u["unit"], "title": u["title"], "scenario": u["scenario"]}
             for u in json.load(f)["units"]]

BRIEFS_SYSTEM = """You design dialogue-practice scenarios for Taiwanese learners of American conversational English.
For the given theme, create 10 DISTINCT everyday scenarios Americans actually encounter — different sub-situations, moods and relationships (friends, strangers, staff/customer, coworkers...). Each scenario is a two-person conversation between one male and one female speaker.
Pick common, varied American first names (different pairs across the 10 scenarios; do not reuse a name twice in this list; avoid Claire).
Output JSON: {"scenarios": [{"i": 1, "title": "簡短中文標題", "titleEn": "Short English Title", "scene": "一句繁中情境描述（誰、在哪、要做什麼）", "m": "MaleName", "f": "FemaleName"}]}
Exactly 10 scenarios, i = 1-10."""

DIALOG_SYSTEM = """You write dialogue scripts that teach non-native speakers REAL spoken American English for communication practice.
Hard requirements:
- Two speakers: {m} (male, "M") and {f} (female, "F"). Natural turn-taking (mostly alternating; an occasional double turn is fine).
- 18 to 22 lines total. Lines are SHORT and punchy like real speech — not essay sentences.
- Authentic casual register: contractions (I'm, gonna, wanna, kinda), fillers and reactions (Oh nice! No way. Honestly, ... You know what? Gotcha. For sure.), phrasal verbs, the way Americans actually talk day-to-day. NO stiff textbook grammar, NO formal written English.
- The conversation must fit the scene, feel complete (natural opening and wrap-up), and stay friendly/PG.
- Traditional Chinese (Taiwan) translation for every line — translate the vibe, not word-by-word.
- Then pick 4-6 lines' worth of key expressions worth memorizing: the most idiomatic, high-frequency chunks.
Output JSON:
{"lines": [{"n": 1, "s": "M" or "F", "en": "...", "zh": "..."}],
 "phrases": [{"p": "expression", "zh": "繁中意思", "note": "一句話說明何時/為何這樣說（繁中）"}]}"""


def cached(key, fn):
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    r = fn()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False)
    return r


def gen_briefs(u):
    def call():
        return azlib.chat_json(
            [{"role": "system", "content": BRIEFS_SYSTEM},
             {"role": "user", "content": f"主題：{u['title']}（參考情境風格：{u['scenario']}）"}],
            max_completion_tokens=12000, reasoning_effort="medium")
    r = cached(f"dlg_briefs_u{u['unit']:02d}", call)
    assert len(r["scenarios"]) == 10, f"unit {u['unit']}: {len(r['scenarios'])} briefs"
    return r["scenarios"]


def gen_dialog(unit, brief):
    key = f"dlg_u{unit:02d}_s{brief['i']:02d}"
    system = DIALOG_SYSTEM.replace("{m}", brief["m"]).replace("{f}", brief["f"])
    def call():
        lines = []
        for attempt in range(3):
            r = azlib.chat_json(
                [{"role": "system", "content": system},
                 {"role": "user", "content": f"Scene: {brief['scene']}（題目：{brief['title']} / {brief['titleEn']}）"}],
                max_completion_tokens=16000, reasoning_effort="medium")
            lines = r.get("lines", [])
            if 16 <= len(lines) <= 24 and len(r.get("phrases", [])) >= 3 \
               and all(l.get("s") in ("M", "F") and l.get("en") and l.get("zh") for l in lines):
                return r
        raise RuntimeError(f"{key}: bad output after retries ({len(lines)} lines)")
    return cached(key, call)


def main():
    # briefs (parallel)
    briefs = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(gen_briefs, u): u for u in UNITS}
        for fut in as_completed(futs):
            u = futs[fut]
            briefs[u["unit"]] = fut.result()
            print(f"briefs unit {u['unit']:2d} ok", flush=True)

    # dialogues (parallel)
    jobs = [(u["unit"], b) for u in UNITS for b in briefs[u["unit"]]]
    results = {}
    failed = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(gen_dialog, unit, b): (unit, b) for unit, b in jobs}
        done = 0
        for fut in as_completed(futs):
            unit, b = futs[fut]
            try:
                results[(unit, b["i"])] = fut.result()
            except Exception as e:
                failed.append((unit, b["i"], str(e)[:100]))
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(jobs)} dialogues", flush=True)
    if failed:
        print("FAILED:", failed)
        sys.exit(1)

    index = []
    total_lines = 0
    for u in UNITS:
        dialogues = []
        for b in briefs[u["unit"]]:
            r = results[(u["unit"], b["i"])]
            did = f"d{u['unit']:02d}{b['i']:02d}"
            lines = [{"n": i + 1, "s": l["s"], "en": l["en"].strip(), "zh": l["zh"].strip()}
                     for i, l in enumerate(r["lines"])]
            total_lines += len(lines)
            dialogues.append({
                "id": did, "title": b["title"], "titleEn": b["titleEn"], "scene": b["scene"],
                "m": b["m"], "f": b["f"], "lines": lines, "phrases": r["phrases"],
            })
        out = {"unit": u["unit"], "title": u["title"], "dialogues": dialogues}
        with open(os.path.join(OUTDIR, f"{u['unit']:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        index.append({"unit": u["unit"], "title": u["title"], "count": len(dialogues),
                      "lines": sum(len(d["lines"]) for d in dialogues)})
        print(f"unit {u['unit']:2d} {len(dialogues)} dialogues saved")

    with open(os.path.join(ROOT, "data", "dialogues-index.json"), "w", encoding="utf-8") as f:
        json.dump({"total": len(jobs), "totalLines": total_lines, "categories": index}, f,
                  ensure_ascii=False, indent=1)
    print(f"DONE: {len(jobs)} dialogues, {total_lines} lines")


if __name__ == "__main__":
    main()
