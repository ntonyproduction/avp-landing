"""avp_threads - publish videos and text to the Audio Vision Productions Threads profile.

ONE credential store, outside every repo, like avp_instagram:

  store:  %AVP_THREADS_HOME%  or  <home>/.avp/threads
  file:   credentials.json  {token, user_id, username, saved_at}

Commands
  auth      store a long-lived token from the app's User Token Generator
            (developers.facebook.com > AVP Publishing > Use cases > Access the Threads API >
            Settings > User Token Generator). Read it at a prompt so it never lands in a
            shell history or a chat:
              $t = Read-Host 'token'; py -3 -u scripts\\avp_threads.py auth --token $t
  whoami    which profile the token posts as, its age, and a refresh when it is due
  refresh   trade the token for a fresh 60-day one (needs to be at least 24 h old)
  post      one video (or text only) with a caption; --dry-run stops before publishing
  verify    read a published thread back by id

Threads takes the video as a public URL, never the bytes, so `post` stages the file as a
release asset on avp-landing exactly like avp_instagram's post-reel, and removes it after.

Every command re-reads the profile from the token and REFUSES unless it is the pinned
username: a post cannot be moved between accounts afterwards.

Windows: run with `py -3 -u`. Needs `requests`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import avp_instagram as ig  # noqa: E402  (staging helpers: stage_reel, unstage_reel, url_live, probe_video)

API = "https://graph.threads.net/v1.0"
PINNED_USERNAME = "audiovisionproductions"
TEXT_MAX = 500
REFRESH_AFTER_DAYS = 30          # tokens live 60 days; refresh well before


def store() -> Path:
    return Path(os.environ.get("AVP_THREADS_HOME", Path.home() / ".avp" / "threads"))


def load() -> dict:
    path = store() / "credentials.json"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        sys.exit(f"no credentials at {path}. Run `auth` first (see the module docstring).")


def save(creds: dict) -> None:
    path = store() / "credentials.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(creds, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    print(f"wrote {path}")


def call(method: str, path: str, token: str, **params):
    url = path if path.startswith("http") else f"{API}/{path.lstrip('/')}"
    params["access_token"] = token
    try:
        r = requests.request(method, url, params=params if method == "GET" else None,
                             data=params if method == "POST" else None, timeout=60)
    except requests.RequestException as e:
        sys.exit(f"could not reach Threads: {e}")
    if not r.ok:
        try:
            err = r.json().get("error", {})
            detail = err.get("error_user_msg") or err.get("message") or r.text[:400]
        except ValueError:
            detail = r.text[:400]
        sys.exit(f"Threads returned {r.status_code} for {method} {path.split('?')[0]}: {detail}")
    return r.json()


def account(token: str) -> dict:
    me = call("GET", "me", token, fields="id,username")
    if me.get("username") != PINNED_USERNAME:
        sys.exit(f"REFUSING: this token posts as @{me.get('username')}, not @{PINNED_USERNAME}.")
    return me


def maybe_refresh(creds: dict, force: bool = False) -> dict:
    age_days = (time.time() - creds.get("saved_at", time.time())) / 86400
    if not force and age_days < REFRESH_AFTER_DAYS:
        return creds
    got = call("GET", "https://graph.threads.net/refresh_access_token", creds["token"],
               grant_type="th_refresh_token")
    creds = {**creds, "token": got["access_token"], "saved_at": time.time()}
    save(creds)
    print(f"token refreshed; good for another {int(got.get('expires_in', 0)) // 86400} days")
    return creds


def cmd_auth(args) -> None:
    me = account(args.token)
    save({"token": args.token, "user_id": me["id"], "username": me["username"],
          "saved_at": time.time()})
    print(f"ready: posts will go to @{me['username']} on Threads")


def cmd_whoami(args) -> None:
    creds = maybe_refresh(load())
    me = account(creds["token"])
    age = (time.time() - creds["saved_at"]) / 86400
    print(f"@{me['username']}  (threads user {me['id']}), token {age:.0f} days old, "
          f"refreshed automatically after {REFRESH_AFTER_DAYS}")
    limit = call("GET", f"{me['id']}/threads_publishing_limit", creds["token"],
                 fields="quota_usage,config").get("data", [{}])[0]
    print(f"published in the last 24h: {limit.get('quota_usage', '?')}/"
          f"{(limit.get('config') or {}).get('quota_total', 250)}")


def cmd_refresh(args) -> None:
    maybe_refresh(load(), force=True)


def wait_ready(token: str, cid: str, timeout: int = 600) -> None:
    print("waiting for Threads to process it ...")
    deadline = time.time() + timeout
    while True:
        s = call("GET", cid, token, fields="status,error_message")
        if s.get("status") == "FINISHED":
            print("  ready")
            return
        if s.get("status") in ("ERROR", "EXPIRED"):
            sys.exit(f"Threads could not process it: {s.get('error_message') or s.get('status')}")
        if time.time() > deadline:
            sys.exit(f"timed out; container {cid} is still {s.get('status')}")
        time.sleep(10)


def cmd_post(args) -> None:
    creds = maybe_refresh(load())
    me = account(creds["token"])
    text = Path(args.caption_file).read_text(encoding="utf-8").strip() if args.caption_file else (args.text or "")
    if len(text) > TEXT_MAX:
        sys.exit(f"the caption is {len(text)} characters; Threads allows {TEXT_MAX}.")
    asset = None
    try:
        if args.video:
            video = Path(args.video)
            if not video.is_file():
                sys.exit(f"no such file: {video}")
            ig.probe_video(video)
            if args.dry_run:
                print(f"dry run: would post {video.name} to @{me['username']} with:\n{text}")
                return
            url, asset = ig.stage_reel(video)
            ig.url_live(url)
            cid = call("POST", f"{me['id']}/threads", creds["token"], media_type="VIDEO",
                       video_url=url, text=text)["id"]
            wait_ready(creds["token"], cid)
        else:
            if args.dry_run:
                print(f"dry run: would post text to @{me['username']}:\n{text}")
                return
            cid = call("POST", f"{me['id']}/threads", creds["token"], media_type="TEXT",
                       text=text)["id"]
        post_id = call("POST", f"{me['id']}/threads_publish", creds["token"], creation_id=cid)["id"]
        print(f"published: {post_id}")
        show(creds["token"], post_id)
    finally:
        if asset:
            ig.unstage_reel(asset)


def show(token: str, post_id: str) -> None:
    p = call("GET", post_id, token, fields="id,permalink,media_type,timestamp,username")
    print(f"  @{p.get('username')}  {p.get('media_type')}  {p.get('timestamp')}\n  {p.get('permalink')}")


def cmd_verify(args) -> None:
    show(load()["token"], args.id)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("auth"); a.add_argument("--token", required=True); a.set_defaults(fn=cmd_auth)
    sub.add_parser("whoami").set_defaults(fn=cmd_whoami)
    sub.add_parser("refresh").set_defaults(fn=cmd_refresh)
    p = sub.add_parser("post")
    p.add_argument("--video")
    p.add_argument("--text")
    p.add_argument("--caption-file")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_post)
    v = sub.add_parser("verify"); v.add_argument("id"); v.set_defaults(fn=cmd_verify)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
