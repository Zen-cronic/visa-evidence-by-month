#!/usr/bin/env bash
# Rename the Skill: folder, frontmatter name and the evidence-folder wording stay in step.
# Usage: KIT=/path/to/uliya-skill-kit scripts/rename-skill.sh new-skill-name
set -euo pipefail
cd "$(dirname "$0")/.."
new="${1:?usage: scripts/rename-skill.sh new-skill-name}"
[[ "$new" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "use lowercase letters, digits and single hyphens: $new"; exit 1; }
old=$(for d in */; do if [ -f "$d/SKILL.md" ]; then echo "${d%/}"; fi; done)
[ -n "$old" ] && [ "$(echo "$old" | wc -l)" -eq 1 ] || { echo "expected one Skill folder"; exit 1; }
[ "$old" != "$new" ] || { echo "already named $new"; exit 0; }
git mv "$old" "$new"
sed -i "s/^name: $old\$/name: $new/" "$new/SKILL.md"
grep -q "^name: $new\$" "$new/SKILL.md"
grep -rn -- "$old" "$new" && { echo "the old name is still used inside the Skill; fix the lines above"; exit 1; } || true
rm -f "dist/$old.zip"
scripts/build-package.sh
echo "renamed $old -> $new; review with git status, then commit"
