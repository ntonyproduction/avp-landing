"""avp_x - publish videos and text to the Audio Vision Productions X account (@audiovisionprod).

ONE credential store, outside every repo:

  store:  %AVP_X_HOME%  or  <home>/.avp/x
  file:   credentials.json  {consumer_key, consumer_secret, access_token, access_secret, username}

The developer account is "AVP Publishing" at console.x.com (created 2026-11-13), app 33638475,
"Read and write", pay-per-use credits. Posts cost $0.015 each; a post WITH A LINK costs $0.20,
so captions say "Link in bio" and never carry a URL (the script refuses one).

Commands
  auth     store the app's OAuth 1.0a keys, read at prompts so they never land in a shell
           history or a chat:
             py -3 -u scripts\\avp_x.py auth
  whoami   which account the keys post as
  post     one video (or text only); --dry-run stops before anything is uploaded
  verify   read a post back by id

Videos go up through the v2 chunked media upload. X takes up to 512 MB but is fussy about
bitrate, so anything above 20 Mbit/s is re-encoded first to a temporary H.264 copy (the
Dropbox master is never touched).

Windows: run with `py -3 -u`. Needs `requests`; ffmpeg/ffprobe on PATH for the re-encode.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import requests

API = "https://api.x.com/2"
PINNED_USERNAME = "audiovisionprod"
TEXT_MAX = 280
CHUNK = 4 * 1024 * 1024
MAX_MBPS = 20


def store() -> Path:
    return Path(os.environ.get("AVP_X_HOME", Path.home() / ".avp" / "x"))


def load() -> dict:
    path = store() / "credentials.json"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        sys.exit(f"no credentials at {path}. Run `auth` first.")


def save(creds: dict) -> None:
    path = store() / "credentials.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(creds, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    print(f"wrote {path}")


# --------------------------------------------------------------------------- OAuth 1.0a

def _q(s: str) -> str:
    return urllib.parse.quote(str(s), safe="~")


def oauth_header(creds: dict, method: str, url: str, params: dict | None = None) -> str:
    """HMAC-SHA1 signature over the query/form params and the oauth_* params.
    JSON and multipart bodies are not signed, per the OAuth 1.0a spec."""
    oauth = {
        "oauth_consumer_key": creds["consumer_key"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": creds["access_token"],
        "oauth_version": "1.0",
    }
    base_url = url.split("?")[0]
    allp = {**(params or {}), **oauth}
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    allp.update(query)
    pstr = "&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(allp.items()))
    base = "&".join([method.upper(), _q(base_url), _q(pstr)])
    key = f"{_q(creds['consumer_secret'])}&{_q(creds['access_secret'])}"
    oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_q(k)}="{_q(v)}"' for k, v in sorted(oauth.items()))


def call(creds: dict, method: str, path: str, *, params: dict | None = None, json_body=None,
         files=None, data=None, ok=(200, 201, 202, 204)):
    url = path if path.startswith("http") else f"{API}/{path.lstrip('/')}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    headers = {"Authorization": oauth_header(creds, method, url)}
    try:
        r = requests.request(method, url, headers=headers, json=json_body, files=files, data=data, timeout=300)
    except requests.RequestException as e:
        sys.exit(f"could not reach X: {e}")
    if r.status_code not in ok:
        sys.exit(f"X returned {r.status_code} for {method} {path.split('?')[0]}: {r.text[:500]}")
    return r.json() if r.content else {}


def account(creds: dict) -> dict:
    me = call(creds, "GET", "users/me").get("data", {})
    if me.get("username", "").lower() != PINNED_USERNAME:
        sys.exit(f"REFUSING: these keys post as @{me.get('username')}, not @{PINNED_USERNAME}.")
    return me


# --------------------------------------------------------------------------- commands

def cmd_auth(args) -> None:
    print("Paste each value from console.x.com > Apps > AVP Publishing > Keys & Tokens (input is hidden).")
    creds = {
        "consumer_key": getpass.getpass("API key (consumer key): ").strip(),
        "consumer_secret": getpass.getpass("API key secret (consumer secret): ").strip(),
        "access_token": getpass.getpass("Access token: ").strip(),
        "access_secret": getpass.getpass("Access token secret: ").strip(),
    }
    me = account(creds)
    creds["username"] = me["username"]
    save(creds)
    print(f"ready: posts will go to @{me['username']} on X")


def cmd_whoami(args) -> None:
    me = account(load())
    print(f"@{me['username']}  (x user {me['id']})")


def probe(path: Path) -> tuple[float, float]:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,bit_rate",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    f = json.loads(out)["format"]
    return float(f["duration"]), float(f.get("bit_rate", 0)) / 1e6


def x_copy(video: Path) -> Path:
    """Return a file X will accept: the master if its bitrate is sane, else a temp re-encode."""
    dur, mbps = probe(video)
    print(f"  {video.name}: {dur:.1f}s at {mbps:.1f} Mbit/s")
    if dur > 140:
        sys.exit("X takes videos up to 140 s on a standard account")
    if mbps <= MAX_MBPS:
        return video
    if not shutil.which("ffmpeg"):
        sys.exit(f"{mbps:.0f} Mbit/s is too high for X and ffmpeg is not on PATH to re-encode it")
    out = Path(tempfile.mkdtemp(prefix="avp-x-")) / (video.stem + " (x).mp4")
    print(f"  re-encoding for X (H.264, max 12 Mbit/s) -> temp ...")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-c:v", "libx264", "-preset", "medium",
                    "-crf", "19", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    print(f"  {out.stat().st_size / 1048576:.1f} MB")
    return out


def upload_video(creds: dict, path: Path) -> str:
    size = path.stat().st_size
    init = call(creds, "POST", "media/upload/initialize",
                json_body={"media_type": "video/mp4", "total_bytes": size, "media_category": "tweet_video"})
    mid = init["data"]["id"]
    print(f"  uploading {size / 1048576:.1f} MB in {max(1, -(-size // CHUNK))} parts ...")
    with open(path, "rb") as fh:
        i = 0
        while chunk := fh.read(CHUNK):
            call(creds, "POST", f"media/upload/{mid}/append", files={"media": ("chunk", chunk)},
                 data={"segment_index": str(i)})
            i += 1
    fin = call(creds, "POST", f"media/upload/{mid}/finalize").get("data", {})
    info = fin.get("processing_info")
    while info and info.get("state") in ("pending", "in_progress"):
        time.sleep(max(2, int(info.get("check_after_secs", 5))))
        st = call(creds, "GET", "media/upload", params={"command": "STATUS", "media_id": mid}).get("data", {})
        info = st.get("processing_info")
        print(f"  processing: {info.get('state') if info else 'done'} {info.get('progress_percent', '') if info else ''}")
    if info and info.get("state") == "failed":
        sys.exit(f"X could not process the video: {info.get('error')}")
    return mid


def cmd_post(args) -> None:
    creds = load()
    me = account(creds)
    text = Path(args.caption_file).read_text(encoding="utf-8").strip() if args.caption_file else (args.text or "")
    if re.search(r"https?://|www\.|\.(ca|com|net|org)\b", text):
        sys.exit("REFUSING: the caption contains a link, which costs $0.20 a post instead of $0.015. "
                 "Say 'Link in bio' instead.")
    if len(text) > TEXT_MAX:
        sys.exit(f"the caption is {len(text)} characters; X allows {TEXT_MAX} on a standard account.")
    tmp = None
    try:
        body = {"text": text}
        if args.video:
            video = Path(args.video)
            if not video.is_file():
                sys.exit(f"no such file: {video}")
            ready = x_copy(video)
            tmp = ready if ready != video else None
            if args.dry_run:
                print(f"dry run: would post {ready.name} to @{me['username']} with:\n{text}")
                return
            body["media"] = {"media_ids": [upload_video(creds, ready)]}
        elif args.dry_run:
            print(f"dry run: would post text to @{me['username']}:\n{text}")
            return
        post = call(creds, "POST", "tweets", json_body=body).get("data", {})
        print(f"published: {post.get('id')}\n  https://x.com/{me['username']}/status/{post.get('id')}")
    finally:
        if tmp:
            shutil.rmtree(tmp.parent, ignore_errors=True)


def cmd_verify(args) -> None:
    creds = load()
    p = call(creds, "GET", f"tweets/{args.id}", params={"tweet.fields": "created_at,attachments"}).get("data", {})
    print(f"  {p.get('created_at')}  {p.get('text', '')[:80]}\n  https://x.com/{creds.get('username')}/status/{p.get('id')}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth").set_defaults(fn=cmd_auth)
    sub.add_parser("whoami").set_defaults(fn=cmd_whoami)
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
