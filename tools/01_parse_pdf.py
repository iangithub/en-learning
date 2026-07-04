# -*- coding: utf-8 -*-
"""Parse spec/英文聽力高頻句.pdf into data/listening_raw.json using gpt-5.5."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fitz  # pymupdf
import azlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PDF = os.path.join(ROOT, "spec", "英文聽力高頻句.pdf")
OUT = os.path.join(ROOT, "data", "listening_raw.json")

doc = fitz.open(PDF)
full = "\n".join(p.get_text() for p in doc)

# Split body into unit chunks (skip the table of contents by starting search
# after the first real unit heading that is followed by table content).
matches = list(re.finditer(r"Unit\s*(\d+)[ㅤ\s]", full))
# TOC lists units 1..16 first, then body repeats them; keep the LAST occurrence of each unit no.
last_pos = {}
for m in matches:
    last_pos[int(m.group(1))] = m.start()
unit_nums = sorted(last_pos)
chunks = {}
for i, n in enumerate(unit_nums):
    start = last_pos[n]
    end = last_pos[unit_nums[i + 1]] if i + 1 < len(unit_nums) else len(full)
    chunks[n] = full[start:end]

print("units found:", unit_nums)

SYSTEM = """You convert raw text extracted from a PDF table of English listening sentences into clean JSON.
The raw text is messy: sentences wrap across lines, and each row is numbered followed by the English sentence, then its Chinese (Traditional) explanation, then a checkbox mark.
Rules:
- Reconstruct each numbered row exactly. Keep alternatives joined by "/" as one sentence entry.
- Fix words broken across lines; keep original wording, punctuation and capitalization.
- Chinese must be Traditional Chinese exactly as in the source (minor cleanup of stray spaces is OK).
- Output JSON object: {"title": "<unit Chinese title>", "sentences": [{"n": <row number>, "en": "...", "zh": "..."}]}
- Include every numbered row. Do not invent or drop rows."""

units_out = []
for n in unit_nums:
    chunk = chunks[n]
    reply = azlib.chat_json(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Unit {n} raw text:\n\n{chunk}"},
        ],
        max_completion_tokens=24000,
        reasoning_effort="low",
    )
    sents = reply["sentences"]
    nums = [s["n"] for s in sents]
    expected = list(range(1, max(nums) + 1))
    status = "OK" if nums == expected else f"GAPS {set(expected) - set(nums)}"
    print(f"Unit {n}: {len(sents)} sentences [{status}]")
    units_out.append({"unit": n, "title": reply["title"].strip(), "sentences": sents})

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(units_out, f, ensure_ascii=False, indent=1)
total = sum(len(u["sentences"]) for u in units_out)
print(f"saved {OUT}: {len(units_out)} units, {total} sentences")
