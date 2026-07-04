# -*- coding: utf-8 -*-
"""Batch-generate all MP3 audio with Azure Speech TTS. Resumable (skips existing files).
Usage: python 04_tts.py [toeic|listening|all]
Voices: female=Ava, male=Andrew — listening dialogues alternate voices per line."""
import glob
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FEMALE = "en-US-AvaMultilingualNeural"
MALE = "en-US-AndrewMultilingualNeural"

jobs = []  # (text, out_path, voice)

mode = sys.argv[1] if len(sys.argv) > 1 else "all"

if mode in ("toeic", "all"):
    outdir = os.path.join(ROOT, "audio", "toeic")
    os.makedirs(outdir, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "toeic", "*.json"))):
        with open(path, encoding="utf-8") as f:
            cat = json.load(f)
        for w in cat["words"]:
            jobs.append((w["word"], os.path.join(outdir, f"{w['id']}.mp3"), FEMALE))
            if w["examples"]:
                jobs.append((w["examples"][0]["english"], os.path.join(outdir, f"{w['id']}_ex.mp3"), MALE))

if mode in ("listening", "all"):
    outdir = os.path.join(ROOT, "audio", "listening")
    os.makedirs(outdir, exist_ok=True)
    lp = os.path.join(ROOT, "data", "listening.json")
    if os.path.exists(lp):
        with open(lp, encoding="utf-8") as f:
            listening = json.load(f)
        for u in listening["units"]:
            for s in u["sentences"]:
                voice = FEMALE if s["n"] % 2 == 1 else MALE
                jobs.append((s["en"], os.path.join(outdir, f"{s['id']}.mp3"), voice))
    else:
        print("listening.json not ready, skipping listening audio")

todo = [j for j in jobs if not os.path.exists(j[1])]
print(f"jobs total={len(jobs)} todo={len(todo)}")

lock = threading.Lock()
done = [0]
failed = []
start = time.time()


def work(job):
    text, path, voice = job
    tmp = path + ".tmp"
    try:
        azlib.tts(text, tmp, voice=voice)
        os.replace(tmp, path)
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        with lock:
            failed.append((path, str(e)[:120]))
        return
    with lock:
        done[0] += 1
        if done[0] % 200 == 0:
            rate = done[0] / (time.time() - start)
            eta = (len(todo) - done[0]) / rate / 60
            print(f"  {done[0]}/{len(todo)}  {rate:.1f}/s  ETA {eta:.1f} min", flush=True)


with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(work, todo))

print(f"done={done[0]} failed={len(failed)} elapsed={(time.time()-start)/60:.1f} min")
for p, e in failed[:10]:
    print("FAIL", os.path.basename(p), e)
