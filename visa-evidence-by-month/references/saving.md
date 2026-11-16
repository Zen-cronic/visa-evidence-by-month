# Saving the pack

SKILL.md points here at Step 7 (naming the folder and album) and Step 8 (before 8e). The delegations themselves stay in SKILL.md.

## Naming the folder and album (Step 7)

After the two Step 7 reads, `{EXISTING_FOLDERS}` is the folder names returned and `{EXISTING_ALBUMS}` is the album names; `{EXISTING}` is both together. `{NAMES_LINE}` is the names in `{PEOPLE}` joined with commas and "and". The base name is Visa evidence {NAMES_LINE}. If it is in `{EXISTING}`, add `{TODAY}` as YYYY-MM-DD; if that name is also in `{EXISTING}`, add a number after the date, starting from 2, until the name is unused. `{EVIDENCE_FOLDER}` is `{SAVE_LOCATION}` plus a folder with that name, and `{ALBUM_NAME}` is the same name. If `{SAVE_LOCATION}` does not exist yet, `{EXISTING_FOLDERS}` is empty and 8a creates it with the evidence folder. If either read failed for another reason, say so and ask the user whether to continue with the base name.

## Fallback copies (Step 8, before 8e)

Before 8e, update `{PHOTO_COPIES}` and `{PAPER_COPIES}` to the fallback paths 8b and 8c reported (a subfolder named with the order number, holding the original name), so Step 9 compares against what was really saved; then mark in `{INDEX_TEXT}` and `{DESCRIPTIONS_TEXT}` every photo or paper copy that 8b or 8c did not report as copied with "copy failed" (or "not copied: declined by you" when the user declined it at an approval prompt), and give each copy kept under its original name that name next to its upload order, so neither file lists a file that is not there.
