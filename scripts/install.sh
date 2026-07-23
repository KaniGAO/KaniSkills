#!/usr/bin/env bash
# 把本仓库 skills/ 下的每个法术软链到 CodeBuddy 发现目录 ~/.codebuddy/skills/
# 用法： ./scripts/install.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/skills"
DEST="${CODEBUDDY_SKILLS_DIR:-$HOME/.codebuddy/skills}"

mkdir -p "$DEST"

for d in "$SRC"/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"

  # 若目标已存在且是真实目录（非软链），跳过以免覆盖/丢失数据
  if [ -e "$DEST/$name" ] && [ ! -L "$DEST/$name" ]; then
    echo "⚠️  $DEST/$name 已存在且非软链，跳过（如需覆盖请先备份）"
    continue
  fi

  ln -sfn "$d" "$DEST/$name"
  echo "✅ linked $name -> $DEST/$name"
done

echo "完成。请重启 CodeBuddy 以重新加载法术。"
