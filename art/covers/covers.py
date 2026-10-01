"""Reel covers for the organic ads: the brand ground, one drawn object that says what the tool does,
and the headline. Nothing grabbed from the video, no faces, no small print.

    python covers.py                    renders every cover in COVERS
    python covers.py shutterdrag-ad1    renders just the ones named

Each cover is written as <slug>.jpg at 1080x1920, and preview.jpg shows the set whole, with the part
the Instagram and TikTok grids show (the centre 1080x1440, y 240 to 1680) boxed, and beside it at
the size the grid draws it on a phone. Rendered with headless Edge, like the banner, using the
banner's font files (fetched on its first run, not committed)."""
import random, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BANNER = HERE.parent / "youtube-banner"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
W, H, CROP = 1080, 1920, (240, 1680)


# --- the heroes: one object per tool --------------------------------------------------------------

def comments():
    """Chatterbox. A comment section behind, blurred to grey shapes so there is nothing to read, and
    one real Chatterbox card in front: the thing the tool makes."""
    rnd = random.Random(7)
    hues = ["#4A5A6B", "#5B4E6E", "#3F5E5A", "#6B5A4A", "#4E6280", "#5E6B4A"]
    rows = []
    for i in range(10):
        lines = "".join(f'<i style="width:{rnd.randint(300, 620)}px"></i>' for _ in range(rnd.choice((1, 2))))
        rows.append(f'<div class="row" style="top:{40 + i * 118}px"><b style="background:{rnd.choice(hues)}"></b>'
                    f'<div><u style="width:{rnd.randint(140, 240)}px"></u>{lines}</div><s></s></div>')
    return f'<div class="thread">{"".join(rows)}</div><img class="card" src="{(HERE / "card_hook.png").as_uri()}" alt="">'


def phone():
    """Cropduster. A phone showing a reel: the platform's buttons on the right, its caption block at
    the bottom, the safe-zone box the tool draws, and a caption sitting inside it. The box stays
    green, the one colour outside the blues, because green is what Cropduster itself draws."""
    icon = 'fill="none" stroke="#EAEDF0" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"'
    return f"""<div class="phone"><div class="screen">
      <div class="safe"><span class="cap">Your text,<br>right here.</span></div>
      <svg class="rail" viewBox="0 0 40 260" {icon}>
        <path d="M20 33s-13-8-13-17a7 7 0 0 1 13-4 7 7 0 0 1 13 4c0 9-13 17-13 17z"/>
        <path d="M8 82a12 12 0 1 1 5 9l-6 2 1-6z"/>
        <path d="M34 140 6 152l11 4 4 11z"/><path d="m17 156 6-6"/>
        <circle cx="20" cy="210" r="2"/><circle cx="20" cy="220" r="2"/><circle cx="20" cy="230" r="2"/></svg>
      <div class="meta"><b></b><u></u><i style="max-width:210px"></i><i style="max-width:150px"></i></div>
    </div></div>"""


def skateboard():
    """Shutterdrag. A skateboard caught the way a slow shutter catches it: sharp where it is now,
    smeared along the path it took to get there. Loose light trails were tried first and read as
    speed lines; the smear only says "slow shutter" when something recognisable is making it. The
    trail sits behind the board because Shutterdrag's does: it blends the frames before, it cannot
    look ahead."""
    p0, c, p1 = (-160, 1060), (220, 440), (640, 400)    # the arc, bottom left to top right

    def at(t):
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]
        return x, y, -34 + 22 * t                       # levels out as it rises, nose still up

    n = 60
    trail = []
    for k in range(n):
        x, y, a = at(0.18 + 0.8 * k / (n - 1))
        trail.append(f'<use href="#board" transform="translate({x:.1f} {y:.1f}) rotate({a:.1f}) scale(1.2)" '
                     f'opacity="{0.07 + 0.28 * (k / n) ** 1.5:.3f}"/>')
    x, y, a = at(1.0)
    return f"""<svg class="draw" viewBox="0 0 1080 960"><defs>
      <g id="board">
        <path d="M-196 12 L-124 12 L-140 34 L-180 34Z M124 12 L196 12 L180 34 L140 34Z" fill="#8695A2"/>
        <circle cx="-160" cy="52" r="25" fill="#62A3DA"/><circle cx="160" cy="52" r="25" fill="#62A3DA"/>
        <circle cx="-160" cy="52" r="8" fill="#0A0E12"/><circle cx="160" cy="52" r="8" fill="#0A0E12"/>
        <path d="M-282 -36 Q-264 0 -226 0 L226 0 Q264 0 282 -36" fill="none" stroke="#EAEDF0" stroke-width="24" stroke-linecap="round"/>
      </g>
      <filter id="smear" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>
      <filter id="lift" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#000" flood-opacity=".5"/></filter></defs>
      <g filter="url(#smear)">{"".join(trail)}</g>
      <use href="#board" transform="translate({x:.1f} {y:.1f}) rotate({a:.1f}) scale(1.2)" filter="url(#lift)"/></svg>"""


