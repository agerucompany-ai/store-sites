#!/bin/zsh
# dist/<店>/ に 店のページ + 共通 store.css/store.js をまとめる
cd "$(dirname "$0")"
rm -rf dist && mkdir dist
for s in washoku naniwa tempura; do
  cp -R $s dist/$s && cp store.css store.js dist/$s/
done
echo "built: $(ls dist)"
