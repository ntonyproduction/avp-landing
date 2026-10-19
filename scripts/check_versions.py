"""Checks that every tool card on the home page shows the same version as the tool's own page.

    py -3 scripts/check_versions.py

Run it before pushing any tool update. The home page's card chip ("v1.2") is written by hand and nothing else
updates it: a tool page rebuilt by its repo's build_landing.py moves to the new version, the card stays behind.
That happened twice (Paperboy 1.2, 2026-10-19, and before it). Exits 1 and names each card that disagrees.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
home = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
cards = re.findall(r'<h2>([^<]+)</h2><span class="chips"><span class="chip">v([0-9.]+)<', home)
if not cards:
    sys.exit("no tool cards found on index.html: the card markup changed, so update this check")

bad = []
for name, card in cards:
    page = os.path.join(ROOT, name.lower(), "index.html")
    if not os.path.exists(page):
        bad.append(f"{name}: no {name.lower()}/index.html to compare with")
        continue
    m = re.search(r'class="chip">v([0-9.]+)<', open(page, encoding="utf-8").read())
    if not m:
        bad.append(f"{name}: no version chip on its page")
    elif m.group(1) != card:
        bad.append(f"{name}: home card says v{card}, its page says v{m.group(1)}")
    else:
        print(f"ok  {name} v{card}")

for b in bad:
    print("MISMATCH  " + b)
sys.exit(1 if bad else 0)
