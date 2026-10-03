#!/usr/bin/env python3
"""サイト間リンク（会社概要・採用・各店・丹波農商）の向き先を一括で切り替える。

  python3 tools/links.py preview   # いま：GitHub Pages のプレビューURLへ
  python3 tools/links.py domain    # ドメイン切替後：本番ドメインへ

対象は会社サイト(~/ageruinc-site)と店舗サイト(~/store-sites)の手書きHTMLと、
メニュー生成スクリプト。書き換えたら各サイトの deploy で公開する。
"""
import re, sys
from pathlib import Path

HOME = Path.home()
SITES = {  # 本番ドメイン : プレビューURL
    "https://ageruinc.com/": "https://agerucompany-ai.github.io/ageruinc-site/",
    "https://washoku-oshio.com/": "https://agerucompany-ai.github.io/washoku-oshio-site/",
    "https://takoyakinaniwa.com/": "https://agerucompany-ai.github.io/takoyakinaniwa-site/",
    "https://tempura-oshio.com/": "https://agerucompany-ai.github.io/tempura-oshio-site/",
    "https://tambanosho.net/": "https://agerucompany-ai.github.io/tambanosho-site/",
}
FILES = [
    *sorted((HOME / "ageruinc-site/src").glob("*.html")),
    *sorted((HOME / "ageruinc-site/partials").glob("*.html")),
    *sorted((HOME / "store-sites").glob("*/index.html")),
    HOME / "store-sites/tools/tabelog_menu.py",
]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("preview", "domain"):
        sys.exit(__doc__)
    pairs = SITES.items() if mode == "preview" else [(b, a) for a, b in SITES.items()]
    skip = set(sys.argv[2:])  # 例: tanba を除外したいときは  links.py preview tanba
    for f in FILES:
        if f.parent.name in skip:
            continue
        s = t = f.read_text()
        for src, dst in pairs:
            # 旧Canvaのアンカー（#会社概要 等）付きも含めて置き換える
            t = re.sub(re.escape(src) + r"(#[^\"'<\s]*)?", lambda m: dst + (m.group(1) or ""), t)
        # 旧Canva時代の「#会社概要」「#採用情報」は新サイトのページへ
        t = t.replace("ageruinc-site/#%E4%BC%9A%E7%A4%BE%E6%A6%82%E8%A6%81", "ageruinc-site/company.html")
        if t != s:
            f.write_text(t)
            print("更新:", f.relative_to(HOME))


if __name__ == "__main__":
    main()
