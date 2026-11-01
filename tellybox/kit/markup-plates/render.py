"""Renders the evidence markup demo's plates (the HTML pages beside this file) to 1920 x 1080 PNGs with headless Edge,
and writes marks.json: each [data-mark] element's box on the frame, so the demo can put each mark on its words.

    py -3 web/kit/markup-plates/render.py
    py -3 web/kit/markup-plates/render.py 2      (the 4K demo: 3840 x 2160 shots in 4k/, marks.json left alone)
"""
import sys
import json, os, re, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PLATES = ["paper-1", "paper-2", "memo"]
PROFILE = os.path.join(tempfile.gettempdir(), "edge-headless-plates")
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 1  # the same 1920 x 1080 layout, shot at SCALE times the pixels
MEASURE = """<script>addEventListener("load",()=>{const o={};document.querySelectorAll("[data-mark]").forEach(e=>{
const r=e.getBoundingClientRect();o[e.dataset.mark]=[r.left,r.top,r.width,r.height].map(Math.round)});
const p=document.createElement("pre");p.id="rects";p.textContent=JSON.stringify(o);document.body.appendChild(p)})</script>"""


def edge(*args):
    return subprocess.run([EDGE, "--headless=new", f"--user-data-dir={PROFILE}", "--disable-gpu", "--hide-scrollbars",
                           f"--force-device-scale-factor={SCALE}", "--window-size=1920,1080", *args],
                          capture_output=True, text=True, timeout=90)


marks = {}
for name in PLATES:
    html = os.path.join(HERE, name + ".html")
    url = "file:///" + html.replace("\\", "/")
    out = HERE if SCALE == 1 else os.path.join(HERE, "4k")
    os.makedirs(out, exist_ok=True)
    edge(f"--screenshot={os.path.join(out, name + '.png')}", url)
    if SCALE != 1:  # the boxes are the same at any scale: marks.json stays the 1080p run's
        continue
    tmp = os.path.join(tempfile.gettempdir(), f"measure-{name}.html")
    src = open(html, encoding="utf-8").read().replace("</body>", MEASURE + "</body>")
    open(tmp, "w", encoding="utf-8").write(src)
    dom = edge("--virtual-time-budget=3000", "--dump-dom", "file:///" + tmp.replace("\\", "/")).stdout
    marks[name] = json.loads(re.search(r'<pre id="rects">(.*?)</pre>', dom, re.S).group(1).replace("&quot;", '"'))
    print(name, marks[name])
if SCALE == 1:
    json.dump(marks, open(os.path.join(HERE, "marks.json"), "w"), indent=1)
