"""Downloads the latin subsets of the landing page's fonts, so the banner renders offline."""
import os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
CSS = ("https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800;900"
       "&family=IBM+Plex+Mono:wght@600&display=swap")

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read()

os.makedirs(os.path.join(HERE, "fonts"), exist_ok=True)
css = get(CSS).decode()
out = []
for subset, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, re.S):
    if subset != "latin":
        continue
    fam = re.search(r"font-family: '([^']+)'", block).group(1)
    wt = re.search(r"font-weight: (\d+)", block).group(1)
    url = re.search(r"url\((https://[^)]+)\)", block).group(1)
    name = f"{fam.replace(' ', '').lower()}-{wt}.woff2"
    with open(os.path.join(HERE, "fonts", name), "wb") as f:
        f.write(get(url))
    out.append(f'@font-face{{font-family:"{fam}";font-weight:{wt};src:url(fonts/{name}) format("woff2")}}')
with open(os.path.join(HERE, "fonts.css"), "w") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
