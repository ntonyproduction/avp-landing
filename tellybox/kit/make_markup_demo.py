"""The landing page's demo of the evidence markup (kit item 7): the kit's own marks drawing on, scene by scene:
a page of an AI research paper (a title underlined, the key result highlighted, a graph circled), the same paper's results table (the best row highlighted, its number circled, a tick and a cross, a box
round a chart), an internal memo (names redacted, a line underlined, the Confidential stamp), then pins and sonar
rings on a map. Anthony, 2026-10-26: our own documents instead of the Wikipedia page, the stamp on a classified one.

The documents are invented (web/kit/markup-plates: the paper, its authors and the institute do not exist), drawn as
HTML and rendered by web/kit/markup-plates/render.py, which also writes marks.json: where each target word sits.
Writes, next to this file:
    markup.mp4      the Markup tab's loop: 1280 x 720, 24 fps, H.264 CRF 22, silent (the page's clips play muted)
    markup.jpg      its poster: the paper's first page with its marks down

SINCE 2026-10-28 THE PAGE'S markup.mp4 AND markup.jpg ARE ANTHONY'S EDIT, not this script's: he cut the 4K master on
Resolve's timeline "Markups" (AVP - Tellybox) with Tellybox over it; its render is markup-1080.mov (git-ignored), and
the page's loop (1280 x 720, H.264 CRF 22, silent) and poster (the stamp, 12 s in) were cut from that. A plain run of
this script overwrites both with the untextured demo: run it only to remake his source (4k), or to replace his edit.

The marks are the buyer's files (kit/markup/make_markup.py), read from Drive's copy; MARKUP_DIR=<folder> reads another.

    py -3 web/kit/markup-plates/render.py      (only after changing a plate)
    py -3 web/kit/make_markup_demo.py

The 4K master (Anthony, 2026-10-28: to grade under Tellybox; the page keeps its 720p loop), markup-4k.mov, 3840 x 2160,
24 fps, ProRes 422 HQ, silent: the documents shot again at twice the pixels, the marks drawn again at twice the pixels
(their own folder: the kit's files stay 1080p), the map upscaled (its plate is only 1920 x 1080).

    py -3 web/kit/markup-plates/render.py 2
    set MARKUP_OUT=<folder> & set MARKUP_SCALE=2 & set MARKUP_SILENT=1 & py -3 kit/markup/make_markup.py <the marks below>
    set MARKUP_DIR=<that folder> & py -3 web/kit/make_markup_demo.py 4k
"""
import sys
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PLATES = os.path.join(HERE, "markup-plates")
MARKS = os.environ.get("MARKUP_DIR",
                       r"G:\My Drive\AVP Tools\Tellybox\Material\Documentary Kit evidence markup (first set)")
MAP = r"C:\Users\Client\Videos\Tellybox test\Evidence markup test\map plate.png"
BOX = json.load(open(os.path.join(PLATES, "marks.json")))


def at(plate, key, dx=0, dy=0, where="centre"):
    """A point on a plate's target: its centre, or just under it (for an underline)."""
    x, y, w, h = BOX[plate][key]
    return (x + w / 2 + dx, (y + h + 4 if where == "under" else y + h / 2) + dy)


def width(plate, key):
    return BOX[plate][key][2]


