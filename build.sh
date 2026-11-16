#!/bin/zsh
# dist/<店>/ に 店のページ + 共通 store.css/store.js をまとめる
cd "$(dirname "$0")"
rm -rf dist && mkdir dist
for s in washoku naniwa tempura tanba; do
  cp -R $s dist/$s && cp store.css store.js dist/$s/
done
# 天ぷら大塩: 全ページに GA4 と track.js（予約ボタンへ広告の印を引き継ぐ）を入れる（2026-11-16）
python3 tools/tempura_track.py dist/tempura
echo "built: $(ls dist)"
