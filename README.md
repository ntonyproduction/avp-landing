# avp-landing

The Audio Vision Productions website, served by GitHub Pages at the domain in `CNAME`,
[audiovisionproductions.ca](https://audiovisionproductions.ca). The repo is public, so **everything
here is publicly readable, including the download zips**. That is fine for free tools, where the
email signup is a soft gate. A paid tool cannot be delivered from this repo: its file would sit at a
guessable URL with nothing checking who is asking.

**Pushing to `main` publishes.** There is no build step and no staging site.

## Layout

| Path | What it is |
|---|---|
| `index.html` | The tools hub. The site's front page, listing every tool. Written by hand, here. |
| `tt/`, `yt/`, `ig/` | **The bio links.** Each redirects to the hub carrying `?from=tiktok`, `?from=youtube` or `?from=instagram`. Set once in each profile's bio and never changed; see "The bio link" below. |
| `art/` | Images the hub uses. Plain files, not inlined. Tool renders are 900×900 JPEGs so the cards match. |
| `art/youtube-banner/` | The channel banner, one render per tool from `art/`. `python render.py` writes `banner.png` (2560×1440, uploaded to YouTube by hand) and `banner-preview.png` (the desktop, phone and TV crops). Moved here from the Cropduster repo because it covers every tool; fonts are fetched on the first run and not committed. |
| `art/covers/` | Reel covers for the organic ads, one `<tool>-ad<N>.jpg` each (1080×1920). `python covers.py` renders them and `preview.jpg`; the covers are listed in `COVERS` at the top of the script. See "Reel covers" below. |
| `art/ig/<slug>/` | Carousel and photo posts staged for Instagram to fetch. Written by `scripts/avp_instagram.py`, committed and pushed, because the Graph API reads a public URL rather than taking an upload. Small JPEGs, so they stay. |
| `cropduster/index.html` | Cropduster's product page. **Generated**, see below. |
| `cropduster/thanks/index.html` | The page people land on after subscribing. **Generated.** |
| `cropduster/Cropduster.zip` | The download itself. |
| `cropduster/demo.mp4`, `demo.jpg` | The page's demo video (a cut of the organic Short, 720×1280, audio in the -16 to -14 LUFS band) and its first frame as poster. Not generated: rendered from Resolve, then copied here. |
| `cd/yt/`, `cd/tt/` | Short links that redirect to the Cropduster page carrying `?from=youtube` and `?from=tiktok`, for pasting into comments. |
| `chatterbox/index.html` | Chatterbox's product page. **Generated**, see below. |
| `chatterbox/thanks/index.html` | Where Chatterbox's Kit form sends people after they subscribe. **Generated.** |
| `chatterbox/Chatterbox.zip` | The download: `Chatterbox-<version>-Complete.zip` from the Chatterbox repo's `release.py`, renamed. |
| `chatterbox/demo.mp4`, `demo.jpg` | Chatterbox's demo video and poster, made the same way as Cropduster's. |
| `cb/yt/`, `cb/tt/` | The same short links for Chatterbox. |
| `thank-you/index.html` | Where Polar sends a buyer after paying for **any** paid tool. It names no tool, so it can sit in this public repo before a paid tool is announced. It reads `checkout_id` from its URL and points **Get your download** at the relay in the `time-tracker` repo (`DOWNLOAD_ROUTE` in its script), which checks the payment and opens the buyer's Polar download page. It strips the session token Polar appends from the address bar. Without a `checkout_id` it shows where to find the receipt. Written by hand, here. |
| `clipping/` | The old clipping-service page, kept after the tools hub took over the root. Nothing links to it; it is reachable only by its URL. |
| `scripts/avp_instagram.py` | Posts to @audiovisionproductions from the command line: `post` for an image or carousel, `post-reel` for a video (with `--cover` for its cover image). See below. |
| `scripts/avp_youtube.py` | Uploads and schedules on @audiovisionproductions: `auth`, `whoami`, `upload` (with `--thumbnail` for a cover), `thumbnail` (a cover on a video already up, never on a Short), `verify`. A copy of the `youtube-upload` skill's script, kept here because the canonical copy lives in the credential store (`~/.avp/youtube/`) and a store can go missing while a repo cannot. Holds no credentials. |

## Do not hand-edit the generated pages

`cropduster/index.html` and `cropduster/thanks/index.html` are built by `web/build_landing.py` in
the **Cropduster** repo, which inlines every image as a data URI and then gets copied here. Editing
them here works until the next release, which silently overwrites the change. Edit
`web/landing.template.html` or `web/thanks.template.html` in that repo instead.

The same goes for `chatterbox/index.html` and `chatterbox/thanks/index.html`, built by
`web/build_landing.py` in the **Chatterbox** repo. Its example cards are rendered there too, from
the template's own layouts, with the avatar photos in `web/avatars/`. Its Kit form ID is
`KIT_FORM_ID` at the top of that script.

**The thank-you page carries the download itself.** Delivery used to depend entirely on Kit's
confirmation email, so anyone whose email landed in spam, or who simply never clicked, gave up their
address and got nothing. The thank-you page now shows a **Download <Tool>** button pointing at the
zip beside it, and the email is described as a copy for later rather than the way in. The zip is
publicly readable at a guessable URL anyway (see the top of this file), and the address is already
captured by the time anyone reaches this page, so the button costs no signups. Do the same on every
tool's thank-you page.

Every accent on these pages is the house blue. No gold, orange or yellow. On every page, the hub
included, the logo top left is a link to `/`.

**Demo videos.** Each product page shows a short demo next to its signup form: `demo.mp4` loops
muted as a preview (browsers only autoplay silent video), and **Play with sound** restarts it from
0:00 with audio, plays it once, then returns to the muted loop. The markup and script live in the
tool repo's `web/landing.template.html`; the video files live here, beside the page. To replace
one, render the new cut, check it passes the loudness gate, encode it to 720×1280 H.264 with
`-movflags +faststart`, write its first frame as `demo.jpg`, and overwrite both files.

The hub is the exception. It belongs to no single tool, so it is written and edited directly here.
Its version chips are typed by hand too, so a tool's release also sets its chip to the exact
version its product page shows (Chatterbox 1.0.1 read "v1.0" on the hub until fixed).

**The newest tool wears a NEW badge**, and only the newest. It is the `new` class on that card's
`<a>`, drawn over the render by CSS, so a launch moves one word: add `new` to the new card and take
it off the old one. Two cards reading NEW means neither is, and a badge left behind ends up on a
tool that is months old.

The **texture tool** is not on the hub at all. It had a card, the name was settled and briefly
shipped on it, then the whole card came out on 17 September 2026: the tool moved to the back
burner and a card reading "Soon" still advertises something. It was removed rather than blanked,
and with no HTML comment marking the spot, because a comment would put the name back in the page
source. The markup is in this repo's history, so restoring it is a revert, not a rewrite. Its
finished 900x900 render is already made and staged in the tool's own repo, not here.

Two things still have to be true before that card can come back as a link. The name goes in the
`<h2>` and the `.role` and `.for` lines go back together, because a card that names a tool without
saying what it runs in is a claim waiting to be wrong -- that tool is a Fusion fuse, so it is
Resolve only and a Premiere build is a rewrite rather than a target. And it is the first tool
planned as paid, so its download cannot sit in this repo for the reason at the top of this file:
the file would be publicly readable at a guessable URL.

## Posting to Instagram

`scripts/avp_instagram.py` publishes without a browser. One fact shapes the whole design: **the
Graph API never takes the bytes.** It is handed a public URL and fetches the file itself, so
anything being posted has to be readable by Meta, unauthenticated, at the moment of posting.

Run `whoami` to see which account the stored token posts as and how much of the daily quota is
left, and put `--dry-run` in front of any real post. Every command re-reads the account from the
token and **refuses if it is not `audiovisionproductions`**, because this browser profile is signed
into a personal account too and a post cannot be moved between accounts afterwards.

**That refusal is the whole reason to prefer the script**, and ad 3 (2026-09-21) proved it the hard
way. The credential store was missing, restoring it needed a Meta app secret that was not to hand,
so the reel went up through instagram.com instead. The browser has no such guard, and that profile
was signed in as **`avp.anthony`**, not `audiovisionproductions`: the account picker holds four
saved sessions and switching is one click with no password, but nothing prompts you to. TikTok is
worse, because it stores only one session (`@gtmcutshq`) and offers **no account switcher at all**
in Studio, on tiktok.com, or under Studio > Settings, so reaching the right account means a full log
out and log in. Posting by browser is a fallback, not an equivalent: check the account on screen
before staging and again immediately before the publish click.

**Images and carousels** stage into `art/ig/<slug>/`, get committed and pushed, and are served from
`raw.githubusercontent.com`. They are small and they stay in the repo. How the staging behaves, since
2026-09-27 (`commit_folder` in the script, shared by `post` and `post-reel --cover`):

- **Only that folder is committed**, whatever else happens to be staged.
- **Only on `main` tracking `origin/main`**; anywhere else it refuses before writing a commit.
- **It never publishes anything else.** A push sends every local commit on main, and main is the live
  site, so if main holds unpushed commits that touch anything outside the post's folder (a launch page
  held back, say), it refuses before committing and names them. Push or move those first.
