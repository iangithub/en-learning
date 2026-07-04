# -*- coding: utf-8 -*-
"""Generate cover images with gpt-image-2, then downscale to WebP for the site.
Resumable: skips images whose .webp already exists. PNG originals stay in tools/.imgcache/."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azlib
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
IMGDIR = os.path.join(ROOT, "images")
CACHE = os.path.join(HERE, ".imgcache")
os.makedirs(IMGDIR, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

STYLE = ("Warm flat illustration, friendly modern vector style, soft coral, teal and cream palette, "
         "clean shapes, cozy lighting. No text, no letters, no captions.")

SPECS = [
    ("hero-listening", "1536x1024", "Two young American friends having a lively casual conversation at a cafe table, speech-bubble shapes floating, headphones resting nearby."),
    ("hero-toeic", "1536x1024", "A confident young professional studying vocabulary flashcards at a tidy desk, laptop, coffee, skyscraper office view through window."),
    ("unit01", "1536x1024", "Young people chatting at a rooftop New Year party, city skyline, festive string lights."),
    ("unit02", "1536x1024", "Two roommates chatting while cooking dinner together in a cozy apartment kitchen."),
    ("unit03", "1536x1024", "Ordering food at a fast-casual burrito counter, server assembling a bowl behind glass."),
    ("unit04", "1536x1024", "A young woman shopping for clothes in a bright boutique, browsing racks, fitting rooms."),
    ("unit05", "1536x1024", "A technician repairing a home air conditioner while resident watches, toolbox open."),
    ("unit06", "1536x1024", "Traveler with suitcase checking in at a sunny hotel lobby front desk, palm trees outside."),
    ("unit07", "1536x1024", "A caring doctor talking with a patient in a clinic exam room, warm and reassuring."),
    ("unit08", "1536x1024", "A person on the phone beside a car with a flat tire warning, roadside assistance arriving."),
    ("unit09", "1536x1024", "Two strangers becoming friends chatting on a subway train, ticket machine in background."),
    ("unit10", "1536x1024", "Two close friends having a heartfelt talk on a couch with tea, comforting embrace mood."),
    ("unit11", "1536x1024", "Friends laughing hard together at a casual dinner table, playful joking atmosphere."),
    ("unit12", "1536x1024", "Friends planning weekend fun with a calendar, one politely declining an invitation at the door."),
    ("unit13", "1536x1024", "A job interview in a modern office, candidate shaking hands with interviewer, portfolio on table."),
    ("unit14", "1536x1024", "Coworkers having friendly small talk by the office water cooler and washroom hallway."),
    ("unit15", "1536x1024", "Two roommates on a couch watching TV news, discussing current events, remote in hand."),
    ("unit16", "1536x1024", "Two friends in deep thoughtful discussion at a kitchen table at night, sharing perspectives."),
    ("unit17", "1536x1024", "A young woman making a phone reservation, calendar and notepad, restaurant and clinic icons floating."),
    ("unit18", "1536x1024", "A tourist asking for directions at a city street corner, subway entrance and bus stop nearby."),
    ("unit19", "1536x1024", "Ordering coffee at a cozy cafe counter, barista writing a name on a cup, pastry case."),
    ("unit20", "1536x1024", "Neighbors chatting about the weather over a fence, one holding an umbrella, sun and clouds."),
    ("cat-office", "1536x1024", "A bright open-plan office with people at desks, printer, sticky notes, daily office life."),
    ("cat-communication", "1536x1024", "People connecting via emails, phone calls and chat bubbles between two desks."),
    ("cat-operations", "1536x1024", "A manager reviewing dashboards and checklists over a factory-and-office split scene."),
    ("cat-travel", "1536x1024", "An airport departure hall with travelers, airplane through window, passport and tickets."),
    ("cat-hr", "1536x1024", "An HR specialist welcoming a new employee, org chart and resumes on the wall."),
    ("cat-procurement", "1536x1024", "Warehouse logistics: forklift, packages, delivery truck and a clipboard checklist."),
    ("cat-general", "1536x1024", "A diverse team of professionals collaborating around a table with documents and laptops."),
    ("cat-finance", "1536x1024", "An accountant with calculator, charts, invoices and a piggy bank on a tidy desk."),
    ("cat-marketing", "1536x1024", "A marketing team around a whiteboard with growth chart, megaphone and product mockups."),
    ("cat-hospitality", "1536x1024", "A hotel concierge and a restaurant waiter serving happy guests, elegant lobby-dining scene."),
    ("cat-tech", "1536x1024", "An IT support engineer fixing a laptop, server racks and code windows in background."),
    ("cat-meetings", "1536x1024", "A presenter giving a slideshow to colleagues in a glass meeting room, projector screen."),
    ("cat-customer-service", "1536x1024", "A friendly call-center agent with headset helping a customer, chat windows floating."),
    ("cat-legal", "1536x1024", "A lawyer reviewing a contract with scales of justice, shield and compliance checkmarks."),
    ("cat-real-estate", "1536x1024", "A real-estate agent showing a modern house to a couple, keys and floor plan in hand."),
]


def make(spec):
    name, size, scene = spec
    webp = os.path.join(IMGDIR, f"{name}.webp")
    if os.path.exists(webp):
        return name, "skip"
    png = os.path.join(CACHE, f"{name}.png")
    if not os.path.exists(png):
        azlib.gen_image(f"{STYLE} Scene: {scene}", png, size=size, quality="medium")
    img = Image.open(png).convert("RGB")
    w, h = img.size
    target_w = 768
    img = img.resize((target_w, int(h * target_w / w)), Image.LANCZOS)
    img.save(webp, "WEBP", quality=82)
    return name, f"{os.path.getsize(webp)//1024} KB"


failed = []
with ThreadPoolExecutor(max_workers=3) as ex:
    futs = {ex.submit(make, s): s[0] for s in SPECS}
    for fut in as_completed(futs):
        name = futs[fut]
        try:
            n, info = fut.result()
            print(f"{n}: {info}", flush=True)
        except Exception as e:
            failed.append(name)
            print(f"FAIL {name}: {str(e)[:150]}", flush=True)

print(f"done, failed={failed}")
