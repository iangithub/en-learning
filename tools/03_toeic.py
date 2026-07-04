# -*- coding: utf-8 -*-
"""Build TOEIC high-frequency dataset: star_rating=5 words split per category.
Produces data/toeic/<slug>.json + data/toeic-index.json."""
import json
import os
import re
import unicodedata

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

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

hifreq = [e for e in data if e.get("star_rating") == 5]
print(f"star-5 words: {len(hifreq)} / {len(data)}")

cats = {}
for e in hifreq:
    cats.setdefault(e["category"], []).append(e)

index = []
wid = 0
for cat in sorted(cats, key=lambda c: -len(cats[c])):
    slug = CATEGORY_SLUGS.get(cat)
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", cat).encode("ascii", "ignore").decode().lower()) or f"cat{len(index)}"
        print(f"WARN unmapped category {cat!r} -> {slug}")
    words = []
    for e in sorted(cats[cat], key=lambda x: x["english_word"].lower()):
        wid += 1
        words.append({
            "id": f"w{wid:04d}",
            "word": e["english_word"],
            "zh": e["chinese_definition"],
            "score": e["toeic_score_range"],
            "pos": e["parts_of_speech"],
            "forms": e["word_forms"],
            "examples": e["examples"],
            "tips": e["exam_tips"],
        })
    out_path = os.path.join(OUTDIR, f"{slug}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"category": cat, "slug": slug, "words": words}, f, ensure_ascii=False, separators=(",", ":"))
    index.append({"category": cat, "slug": slug, "count": len(words)})
    print(f"{slug}: {len(words)} words ({os.path.getsize(out_path)//1024} KB)")

with open(os.path.join(ROOT, "data", "toeic-index.json"), "w", encoding="utf-8") as f:
    json.dump({"total": wid, "categories": index}, f, ensure_ascii=False, indent=1)
print(f"total: {wid} words in {len(index)} categories")