- **It pushes only when the folder's own commit is not on GitHub yet**, so a retry after a failed
  push still pushes, and a re-run with the images already there pushes nothing.
- **Instagram gets URLs pinned to that commit**, not `/main/` ones: GitHub caches a branch path for
  five minutes, so an image re-staged at the same path could reach Instagram as the old one.
- `post --no-push` commits nothing: it checks the folder is committed, unchanged and on GitHub, and
  says which of the three it is not.

**Reels do not.** An ad render is 65 to 70 MB, and committing one would put it in this repo's
history permanently. Deleting it in a later commit does **not** reclaim anything, because the blob
stays in history and every clone keeps paying for it. So `post-reel` uploads the file as an asset on
the **`ig-staging`** prerelease instead. Release assets live entirely outside git history. The flow
is: upload, create a `REELS` container, poll until Instagram finishes transcoding, publish, then
delete the asset. Instagram keeps its own copy once the container reports `FINISHED`, so the URL is
read exactly once and the original is never needed again.

**A reel's cover is staged like a carousel image, not like the reel.** `post-reel --cover
art/covers/<tool>-ad<N>.jpg` converts the cover to JPEG under `art/ig/<slug>/cover.jpg` (the slug
defaults to the date and the video's name; `--slug` sets it) and goes through the same staging as a
carousel (above), so Instagram gets a URL pinned to the cover's commit as the container's `cover_url`.
The cover goes up before the video, so a failed push never strands 65 MB on the release, and after
publishing the script reads the reel's `thumbnail_url` back to show which cover Instagram used (a
failed read only says so; the reel is already live). The cover stays in the
repo, like any posted image. Release assets were not used for it because they come back as
`application/octet-stream`, still unproven even for video (below). Added 2026-09-27 and tested with
dry runs and simulated runs only: this PC has no Instagram credentials, so the first real post with
`--cover` is also its first live test. Read the `thumbnail_url` line that time.

**`ig-staging` is scratch space, not a release.** Do not delete the tag and do not write release
notes on it. It should normally hold **zero** assets; an asset sitting there means a publish failed
after the upload, and the command prints the `gh release delete-asset` line to clear it. Failures
deliberately leave the file in place so a retry does not re-upload 65 MB.

**Where the ads actually live** is Drive, under `Business\Lead Magnets\<Tool>\Ads\Ad<N>\`, not
this repo. Drive cannot serve the API either: a share link returns an HTML page rather than the
bytes, and the `uc?export=download` form hits a virus-scan interstitial above about 25 MB, so Meta
would fetch HTML and the container would fail.

**The copy in that folder is the one the loudness gate applies to**, since it is the file that
uploads. Resolve does not hand back a compliant render on its own: ad 3 came out at **-13.4 LUFS**
(Instagram cut) and **-13.6** (YouTube/TikTok cut), both over the -14 ceiling, and each needed a
static gain (`-af volume=-1.1dB` and `-0.9dB`, video stream copied) to land at -14.5. Measure every
cut before it goes anywhere, and re-measure the corrected file rather than trusting the arithmetic.

One thing still unproven: GitHub serves release assets as `application/octet-stream` rather than
`video/mp4`. The URL ends in `.mp4` and Meta appears to go by that and by the bytes, but if a
container ever comes back `ERROR` with a healthy-looking file, suspect the content type first.

## Reel covers

Every organic ad gets a drawn cover from `art/covers/covers.py`. **This is the house style from
2026-09-27**, chosen over covers built from the ad's own frames. A cover has three things and nothing
else:

1. **The brand ground**: `#0A0E12` with a house-blue glow behind the object.
2. **One drawn object that says what the tool does.** Chatterbox: a blurred comment section with one
   sharp Chatterbox card in front. Cropduster: a phone with the platform's buttons, the green
   safe-zone box and a caption inside it. Shutterdrag: a skateboard, sharp at the front, smeared
   along its path. Every element has to earn its place; a new tool gets its own hero function.
   **Each ad shows its own subject**, never one subject in variations across a tool's ads (Anthony,
   2026-09-27): an ad about a car gets the car, an ad about a skater the skater. When the ad's subject
   is Anthony's face, the object stands for the look instead.
