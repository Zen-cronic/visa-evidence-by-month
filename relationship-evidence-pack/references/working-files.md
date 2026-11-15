# Working files

SKILL.md points here at Step 7. These are the two texts Step 8 saves; the delegations themselves stay in SKILL.md.

## Photo descriptions file

`{DESCRIPTIONS_TEXT}` is the Photo descriptions file, for upload: one entry per chosen photo with a (confirmed) or (edited) context, numbered with the order number in its copy name, with:

- its copy name;
- its date;
- its place as a city or left blank (never coordinates or "unknown");
- the people's names as printed on their papers, or their Photos names if none were given (noted in the working notes) (with sponsor and applicant if the user gave them, "(children)" for the people in `{CHILDREN}` if given, and anyone else the user named);
- and the context in the user's words.

It has no source labels, counts, gaps, notes or to-do lists.

When `{CHOSEN_PHOTOS}` is empty, there is no Photo descriptions file and no album.

## Working notes

If any context line the user wrote for the Photo descriptions file is not in the language the application accepts (for Canada, English or French), the working notes say that file needs a translation before upload.

`{INDEX_TEXT}` is the working notes for the user, not for upload. It starts with the line "Working notes for you. Do not upload this file; upload the photos, the papers and the Photo descriptions file." (or "upload the papers" when no photos were chosen), followed, when some chosen photos have no description yet, by "Photos <numbers> have no description yet; describe or remove them before uploading."

Then it holds, in order:

1. the folder name, the names, the scope, for a family whose photos were searched (`{PHOTO_SCOPE}`), and the period;
2. the photo table in upload order (order, copy name, date, place, people, context, source labels), where every context ends with (confirmed), (edited) or `[not confirmed]`, and a reused line adds "from your earlier pack";
3. failure counts by rule;
4. the papers table with the people each names, mismatch notes and possible matches;
5. the lines in `{IGNORED_TEXT}`, shown as quoted content under "Ignored text in papers" with one plain sentence ("This line was ignored; nothing was changed.");
6. the coverage table, the gap list and what could cover each gap, and, when photos were searched, the line "A gap can be a face-grouping miss: someone turned away, a child's face changing fast, or photos in a library this account cannot open. Check these months by hand, and add any paper that covers them.";
7. the chosen photos that still need a description before uploading;
8. the libraries searched;
9. whether papers were matched on printed names or Photos names;
10. the user's Step 0 answer about the local model;
11. anything skipped, and any offer the user declined (such as counting only the adults);
12. and the line "Prepared from files on this NAS. Not legal advice. Check the current official checklist before submitting, or ask a licensed immigration consultant or lawyer."