# (plate png, seconds on screen, [(mark, start in s, centre on the 1920 x 1080 frame, scale)]). Each mark's clip is
# full frame with the mark in its middle, at the size it was drawn for on 1080p: an underline or highlighter is 600 px
# long (the long highlighter 1100), a redaction bar 520, so the scale fits it to its words.
SCENES = [
    (os.path.join(PLATES, "paper-1.png"), 5.0, [
        ("Underline - Blue", 0.35, at("paper-1", "title", where="under"), width("paper-1", "title") / 600),
        ("Highlighter - Yellow", 1.2, at("paper-1", "hl", dx=16), width("paper-1", "hl") / 560),
        ("Circle (Large) - Red", 2.2, at("paper-1", "fig", dy=-16), 0.97),
    ]),
    (os.path.join(PLATES, "paper-2.png"), 4.6, [
        ("Highlighter (Long) - Yellow", 0.3, at("paper-2", "row"), width("paper-2", "row") / 1080),
        ("Circle (Small) - Red", 1.25, at("paper-2", "num"), 0.8),
        ("Tick - Green", 1.9, at("paper-2", "tick", dx=-width("paper-2", "tick") / 2 - 40), 0.55),
        ("Cross - Red", 2.4, at("paper-2", "cross", dx=-width("paper-2", "cross") / 2 - 40), 0.55),
        ("Box - Red", 3.0, at("paper-2", "bars", dy=-4), 1.0),
    ]),
    (os.path.join(PLATES, "memo.png"), 4.6, [
        ("Redaction Bar", 0.3, at("memo", "red1"), width("memo", "red1") / 500),
        ("Redaction Bar", 0.75, at("memo", "red2"), width("memo", "red2") / 500),
        ("Underline - Red", 1.35, at("memo", "ul", where="under"), width("memo", "ul") / 600),
        ("Stamp - Confidential", 2.2, (1380, 830), 0.9),
    ]),
    (MAP, 4.0, [
        ("Pin - Red", 0.3, (958, 150), 1.0),                  # its tip on Paris
        ("Sonar Rings - White", 0.75, (958, 300), 1.0),
        ("Pin - White", 1.8, (1062, 540), 1.0),               # its tip near Marseille
    ]),
]


def build(k=1):
    """k = 1: the page's 720p loop and its poster. k = 2: the 4K master (the 4K plates and marks, see the top)."""
    inputs, graph, idx = [], [], 0
    W, H = 1920 * k, 1080 * k
    for plate, secs, _ in SCENES:
        if k != 1 and os.path.dirname(plate) == PLATES:
            plate = os.path.join(PLATES, "4k", os.path.basename(plate))
        inputs += ["-loop", "1", "-framerate", "24", "-t", str(secs), "-i", plate]
    idx = len(SCENES)
    for s, (plate, secs, items) in enumerate(SCENES):
        last = f"s{s}b"
        graph.append(f"[{s}:v]format=rgba,scale={W}:{H}:flags=lanczos[{last}]")
        for i, (name, start, (cx, cy), sc) in enumerate(items):
            inputs += ["-i", os.path.join(MARKS, name + ".mov")]
            w, h = round(W * sc / 2) * 2, round(H * sc / 2) * 2
            graph.append(f"[{idx}:v]setpts=PTS-STARTPTS+{start}/TB,scale={w}:{h}[s{s}k{i}]")
            graph.append(f"[{last}][s{s}k{i}]overlay={round(cx * k - w / 2)}:{round(cy * k - h / 2)}:eof_action=repeat[s{s}m{i}]")
            last, idx = f"s{s}m{i}", idx + 1
        graph.append(f"[{last}]trim=duration={secs},setpts=PTS-STARTPTS[s{s}]")
    concat = "".join(f"[s{s}]" for s in range(len(SCENES))) + f"concat=n={len(SCENES)}:v=1:a=0"
    if k != 1:
        graph.append(concat + ",format=yuv422p10le[v]")
        out = os.path.join(HERE, "markup-4k.mov")
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", "[v]",
                        "-r", "24", "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0", "-color_primaries",
                        "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-an", out], check=True)
        return out
    graph.append(concat + ",scale=1280:720:flags=lanczos,format=yuv420p[v]")
    out = os.path.join(HERE, "markup.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", "[v]",
                    "-r", "24", "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-movflags", "+faststart", "-an",
                    out], check=True)
    # the poster: the paper's first page with all its marks down, just before the cut
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(SCENES[0][1] - 0.3), "-i", out, "-frames:v", "1",
                    "-q:v", "4", os.path.join(HERE, "markup.jpg")], check=True)
    return out


if __name__ == "__main__":
    print(build(2 if sys.argv[1:] == ["4k"] else 1))
