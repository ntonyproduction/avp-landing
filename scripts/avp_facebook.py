"""avp_facebook - publish reels to the Audio Vision Productions Facebook Page.

Uses the Page token avp_instagram stores (%USERPROFILE%\\.avp\\instagram\\credentials.json),
which carries pages_manage_posts since 2026-11-13. No second credential.

Commands
  post-reel  one vertical video to the Page as a reel, now or scheduled
             --at "2026-11-14 18:00" schedules it (local time, 10 min to 75 days ahead);
             --dry-run stops before anything is uploaded
  verify     read a reel back by its video id

Facebook fetches the video from a public URL (the file_url upload), so the file is staged
as a release asset on avp-landing exactly like avp_instagram's post-reel, and removed once
Facebook has it.

Windows: run with `py -3 -u`. Needs `requests`.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import avp_instagram as ig  # noqa: E402

API = ig.API
PAGE_NAME = "Audio Vision Productions"


def page(creds: dict) -> dict:
    p = ig.graph("GET", creds["page_id"], fields="id,name", access_token=creds["page_token"])
    if p.get("name") != PAGE_NAME:
        sys.exit(f"REFUSING: the stored token's Page is {p.get('name')!r}, not {PAGE_NAME!r}.")
    return p


def wait_uploaded(creds: dict, vid: str, timeout: int = 900) -> None:
    print("waiting for Facebook to fetch and process it ...")
    deadline = time.time() + timeout
    while True:
        s = ig.graph("GET", vid, fields="status", access_token=creds["page_token"]).get("status", {})
        up = (s.get("uploading_phase") or {}).get("status")
        proc = (s.get("processing_phase") or {}).get("status")
        if up == "error" or proc == "error":
            sys.exit(f"Facebook could not take the video: {s}")
        if up == "complete":
            print(f"  uploaded (processing: {proc or 'queued'})")
            return
        if time.time() > deadline:
            sys.exit(f"timed out waiting for the upload: {s}")
        time.sleep(5)


def cmd_post_reel(args) -> None:
    creds = ig.load()
    p = page(creds)
    video = Path(args.video)
    if not video.is_file():
        sys.exit(f"no such file: {video}")
    text = Path(args.caption_file).read_text(encoding="utf-8").strip() if args.caption_file else (args.text or "")
    when = None
    if args.at:
        when = int(datetime.strptime(args.at, "%Y-%m-%d %H:%M").timestamp())
        if not 600 <= when - time.time() <= 75 * 86400:
            sys.exit("--at must be between 10 minutes and 75 days from now")
    ig.probe_video(video)
    if args.dry_run:
        print(f"dry run: would post {video.name} to the Page {p['name']!r}"
              f"{' at ' + args.at if args.at else ' now'} with:\n{text}")
        return

    start = ig.graph("POST", f"{p['id']}/video_reels", upload_phase="start",
                     access_token=creds["page_token"])
    vid = start["video_id"]
    url, asset = ig.stage_reel(video)
    try:
        ig.url_live(url)
        r = requests.post(start["upload_url"], timeout=120,
                          headers={"Authorization": f"OAuth {creds['page_token']}", "file_url": url})
        if not r.ok:
            sys.exit(f"Facebook refused the file URL: {r.status_code} {r.text[:300]}")
        wait_uploaded(creds, vid)
    finally:
        ig.unstage_reel(asset)

    extra = {"video_state": "SCHEDULED", "scheduled_publish_time": when} if when else {"video_state": "PUBLISHED"}
    done = ig.graph("POST", f"{p['id']}/video_reels", upload_phase="finish", video_id=vid,
                    description=text, access_token=creds["page_token"], **extra)
    if not done.get("success"):
        sys.exit(f"finish did not succeed: {done}")
    print(f"{'scheduled for ' + args.at if when else 'published'}: video {vid}")
    show(creds, vid)


def show(creds: dict, vid: str) -> None:
    v = ig.try_graph("GET", vid, fields="id,permalink_url,status,created_time,scheduled_publish_time,published",
                     access_token=creds["page_token"]) or {}
    link = v.get("permalink_url", "")
    if link.startswith("/"):
        link = "https://www.facebook.com" + link
    print(f"  {link}  published={v.get('published')}  status={(v.get('status') or {}).get('video_status')}")


def cmd_verify(args) -> None:
    show(ig.load(), args.id)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post-reel")
    p.add_argument("video")
    p.add_argument("--text")
    p.add_argument("--caption-file")
    p.add_argument("--at")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_post_reel)
    v = sub.add_parser("verify"); v.add_argument("id"); v.set_defaults(fn=cmd_verify)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
