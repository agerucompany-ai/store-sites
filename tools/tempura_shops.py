#!/usr/bin/env python3
"""天ぷらとワイン大塩：店舗一覧（index.html の SHOPS 枠）と各店ページ shop-<店>.html を作る。

  python3 tools/tempura_shops.py

店の情報（並び順・住所・電話・営業時間・予約先）は tempura/shops.json だけを直す。
各店ページの「今の旬」写真は menu.json（毎朝の食べログ同期）から取るので、同期のあとに毎回流す。
"""
import html, json, re, urllib.parse
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "tempura"
NAME = "天ぷらとワイン 大塩"
SITE = "https://tempuraoshio.com/"
esc = lambda s: html.escape(s).replace("\n", "<br>")


def hours_html(s):
    dl = "".join(f"<dt>{esc(a)}</dt><dd>{esc(b)}</dd>" for a, b in s["hours"])
    notes = "".join(f'<p class="note">※ {esc(n)}</p>' for n in s["notes"])
    return f'<dl class="hours">{dl}</dl>{notes}'


def card(s):
    k = s["key"]
    return f"""      <article class="shop-card fade" id="shop-{k}">
        <a href="shop-{k}.html"><img src="{s["photo"]}" alt="{NAME} {s["name"]}" loading="lazy"></a>
        <div class="body">
          <span class="area">{s["area"]}</span>
          <h3><a href="shop-{k}.html">{s["name"]}</a></h3>
          <p class="addr">{esc(s["addr"])}</p>
          <a class="tel" href="tel:{s["tel"]}">TEL {s["tel_label"]}</a>
          <details>
            <summary>営業時間・定休日</summary>
            {hours_html(s)}
          </details>
          <div class="btns">
            <a class="btn solid" href="{s["reserve"]}" target="_blank" rel="noopener">ご予約</a>
            <a class="btn line" href="shop-{k}.html">店舗ページ</a>
            <a class="btn line" href="menu-{k}.html">メニュー</a>
          </div>
        </div>
      </article>"""


def season_items(k):
    """その店のメニューから写真つきの品を、おすすめを先に最大12品。"""
    try:
        menu = json.loads((D / "menu.json").read_text()).get(f"menu-{k}.html", [])
    except FileNotFoundError:
        return []
    items, seen = [], set()
    for part in menu:
        for c in part["categories"]:
            for it in c["items"]:
                if it.get("file") and it["file"] not in seen and (D / "menu-img" / it["file"]).exists():
                    seen.add(it["file"])
                    items.append(it)
    items.sort(key=lambda it: not it["recommend"])
    return items[:12]


def page(s, shops):
    k, full = s["key"], f'{NAME} {s["name"]}'
    q = urllib.parse.quote(f'{full} {s["addr"]}')
    items = season_items(k)
    strip = ""
    if items:
        cards = "".join(f'<figure class="m-card"><img src="menu-img/{it["file"]}" alt="{esc(it["name"])}" loading="lazy">'
                        f'<figcaption>{esc(it["name"])}<span>{esc(it["price"])}</span></figcaption></figure>' for it in items)
        dup = cards.replace('<figure class="m-card">', '<figure class="m-card" aria-hidden="true">')
        strip = f"""
<section class="dark season">
  <h2 class="sec-title fade">{esc(s["name"])}の旬</h2>
  <div class="h-row"><div class="h-track">{cards}{dup}</div></div>
  <p class="menu-more"><a class="btn" href="menu-{k}.html">メニューをすべて見る</a></p>
</section>"""
    on = ' class="on"'
    others = "".join(f'<a href="shop-{o["key"]}.html"{on if o["key"] == k else ""}>{o["name"]}</a>' for o in shops)
    ld = {"@context": "https://schema.org", "@type": "Restaurant", "name": full, "url": f"{SITE}shop-{k}.html",
          "image": SITE + s["photo"], "telephone": s["tel_label"], "servesCuisine": ["天ぷら", "ワイン"],
          "address": {"@type": "PostalAddress", "streetAddress": s["addr"], "addressCountry": "JP"},
          "menu": f"{SITE}menu-{k}.html", "acceptsReservations": s["reserve"]}
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{full}｜旬に勝る素材なし</title>
<meta name="description" content="{full}（{esc(s["addr"])}）。旬の素材の天ぷらとワイン。営業時間・地図・ご予約・メニュー。">
<link rel="canonical" href="{SITE}shop-{k}.html">
<link rel="icon" href="img/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="store.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body style="--main:#1c1c1c" class="shop-page">
<!-- このページは tools/tempura_shops.py が tempura/shops.json から自動生成します。手で直さないこと。 -->
<header class="site-header solid">
  <a class="brand" href="index.html"><img src="img/ageru.png" alt="AGERU inc."></a>
  <button class="menu-btn" aria-label="メニュー">☰</button>
  <nav>
    <a href="index.html">トップ</a>
    <a href="#info">店舗情報</a>
    <a href="#map">地図</a>
    <a href="menu-{k}.html">メニュー</a>
    <a href="index.html#shops">ほかの店舗</a>
    <a class="nav-reserve" href="{s["reserve"]}" target="_blank" rel="noopener">ご予約</a>
  </nav>