def picture(name):
    """A tool whose object is best made elsewhere hands over a transparent 1080x980 PNG, placed on the picture area
    as it is. Pixelito's come from its own repo (marketing/covers/make_cover_art.py), through the effect's maths."""
    def hero():
        return f'<img class="pic" src="{(HERE / name).as_uri()}" alt="">'
    return hero


# --- the covers: one per posted ad --------------------------------------------------------------
# slug = <tool>-ad<N>. The headline traces to the ad's own words (its on-screen title, its hook or
# its voiceover), two or three lines, one phrase in <em> for the house blue. At 110px a line holds
# about 13 characters; a longer one runs off the right edge, so break it rather than shrink it.

COVERS = [
    dict(slug="shutterdrag-ad1", hero=skateboard, headline="<em>Free</em> slow<br>shutter FX."),
    dict(slug="cropduster-ad4", hero=phone, headline="Stop your<br>text getting<br><em>cropped.</em>"),
    dict(slug="chatterbox-ad3", hero=comments, headline="How to create<br><em>fake comments.</em>"),
    # Pixelito: each ad's own subject through Pixelito's maths: ad 1's car (split), ad 2's skater (8-bit), and for
    # ad 3, whose subject is Anthony's face, a sphere in its two tones (the dither). Committed with the launch,
    # 2026-09-28. Ad 1's third line was "No AI." until 2026-09-30: its hook car is Veo footage, so it now traces to
    # the voiceover's "with one effect" (the YouTube thumbnail, picked from the old cover frame, still says No AI).
    dict(slug="pixelito-ad1", hero=picture("pixelito-ad1-art.png"), headline="<em>Low-res</em><br>transition.<br>One effect."),
    dict(slug="pixelito-ad2", hero=picture("pixelito-ad2-art.png"), headline="<em>Free</em> 8-bit<br>effect."),
    dict(slug="pixelito-ad3", hero=picture("pixelito-ad3-art.png"), headline="<em>Dither</em> effect<br>in one drag."),
    # Paperboy: three different objects, since the same one three times read as one post three times (Anthony,
    # 2026-09-30), all made in paperboy/marketing/covers/make_cover_art.py. Ad 1: the product card (the ad's "1.
    # download paperboy"), headline from its on-screen "i made this animation with one free tool". Ad 2: FULL screen,
    # the app's own held last card, whose printed headline IS the cover's ("Free Match Cut effect", the voiceover's
    # words, in ad 2's dark look). Ad 3: a stack of its #paperboy pages turned about the pinned phrase; it has no words.
    dict(slug="paperboy-ad1", hero=picture("paperboy-ad1-art.png"), headline="Made with<br><em>one free</em><br>tool."),
    dict(slug="paperboy-ad2", hero=lambda: "", headline="", full="paperboy-ad2-full.png"),
    dict(slug="paperboy-ad3", hero=picture("paperboy-ad3-art.png"), headline="Type a word.<br><em>Get this.</em>"),
]

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Montserrat;font-weight:900;src:url({fonts}/montserrat-900.woff2)}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#0A0E12}}
.cover{{position:relative;width:1080px;height:1920px;overflow:hidden;color:#EAEDF0;font-family:Montserrat,sans-serif;
  background:radial-gradient(1000px 820px at 540px 1260px,rgba(13,85,146,.62),rgba(13,85,146,.18) 55%,rgba(10,14,18,0) 80%),#0A0E12}}
h1{{position:absolute;left:76px;top:300px;margin:0;font-size:110px;font-weight:900;line-height:.98;letter-spacing:-.03em;white-space:nowrap;z-index:3}}
h1 em{{font-style:normal;color:#62A3DA}}
.hero{{position:absolute;left:0;top:700px;width:1080px;height:980px}}
.foot{{position:absolute;left:76px;top:1745px}}
.foot img{{display:block;width:62px;height:auto}}
.draw{{position:absolute;left:0;top:0;width:1080px;height:960px}}
.pic{{position:absolute;left:0;top:0;width:1080px;height:980px;image-rendering:pixelated}}
.full{{position:absolute;left:0;top:0;width:1080px;height:1920px}}

.thread{{position:absolute;inset:-20px 40px 0;filter:blur(6px);opacity:.42;
  -webkit-mask-image:linear-gradient(transparent,#000 18%,#000 82%,transparent)}}
.row{{position:absolute;left:0;right:0;display:flex;gap:26px;align-items:flex-start}}
.row>b{{flex:none;width:72px;height:72px;border-radius:50%}}
.row>div{{display:flex;flex-direction:column;gap:14px;padding-top:6px;flex:1}}
.row u{{display:block;height:18px;border-radius:9px;background:#8695A2}}
.row i{{display:block;height:24px;border-radius:12px;background:#EAEDF0}}
.row s{{flex:none;width:34px;height:30px;margin-top:20px;border-radius:8px;background:#70818F}}
.card{{position:absolute;left:50%;top:330px;width:960px;transform:translateX(-50%) rotate(-3deg);
  filter:drop-shadow(0 26px 48px rgba(0,0,0,.6))}}

.phone{{position:absolute;left:50%;top:20px;width:500px;height:960px;transform:translateX(-50%) rotate(-5deg);border-radius:66px;
  background:#05080B;padding:16px;box-sizing:border-box;box-shadow:0 0 0 3px #2A3744,0 40px 80px rgba(0,0,0,.55)}}
.screen{{position:relative;height:100%;border-radius:48px;overflow:hidden;background:linear-gradient(160deg,#243242,#141C25 60%,#0E141A)}}
.safe{{position:absolute;left:36px;right:86px;top:130px;bottom:220px;border:4px solid #3BD97A;border-radius:6px;
  display:flex;align-items:flex-end;padding:0 0 28px 22px}}
.cap{{font-weight:900;font-size:54px;line-height:1.02;letter-spacing:-.02em;color:#fff}}
.rail{{position:absolute;right:18px;bottom:150px;width:40px;height:260px}}
.meta{{position:absolute;left:28px;right:90px;bottom:40px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}}
.meta b{{width:44px;height:44px;border-radius:50%;background:#8695A2}}
.meta u{{width:150px;height:16px;border-radius:8px;background:#EAEDF0;opacity:.8}}
.meta i{{flex-basis:100%;height:14px;border-radius:7px;background:#EAEDF0;opacity:.45}}
</style></head><body><div class="cover">
{full}<h1>{headline}</h1>
<div class="hero">{hero}</div>
<div class="foot"><img src="{logo}" alt=""></div>
</div></body></html>"""


def render(cover, tmp):
    html = tmp / f"{cover['slug']}.html"
    html.write_text(PAGE.format(fonts=(BANNER / "fonts").as_uri(), logo=(HERE.parent / "avp-logo.png").as_uri(),
                                headline=cover["headline"], hero=cover["hero"](),
                                # full: a 1080x1920 picture laid edge to edge over the ground, for a cover whose
                                # picture carries its own headline (Paperboy ad 2's printed page)
                                full=f'<img class="full" src="{(HERE / cover["full"]).as_uri()}" alt="">'
                                if cover.get("full") else ""), encoding="utf-8")
    png = tmp / f"{cover['slug']}.png"
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--window-size={W},{H}", "--virtual-time-budget=5000", "--allow-file-access-from-files",
                    f"--screenshot={png}", html.as_uri()], check=True, capture_output=True, timeout=120)
    im = Image.open(png).convert("RGB")
    assert im.size == (W, H), im.size
    im.save(HERE / f"{cover['slug']}.jpg", quality=92)
    return im


def preview(ims):
    """The covers whole with the grid's crop boxed, and each at the size the grid draws it (124 px
    wide on a 375-wide phone, doubled here), which is the size that decides whether it works."""
    pad, cw, ch, tw, th = 48, 450, 800, 248, 330
    sheet = Image.new("RGB", (pad + len(ims) * (cw + pad), pad * 2 + ch + 40 + th + 50), (18, 20, 23))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 22)
    for k, (slug, im) in enumerate(ims):
        x = pad + k * (cw + pad)
        sheet.paste(im.resize((cw, ch), Image.LANCZOS), (x, pad))
        d.rectangle([x, pad + round(CROP[0] * ch / H), x + cw - 1, pad + round(CROP[1] * ch / H)],
                    outline=(98, 163, 218), width=3)
        sheet.paste(im.crop((0, CROP[0], W, CROP[1])).resize((tw, th), Image.LANCZOS), (x, pad + ch + 40))
        d.text((x + tw + 16, pad + ch + 40), slug, font=font, fill=(200, 205, 210))
    d.text((pad, sheet.height - 42), "Blue box: what the grid shows. Below: the grid tile at phone size (x2).",
           font=font, fill=(150, 158, 166))
    sheet.save(HERE / "preview.jpg", quality=88)


if __name__ == "__main__":
    if not (BANNER / "fonts" / "montserrat-900.woff2").exists():
        subprocess.run([sys.executable, str(BANNER / "fetch_fonts.py")], check=True)
    wanted = sys.argv[1:]
    todo = [c for c in COVERS if not wanted or c["slug"] in wanted]
    missing = set(wanted) - {c["slug"] for c in todo}
    if missing:
        sys.exit("no such cover: " + ", ".join(sorted(missing)))
    with tempfile.TemporaryDirectory() as t:
        ims = [(c["slug"], render(c, Path(t))) for c in todo]
    preview(ims)
    for slug, _ in ims:
        print(HERE / f"{slug}.jpg")
