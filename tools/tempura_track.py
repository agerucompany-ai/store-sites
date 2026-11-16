#!/usr/bin/env python3
"""天ぷら大塩サイトの全ページ <head> に GA4 と track.js を入れる（公開直前に dist/tempura へ流す）。

  python3 tools/tempura_track.py dist/tempura

2026-11-16 オーナー指示「広告→店ページ→予約ボタン→予約ページのどこで落ちたか分かるように」。
測定ID は Googleアナリティクス「tempura-oshio.com」プロパティのウェブストリーム（予約ページ yoyaku.tempuraoshio.com と同じ G-）。
何度流しても二重には入らない（印 <!--TRACK--> を見る）。
"""
import sys
from pathlib import Path

GA4 = "G-GENBEMC32Y"
MARK = "<!--TRACK-->"
SNIP = (MARK
        + f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4}"></script>'
        + "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());"
        + f"gtag('config','{GA4}',{{allow_google_signals:false,allow_ad_personalization_signals:false}});</script>"
        + '<script src="/track.js" defer></script>')


def main(root):
    n = 0
    for p in Path(root).rglob("*.html"):
        t = p.read_text(encoding="utf-8")
        if MARK in t or "</head>" not in t:
            continue
        p.write_text(t.replace("</head>", SNIP + "\n</head>", 1), encoding="utf-8")
        n += 1
    print(f"計測タグを入れたページ: {n}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist/tempura")
