#!/usr/bin/env bash
# 把本仓库的 skill 软链到 CodeBuddy 发现目录 ~/.codebuddy/skills/
# 用法： ./scripts/install.sh
#
# 两类来源：
#   1) skills/<name>/        —— 你自己编写、要传 GitHub 的 skill
#   2) downloaded/<repo>/... —— 从网上下载、个人使用、不传 GitHub 的第三方 skill
#      （其 SKILL.md 通常在 downloaded/<repo>/skills/<skillname>/SKILL.md
#        或 downloaded/<repo>/<skillname>/SKILL.md）
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/skills"
DEST="${CODEBUDDY_SKILLS_DIR:-$HOME/.codebuddy/skills}"

mkdir -p "$DEST"

# 1) 自有 skill：skills/<name> 直接软链
for d in "$SRC"/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  # 若目标已存在且是真实目录（非软链），跳过以免覆盖/丢失数据
  if [ -e "$DEST/$name" ] && [ ! -L "$DEST/$name" ]; then
    echo "⚠️  $DEST/$name 已存在且非软链，跳过（如需覆盖请先备份删除）"
    continue
  fi
  ln -sfn "$d" "$DEST/$name"
  echo "✅ linked (own)    $name -> $DEST/$name"
done

# 2) 第三方 skill：downloaded/<repo>/ 下递归找 SKILL.md，软链其父目录
#    同名 skill 只链一次；优先标准 skills/，跳过 .cursor/ 等宿主专属目录
if [ -d "$REPO_ROOT/downloaded" ]; then
  tmp_linked="$(mktemp)"
  while IFS= read -r skillfile; do
    pdir="$(dirname "$skillfile")"
    name="$(basename "$pdir")"
    case "$pdir" in
      */.cursor/*|*/.github/*|*/.vscode/*) continue ;;  # 跳过宿主专属变体
    esac
    if grep -qxF "$name" "$tmp_linked" 2>/dev/null; then
      continue                                        # 同名只链一次
    fi
    if [ -e "$DEST/$name" ] && [ ! -L "$DEST/$name" ]; then
      echo "⚠️  $DEST/$name 已存在且非软链，跳过"
      echo "$name" >> "$tmp_linked"
      continue
    fi
    ln -sfn "$pdir" "$DEST/$name"
    echo "✅ linked (vendor) $name -> $DEST/$name"
    echo "$name" >> "$tmp_linked"
  done < <(find "$REPO_ROOT/downloaded" -name SKILL.md -not -path '*/node_modules/*')
  rm -f "$tmp_linked"
fi

echo "完成。请重启 CodeBuddy 以重新加载法术。"
