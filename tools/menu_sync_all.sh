#!/bin/zsh
# 毎朝 launchd から呼ぶ：食べログのメニューを各店サイトに同期（変わった時だけ公開）
cd "$(dirname "$0")/.."
echo "=== $(date '+%Y-%m-%d %H:%M')"
for s in naniwa washoku; do /usr/bin/python3 tools/tabelog_menu.py $s --deploy; done
