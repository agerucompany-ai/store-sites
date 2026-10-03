#!/bin/zsh
# 使い方: ./deploy.sh washoku | naniwa | all
set -e
cd "$(dirname "$0")"
source ~/.github_env
T=${GITHUB_TOKEN:-$GH_TOKEN}
./build.sh
typeset -A REPO=(washoku washoku-oshio-site naniwa takoyakinaniwa-site tempura tempura-oshio-site tanba tambanosho-site)
targets=(${@:-all}); [[ $targets == all ]] && targets=(washoku naniwa tempura tanba)
for s in $targets; do
  cd dist/$s
  git init -q -b gh-pages && git config user.name agerucompany-ai && git config user.email ageru.company@gmail.com
  git add -A && git commit -qm "deploy $(date '+%Y-%m-%d %H:%M')"
  git push -qf "https://x-access-token:$T@github.com/agerucompany-ai/${REPO[$s]}.git" gh-pages
  rm -rf .git; cd ../..
  echo "deployed $s -> https://agerucompany-ai.github.io/${REPO[$s]}/"
done
