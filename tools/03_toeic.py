# -*- coding: utf-8 -*-
"""Build TOEIC dataset: ALL star levels, deduped, split per category.
IDs are stable across rebuilds: existing (category, word) -> id mappings are
preserved (so already-generated audio stays valid); new words get new ids.
Produces data/toeic/<slug>.json + data/toeic-index.json."""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "spec", "toeic_vocabulary.json")
OUTDIR = os.path.join(ROOT, "data", "toeic")
os.makedirs(OUTDIR, exist_ok=True)

CATEGORY_SLUGS = {
    "辦公日常": "office",
    "溝通互動": "communication",
    "住宿與餐飲": "hospitality",
    "會議與簡報": "meetings",
    "科技與技術支援": "tech",
    "營運管理": "operations",
    "一般專業": "general",
    "人力資源": "hr",
    "法務合規與安全": "legal",
    "旅遊與交通": "travel",
    "金融與會計": "finance",
    "採購與物流": "procurement",
    "行銷與銷售": "marketing",
    "物業與不動產": "real-estate",
    "客戶服務": "customer-service",
}

# --- preserve existing ids ---
id_map = {}   # (category, word) -> id
max_id = 0
for path in glob.glob(os.path.join(OUTDIR, "*.json")):
    with open(path, encoding="utf-8") as f:
        old = json.load(f)
    for w in old["words"]:
        id_map.setdefault((old["category"], w["word"]), w["id"])
        max_id = max(max_id, int(w["id"][1:]))
print(f"existing ids: {len(id_map)} (max w{max_id:04d})")

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

# dedupe on (category, word): keep highest star, then first occurrence
best = {}
for e in data:
    k = (e["category"], e["english_word"])
    if k not in best or e["star_rating"] > best[k]["star_rating"]:
        best[k] = e
print(f"words: {len(data)} -> deduped {len(best)}")

cats = {}
for e in best.values():
    cats.setdefault(e["category"], []).append(e)

index = []
next_id = max_id
used_ids = set()
n_new = 0
for cat in sorted(cats, key=lambda c: -len(cats[c])):
    slug = CATEGORY_SLUGS[cat]
    words = []
    for e in sorted(cats[cat], key=lambda x: x["english_word"].lower()):
        wid = id_map.get((cat, e["english_word"]))
        if wid is None:
            next_id += 1
            wid = f"w{next_id:04d}"
            n_new += 1
        used_ids.add(wid)
        words.append({
            "id": wid,
            "word": e["english_word"],
            "zh": e["chinese_definition"],
            "star": e["star_rating"],
            "score": e["toeic_score_range"],
            "pos": e["parts_of_speech"],
            "forms": e["word_forms"],
            "examples": e["examples"],
            "tips": e["exam_tips"],
        })
    out_path = os.path.join(OUTDIR, f"{slug}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"category": cat, "slug": slug, "words": words}, f, ensure_ascii=False, separators=(",", ":"))
    stars = {s: sum(1 for w in words if w["star"] == s) for s in (5, 4, 3, 2, 1)}
    index.append({"category": cat, "slug": slug, "count": len(words), "stars": stars})
    print(f"{slug}: {len(words)} words ({os.path.getsize(out_path)//1024} KB)")

total = sum(c["count"] for c in index)
with open(os.path.join(ROOT, "data", "toeic-index.json"), "w", encoding="utf-8") as f:
    json.dump({"total": total, "categories": index}, f, ensure_ascii=False, indent=1)
print(f"total: {total} words, new ids: {n_new}")

# retired ids (deduped duplicates) -> orphan audio cleanup
retired = set(id_map.values()) - used_ids
removed = 0
for rid in retired:
    for suffix in ("", "_ex"):
        p = os.path.join(ROOT, "audio", "toeic", f"{rid}{suffix}.mp3")
        if os.path.exists(p):
            os.remove(p)
            removed += 1
print(f"retired ids: {len(retired)}, orphan audio removed: {removed}")
