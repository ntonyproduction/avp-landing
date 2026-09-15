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
| `cropduster/index.html` | Cropduster's product page. **Generated**, see below. |
| `cropduster/thanks/index.html` | The page people land on after subscribing. **Generated.** |
| `cropduster/Cropduster.zip` | The download itself. |
| `cd/yt/`, `cd/tt/` | Short links that redirect to the Cropduster page carrying `?from=youtube` and `?from=tiktok`, for pasting into comments. |
| `chatterbox/index.html` | Chatterbox's product page. **Generated**, see below. |
| `chatterbox/thanks/index.html` | Where Chatterbox's Kit form sends people after they subscribe. **Generated.** |
| `chatterbox/Chatterbox.zip` | The download: `Chatterbox-<version>-Complete.zip` from the Chatterbox repo's `release.py`, renamed. |
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

Every accent on these pages is the house blue. No gold, orange or yellow.

The hub is the exception. It belongs to no single tool, so it is written and edited directly here.

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

## Downloads carry no version

`cropduster/Cropduster.zip` has no version in its name on purpose: the delivery email and every link
ever posted point at one URL forever and always get the current build. Overwrite it with the new
`-Complete.zip` on each release rather than adding a file beside it.