</header>

<div class="shop-hero">
  <img class="bg" src="{s["photo"]}" alt="{full}">
  <div class="cap">
    <img class="logo" src="img/logo.png" alt="{NAME}">
    <span class="area">{s["area"]}</span>
    <h1>{esc(s["name"])}</h1>
  </div>
</div>
{strip}
<section id="info">
  <div class="wrap shop-info">
    <div class="fade">
      <h2>店舗情報</h2>
      <dl class="facts">
        <dt>住所</dt><dd>{esc(s["addr"])}</dd>
        <dt>電話</dt><dd><a class="tel" href="tel:{s["tel"]}">{s["tel_label"]}</a></dd>
      </dl>
      <h3>営業時間・定休日</h3>
      {hours_html(s)}
      <div class="btns">
        <a class="btn solid" href="{s["reserve"]}" target="_blank" rel="noopener">ネットで予約</a>
        <a class="btn line" href="tel:{s["tel"]}">電話する</a>
        <a class="btn line" href="menu-{k}.html">メニュー</a>
      </div>
    </div>
    <div class="fade" id="map">
      <iframe class="map" src="https://www.google.com/maps?q={q}&amp;hl=ja&amp;z=17&amp;output=embed" loading="lazy" referrerpolicy="no-referrer-when-downgrade" title="{full}の地図"></iframe>
      <p class="center"><a class="btn line" href="https://www.google.com/maps/search/?api=1&amp;query={q}" target="_blank" rel="noopener">Googleマップで開く</a></p>
    </div>
  </div>
</section>

<section class="dark">
  <div class="wrap center">
    <h2 class="sec-title fade">ほかの店舗</h2>
    <div class="shop-switch">{others}</div>
  </div>
</section>

<footer class="site-footer">
  <a href="https://agerucompany-ai.github.io/ageruinc-site/" target="_blank" rel="noopener"><img src="img/ageru.png" alt="AGERU inc."></a>
  運営：株式会社アゲル
  <small>© {NAME}</small>
</footer>
<script src="store.js"></script>
</body>
</html>
"""


def main():
    shops = json.loads((D / "shops.json").read_text())
    idx = D / "index.html"
    t = idx.read_text()
    grid = "\n".join(card(s) for s in shops)
    t2 = re.sub(r"<!-- SHOPS:START -->.*?<!-- SHOPS:END -->", lambda m: f"<!-- SHOPS:START -->\n{grid}\n      <!-- SHOPS:END -->", t, flags=re.S)
    if t2 != t:
        idx.write_text(t2)
    for s in shops:
        (D / f'shop-{s["key"]}.html').write_text(page(s, shops))
    print("店舗ページ:", " ".join(f'shop-{s["key"]}.html' for s in shops))


if __name__ == "__main__":
    main()
