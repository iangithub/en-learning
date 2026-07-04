# -*- coding: utf-8 -*-
"""Rename protagonist Claire -> Cheryl/Ian/Oliver (per unit) in data/listening.json.
Deterministic name swap everywhere; LLM fixes protagonist-referring gender pronouns
in male-assigned units. Prints ids whose EN text changed (audio must be regenerated)."""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PATH = os.path.join(ROOT, "data", "listening.json")

ASSIGN = {
    1: "Cheryl", 4: "Cheryl", 10: "Cheryl", 11: "Cheryl", 17: "Cheryl",
    2: "Ian", 5: "Ian", 7: "Ian", 9: "Ian", 13: "Ian", 15: "Ian", 18: "Ian", 20: "Ian",
    3: "Oliver", 6: "Oliver", 8: "Oliver", 12: "Oliver", 14: "Oliver", 16: "Oliver", 19: "Oliver",
}
MALE = {"Ian", "Oliver"}

GENDER_SYSTEM = """You fix gender references in a Traditional-Chinese/English bilingual dialogue after the protagonist was renamed from Claire (female) to {name} (male).
Rules:
- ONLY adjust words that refer to {name}: English she/her/hers -> he/him/his; Chinese 妳 -> 你 (when addressing {name}), 她 -> 他 (when referring to {name}).
- Words referring to OTHER people (Daisy, Karen, Mia, Susan, Joanna, mothers, girlfriends, etc.) must stay unchanged.
- Change NOTHING else: no rewording, no punctuation changes.
- Use the dialogue flow to decide who each pronoun refers to (speakers alternate naturally).
Output JSON: {{"fixes": [{{"n": <number>, "en": "<full corrected en>", "zh": "<full corrected zh>"}}]}} — include ONLY sentences that needed a change; if none, return {{"fixes": []}}."""


def gender_fix_unit(u, name):
    lines = "\n".join(f'{s["n"]}. {s["en"]}  ｜ {s["zh"]}' for s in u["sentences"])
    payload = f"情境：{u['scenario']}（主角 {name}，男性）\n\n{lines}"
    reply = azlib.chat_json(
        [{"role": "system", "content": GENDER_SYSTEM.format(name=name)},
         {"role": "user", "content": payload}],
        max_completion_tokens=16000, reasoning_effort="medium")
    return reply.get("fixes", [])


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)

    old_en = {}
    for u in data["units"]:
        for s in u["sentences"]:
            old_en[s["id"]] = s["en"]

    # pass 1: deterministic name replacement everywhere
    for u in data["units"]:
        name = ASSIGN[u["unit"]]
        u["scenario"] = u["scenario"].replace("Claire", name)
        for s in u["sentences"]:
            s["en"] = s["en"].replace("Claire", name)
            s["zh"] = s["zh"].replace("Claire", name)
            if s.get("back"):
                blob = json.dumps(s["back"], ensure_ascii=False).replace("Claire", name)
                s["back"] = json.loads(blob)

    # pass 2: LLM gender fixes for male-assigned units
    male_units = [u for u in data["units"] if ASSIGN[u["unit"]] in MALE]
    fixes_applied = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(gender_fix_unit, u, ASSIGN[u["unit"]]): u for u in male_units}
        for fut in as_completed(futs):
            u = futs[fut]
            try:
                fixes = fut.result()
            except Exception as e:
                print(f"FAIL unit {u['unit']}: {e}")
                continue
            by_n = {s["n"]: s for s in u["sentences"]}
            for fx in fixes:
                s = by_n.get(fx["n"])
                if not s:
                    continue
                s["en"], s["zh"] = fx["en"], fx["zh"]
                fixes_applied += 1
            print(f"unit {u['unit']:2d} ({ASSIGN[u['unit']]}): {len(fixes)} gender fixes")

    # verify: no Claire anywhere
    blob = json.dumps(data, ensure_ascii=False)
    leftover = blob.count("Claire")
    print(f"gender fixes applied: {fixes_applied}; leftover 'Claire': {leftover}")

    changed = [sid for u in data["units"] for s in u["sentences"]
               if (sid := s["id"]) and s["en"] != old_en[sid]]
    with open(os.path.join(HERE, ".rename_changed_ids.json"), "w", encoding="utf-8") as f:
        json.dump(changed, f)
    print(f"EN changed (audio regen needed): {len(changed)} sentences")

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("saved", PATH)


if __name__ == "__main__":
    main()