3. **The headline**, Montserrat 900 at 110px, one phrase in blue, traced to the ad's own words.

What was tried and dropped, so nobody tries it again: **frames from the ad** (every frame carries
burned-in captions and titles, and Anthony does not want his face on them), **small print** such as
an eyebrow line over the headline or BEFORE/AFTER tags (unreadable at grid size, so it was removed),
and **abstract light trails** for Shutterdrag (they read as speed lines; the smear only says "slow
shutter" when something recognisable is making it).

**Judge a cover at grid size, not full size.** The Instagram and TikTok grids crop a 9:16 cover to
its centre 3:4 (y 240 to 1680), and on a phone a tile is about 124px wide. `preview.jpg` shows both
the whole cover with that crop boxed and the tile at that size. The logo sits below the crop on
purpose: it shows only on the full cover.

**This repo is public, so a cover is public the moment it is pushed**, including its headline.
Adding an unreleased tool's cover and committing it announces the tool, exactly as its card in `art/`
would. Prepare it locally and commit on launch day.

**Where a cover can go, checked 2026-09-27:**

| | At posting | On a post already up |
|---|---|---|
| Instagram | `avp_instagram.py post-reel --cover art/covers/<tool>-ad<N>.jpg` (the container's `cover_url`), or the web uploader | the phone app only, from the camera roll (done for the first three, 2026-09-27): instagram.com's Edit has no cover |
| TikTok | the uploader's cover picker (whether it takes an image is still to be confirmed on the next ad; if it will not, `art/covers/cover_frame.py --frames 1` makes the cover the video's first frame, which is TikTok's default cover, as a one-frame flash) | **never**: for 7 days the app and TikTok Studio let you pick a frame and add text, but neither takes an image (the app checked on an iPhone, 2026-09-27) |
| YouTube Shorts | **only as a frame of the video**: the cover-frame method below | only one of its own frames, so the cover cannot reach a Short already up without re-uploading it |

**Never upload a cover image to a YouTube Short.** Fully custom Shorts covers are for Partner
Program channels only, but the API accepts one from any channel. On 2026-09-27 three Shorts given
these covers through the API showed as grey tiles in the app's Shorts tab and in Studio, and had to
be put back on a frame by hand in Studio. `avp_youtube.py` refuses a Short unless `--allow-short`.
A horizontal video (a long-form upload) takes a cover image normally.

**The cover-frame method: how a Short wears the cover anyway.** A frame of the video is allowed as a
Short's thumbnail on any channel, so the cover goes in as frames. Anthony's idea, proven on
2026-09-27 on a private test (`nittzNfuqrM`): the thumbnail stayed the cover after the trim, with
the same image version, and the video played without it on his phone.

1. **Put the cover on the front of the YouTube cut** with `art/covers/cover_frame.py`: half a
   second of it, and half a second of silence ahead of the audio. It reads the ad's frame rate, size
   and audio format (the Shutterdrag ads are 24 fps, the Chatterbox ones 30000/1001), checks the frame
   count, prints the loudness for the gate (it does not move: -14.6 and -14.4 in the tests) and the
   frame to trim at:

   ```
   python art/covers/cover_frame.py art/covers/<tool>-ad<N>.jpg "<ad> - YouTube.mp4"
   ```

   It writes `<ad> - YouTube (cover).mp4` next to the video.

2. **Upload it private, or scheduled with `--publish-at`, never public.** Until step 4 the cover
   plays for half a second.
3. **Pick the first frame as the thumbnail in the YouTube phone app** (the Short, then Edit, then
   the thumbnail, then drag to the far left). This step is Anthony's: desktop Studio's "Select from
   video" offers only three frames YouTube chooses, never the first one.
4. **Trim the cover off in Studio**: Editor, then Trim & cut, then zoom the timeline in and drag the
   start handle just past the cover (frame 13 at 24 fps; a frame of the ad is cheaper than a
   sliver of cover). The preview must open on the ad. Save and acknowledge. It applied in a few
   minutes; the length drops by half a second.
5. Check the thumbnail is still the cover, then publish, or let the schedule do it.

## Where signups come from

A link posted on a platform carries a tag, `?from=tiktok` or `?from=youtube` for example. The tool
page copies it into a hidden `fields[source]` input on its Kit form, and it lands in the
subscriber's **Source** custom field. An untagged visit records the referring site instead, or
`direct`.

The hub has no form on it, so it hands the tag onward two ways, because each covers a gap in the
other:

1. `sessionStorage`, under both `avp_source` and the tool-specific `cropduster_source` the
   generated Cropduster page already reads. Writing both means that page needs no change.
2. The link itself, rewritten to carry `?from=`, which survives a tool page opened in a window that
   does not inherit this tab's session storage.

Keep tags short and lowercase, one per place: `tiktok`, `youtube`, `instagram`, `reddit`.

## The bio link

Every profile's bio points at the hub, never at one tool: `audiovisionproductions.ca/tt` on
TikTok, `/yt` on YouTube, `/ig` on Instagram. Introduced on 2026-09-26.

**Why the bio never points at a tool.** A video keeps being watched for months, and "link in bio"
is only true while the bio still leads to what the video showed. Until this change the bio was
swapped to the newest tool at each launch, which quietly broke every older video's call to action:
someone watching a Cropduster ad after the Shutterdrag launch landed on Shutterdrag. The hub lists
every tool, so every video's call to action stays true for good. A launch adds the new tool's card
to the hub, and nothing in any bio changes.

The hub's look was deliberately left alone when the bio links went in. A featured card for the
newest tool and a line for visitors arriving from a video were built and previewed on 2026-09-26,
then shelved ("not yet"). On 2026-09-27 the lighter version went in instead: the NEW badge on the
newest card (see above), with the grid and the cards otherwise unchanged. If the newest tool ever
needs to stand out more than that, the featured card is the place to start.

**Attribution is unchanged.** The redirect adds `?from=`, and the hub passes it on through
`sessionStorage` and the rewritten card links described above, so a signup still records its
platform. The per-tool short links (`/cd/tt`, `/cb/yt` and the rest) still go straight to one
tool's page. They are for comments and descriptions that name one tool, not for bios.

**A video that promises something specific** ("the overlay is in the link") must say which card to
tap, because the bio now lands on the hub: "link in bio, then Pixelito". The promised file has to
be on that tool's page or in its download, since the hub itself hands nothing over.

## What happens after someone subscribes

Every tool's Kit form is wired the same way. A new tool needs all four pieces, or its funnel leaks
quietly the way Cropduster's did until 2026-09-16:

| | Chatterbox | Cropduster |
|---|---|---|
| Kit form | 9919442 | 9901490 |
| Auto-confirm new subscribers | on | on |
| Tag | `chatterbox` | `cropduster` |
| Welcome sequence | Chatterbox welcome (2895956) | Cropduster welcome (2896045) |
| Launch broadcast | to `cropduster` subscribers | to `chatterbox` subscribers |

**Auto-confirm is on**, so someone is a confirmed subscriber the moment they submit and can be
reached by a broadcast. Kit still sends its confirmation email and that email still carries the
download link, but nothing depends on the click any more, because the thank-you page hands over the
zip itself. Before that, six of seventeen subscribers had given an address and received nothing:
they never clicked, so Kit never delivered and never let them be mailed again.

**The welcome sequence** is four emails, on days 0, 2, 5 and 9. The download; the one feature of
that tool most people miss; the other free tool; then an open question about what to build next.
Emails 1 and 2 are tool-specific. Emails 3 and 4 are the same text in both sequences apart from
which tool they point at, so a new tool means writing two, not four. A Kit rule subscribes people to
the sequence when they subscribe to that tool's form.

**The tag comes from a rule, not from the form.** There are four rules: each tool's form subscribes
people to its welcome sequence, and each also adds that tool's tag. The tag used to ride along with
the website embed, which was enough until Instagram, because ManyChat hits the same form without
it. The first two subscribers in from Instagram landed in a sequence carrying no tag at all.
Every exclusion filter below keys off tags, so one untagged subscriber quietly defeats them all.
Tagging on the rule covers every route in: website, Instagram, API.

**Which Instagram post, though.** On 2026-09-16 the launch carousel had 16 views and the demo reel
had 2,676, so the signups are the reel's, not the carousel's. Kit cannot tell them apart: both
arrive with `source` set to `instagram`, because that is all the link carries. If the two ever need
separating, the `?from=` value is the place to do it.

As of 2026-09-21 that ambiguity covers **four** posts: the launch carousel, and organic ads 1, 2 and
3. All four send people through the same bio link, so `instagram` is at once the tag carrying the
most signups and the least informative one on the list. YouTube and TikTok avoid this only because
`/cb/yt` and `/cb/tt` are separate links and each carries one post at a time.

**Giving a post its own `?from=` value is not the free fix this file used to call it.** The obvious
move is a suffixed value, `instagram-ad3` say, decided before the post goes up. The cost only shows
up in the daily Telegram report: `newBySource` in `time-tracker/src/lib/kit.ts` groups the raw Kit
`source` string with **no normalisation** and prints one bullet per distinct value, so a suffix
appears as a row *separate from* `instagram` and the per-platform total has to be summed by hand.
Ad 3 therefore shipped with a bare `?from=instagram` (2026-09-21): the report answers "which
platform", which is the question actually being asked of it, and per-post attribution is not worth
fragmenting it. Suffix a post only when that post's own numbers matter more than the platform line,
and expect to add the rows up afterwards. The same applies to `youtube` and `tiktok`, which `/cb/yt`
and `/cb/tt` carry.

**Where the twenty subscribers came from**, read with `kit_list.py` on 2026-09-17:

| Source | Confirmed | Unconfirmed |
|---|---|---|
| `instagram` | 5 | 4 |
| `youtube` | 4 | 2 |
| `direct` | 1 | 0 |
| `tiktok` | 0 | 0 |
| untagged or test | 4 | 0 |

**TikTok has produced nothing.** The first organic ad went there on 2026-09-15, the second on
2026-09-17 and the third on 2026-09-21, the bio link is `/cb/tt` and it carries `?from=tiktok`, so
a signup would be attributed correctly if one arrived. None has. Instagram, running the same
footage with a ManyChat keyword in front of it, is the largest single source. That is one
platform's worth of evidence and not a verdict: the Instagram cut asks for a comment and answers
with a DM, while the TikTok cut asks people to go and find a link in a bio, so the gap may be the
call to action rather than the audience. Worth re-reading once ad 3 has run a week.

Sequences are a paid Kit feature (Creator Monthly, from 2026-09-23). `scripts/kit_list.py` in
the Cropduster repo reads the list from the API without a browser, and `scripts/kit_emails.py`
beside it prints the sequences and the broadcast as text for review.

**One welcome sequence per product, one broadcast per launch.** The sequence is the evergreen part:
it runs for anyone who ever downloads that tool, and it is written to still make sense a year later,
so it carries no dates and no version numbers. A launch instead gets a single broadcast, sent once
to the *other* tool's subscribers, and that one can be specific about the day. A new tool therefore
means one new sequence and one new broadcast, never a second sequence aimed at the same people.

Chatterbox is the exception that proves it. Its broadcast was written when the sequences reached
almost nobody, so it was covering a backlog rather than announcing a launch, and it is being retired
unsent for the reason below. A real launch broadcast still earns its place: by the time a third tool
ships, the first two lists will be in their sequences, and no existing sequence mentions a tool that
did not exist when it was written.

**Email 3 excludes the tool it is promoting.** Someone who owns both tools should not be pitched
either one, so Chatterbox email 3 excludes the `cropduster` tag and Cropduster email 3 excludes
`chatterbox`. The filter is per email, set with the funnel icon beside *On days* in the sequence
editor, and it does not exist in Kit's v4 API: the sequence email model carries no condition field,
so this can only be set and checked in the browser. The sidebar shows a small funnel on any email
that has one.

**Email 4 is filtered on one side only.** It is the same text in both sequences, so someone in both
would otherwise be asked the same question twice, four days apart. Cropduster's copy excludes
`chatterbox`; Chatterbox's carries no filter. Filtering both would mean a two-tool subscriber is
never asked at all, which is the trap worth remembering when a third tool arrives.

Both sequences went live on 2026-09-16 with all four emails published. Note that publishing does not
enrol anyone retroactively: the Kit rule fires on the subscribe event, so subscribers who arrived
before a sequence was publishable are simply not in it, and adding them is a manual decision.

**A broadcast reaches people a sequence cannot.** "Why the tools live inside your editor" (25953928)
went to all 11 tagged subscribers on 2026-09-16: a plain letter, no links, no images, whose only ask
is a reply, because a reply is the strongest engagement signal a mailbox provider reads. It exists
because publishing the sequences reached almost nobody, for the reason above.

**The backlog gets enrolled, not broadcast at.** As of 2026-09-16, 11 of 13 confirmed subscribers
are in no sequence: they downloaded before their sequence could enrol them, and the rule only fires
on the subscribe event. The plan is to add them by hand rather than mail them a one-off:

| Wave | Who | Sequence | What they get |
|---|---|---|---|
| 1 | 7 cropduster-only | Cropduster welcome | 4 emails, the Chatterbox pitch on day 5 |
| 2 | 3 chatterbox-only | Chatterbox welcome | 4 emails, the Cropduster pitch on day 5 |
| 3 | 1 holding both tags | Chatterbox welcome only | 3 emails, both pitches filtered out |

Which retires "I made a second one" (25949900) rather than sending it. Wave 1's day-5 email is the
same Chatterbox pitch to the same seven people, so doing both would pitch them twice. The broadcast
only ever existed to cover ground the sequence could not; enrolling them covers it better, because
the pitch arrives after three emails that earn it instead of on its own.

The person holding both tags goes into one sequence only. In both, they would get two download
emails on the same day, and nothing here sends more than one email a day to anyone.

This was held until Chatterbox's bugs were fixed: wave 1 sends people to download Chatterbox and
wave 2's second email teaches its highlighter in detail, so neither could go out while the
highlighter did not draw in Premiere. **Chatterbox 1.0.4 (2026-09-16) fixed the editor's whole
report** in both editors. The waves waited on a tester confirming it, because shipping a build and
trusting one are different gates, and the waves are the thing that tells people to go and get it.
That tester (a Mac, Premiere in Spanish) took it through 1.0.5 to 1.0.9; the report on 1.0.9 found
nothing left in Premiere and one Resolve fault, a card that shrank at a lower Timeline Playback
Resolution. **1.0.10 (2026-09-19) fixes it**, confirmed in Resolve on Windows, and the download
here is that build.

**A release can quietly invalidate the sequence copy.** 1.0.4 moved Draw-on, Delay and Easing into
Resolve, where they had been a Premiere-only substitute for keyframing, and replaced the seven
marker-colour presets with a swatch. Chatterbox email 2 described the old behaviour and its
screenshot showed the old panel, so both went wrong the moment the build shipped, and nothing in
Kit would ever have said so. Read the sequence emails against the release notes whenever a tool
ships. The download link survives a version bump; the copy explaining the tool does not, and
neither does a screenshot of its inspector.

**Three places Kit's API answers 200 and does nothing.** Read the result back after every write:

- `content` on a **published** sequence email is dropped silently. Unpublish, write, republish.
  `subject` and `preview_text` update fine either way, which is what makes it easy to miss.
- A broadcast `subscriber_filter` takes only **one** group. Sending `all` and `none` together
  returns 422, so the two-group filter on 25949900 had to be built in the browser. The API reads
  two groups back quite happily; it just will not write them.
- `GET /tags/{id}/subscribers` lags. `GET /subscribers/{id}/tags` is the one to trust: after two
  people were tagged it went on listing the stale count for the rest of the session, which reads
  exactly like a failed write.

## Downloads carry no version

`cropduster/Cropduster.zip` has no version in its name on purpose: the delivery email and every link
ever posted point at one URL forever and always get the current build. Overwrite it with the new
`-Complete.zip` on each release rather than adding a file beside it.
