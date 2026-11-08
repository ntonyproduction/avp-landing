"""Checks that every tool card on the home page shows the same version as the tool's own page.

    py -3 scripts/check_versions.py

Run it before pushing any tool update. The home page's card chip ("v1.2") is written by hand and nothing else
updates it: a tool page rebuilt by its repo's build_landing.py moves to the new version, the card stays behind.
That happened twice (Paperboy 1.2, 2026-10-19, and before it). Exits 1 and names each card that disagrees.

It also checks the "Most downloaded" badge (the `top` class, 2026-11-08): among the free tools on the home page, the
one with the most confirmed Kit subscribers on its tool tag must be the card wearing it, or this exits 1 and names
the one that passed it. The Kit key is read from KIT_API_KEY or time-tracker's .env.local beside this repo, never
printed; with no key or no network, that check says it was skipped and does not fail.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

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


def kit_key():
    if os.environ.get("KIT_API_KEY"):
        return os.environ["KIT_API_KEY"]
    for f in (".env.local", ".env"):
        path = os.path.join(os.path.dirname(ROOT), "time-tracker", f)
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                if line.startswith("KIT_API_KEY=") and line.split("=", 1)[1].strip().strip('"'):
                    return line.split("=", 1)[1].strip().strip('"')
    return None


def kit_signups(key, tools):
    # Confirmed subscribers per tool tag, as the daily email-list report counts them (time-tracker src/lib/kit.ts)
    def get(path, **q):
        req = urllib.request.Request("https://api.kit.com/v4" + path + "?" + urllib.parse.urlencode(q),
                                     headers={"X-Kit-Api-Key": key, "Accept": "application/json",
                                              "User-Agent": "avp-check-versions"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    ids, after = {}, None
    while True:
        d = get("/tags", per_page=1000, **({"after": after} if after else {}))
        ids.update({t["name"]: t["id"] for t in d["tags"]})
        if not d["pagination"]["has_next_page"]:
            break
        after = d["pagination"]["end_cursor"]
    return {t: get(f"/tags/{ids[t]}/subscribers", per_page=1, include_total_count="true",
                   status="active")["pagination"]["total_count"] for t in tools if t in ids}


# One block per card: its classes, its name and whether its price says Free
blocks = re.findall(r'<a class="card([^"]*)"[^>]*>(.*?)</a>', home, re.S)
free = [re.search(r"<h2>([^<]+)</h2>", b).group(1) for c, b in blocks if '<p class="price">Free</p>' in b]
badged = [re.search(r"<h2>([^<]+)</h2>", b).group(1) for c, b in blocks if " top" in f" {c} "]
if len(badged) > 1:
    bad.append("Most downloaded: on " + " and ".join(badged) + ", one card only")
elif badged:
    key = kit_key()
    if not key:
        print(f"skip  Most downloaded ({badged[0]}): no Kit key here to check it with")
    else:
        try:
            counts = kit_signups(key, [n.lower() for n in free])
        except Exception as e:  # noqa: BLE001 - no network, Kit down: say so, never fail the push on it
            counts = None
            print(f"skip  Most downloaded ({badged[0]}): Kit did not answer ({e.__class__.__name__})")
        if counts:
            lead = max(counts, key=counts.get)
            mine = counts.get(badged[0].lower(), 0)
            if lead != badged[0].lower():
                bad.append(f"Most downloaded: {lead.capitalize()} has {counts[lead]:,} signups, {badged[0]} {mine:,}; "
                           "move the `top` class to its card")
            else:
                runner = sorted(counts.values())[-2] if len(counts) > 1 else 0
                print(f"ok  Most downloaded: {badged[0]} {mine:,} signups (next {runner:,})")

for b in bad:
    print("MISMATCH  " + b)
sys.exit(1 if bad else 0)
