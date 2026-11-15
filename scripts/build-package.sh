#!/usr/bin/env bash
# Check the Skill and build the upload ZIP.
# Usage: KIT=/path/to/uliya-skill-kit scripts/build-package.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mapfile -t found < <(ls -d */ 2>/dev/null | while read -r d; do [ -f "$d/SKILL.md" ] && echo "${d%/}"; done)
[ "${#found[@]}" -eq 1 ] || { echo "expected exactly one Skill folder with SKILL.md, found: ${found[*]:-none}"; exit 1; }
SKILL="${found[0]}"
name=$(sed -n 's/^name: *//p' "$SKILL/SKILL.md" | head -1)
[ "$name" = "$SKILL" ] || { echo "folder $SKILL does not match frontmatter name $name"; exit 1; }
: "${KIT:?set KIT to the unpacked uliya-skill-kit folder}"

echo "1. Rule checks"
python3 -I -m unittest discover -s tools/rulecheck

echo "1b. End-to-end simulation against a mock NAS"
python3 -I -m unittest discover -s tools/simrun

echo "1c. README check counts match the real tests"
python3 -I -m unittest discover -s tools/rulecheck -p "check_readme_counts.py"

echo "2. UGREEN kit checker"
node "$KIT/scripts/check-skill.mjs" "$SKILL" > dist-check.json || { cat dist-check.json; exit 1; }
grep -q '"status": "static-pass"' dist-check.json
grep -q '"errors": 0' dist-check.json
grep -q '"warnings": 0' dist-check.json
rm dist-check.json

echo "2b. Capability trace against the catalog"
python3 -I tools/capcheck/check_trace.py "$KIT" | tail -1

echo "3. Package contents"
extra=$(find "$SKILL" -mindepth 1 -maxdepth 1 ! -name SKILL.md ! -name references)
[ -z "$extra" ] || { echo "only SKILL.md and references/ are allowed: $extra"; exit 1; }
bad=$(find "$SKILL" -type f ! -name '*.md')
[ -z "$bad" ] || { echo "Markdown only: $bad"; exit 1; }
big=$(find "$SKILL" -type f -size +1024k)
[ -z "$big" ] || { echo "file over 1 MB: $big"; exit 1; }
n=$(find "$SKILL" -type f | wc -l)
[ "$n" -le 100 ] || { echo "more than 100 files"; exit 1; }
if grep -rnE 'curl |wget |BEGIN [A-Z ]*PRIVATE KEY|\bsk-[A-Za-z0-9_-]{20,}|@gmail\.com' "$SKILL"; then
  echo "remove scripts, secrets or personal email from the package"; exit 1
fi

echo "4. ZIP"
mkdir -p dist
out="dist/$SKILL.zip"
rm -f "$out"
zip -qrX "$out" "$SKILL"
size=$(stat -c %s "$out")
[ "$size" -le 10485760 ] || { echo "ZIP over 10 MB"; exit 1; }
unzip -l "$out" | tail -1
echo "built $out ($size bytes)"
