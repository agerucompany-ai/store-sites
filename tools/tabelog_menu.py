#!/usr/bin/env python3
"""食べログの公開メニュー（料理・ドリンク）を読み、店舗サイトの menu.html を作り直す。

  python3 tools/tabelog_menu.py naniwa          # 生成だけ
  python3 tools/tabelog_menu.py naniwa --deploy # 変わっていたらコミットして公開

食べログ側は Mr.Menu → 食べログ の週次同期（月曜05:30・AI金井）で更新される。
写真は食べログのファイル名（ハッシュ）で保存し、同じ写真は二度と落とさない。
"""
import hashlib, html, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORES = {
    "naniwa": {
        "url": "https://tabelog.com/tokyo/A1302/A130201/13298448/",
        "name": "たこ焼き酒場 なにわ",
        "color": "#0c1a38",
        "nav": [("index.html#menu", "看板メニュー"), ("menu.html", "メニュー"), ("index.html#staff", "社員紹介"),
                ("index.html#shop", "店舗詳細"), ("https://yoyaku.takoyakinaniwa.com/", "ご予約")],
        "reserve": "https://yoyaku.takoyakinaniwa.com/",
    },
    "washoku": {
        "url": "https://tabelog.com/osaka/A2701/A270101/27156689/",
        "name": "和食 大塩",
        "color": "#371501",
        "nav": [("index.html#menu", "看板メニュー"), ("menu.html", "メニュー"), ("index.html#owner", "店主挨拶"),
                ("index.html#shop", "店舗詳細"), ("https://yoyaku.tempuraoshio.com/dai3washoku", "ご予約")],
        "reserve": "https://yoyaku.tempuraoshio.com/dai3washoku",
    },
}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                b = r.read()
                return b if binary else b.decode("utf-8", "replace")
        except Exception:
            if i == 2:
                raise
            time.sleep(3)


