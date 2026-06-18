#!/usr/bin/env bash
# Verify deadcode docs: index.md links resolve to existing files, and every
# file:line anchor in docs/*.md resolves to a real file with >= that many lines.
set -uo pipefail

REPO_ROOT="/home/niekas/tools/deadcode"
DOCS_DIR="$REPO_ROOT/docs"
INDEX="$DOCS_DIR/index.md"
status=0

# 1. Every relative markdown link in index.md points at an existing file.
while IFS= read -r target; do
  path="${target%%#*}"            # strip #fragment
  [ -z "$path" ] && continue
  case "$path" in http*|/*) continue ;; esac   # skip external / absolute
  if [ ! -f "$DOCS_DIR/$path" ]; then
    echo "DANGLING LINK: $path (from index.md)"; status=1
  fi
done < <(grep -oE '\]\([^)]+\)' "$INDEX" | sed -E 's/^\]\(//; s/\)$//')

# 2. Every file:line(-range) anchor in docs/*.md resolves.
# Note: uses `|| true` on grep so pipefail does not fire when a doc has no anchors.
for doc in "$DOCS_DIR"/*.md; do
  if ! { grep -oE '[A-Za-z0-9_./-]+\.(py|toml):[0-9]+(-[0-9]+)?' "$doc" || true; } \
      | while read -r anchor; do
          file="${anchor%%:*}"; lines="${anchor#*:}"; last="${lines##*-}"
          if [[ "$file" == */* ]]; then
            # Anchors with '/' are repo-root-relative; fall back to deadcode/ prefix
            # if not found at repo root (handles partial paths like visitor/xxx.py).
            if [ -f "$REPO_ROOT/$file" ]; then
              resolved="$REPO_ROOT/$file"
            else
              resolved="$REPO_ROOT/deadcode/$file"
            fi
          else
            # Bare basenames: search deadcode/, tests/, and repo root.
            resolved=$(find "$REPO_ROOT/deadcode" "$REPO_ROOT/tests" \
                        -name "$file" -type f 2>/dev/null | head -1)
            if [ -z "$resolved" ] && [ -f "$REPO_ROOT/$file" ]; then
              resolved="$REPO_ROOT/$file"
            fi
          fi
          if [ -z "$resolved" ] || [ ! -f "$resolved" ]; then
            echo "UNRESOLVED ANCHOR: $anchor (in $(basename "$doc"))"; exit 1
          fi
          filelines=$(wc -l < "$resolved")
          if [ "$last" -gt "$filelines" ]; then
            echo "STALE ANCHOR: $anchor > $resolved ($filelines lines)"; exit 1
          fi
        done; then
    status=1
  fi
done

exit $status
