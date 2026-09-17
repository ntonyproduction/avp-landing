"""avp_instagram - publish photos and carousels to the Audio Vision Productions Instagram.

ONE credential store for every repo. Nothing secret lives in a project folder.

  store:  %AVP_IG_HOME%  or  <home>/.avp/instagram
  file:   credentials.json  {app_id, app_secret, page_id, page_token, ig_user_id, ig_username}

Commands
  auth      one-time: trade a short-lived token for a Page token that does not expire
  whoami    print which Instagram account the stored token posts to, and today's quota
  post      one image or a carousel, from files or a folder
  post-reel one vertical video, staged as a GitHub release asset and removed after
  publish   publish a container left behind by `post --stop-before-publish`
  verify    read a published post back by id

Instagram only accepts JPEG, so PNG slides are converted on the way out. The API never
takes the bytes: it fetches a public URL, so `post` stages the JPEGs into this repo,
pushes, waits for GitHub to serve them, and only then publishes.

Every post re-reads the token's account and REFUSES if it is not the pinned username:
this browser profile is signed in as a personal account too, and a post cannot be moved
between accounts afterwards.

Windows: run with `py -3 -u`. Needs `requests` and `Pillow`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
from PIL import Image

try:
    sys.stdout.reconfigure(errors="replace", line_buffering=True)
    sys.stderr.reconfigure(errors="replace", line_buffering=True)
except Exception:  # noqa: BLE001
    pass

API = "https://graph.facebook.com/v26.0"
PINNED_USERNAME = "audiovisionproductions"
REPO = Path(__file__).resolve().parent.parent
STAGE_DIR = "art/ig"
RAW = "https://raw.githubusercontent.com/ntonyproduction/avp-landing/main"
MAX_WIDTH = 1440          # Instagram downscales anything wider, so do it here with a good filter
REEL_TAG = "ig-staging"   # a release that exists only to hand Instagram a public URL
REEL_MIN_SEC, REEL_MAX_SEC = 3, 15 * 60
REEL_MAX_BYTES = 1_000_000_000
MIN_RATIO, MAX_RATIO = 0.79, 1.91  # 4:5 portrait .. 1.91:1 landscape, with slack:
                                   # a 1080x1350 slide lands exactly on 0.8 and must not
                                   # fail the check on a float rounding


# --------------------------------------------------------------------------- store

def store() -> Path:
    return Path(os.environ.get("AVP_IG_HOME", Path.home() / ".avp" / "instagram"))


def load() -> dict:
    path = store() / "credentials.json"
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh)
    except FileNotFoundError:
        sys.exit(f"no credentials at {path}. Run `auth` first (see the module docstring).")
    except OSError as e:
        sys.exit(f"could not read {path}: {e}")


def save(creds: dict) -> None:
    path = store() / "credentials.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(creds, fh, indent=2)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    print(f"wrote {path}")


# --------------------------------------------------------------------------- graph

def graph(method: str, path: str, **params):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url,
                             data=params if method == "POST" else None,
                             params=None if method == "POST" else params,
                             timeout=60)
    except requests.RequestException as e:
        sys.exit(f"could not reach the Graph API: {e}")
    if not r.ok:
        try:
            err = r.json().get("error", {})
            detail = err.get("error_user_msg") or err.get("message") or r.text[:400]
        except ValueError:
            detail = r.text[:400]
        sys.exit(f"Graph API returned {r.status_code} for {method} {path}: {detail}")
    return r.json()


def try_graph(method: str, path: str, **params):
    """Like graph() but returns None instead of exiting, for probing."""
    try:
        r = requests.request(method, f"{API}/{path.lstrip('/')}",
                             data=params if method == "POST" else None,
                             params=None if method == "POST" else params, timeout=60)
    except requests.RequestException:
        return None
    return r.json() if r.ok else None


def granted_pages(app_id: str, app_secret: str, token: str) -> list[dict]:
    """Pages the user actually granted, read from the token itself.

    Facebook Login for Business hands out business-scoped tokens, and those can leave
    /me/accounts empty even when the Page was granted. The Page ids are in the token's
    granular_scopes, so ask the token what it was given and look each one up.
    """
    data = graph("GET", "debug_token", input_token=token,
                 access_token=f"{app_id}|{app_secret}").get("data", {})
    ids: list[str] = []
    for scope in data.get("granular_scopes", []):
        for target in scope.get("target_ids") or []:
            if target not in ids:
                ids.append(target)
    pages = []
    for target in ids:
        page = try_graph("GET", target, fields="name,access_token", access_token=token)
        if page and page.get("access_token"):
            pages.append(page)
    return pages


def account(creds: dict) -> dict:
    """Re-read who the stored token actually posts as. Never trust the cached username."""
    me = graph("GET", creds["ig_user_id"], fields="id,username",
               access_token=creds["page_token"])
    if me.get("username") != PINNED_USERNAME:
        sys.exit(f"REFUSING: the stored token posts as @{me.get('username')}, "
                 f"not @{PINNED_USERNAME}. Re-run `auth` with the right account.")
    return me


# --------------------------------------------------------------------------- auth

def cmd_auth(args) -> None:
    creds = {}
    path = store() / "credentials.json"
    if path.exists():
        with open(path, encoding="utf-8-sig") as fh:
            creds = json.load(fh)
    app_id = args.app_id or creds.get("app_id")
    app_secret = args.app_secret or creds.get("app_secret")
    if not app_id or not app_secret:
        sys.exit("need --app-id and --app-secret the first time")

    print("trading the short-lived token for a long-lived one ...")
    long_lived = graph("GET", "oauth/access_token", grant_type="fb_exchange_token",
                       client_id=app_id, client_secret=app_secret,
                       fb_exchange_token=args.token)["access_token"]

    print("looking for the Page ...")
    pages = graph("GET", "me/accounts", fields="name,id,access_token",
                  access_token=long_lived).get("data", [])
    if not pages:
        print("  /me/accounts is empty; reading the Pages out of the token instead ...")
        pages = granted_pages(app_id, app_secret, long_lived)
    if not pages:
        sys.exit("that token has no Pages on it. Is the account a Business/Creator "
                 "account linked to a Facebook Page, and did you grant every permission?")

    chosen = None
    for page in pages:
        ig = graph("GET", page["id"], fields="instagram_business_account{id,username}",
                   access_token=page["access_token"]).get("instagram_business_account")
        if ig and ig.get("username") == PINNED_USERNAME:
            chosen = (page, ig)
            break
        print(f"  skipping Page {page['name']!r} -> "
              f"@{ig.get('username') if ig else 'no Instagram account'}")
    if not chosen:
        sys.exit(f"none of those Pages is linked to @{PINNED_USERNAME}")
    page, ig = chosen

    save({"app_id": app_id, "app_secret": app_secret,
          "page_id": page["id"], "page_token": page["access_token"],
          "ig_user_id": ig["id"], "ig_username": ig["username"]})
    print(f"ready: posts will go to @{ig['username']} via the Page {page['name']!r}")
    print("this Page token has no expiry date; re-run `auth` only if it is revoked.")


# --------------------------------------------------------------------------- whoami

def cmd_doctor(args) -> None:
    """Ask Facebook what a token can actually see. Run this when `auth` says it found no Page."""
    token = args.token
    print("who the token belongs to")
    me = graph("GET", "me", fields="id,name", access_token=token)
    print(f"  {me.get('name')}  (id {me.get('id')})\n")

    print("permissions on the token")
    perms = graph("GET", "me/permissions", access_token=token).get("data", [])
    granted = sorted(p["permission"] for p in perms if p.get("status") == "granted")
    declined = sorted(p["permission"] for p in perms if p.get("status") != "granted")
    print(f"  granted:  {', '.join(granted) or 'none'}")
    if declined:
        print(f"  DECLINED: {', '.join(declined)}")
    for need in ("pages_show_list", "instagram_basic", "instagram_content_publish"):
        if need not in granted:
            print(f"  !! {need} is missing; the token cannot do the job without it")
    print()

    print("Pages this person has a role on  (GET /me/accounts)")
    pages = graph("GET", "me/accounts", fields="name,id", access_token=token).get("data", [])
    if not pages:
        print("  NONE from /me/accounts.")
        if args.app_id and args.app_secret:
            print("  reading the Pages out of the token instead ...")
            pages = granted_pages(args.app_id, args.app_secret, token)
        else:
            print("  pass --app-id and --app-secret to look inside the token itself,")
            print("  which is where a business-scoped token keeps its Page ids.")
    if not pages:
        print("  still nothing: this profile really has no Page granted to the app.")
        return
    for page in pages:
        ig = graph("GET", page["id"], fields="instagram_business_account{id,username}",
                   access_token=token).get("instagram_business_account")
        mark = "<-- this one" if ig and ig.get("username") == PINNED_USERNAME else ""
        print(f"  {page['name']!r} (id {page['id']}) -> "
              f"@{ig.get('username') if ig else 'no Instagram account linked'} {mark}")
    print("\nIf the Page is listed but shows no Instagram account, the link between the Page")
    print("and @" + PINNED_USERNAME + " is what is missing, not the token.")


def cmd_whoami(args) -> None:
    creds = load()
    me = account(creds)
    print(f"@{me['username']}  (ig user {me['id']}, page {creds['page_id']})")
    info = graph("GET", "debug_token", input_token=creds["page_token"],
                 access_token=f"{creds['app_id']}|{creds['app_secret']}").get("data", {})
    expires = info.get("expires_at")
    when = "never expires" if not expires else time.strftime("%Y-%m-%d", time.localtime(expires))
    print(f"token: {when}   scopes: {', '.join(info.get('scopes', [])) or 'unknown'}")
    data = graph("GET", f"{creds['ig_user_id']}/content_publishing_limit",
                 fields="config,quota_usage", access_token=creds["page_token"]).get("data", [])
    quota = data[0] if data else {}
    used = quota.get("quota_usage", 0)
    cap = (quota.get("config") or {}).get("quota_total", 100)
    print(f"published in the last 24h: {used}/{cap}")


# --------------------------------------------------------------------------- images

def to_jpeg(src: Path, dest: Path) -> tuple[int, int]:
    with Image.open(src) as im:
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            flat = Image.new("RGB", im.size, (255, 255, 255))
            flat.paste(im, mask=im.split()[-1])
            im = flat
        else:
            im = im.convert("RGB")
        if im.width > MAX_WIDTH:
            im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=92, optimize=True, progressive=True)
        return im.size


def collect(args) -> list[Path]:
    if args.folder:
        folder = Path(args.folder)
        files = sorted(folder.glob("*.png")) + sorted(folder.glob("*.jpg"))
        if not files:
            sys.exit(f"no .png or .jpg in {folder}")
    else:
        files = [Path(f) for f in args.images]
    if not files:
        sys.exit("give me image paths or --folder")
    for f in files:
        if not f.is_file():
            sys.exit(f"no such file: {f}")
    if len(files) > 10:
        sys.exit(f"a carousel takes at most 10 images, got {len(files)}")
    return files


# --------------------------------------------------------------------------- staging

def git(*cmd: str) -> str:
    r = subprocess.run(["git", *cmd], cwd=REPO, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"git {' '.join(cmd)} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def stage(files: list[Path], slug: str, push: bool) -> list[str]:
    rel = f"{STAGE_DIR}/{slug}"
    urls, sizes = [], set()
    for i, src in enumerate(files, 1):
        dest = REPO / rel / f"{i:02d}.jpg"
        w, h = to_jpeg(src, dest)
        ratio = w / h
        if not MIN_RATIO <= ratio <= MAX_RATIO:
            sys.exit(f"{src.name} is {w}x{h} ({ratio:.2f}:1). Instagram takes 4:5 to 1.91:1.")
        sizes.add((w, h))
        urls.append(f"{RAW}/{rel}/{i:02d}.jpg")
        print(f"  {src.name} -> {rel}/{dest.name}  {w}x{h}")
    if len(sizes) > 1:
        print(f"  note: mixed sizes {sorted(sizes)}; Instagram crops a carousel "
              f"to the first image's shape")

    if not push:
        print("  --no-push: assuming those URLs are already live")
        return urls
    git("add", "--", rel)
    if git("status", "--porcelain", "--", rel):
        git("commit", "-m", f"Instagram carousel images: {slug}")
        git("push")
        print(f"  pushed {len(files)} image(s)")
    else:
        print("  already committed, nothing to push")
    return urls


def wait_for(urls: list[str], timeout: int = 180) -> None:
    print("waiting for GitHub to serve them ...")
    deadline = time.time() + timeout
    for url in urls:
        while True:
            try:
                if requests.head(url, timeout=20, allow_redirects=True).status_code == 200:
                    break
            except requests.RequestException:
                pass
            if time.time() > deadline:
                sys.exit(f"timed out waiting for {url}")
            time.sleep(3)
    print(f"  all {len(urls)} reachable")


# --------------------------------------------------------------------------- reels

def gh(*cmd: str, check: bool = True) -> str:
    """The GitHub CLI, run against this repo. Release assets live outside git history,
    which is the whole point: a 65 MB ad must never become a commit."""
    r = subprocess.run(["gh", *cmd], cwd=REPO, capture_output=True, text=True)
    if r.returncode and check:
        sys.exit(f"gh {' '.join(cmd)} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip() if not r.returncode else ""


def probe_video(path: Path) -> None:
    """Best effort. ffprobe is not a dependency, so a missing one is a note, not an error."""
    if not shutil.which("ffprobe"):
        print("  (ffprobe not on PATH, skipping the shape check)")
        return
    r = subprocess.run(["ffprobe", "-v", "error", "-of", "json",
                        "-show_entries", "format=duration",
                        "-show_entries", "stream=codec_type,codec_name,width,height",
                        str(path)], capture_output=True, text=True)
    if r.returncode:
        print("  (ffprobe could not read it, skipping the shape check)")
        return
    data = json.loads(r.stdout)
    dur = float(data.get("format", {}).get("duration", 0))
    video = next((st for st in data.get("streams", []) if st.get("codec_type") == "video"), {})
    audio = next((st for st in data.get("streams", []) if st.get("codec_type") == "audio"), None)
    w, h = video.get("width", 0), video.get("height", 0)
    print(f"  {w}x{h}  {dur:.1f}s  {video.get('codec_name')}"
          f"{'/' + audio['codec_name'] if audio else ', NO AUDIO'}")
    if not REEL_MIN_SEC <= dur <= REEL_MAX_SEC:
        sys.exit(f"a reel runs {REEL_MIN_SEC}s to {REEL_MAX_SEC // 60}min, this is {dur:.1f}s.")
    if video.get("codec_name") != "h264":
        print(f"  note: Instagram wants H.264, this is {video.get('codec_name')}")
    if w and h and abs(w / h - 9 / 16) > 0.02:
        print(f"  note: {w}x{h} is not 9:16; Instagram will letterbox or crop it")


def stage_reel(video: Path) -> tuple[str, str]:
    """Upload the file as a release asset and return (public url, asset name).

    The asset name is sanitised because it becomes part of the URL, and Instagram's
    fetcher is handed that URL verbatim.
    """
    if not gh("release", "view", REEL_TAG, "--json", "tagName", check=False):
        print(f"  creating the {REEL_TAG!r} release ...")
        gh("release", "create", REEL_TAG, "--title", "Instagram staging", "--prerelease",
           "--notes", "Scratch space for publishing reels. Assets here are deleted "
                      "once Instagram has fetched them; nothing here is permanent.")

    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", video.stem).strip("-") or "reel"
    asset = f"{stem}-{time.strftime('%Y%m%d-%H%M%S')}{video.suffix.lower()}"
    tmp = Path(tempfile.mkdtemp(prefix="avp-reel-")) / asset
    try:
        os.link(video, tmp)          # same volume: instant, no second copy on disk
    except OSError:
        shutil.copy2(video, tmp)
    try:
        print(f"  uploading {asset} ({video.stat().st_size / 1048576:.1f} MB) ...")
        gh("release", "upload", REEL_TAG, str(tmp), "--clobber")
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)

    listing = json.loads(gh("release", "view", REEL_TAG, "--json", "assets") or "{}")
    for item in listing.get("assets", []):
        if item.get("name") == asset:
            return item["url"], asset
    sys.exit(f"uploaded {asset} but GitHub does not list it on {REEL_TAG}")


def unstage_reel(asset: str) -> None:
    print(f"  removing {asset} from the {REEL_TAG!r} release ...")
    gh("release", "delete-asset", REEL_TAG, asset, "--yes", check=False)


def url_live(url: str, timeout: int = 180) -> None:
    """A release URL 302s to objects.githubusercontent.com. Follow it, and fall back to a
    one-byte GET for the case where the object store refuses HEAD."""
    print("waiting for GitHub to serve it ...")
    deadline = time.time() + timeout
    while True:
        for probe in (lambda: requests.head(url, timeout=20, allow_redirects=True),
                      lambda: requests.get(url, timeout=20, allow_redirects=True,
                                           headers={"Range": "bytes=0-0"}, stream=True)):
            try:
                if probe().status_code in (200, 206):
                    print("  reachable")
                    return
            except requests.RequestException:
                pass
        if time.time() > deadline:
            sys.exit(f"timed out waiting for {url}")
        time.sleep(3)


def cmd_post_reel(args) -> None:
    if args.dry_run and not (store() / "credentials.json").exists():
        creds, who = {}, "(not set up yet)"
    else:
        creds = load()
        who = "@" + account(creds)["username"]

    video = Path(args.video)
    if not video.is_file():
        sys.exit(f"no such file: {video}")
    size = video.stat().st_size
    if size > REEL_MAX_BYTES:
        sys.exit(f"{video.name} is {size / 1048576:.0f} MB; Instagram takes up to 1 GB.")
    caption = (Path(args.caption_file).read_text(encoding="utf-8").strip()
               if args.caption_file else (args.caption or ""))

    print(f"posting a reel to {who}")
    print(f"  {video.name}  ({size / 1048576:.1f} MB)")
    probe_video(video)
    print(f"caption ({len(caption)} chars):\n{caption}\n")
    if args.dry_run:
        print("--dry-run: stopping before anything is uploaded or published")
        return

    url, asset = stage_reel(video)
    published = False
    try:
        url_live(url)
        print("creating the container ...")
        container = graph("POST", f"{creds['ig_user_id']}/media", media_type="REELS",
                          video_url=url, caption=caption,
                          access_token=creds["page_token"])["id"]
        print(f"  container {container}; Instagram is transcoding, this takes a minute ...")
        container_ready(creds, container, timeout=args.timeout)

        if args.stop_before_publish:
            print(f"\ncontainer {container} is built and NOT published.")
            print(f"publish it with:  py -3 -u scripts/avp_instagram.py publish {container}")
            print(f"the staged asset is being left in place; remove it afterwards with:")
            print(f"  gh release delete-asset {REEL_TAG} {asset} --yes")
            return
        publish(creds, container)
        published = True
    finally:
        # Instagram keeps its own copy once the container is FINISHED, so the asset has
        # done its job. Leave it only when the post did not go out, so a retry has a URL.
        if published and not args.keep_asset:
            unstage_reel(asset)
        elif not published:
            print(f"\nleaving {asset} staged so you can retry without re-uploading.")
            print(f"remove it with:  gh release delete-asset {REEL_TAG} {asset} --yes")


# --------------------------------------------------------------------------- publish

def container_ready(creds: dict, cid: str, timeout: int = 300) -> None:
    deadline = time.time() + timeout
    while True:
        s = graph("GET", cid, fields="status_code,status", access_token=creds["page_token"])
        code = s.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram rejected container {cid}: {s.get('status', code)}")
        if time.time() > deadline:
            sys.exit(f"container {cid} stuck at {code}")
        time.sleep(3)


def cmd_post(args) -> None:
    if args.dry_run and not (store() / "credentials.json").exists():
        creds, who = {}, "(not set up yet)"   # a plan is worth printing before `auth` has run
    else:
        creds = load()
        who = "@" + account(creds)["username"]
    files = collect(args)
    if args.caption_file:
        caption = Path(args.caption_file).read_text(encoding="utf-8").strip()
    else:
        caption = args.caption or ""
    default_name = Path(args.folder).name if args.folder else files[0].stem
    slug = args.slug or f"{time.strftime('%Y-%m-%d')}-{default_name}"

    print(f"posting {len(files)} image(s) to {who} as {slug!r}")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    print(f"caption ({len(caption)} chars):\n{caption}\n")
    if args.dry_run:
        print("--dry-run: stopping before anything is converted, pushed or published")
        return

    urls = stage(files, slug, push=not args.no_push)
    wait_for(urls)

    ig = creds["ig_user_id"]
    if len(urls) == 1:
        print("creating the container ...")
        parent = graph("POST", f"{ig}/media", image_url=urls[0], caption=caption,
                       access_token=creds["page_token"])["id"]
    else:
        children = []
        for i, url in enumerate(urls, 1):
            print(f"creating container {i}/{len(urls)} ...")
            children.append(graph("POST", f"{ig}/media", image_url=url,
                                  is_carousel_item="true",
                                  access_token=creds["page_token"])["id"])
        for cid in children:
            container_ready(creds, cid)
        print("creating the carousel ...")
        parent = graph("POST", f"{ig}/media", media_type="CAROUSEL",
                       children=",".join(children), caption=caption,
                       access_token=creds["page_token"])["id"]
    container_ready(creds, parent)

    if args.stop_before_publish:
        print(f"\ncontainer {parent} is built and NOT published.")
        print(f"publish it with:  py -3 -u scripts/avp_instagram.py publish {parent}")
        return
    publish(creds, parent)


def publish(creds: dict, container: str) -> None:
    print("publishing ...")
    media = graph("POST", f"{creds['ig_user_id']}/media_publish", creation_id=container,
                  access_token=creds["page_token"])["id"]
    show(creds, media)


def cmd_publish(args) -> None:
    creds = load()
    account(creds)
    publish(creds, args.container)


def show(creds: dict, media_id: str) -> None:
    m = graph("GET", media_id, fields="id,permalink,media_type,timestamp,caption",
              access_token=creds["page_token"])
    print(f"\nlive: {m.get('permalink')}")
    print(f"  id {m['id']}  {m.get('media_type')}  {m.get('timestamp')}")


def cmd_verify(args) -> None:
    creds = load()
    account(creds)
    show(creds, args.media_id)


# --------------------------------------------------------------------------- cli

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("auth", help="one-time setup")
    a.add_argument("--token", required=True,
                   help="short-lived user token from the Graph API Explorer")
    a.add_argument("--app-id")
    a.add_argument("--app-secret")
    a.set_defaults(func=cmd_auth)

    d = sub.add_parser("doctor", help="ask Facebook what a token can actually see")
    d.add_argument("--token", required=True, help="the short-lived token from the Explorer")
    d.add_argument("--app-id", help="lets doctor look inside the token itself")
    d.add_argument("--app-secret", help="lets doctor look inside the token itself")
    d.set_defaults(func=cmd_doctor)

    w = sub.add_parser("whoami", help="which account, which quota")
    w.set_defaults(func=cmd_whoami)

    o = sub.add_parser("post", help="publish an image or a carousel")
    o.add_argument("images", nargs="*", default=[], help="image paths, in post order")
    o.add_argument("--folder", help="every .png/.jpg in here, in filename order")
    cap = o.add_mutually_exclusive_group()
    cap.add_argument("--caption")
    cap.add_argument("--caption-file", help="a UTF-8 file: safest for emoji and hashtags")
    o.add_argument("--slug", help="folder name under art/ig/ (default: date + source name)")
    o.add_argument("--dry-run", action="store_true", help="show the plan, touch nothing")
    o.add_argument("--no-push", action="store_true", help="images are already live in the repo")
    o.add_argument("--stop-before-publish", action="store_true",
                   help="build the post but leave the last click for a human")
    o.set_defaults(func=cmd_post)

    r = sub.add_parser("post-reel", help="publish one vertical video as a reel")
    r.add_argument("video", help="path to the .mp4")
    rcap = r.add_mutually_exclusive_group()
    rcap.add_argument("--caption")
    rcap.add_argument("--caption-file", help="a UTF-8 file: safest for emoji and hashtags")
    r.add_argument("--dry-run", action="store_true", help="show the plan, touch nothing")
    r.add_argument("--keep-asset", action="store_true",
                   help="leave the staged file on the release instead of deleting it")
    r.add_argument("--stop-before-publish", action="store_true",
                   help="build the reel but leave the last click for a human")
    r.add_argument("--timeout", type=int, default=900,
                   help="seconds to wait for Instagram to transcode (default 900)")
    r.set_defaults(func=cmd_post_reel)

    pb = sub.add_parser("publish", help="publish a container left by --stop-before-publish")
    pb.add_argument("container")
    pb.set_defaults(func=cmd_publish)

    v = sub.add_parser("verify", help="read a published post back")
    v.add_argument("media_id")
    v.set_defaults(func=cmd_verify)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
