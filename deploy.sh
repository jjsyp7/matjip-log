#!/bin/sh
# 사용: ./deploy.sh  — 바뀐 내용을 GitHub Pages에 올린다.
cd "$(dirname "$0")" && git add -A && git commit -qm "update $(date +%F_%H:%M)" && git push -q && echo pushed
