"""Renders banner.html to a 2560x1440 PNG with headless Edge (or Chrome), then builds a preview
sheet showing what YouTube shows on desktop, on a phone, and on a TV (the whole image).
The fonts are fetched on the first run; they stay out of git."""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
FONTS = ("montserrat-900.woff2", "ibmplexmono-600.woff2")
W, H = 2560, 1440
DESKTOP = (0, 508, 2560, 931)      # full width, 423 tall
PHONE = (507, 508, 2053, 931)      # the 1546x423 area YouTube calls safe on every device

name = sys.argv[1] if len(sys.argv) > 1 else "banner"
src = os.path.join(HERE, name + ".html")
png = os.path.join(HERE, name + ".png")
if not all(os.path.exists(os.path.join(HERE, "fonts", f)) for f in FONTS):
    subprocess.run([sys.executable, os.path.join(HERE, "fetch_fonts.py")], check=True)
browser = next((b for b in BROWSERS if os.path.exists(b)), None)
if not browser:
    sys.exit("needs Microsoft Edge or Google Chrome for the headless render")
subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1", f"--window-size={W},{H}",
                "--virtual-time-budget=5000", "--allow-file-access-from-files",
                f"--screenshot={png}", "file:///" + src.replace("\\", "/")],
               check=True, capture_output=True, timeout=120)
im = Image.open(png).convert("RGB")
assert im.size == (W, H), im.size
im.save(png, optimize=True)

font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 30)
SHEET_W, PAD = 1600, 40
desk = im.crop(DESKTOP).resize((SHEET_W - 2 * PAD, round((SHEET_W - 2 * PAD) * 423 / 2560)), Image.LANCZOS)
phone_h = desk.height
phone = im.crop(PHONE).resize((round(phone_h * 1546 / 423), phone_h), Image.LANCZOS)
full = im.resize((SHEET_W - 2 * PAD, round((SHEET_W - 2 * PAD) * H / W)), Image.LANCZOS)
d = ImageDraw.Draw(full)
k = full.width / W
for box, colour in ((DESKTOP, (98, 163, 218)), (PHONE, (59, 217, 122))):
    d.rectangle([round(v * k) for v in box], outline=colour, width=3)

rows = [("Desktop: the full-width strip", desk), ("Phone: the centre only", phone),
        ("TV: the whole image (blue = desktop strip, green = phone)", full)]
sheet_h = PAD + sum(50 + r.height + PAD for _, r in rows)
sheet = Image.new("RGB", (SHEET_W, sheet_h), (24, 27, 31))
sd = ImageDraw.Draw(sheet)
y = PAD
for label, r in rows:
    sd.text((PAD, y), label, font=font, fill=(220, 224, 228))
    y += 50
    sheet.paste(r, (PAD, y))
    y += r.height + PAD
sheet.save(os.path.join(HERE, name + "-preview.png"), optimize=True)
print(png, os.path.getsize(png) // 1024, "KB")
