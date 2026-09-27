"""The cover-frame method, step 1: put a reel cover on the front of a YouTube cut, so a Short can wear it as a frame.

    python cover_frame.py <cover.jpg> "<ad> - YouTube.mp4"
    python cover_frame.py <cover.jpg> "<ad> - TikTok.mp4" --frames 1

writes "<ad> - YouTube (cover).mp4" next to the video: half a second of the cover, then the ad, with half a second of
silence ahead of its audio. The frame rate, size and audio format are read from the ad, so the join is seamless at 24
fps and at 30000/1001 alike. Then upload it private or scheduled, pick the first frame as the thumbnail in the YouTube
app, and trim the cover off in Studio before it goes public (avp-landing README, "Reel covers").

--frames sets how many frames of cover go on the front. One is the TikTok fallback, for when its uploader will not take
a cover image: TikTok's default cover is the first frame, and nothing can be trimmed there afterwards, so the cover
stays in the video as a one-frame flash.

Why a frame and not an image: a cover image uploaded to a Short shows as a grey tile until the channel is in the
Partner Program (2026-09-27), while a frame of the video is allowed on any channel.
"""
import argparse, json, re, shutil, subprocess, sys
from fractions import Fraction
from pathlib import Path

LEAD = Fraction(1, 2)             # seconds of cover: long enough to land on in the phone's frame picker and to trim


def probe(video: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-of", "json", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate,sample_rate,channels,channel_layout",
                        str(video)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffprobe could not read {video}: {r.stderr.strip()}")
    streams = json.loads(r.stdout).get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not v:
        sys.exit(f"{video.name} has no video stream")
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {"w": v["width"], "h": v["height"], "fps": v["r_frame_rate"],
            "rate": a and a.get("sample_rate"), "layout": a and (a.get("channel_layout") or
                                                              ("stereo" if a.get("channels") == 2 else "mono"))}


def frames(video: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    counts = re.findall(r"\d+", r.stdout)          # Resolve renders list the video stream twice (a stream group)
    return int(counts[0]) if counts else 0


def loudness(video: Path) -> str:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return f"{i[-1]} LUFS" if i else "unknown"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cover")
    ap.add_argument("video")
    ap.add_argument("--frames", type=int, help="frames of cover on the front (default: half a second)")
    a = ap.parse_args()
    cover, video = Path(a.cover), Path(a.video)
    for f in (cover, video):
        if not f.is_file():
            sys.exit(f"not found: {f}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        sys.exit("needs ffmpeg and ffprobe on PATH")
    p = probe(video)
    fps = Fraction(p["fps"])
    n = a.frames if a.frames is not None else round(fps * LEAD)   # half a second: 12 at 24 fps, 15 at 29.97
    if n < 1:
        sys.exit("--frames must be at least 1")
    out = video.with_name(f"{video.stem} (cover){video.suffix}")

    cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", p["fps"], "-i", str(cover), "-i", str(video)]
    vf = (f"[0:v]scale={p['w']}:{p['h']}:force_original_aspect_ratio=increase,crop={p['w']}:{p['h']},"
          f"trim=end_frame={n},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[c];[1:v]setsar=1[v];"
          f"[c][v]concat=n=2:v=1:a=0[vo]")
    maps = ["-map", "[vo]"]
    if p["rate"]:
        cmd += ["-f", "lavfi", "-t", str(float(Fraction(n) / fps)), "-i",
                f"anullsrc=r={p['rate']}:cl={p['layout']}"]
        vf += ";[2:a][1:a]concat=n=2:v=0:a=1[ao]"
        maps += ["-map", "[ao]"]
    cmd += ["-filter_complex", vf, *maps, "-c:v", "libx264", "-preset", "slow", "-crf", "16",
            "-pix_fmt", "yuv420p", "-r", p["fps"]]
    if p["rate"]:
        cmd += ["-c:a", "aac", "-b:a", "256k"]
    cmd += ["-movflags", "+faststart", str(out)]
    print(f"{video.name}: {p['w']}x{p['h']} at {p['fps']} fps, {n} frames of {cover.name} on the front")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg failed: {r.stderr.strip()[-600:]}")

    got, want = frames(out), frames(video) + n
    print(f"wrote {out}")
    print(f"  frames {got} (the ad's {want - n} + {n} of cover){'' if got == want else '  !! expected ' + str(want)}")
    print(f"  loudness {loudness(out)} (the gate: -16 to -14)")
    if a.frames == 1:
        print("  one cover frame: TikTok's default cover. Check it is the cover in the uploader's picker.")
    else:
        print(f"  trim point: frame {n + 1} (first frame of the ad). Upload private or scheduled, never public.")


if __name__ == "__main__":
    main()
