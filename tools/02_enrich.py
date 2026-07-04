# -*- coding: utf-8 -*-
"""Enrich listening sentences with card-back content and add 4 new AI-generated units.
Produces data/listening.json. Resumable: caches per-chunk results in tools/.cache/."""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RAW = os.path.join(ROOT, "data", "listening_raw.json")
OUT = os.path.join(ROOT, "data", "listening.json")
CACHE = os.path.join(HERE, ".cache")
os.makedirs(CACHE, exist_ok=True)

TOC_TITLES = {
    1: "認識新朋友", 2: "家庭對話", 3: "餐廳點餐", 4: "購物與結帳",
    5: "住家維修", 6: "旅行與住宿", 7: "健康與醫療", 8: "客訴與抱怨",
    9: "交朋友閒聊", 10: "心靈對話", 11: "開玩笑幽默", 12: "生活分享、社交邀約與拒絕",
    13: "工作與面試", 14: "工作閒聊", 15: "新聞時事探討", 16: "價值觀傳遞",
}

NEW_UNITS = [
    (17, "電話溝通與預約", "打電話預約餐廳、診所、客服等美國日常電話用語"),
    (18, "問路與大眾運輸", "在美國問路、搭地鐵公車、叫 Uber 的常用句"),
    (19, "咖啡廳點餐與外送", "星巴克點咖啡、點外送、取餐的道地說法"),
    (20, "天氣閒聊與週末計畫", "美國人最愛的天氣 small talk 與週末計畫閒聊"),
]

ENRICH_SYSTEM = """You are an American English teacher creating flashcard BACK-side content for Taiwanese learners.
For each numbered sentence, produce:
- "grammar": 一句簡短的時態/文法/口語重點說明（繁體中文，聚焦這句最值得學的文法或口語現象，例如縮讀 gonna、現在完成式、片語動詞）
- "variations": 2-3 個美國人日常會說的同義替換說法（英文，自然口語，不要死板教科書句）
- "keyPhrases": 1-3 個關鍵片語，各為 {"phrase": "...", "zh": "繁中意思"}
- "extraExamples": 2 個使用相同句型/關鍵片語的新例句，各為 {"en": "...", "zh": "繁中翻譯"}，情境要生活化
Output JSON: {"items": [{"n": <number>, "grammar": "...", "variations": [...], "keyPhrases": [...], "extraExamples": [...]}]}
Cover every input sentence number exactly once."""

NEWUNIT_SYSTEM = """You are an American English conversation expert creating listening/speaking flashcards for Taiwanese learners.
Create a realistic everyday American dialogue-flow of 20 sentences for the given theme — the kind of natural, idiomatic lines Americans actually say (contractions, fillers, phrasal verbs), NOT stiff textbook grammar sentences.
Follow the style of these real examples: "You're coming to the party later tonight, right?", "No worries. It's okay.", "I'm just gonna take some Theraflu.", "What can I get started for you today?"
Sentences should flow as a coherent scenario (like a conversation script) and each be independently useful as a high-frequency line.
Output JSON: {"scenario": "一句繁中情境描述（以Claire為主角）", "sentences": [{"n": 1, "en": "...", "zh": "繁體中文翻譯（台灣用語）"}]}
Exactly 20 sentences, numbered 1-20."""


def cached_call(key, fn):
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    result = fn()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result


def gen_new_unit(num, title, brief):
    def call():
        return azlib.chat_json(
            [
                {"role": "system", "content": NEWUNIT_SYSTEM},
                {"role": "user", "content": f"主題：{title}（{brief}）"},
            ],
            max_completion_tokens=20000,
            reasoning_effort="medium",
        )
    reply = cached_call(f"newunit_{num:02d}", call)
    return {
        "unit": num,
        "title": title,
        "scenario": reply["scenario"],
        "sentences": [{"n": s["n"], "en": s["en"].strip(), "zh": s["zh"].strip()} for s in reply["sentences"]],
    }


def enrich_chunk(unit_num, chunk_idx, sentences):
    payload = "\n".join(f'{s["n"]}. {s["en"]}  （{s["zh"]}）' for s in sentences)
    def call():
        return azlib.chat_json(
            [
                {"role": "system", "content": ENRICH_SYSTEM},
                {"role": "user", "content": payload},
            ],
            max_completion_tokens=28000,
            reasoning_effort="low",
        )
    reply = cached_call(f"enrich_u{unit_num:02d}_c{chunk_idx}", call)
    return {item["n"]: item for item in reply["items"]}


def main():
    with open(RAW, encoding="utf-8") as f:
        raw_units = json.load(f)

    units = []
    for u in raw_units:
        n = u["unit"]
        scenario = u["title"].replace("課文情境：", "").strip()
        units.append({"unit": n, "title": TOC_TITLES[n], "scenario": scenario, "sentences": u["sentences"]})

    # generate the 4 new units (parallel)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(gen_new_unit, *nu) for nu in NEW_UNITS]
        for fut in as_completed(futs):
            u = fut.result()
            print(f"new unit {u['unit']} {u['title']}: {len(u['sentences'])} sentences")
            units.append(u)
    units.sort(key=lambda u: u["unit"])

    # enrichment for every sentence, chunked 15 per call
    jobs = []
    for u in units:
        sents = u["sentences"]
        for ci in range(0, len(sents), 15):
            jobs.append((u, ci // 15, sents[ci:ci + 15]))
    print(f"enrichment jobs: {len(jobs)}")

    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(enrich_chunk, u["unit"], ci, chunk): (u["unit"], ci, chunk) for u, ci, chunk in jobs}
        done = 0
        for fut in as_completed(futs):
            unum, ci, chunk = futs[fut]
            try:
                results[(unum, ci)] = fut.result()
            except Exception as e:
                print(f"FAIL u{unum} c{ci}: {e}")
                results[(unum, ci)] = {}
            done += 1
            if done % 5 == 0:
                print(f"  {done}/{len(jobs)} chunks done")

    missing = 0
    for u, ci, chunk in jobs:
        m = results.get((u["unit"], ci), {})
        for s in chunk:
            item = m.get(s["n"])
            if not item:
                missing += 1
                s["back"] = None
                continue
            s["back"] = {
                "grammar": item.get("grammar", ""),
                "variations": item.get("variations", []),
                "keyPhrases": item.get("keyPhrases", []),
                "extraExamples": item.get("extraExamples", []),
            }

    for u in units:
        for s in u["sentences"]:
            s["id"] = f"u{u['unit']:02d}s{s['n']:02d}"

    out = {"units": units}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(u["sentences"]) for u in units)
    print(f"saved {OUT}: {len(units)} units, {total} sentences, missing back: {missing}")


if __name__ == "__main__":
    main()
