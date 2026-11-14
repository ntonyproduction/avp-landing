"""crosspost_queue - repost proven Instagram reels to Facebook, Threads and X, one a day.

The queue is a JSON file in Dropbox (default: AVP Tools\\Organic Ads\\Cross-post queue.json):
a list of items {date "YYYY-MM-DD", tool, ad, ig_code, video, text, fb_text, done{...}}.
`text` is the "Link in bio" caption for Threads and X (no URL: a link costs $0.20 on X);
`fb_text` ends with audiovisionproductions.ca/facebook.

Commands
  schedule-facebook   upload every future item to Facebook now as a scheduled reel (Facebook
                      publishes it on its date at --time), and record the video id
  run                 post today's item to Threads and X (whichever is not done yet), record the
                      ids in the queue and in Organic ads log.csv. Meant for a daily run;
                      it does nothing when today has no item or it is already done.
  status              print the queue

Windows: run with `py -3 -u`.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADS = Path.home() / "Dropbox" / "AVP Tools" / "Organic Ads"
QUEUE = ADS / "Cross-post queue.json"
LOG = ADS / "Organic ads log.csv"
PY = sys.executable


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, q: list[dict]) -> None:
    path.write_text(json.dumps(q, indent=2, ensure_ascii=False), encoding="utf-8")


def run_script(*args: str) -> str:
    r = subprocess.run([PY, "-u", str(HERE / args[0]), *args[1:]], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(r.stdout, end="")
    if r.returncode:
        print(r.stderr, end="")
        raise RuntimeError(f"{args[0]} {args[1]} failed")
    return r.stdout


def tmp_caption(text: str, name: str) -> str:
    p = Path(__import__("tempfile").gettempdir()) / f"avp-caption-{name}.txt"
    p.write_text(text, encoding="utf-8")
    return str(p)


def log_ids(ig_code: str, **ids: str) -> None:
    raw = LOG.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    head = list(rows[0].keys())
    hit = [r for r in rows if r["Instagram"].strip() == ig_code]
    if len(hit) != 1:
        print(f"  log: {len(hit)} rows match {ig_code}, not written")
        return
    for col, val in ids.items():
        hit[0][col] = val
    with open(LOG, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=head, lineterminator=nl)
        w.writeheader()
        w.writerows(rows)
    print(f"  log: {hit[0]['Tool']} {hit[0]['Ad'][:30]} <- {ids}")


def cmd_schedule_facebook(args) -> None:
    q = load(args.queue)
    for item in q:
        done = item.setdefault("done", {})
        if done.get("facebook") or item["date"] <= date.today().isoformat():
            continue
        print(f"== {item['date']} {item['tool']} {item['ad']}")
        out = run_script("avp_facebook.py", "post-reel", item["video"],
                         "--caption-file", tmp_caption(item["fb_text"], "fb"),
                         "--at", f"{item['date']} {args.time}")
        m = re.search(r"video (\d+)", out)
        done["facebook"] = m.group(1) if m else "scheduled"
        save(args.queue, q)
        log_ids(item["ig_code"], Facebook=done["facebook"])


def cmd_run(args) -> None:
    q = load(args.queue)
    today = args.date or date.today().isoformat()
    items = [i for i in q if i["date"] == today]
    if not items:
        print(f"nothing queued for {today}")
        return
    item = items[0]
    done = item.setdefault("done", {})
    print(f"== {today} {item['tool']} {item['ad']}")
    failed = []
    for plat, script, pattern in (("threads", "avp_threads.py", r"/post/([A-Za-z0-9_-]+)"),
                                  ("x", "avp_x.py", r"status/(\d+)")):
        if done.get(plat):
            print(f"  {plat}: already posted ({done[plat]})")
            continue
        try:
            out = run_script(script, "post", "--video", item["video"],
                             "--caption-file", tmp_caption(item["text"], plat))
            m = re.search(pattern, out)
            done[plat] = m.group(1) if m else "posted"
            save(args.queue, q)
            log_ids(item["ig_code"], **{"Threads" if plat == "threads" else "X": done[plat]})
        except RuntimeError as e:
            failed.append(str(e))
    if failed:
        sys.exit("FAILED: " + "; ".join(failed))


def cmd_status(args) -> None:
    for i in load(args.queue):
        d = i.get("done", {})
        print(f"{i['date']}  {i['tool']:<9} {i['ad'][:28]:<28}  fb={d.get('facebook', '-')}  "
              f"threads={d.get('threads', '-')}  x={d.get('x', '-')}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queue", type=Path, default=QUEUE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("schedule-facebook"); s.add_argument("--time", default="19:30"); s.set_defaults(fn=cmd_schedule_facebook)
    r = sub.add_parser("run"); r.add_argument("--date"); r.set_defaults(fn=cmd_run)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
