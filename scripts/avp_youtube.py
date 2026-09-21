"""avp_youtube - upload and schedule videos on the Audio Vision Productions channel.

ONE credential store for every repo. Nothing secret lives in a project folder.

  store:  %AVP_YT_HOME%  or  <home>/.avp/youtube
  file:   credentials.json  {client_id, client_secret, refresh_token, channel_handle}

Commands
  auth      one-time browser consent; writes refresh_token + the channel it belongs to
  whoami    print which channel the stored token posts to
  upload    one video (flags) or many (--batch entries.json)
  verify    read a video back by id

Every upload re-reads the token's channel and REFUSES if it is not the pinned handle:
an API-uploaded video cannot be moved between channels afterwards.

Windows: run with `py -3.14 -u`. Needs `requests` (pip install requests).
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(errors="replace", line_buffering=True)
    sys.stderr.reconfigure(errors="replace", line_buffering=True)
except Exception:  # noqa: BLE001
    pass

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
API_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
# upload = post the video; readonly = read it back, so a run is verified on the
# artifact and not on the request. Editing an existing video's metadata or touching
# playlists would need youtube.force-ssl: re-run `auth` if that is ever added.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]
DEFAULT_HANDLE = "@audiovisionproductions"
MAX_TITLE, MAX_DESC, MAX_TAGS_CHARS = 100, 5000, 460
CHUNK = 8 * 1024 * 1024
MIME = {".mp4": "video/mp4", ".mov": "video/quicktime", ".mkv": "video/x-matroska",
        ".webm": "video/webm", ".avi": "video/x-msvideo", ".m4v": "video/x-m4v"}


def store_dir() -> Path:
    return Path(os.environ.get("AVP_YT_HOME") or (Path.home() / ".avp" / "youtube"))


def creds_path() -> Path:
    return store_dir() / "credentials.json"


def read_creds(require_token: bool = True) -> dict:
    p = creds_path()
    if not p.is_file():
        sys.exit(f"no credential store at {p}\nCreate it with the Desktop-app OAuth "
                 'client:\n  {"client_id": "...", "client_secret": "...", '
                 f'"channel_handle": "{DEFAULT_HANDLE}"}}\nthen run:  auth')
    c = json.loads(p.read_text(encoding="utf-8"))
    for k in ("client_id", "client_secret"):
        if not c.get(k):
            sys.exit(f"{p} is missing {k}")
    if require_token and not c.get("refresh_token"):
        sys.exit(f"{p} has no refresh_token yet - run:  auth")
    c.setdefault("channel_handle", DEFAULT_HANDLE)
    return c


def write_creds(c: dict) -> None:
    p = creds_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(c, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:  # noqa: BLE001
        pass          # Windows: rely on the user profile's own ACL


def _requests():
    # NOT named http(): that name shadows the http.server module imported above and
    # breaks `auth` with AttributeError (hit on the first real run, 2026-09-12).
    try:
        import requests
    except ImportError:
        sys.exit("this script needs `requests`:  py -3.14 -m pip install requests")
    return requests


def access_token(c: dict) -> str:
    requests = _requests()
    r = requests.post(TOKEN_URL, data={
        "client_id": c["client_id"], "client_secret": c["client_secret"],
        "refresh_token": c["refresh_token"], "grant_type": "refresh_token"}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"token refresh failed: {r.status_code} {r.text[:300]}\n"
                 "invalid_grant means the refresh token was revoked - run:  auth")
    return r.json()["access_token"]


def channel(token: str) -> dict:
    requests = _requests()
    r = requests.get(CHANNELS_URL, params={"part": "snippet", "mine": "true"},
                     headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"could not read the token's channel: {r.status_code} {r.text[:300]}")
    items = r.json().get("items") or []
    if not items:
        sys.exit("the token is valid but owns no channel - consent was approved on an "
                 "account with no YouTube channel. Run:  auth")
    return items[0]


def assert_channel(token: str, expected: str, allow_any: bool) -> None:
    ch = channel(token)
    sn = ch.get("snippet", {})
    handle = (sn.get("customUrl") or "").lower()
    print(f"[yt] channel: {sn.get('title', '?')} ({handle or 'no handle'})")
    if allow_any or handle == expected.lower():
        return
    sys.exit(f"REFUSING TO UPLOAD: the token posts to {handle or 'an unnamed channel'}, "
             f"expected {expected}. Consent was approved on the wrong Google account or "
             "channel - run `auth` signed in as the owner. An uploaded video cannot be "
             "moved between channels afterwards. (--allow-any-channel overrides.)")


# --------------------------------------------------------------------- scheduling ----
def publish_at_utc(stamp: str) -> str:
    """'2026-09-20 08:00' (this machine's timezone) or an ISO stamp with an explicit
    offset -> '2026-09-20T12:00:00Z'. Must be in the future."""
    s = stamp.strip().replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        sys.exit(f"could not read --publish-at {stamp!r}. Use '2026-09-20 08:00' or a "
                 "full ISO stamp like '2026-09-20T08:00:00-04:00'")
    if dt.tzinfo is None:
        dt = dt.astimezone()          # this machine's local zone
    if dt <= datetime.now(timezone.utc):
        sys.exit(f"--publish-at {stamp!r} is in the past ({dt.isoformat()})")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_body(entry: dict) -> dict:
    title = (entry.get("title") or "").strip()
    desc = entry.get("description") or ""
    if not title:
        sys.exit("every video needs a title")
    if len(title) > MAX_TITLE:
        sys.exit(f"title is {len(title)} chars, the limit is {MAX_TITLE}: {title!r}")
    if "<" in title + desc or ">" in title + desc:
        sys.exit("YouTube rejects < and > in the title or description")
    if len(desc) > MAX_DESC:
        sys.exit(f"description is {len(desc)} chars, the limit is {MAX_DESC}")
    tags = entry.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    # YouTube counts the whole tag list against ~500 chars (quoted tags cost more)
    total = sum(len(t) + 2 for t in tags)
    if total > MAX_TAGS_CHARS:
        sys.exit(f"tags total {total} chars, keep them under {MAX_TAGS_CHARS}")

    visibility = (entry.get("visibility") or "private").lower()
    if visibility not in ("private", "unlisted", "public"):
        sys.exit(f"visibility must be private, unlisted or public, got {visibility!r}")
    status = {"privacyStatus": visibility, "selfDeclaredMadeForKids": False}
    if entry.get("publish_at"):
        # a scheduled video MUST be uploaded private; YouTube flips it public itself
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at_utc(entry["publish_at"])
    return {"snippet": {"title": title, "description": desc, "tags": tags,
                        "categoryId": str(entry.get("category") or 22)},
            "status": status}


# ------------------------------------------------------------------------- upload ----
def resume_offset(session: str, size: int):
    requests = _requests()
    r = requests.put(session, headers={"Content-Length": "0",
                                       "Content-Range": f"bytes */{size}"}, timeout=120)
    if r.status_code == 308:
        rng = r.headers.get("Range")
        return int(rng.split("-")[1]) + 1 if rng else 0
    return None


def upload(entry: dict, token: str) -> str:
    requests = _requests()
    path = Path(entry["file"]).expanduser()
    if not path.is_file():
        sys.exit(f"file not found: {path}")
    size = path.stat().st_size
    body = build_body(entry)
    print(f"[yt] {path.name} ({size / 1048576:.0f} MB) -> "
          f"{body['status']['privacyStatus']}"
          + (f", publishAt {body['status']['publishAt']}"
             if body["status"].get("publishAt") else ""), flush=True)

    r = requests.post(UPLOAD_URL,
                      params={"uploadType": "resumable", "part": "snippet,status"},
                      headers={"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Length": str(size),
                               "X-Upload-Content-Type": MIME.get(path.suffix.lower(),
                                                                 "video/*")},
                      json=body, timeout=120)
    if r.status_code not in (200, 201):
        sys.exit(f"could not start the upload: {r.status_code} {r.text[:500]}")
    session = r.headers.get("Location")
    if not session:
        sys.exit("no resumable session URL returned")

    sent, attempts = 0, 0
    with open(path, "rb") as fh:
        while sent < size:
            fh.seek(sent)
            chunk = fh.read(CHUNK)
            end = sent + len(chunk) - 1
            try:
                pr = requests.put(session, data=chunk, headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {sent}-{end}/{size}"}, timeout=600)
            except Exception as exc:  # noqa: BLE001 - any transport error resumes
                attempts += 1
                if attempts > 5:
                    sys.exit(f"upload failed after 5 retries: {exc}")
                print(f"  network error, retrying ({attempts}/5): {exc}", flush=True)
                sent = resume_offset(session, size) or sent
                continue
            if pr.status_code in (200, 201):
                vid = pr.json()["id"]
                print(f"  100% - video id {vid}")
                return vid
            if pr.status_code == 308:
                rng = pr.headers.get("Range")
                sent = int(rng.split("-")[1]) + 1 if rng else sent + len(chunk)
                attempts = 0
                print(f"  {sent * 100 // size}%", end="\r", flush=True)
                continue
            if pr.status_code in (500, 502, 503, 504):
                attempts += 1
                if attempts > 5:
                    sys.exit(f"upload failed after 5 retries: {pr.status_code}")
                time.sleep(2 ** attempts)
                sent = resume_offset(session, size) or sent
                continue
            sys.exit(f"upload failed: {pr.status_code} {pr.text[:500]}")
    sys.exit("upload loop ended without a video id")


def verify(vid: str, token: str) -> dict:
    requests = _requests()
    r = requests.get(API_URL, params={"part": "snippet,status", "id": vid},
                     headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if r.status_code != 200:
        print(f"  !! verify failed: {r.status_code} {r.text[:300]}")
        return {}
    items = r.json().get("items") or []
    if not items:
        print(f"  !! verify: video {vid} not returned")
        return {}
    st, sn = items[0].get("status", {}), items[0].get("snippet", {})
    print(f"  verified: privacy={st.get('privacyStatus')} "
          f"publishAt={st.get('publishAt')} upload={st.get('uploadStatus')}")
    print(f"            title={sn.get('title', '')[:70]!r}")
    print(f"            https://youtu.be/{vid}")
    return items[0]


# --------------------------------------------------------------------------- auth ----
def cmd_auth(a) -> int:
    requests = _requests()
    c = read_creds(require_token=False)
    port = _free_port()
    redirect = f"http://127.0.0.1:{port}"
    state = secrets.token_urlsafe(16)
    got, done = {}, threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            ok = got.get("state") == state and "code" in got
            self.wfile.write((("<h2>Authorised.</h2><p>Close this tab.</p>") if ok
                              else f"<h2>Failed</h2><pre>{got}</pre>").encode("utf-8"))
            done.set()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    params = {"client_id": c["client_id"], "redirect_uri": redirect,
              "response_type": "code", "scope": " ".join(SCOPES),
              "access_type": "offline", "prompt": "consent", "state": state}
    print(f"\n1. Open this URL signed in as the owner of {c['channel_handle']}:\n")
    print("   " + AUTH_URL + "?" + urllib.parse.urlencode(params) + "\n")
    print("2. Approve the upload + read permissions. Waiting (Ctrl-C aborts)...\n")
    if not done.wait(timeout=600):
        srv.shutdown()
        sys.exit("timed out after 10 minutes waiting for the browser redirect")
    srv.shutdown()
    if got.get("state") != state or "code" not in got:
        sys.exit(f"authorisation failed: {got}")
    r = requests.post(TOKEN_URL, data={
        "code": got["code"], "client_id": c["client_id"],
        "client_secret": c["client_secret"], "redirect_uri": redirect,
        "grant_type": "authorization_code"}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"token exchange failed: {r.status_code} {r.text[:400]}")
    refresh = r.json().get("refresh_token")
    if not refresh:
        sys.exit("Google returned no refresh_token. Remove this app at "
                 "https://myaccount.google.com/permissions and run auth again.")
    c["refresh_token"] = refresh
    tok = access_token(c)
    handle = (channel(tok).get("snippet", {}).get("customUrl") or "").lower()
    if handle and c.get("channel_handle") and handle != c["channel_handle"].lower():
        sys.exit(f"consent was approved for {handle}, but the store is pinned to "
                 f"{c['channel_handle']}. Nothing was saved. Re-run signed in as the "
                 "right channel, or change channel_handle in credentials.json first.")
    c["channel_handle"] = handle or c["channel_handle"]
    write_creds(c)
    print(f"[auth] refresh token stored in {creds_path()} for {c['channel_handle']}")
    return 0


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ----------------------------------------------------------------------- commands ----
def entries_from(a) -> list[dict]:
    if a.batch:
        data = json.loads(Path(a.batch).read_text(encoding="utf-8"))
        items = data["videos"] if isinstance(data, dict) else data
        base = Path(a.batch).resolve().parent
        for e in items:
            p = Path(e["file"]).expanduser()
            e["file"] = str(p if p.is_absolute() else base / p)
        return items
    if not a.file:
        sys.exit("pass --file <video> or --batch <json>")
    desc = a.description or ""
    if a.description_file:
        desc = Path(a.description_file).read_text(encoding="utf-8")
    return [{"file": a.file, "title": a.title, "description": desc, "tags": a.tags,
             "publish_at": a.publish_at, "visibility": a.visibility,
             "category": a.category}]


def cmd_upload(a) -> int:
    entries = entries_from(a)
    bodies = [build_body(e) for e in entries]      # validate everything before uploading
    for e, b in zip(entries, bodies):
        p = Path(e["file"]).expanduser()
        mb = p.stat().st_size / 1048576 if p.is_file() else 0
        print(f"- {p.name} ({mb:.0f} MB) {b['status']['privacyStatus']}"
              f"{' @ ' + b['status']['publishAt'] if b['status'].get('publishAt') else ''}"
              f"  {b['snippet']['title']!r}")
        if not p.is_file():
            sys.exit(f"file not found: {p}")
    if a.dry_run:
        print(f"[dry] {len(entries)} video(s) validated, nothing uploaded")
        return 0
    c = read_creds()
    token = access_token(c)
    assert_channel(token, c["channel_handle"], a.allow_any_channel)  # before any bytes
    for i, e in enumerate(entries, 1):
        print(f"[{i}/{len(entries)}]")
        vid = upload(e, token)
        verify(vid, token)
    return 0


def cmd_whoami(a) -> int:
    c = read_creds()
    tok = access_token(c)
    ch = channel(tok)
    sn = ch.get("snippet", {})
    print(f"store:   {creds_path()}")
    print(f"pinned:  {c['channel_handle']}")
    print(f"token:   {sn.get('title')} ({sn.get('customUrl')})  id={ch.get('id')}")
    return 0


def cmd_verify(a) -> int:
    verify(a.id, access_token(read_creds()))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    sub.add_parser("whoami")
    v = sub.add_parser("verify")
    v.add_argument("id")
    u = sub.add_parser("upload")
    u.add_argument("--file")
    u.add_argument("--title")
    u.add_argument("--description")
    u.add_argument("--description-file")
    u.add_argument("--tags", help="comma separated")
    u.add_argument("--publish-at", help="'2026-09-20 08:00' local time, or ISO with offset")
    u.add_argument("--visibility", default="private",
                   choices=["private", "unlisted", "public"])
    u.add_argument("--category", default="22", help="YouTube category id (22 = People & Blogs)")
    u.add_argument("--batch", help="JSON list of entries")
    u.add_argument("--dry-run", action="store_true")
    u.add_argument("--allow-any-channel", action="store_true")
    a = ap.parse_args()
    return {"auth": cmd_auth, "whoami": cmd_whoami, "upload": cmd_upload,
            "verify": cmd_verify}[a.cmd](a) or 0


if __name__ == "__main__":
    raise SystemExit(main())
