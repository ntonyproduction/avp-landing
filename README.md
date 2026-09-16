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
| `art/` | Images the hub uses. Plain files, not inlined. Tool renders are 900×900 JPEGs so the cards match. |
| `art/youtube-banner/` | The channel banner, one render per tool from `art/`. `python render.py` writes `banner.png` (2560×1440, uploaded to YouTube by hand) and `banner-preview.png` (the desktop, phone and TV crops). Moved here from the Cropduster repo because it covers every tool; fonts are fetched on the first run and not committed. |
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
| `clipping/` | The old clipping-service page, kept after the tools hub took over the root. Nothing links to it; it is reachable only by its URL. |

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

The **texture tool** is on the hub as a card only: no render, no product page, no download, no
version chip, priced "Soon". Its name is not settled, so the card carries a working label. It is
the first tool planned as paid, so when it ships its download cannot sit in this repo for the
reason at the top of this file -- the file would be publicly readable at a guessable URL. That
needs solving before the card becomes a link.

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

Sequences are a paid Kit feature (Creator Monthly, from 2026-09-23). `scripts/kit_list.py` in
the Cropduster repo reads the list from the API without a browser, and `scripts/kit_emails.py`
beside it prints the sequences and the broadcast as text for review.

**One welcome sequence per product, one broadcast per launch.** The sequence is the evergreen part:
it runs for anyone who ever downloads that tool, and it is written to still make sense a year later,
so it carries no dates and no version numbers. A launch instead gets a single broadcast, sent once
to the *other* tool's subscribers, and that one can be specific about the day. Chatterbox's is "I
made a second one" (campaign 25949900). A new tool therefore means one new sequence and one new
broadcast, never a second sequence aimed at the same people.

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

## Downloads carry no version

`cropduster/Cropduster.zip` has no version in its name on purpose: the delivery email and every link
ever posted point at one URL forever and always get the current build. Overwrite it with the new
`-Complete.zip` on each release rather than adding a file beside it.
