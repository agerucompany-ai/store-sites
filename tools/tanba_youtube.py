#!/usr/bin/env python3
"""丹波農商サイトの YouTube 欄に、栗原優介チャンネルの最新動画6本を差し込む（RSS・認証不要）。
毎朝 tools/menu_sync_all.sh から呼ぶ。サムネはYouTubeの画像をそのまま参照する。"""
import html, re, subprocess, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CH = "UCRMwkpIaTBNr5DI19n36AAQ"  # 栗原優介 / 関わるすべてに喜びを。
xml = urllib.request.urlopen(f"https://www.youtube.com/feeds/videos.xml?channel_id={CH}", timeout=30).read().decode()
items = re.findall(r"<yt:videoId>([^<]+)</yt:videoId>.*?<media:title>([^<]*)</media:title>", xml, re.S)[:6]
items = [(v, t.strip()) for v, t in items]
if not items:
    sys.exit("YouTubeのRSSが読めませんでした。何も書き換えません。")
first = items[0][0]
cards = "".join(
    f'<a class="yt-card" href="https://www.youtube.com/watch?v={v}" target="_blank" rel="noopener">'
    f'<img src="https://i.ytimg.com/vi/{v}/hqdefault.jpg" alt="" loading="lazy"><span>{t}</span></a>' for v, t in items[1:])
block = (f'<div class="yt-main"><iframe src="https://www.youtube-nocookie.com/embed/{first}" title="{items[0][1]}" '
         f'loading="lazy" allow="accelerometer; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>'
         f'<div class="yt-grid">{cards}</div>')
p = ROOT / "tanba/index.html"
s = p.read_text()
s2 = re.sub(r"<!-- YT:START -->.*?<!-- YT:END -->", lambda m: "<!-- YT:START -->" + block + "<!-- YT:END -->", s, flags=re.S)
# スライドのサムネも最新動画に
img = ROOT / "tanba/img/yt-thumb.jpg"
try:
    img.write_bytes(urllib.request.urlopen(f"https://i.ytimg.com/vi/{first}/maxresdefault.jpg", timeout=30).read())
except Exception:
    img.write_bytes(urllib.request.urlopen(f"https://i.ytimg.com/vi/{first}/hqdefault.jpg", timeout=30).read())
p.write_text(s2)
print("youtube:", len(items), "本 / 最新", items[0][1])
if "--deploy" in sys.argv:
    g = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
    g("add", "tanba/index.html", "tanba/img/yt-thumb.jpg")
    if g("diff", "--cached", "--quiet").returncode:
        g("commit", "-m", "丹波: YouTubeの最新動画を更新"); g("pull", "--rebase", "-q")
        subprocess.run(["zsh", "-c", "source ~/.github_env; git -C '%s' push -q \"https://x-access-token:${GITHUB_TOKEN:-$GH_TOKEN}@github.com/agerucompany-ai/store-sites.git\" main" % ROOT])
        subprocess.run([str(ROOT / "deploy.sh"), "tanba"])