def text(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def parse(page):
    """見出し（カテゴリ）と品目を出てくる順に拾う。"""
    m = re.search(r'<p class="update"><span>更新日 : ([0-9/]+)', page)
    updated = m.group(1) if m else ""
    body = page[page.find('class="rstdtl-menu-lst"'):]
    body = body[:body.find('id="column-side"')] if 'id="column-side"' in body else body
    tokens = re.split(r'(?=<div class="rstdtl-menu-lst__heading">)|(?=<div class="rstdtl-menu-lst__contents[ "])', body)
    cats = []
    for t in tokens:
        if t.startswith('<div class="rstdtl-menu-lst__heading">'):
            h = re.search(r'rstdtl-menu-lst__title">(.*?)</h4>', t, re.S)
            cats.append({"name": text(h.group(1)) if h else "", "items": []})
        elif t.startswith('<div class="rstdtl-menu-lst__contents'):
            title = re.search(r'rstdtl-menu-lst__menu-title">(.*?)</p>', t, re.S)
            if not title:
                continue
            price = re.search(r'rstdtl-menu-lst__price">(.*?)</p>', t, re.S)
            ex = re.search(r'rstdtl-menu-lst__ex">(.*?)</p>', t, re.S)
            img = re.search(r'<a href="(https://tblg\.k-img\.com/[^"]+)"[^>]*js-imagebox-trigger', t)
            if not cats:
                cats.append({"name": "", "items": []})
            cats[-1]["items"].append({
                "name": text(title.group(1)),
                "price": text(price.group(1)) if price else "",
                "desc": text(ex.group(1)) if ex else "",
                "recommend": "feature-label--recommend" in t,
                "img": img.group(1) if img else "",
            })
    return updated, [c for c in cats if c["items"]]


def fetch_image(url, outdir):
    """食べログの画像を1回だけ落とす（ファイル名＝食べログのハッシュ）。"""
    h = re.search(r"([0-9a-f]{32})\.jpg", url)
    name = (h.group(1) if h else hashlib.md5(url.encode()).hexdigest()) + ".jpg"
    p = outdir / name
    if not p.exists():
        p.write_bytes(get(url, binary=True))
        subprocess.run(["sips", "-Z", "640", "-s", "formatOptions", "80", str(p)], capture_output=True)
    return name


def render(store, cfg, data):
    def esc(s):
        return html.escape(s).replace("\n", "<br>")
    nav = "\n".join(f'    <a href="{u}">{l}</a>' for u, l in cfg["nav"])
    tabs, secs = [], []
    for k, (label, updated, cats) in enumerate(data):
        for i, c in enumerate(cats):
            cid = f"c{k}-{i}"
            tabs.append(f'<a href="#{cid}">{esc(c["name"] or label)}</a>')
            rows = []
            for it in c["items"]:
                pic = f'<img src="menu-img/{it["file"]}" alt="{esc(it["name"])}" loading="lazy">' if it.get("file") else ""
                badge = '<span class="rec">おすすめ</span>' if it["recommend"] else ""
                desc = f'<p class="desc">{esc(it["desc"])}</p>' if it["desc"] else ""
                rows.append(f'<li class="{"has-pic" if pic else "no-pic"}">{pic}<div class="txt">{badge}'
                            f'<div class="line"><b>{esc(it["name"])}</b><span class="price">{esc(it["price"])}</span></div>{desc}</div></li>')
            secs.append(f'<section class="menu-cat" id="{cid}"><h2><small>{label}</small>{esc(c["name"])}</h2><ul>{"".join(rows)}</ul></section>')
    updated = max(u for _, u, _ in data)
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>メニュー｜{cfg["name"]}</title>
<meta name="description" content="{cfg["name"]}の料理・ドリンクメニュー（税込価格）。">
<link rel="icon" href="img/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="store.css">
</head>
<body style="--main:{cfg["color"]}" class="menu-page">
<!-- このページは tools/tabelog_menu.py が食べログから自動生成します。手で直さないこと。 -->
<header class="site-header solid">
  <a class="brand" href="index.html"><img src="img/ageru.png" alt="AGERU inc."></a>
  <button class="menu-btn" aria-label="メニュー">☰</button>
  <nav>
{nav}
  </nav>
</header>

<div class="menu-head">
  <img src="img/logo.png" alt="{cfg["name"]}">
  <h1>メニュー</h1>
  <p>税込価格／{updated} 時点</p>
</div>
<div class="menu-tabs">{"".join(tabs)}</div>
<div class="menu-body">
{"".join(secs)}
<p class="menu-note">※ 仕入れ状況により内容・価格が変わる場合があります。</p>
<p class="center"><a class="btn solid" href="{cfg["reserve"]}" target="_blank" rel="noopener">ご予約はこちら</a></p>
</div>

<footer class="site-footer">
  <a href="https://ageruinc.com/" target="_blank" rel="noopener"><img src="img/ageru.png" alt="AGERU inc."></a>
  運営：株式会社アゲル
  <small>© {cfg["name"]}</small>
</footer>
<script src="store.js"></script>
</body>
</html>
"""


def main():
    store = sys.argv[1]
    cfg = STORES[store]
    d = ROOT / store
    imgdir = d / "menu-img"
    imgdir.mkdir(exist_ok=True)
    data = []
    for label, path in (("料理", "dtlmenu/"), ("ドリンク", "dtlmenu/drink/")):
        updated, cats = parse(get(cfg["url"] + path))
        if not cats:
            sys.exit(f"{label}メニューが読めませんでした（食べログの構造変更かアクセス制限）。何も書き換えません。")
        for c in cats:
            for it in c["items"]:
                if it["img"]:
                    try:
                        it["file"] = fetch_image(it["img"], imgdir)
                    except Exception as e:
                        print("写真の取得失敗:", it["name"], e)
        data.append((label, updated, cats))
    used = {it["file"] for _, _, cats in data for c in cats for it in c["items"] if it.get("file")}
    for p in imgdir.glob("*.jpg"):  # メニューから消えた写真は捨てる
        if p.name not in used:
            p.unlink()
    (d / "menu.json").write_text(json.dumps([{"kind": l, "updated": u, "categories": c} for l, u, c in data],
                                            ensure_ascii=False, indent=1))
    (d / "menu.html").write_text(render(store, cfg, data))
    n = sum(len(c["items"]) for _, _, cats in data for c in cats)
    print(f"{store}: {n}品 / 写真{len(used)}枚 / 更新日 {max(u for _, u, _ in data)}")

    if "--deploy" in sys.argv:
        g = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
        g("add", f"{store}/menu.html", f"{store}/menu.json", f"{store}/menu-img")
        if not g("diff", "--cached", "--quiet").returncode:
            print("変更なし。公開しません。")
            return
        g("commit", "-m", f"{store}: 食べログのメニューを同期")
        g("pull", "--rebase", "-q")
        subprocess.run(["zsh", "-c", "source ~/.github_env; git -C '%s' push -q \"https://x-access-token:${GITHUB_TOKEN:-$GH_TOKEN}@github.com/agerucompany-ai/store-sites.git\" main" % ROOT])
        subprocess.run([str(ROOT / "deploy.sh"), store])


if __name__ == "__main__":
    main()
