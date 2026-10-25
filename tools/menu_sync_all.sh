#!/bin/zsh
# 毎朝 launchd から呼ぶ：食べログのメニューを各店サイトに同期（変わった時だけ公開）
cd "$(dirname "$0")/.."
echo "=== $(date '+%Y-%m-%d %H:%M')"
# 10/25 Windows側の牧草ページを古い手元で上書きした→先に必ず最新を取り込む。取り込めない日は公開しない
source ~/.github_env
git pull -q --rebase --autostash "https://x-access-token:${GITHUB_TOKEN:-$GH_TOKEN}@github.com/agerucompany-ai/store-sites.git" main || { echo "pull失敗→今日は公開しない"; git rebase --abort 2>/dev/null; exit 1; }
for s in naniwa washoku tempura; do /usr/bin/python3 tools/tabelog_menu.py $s --deploy; done
/usr/bin/python3 tools/tanba_youtube.py --deploy
