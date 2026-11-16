# Testing

Each line says whether it is MEASURED, PLANNED or NOT VERIFIED. Nothing here has run on a UGREEN NAS yet.

## Static check (MEASURED, 2026-11-15)

UGREEN's checker from uliya-skill-kit 0.7.7 (catalog 2.2.0): `static-pass`, 0 errors, 0 warnings.

## Capability trace (MEASURED, 2026-11-15)

The Skill sends plain-language instructions; each one maps to actions in the kit's capability catalog 2.2.0, and those actions were checked against the catalog: they exist for the agent named and take the inputs the instruction relies on (such as several person names with the AND method, month grouping, and text-in-photo search). Steps 1 to 7 map only to actions the catalog marks as read; every write is in Step 8 and each has an approval gate.

| Step | Agent | Catalog actions |
|---|---|---|
| 1 | photo-agent | figure-albums |
| 2 | photo-agent | timeline-summary, search-picture (sample fallback) |
| 4 | photo-agent | meta, vision-vlm |
| 5a | document-agent | extract, reconcile |
| 5b | photo-agent | search-picture, search-screen, vision-ocr |
| 6a | file-agent, document-agent, photo-agent | ls (the Add here folder only, at most 60 files), extract, reconcile, vision-ocr (image files) |
| 7 | file-agent, photo-agent | ls, cat, albums |
| 8 | file-agent, photo-agent, knowledge-agent | mkdir, cpmv (copy), create-album (with add-item), save-text (working notes, Photo descriptions) |
| 9 | file-agent, photo-agent | ls, cat, album-detail |

## Rule checks (MEASURED, 2026-11-15)

One simulated run, as an example of what these checks look like: the timeline reply leaves out March 2026 and the sample call for March fails. Result: March shows "unresolved" in the photo column and "—" in the pack column, it is not a gap, and with no document covering it the notes list "Photos not returned and no linking document: March 2026; check by hand."

The steps that need no NAS call (planning months, choosing photos, joining documents, coverage and gaps) were restated as a small reference program (70 rule cases), kept in the project's source repository and not part of the Skill, and run on the synthetic cases below plus the worked example in [example-output.md](example-output.md): all checks passed. This shows the written rules give the expected result on these cases and that the worked example follows them; it does not prove the rules cover every case. It does not show how the Skill behaves on a NAS.

## Simulated runs (MEASURED, 2026-11-15)

The Skill's control flow from Step 0 to Step 9 was also restated as a small simulation (52 control-flow scenarios), kept in the project's source repository and not part of the Skill, and run against a mock NAS whose agents return made-up results. These scenarios pass: a couple where everything works; a family with a baby kept for documents only; the same family without marking the baby (the run waits at Step 1); one person running twice on the same day (new folder name, no photo steps); a couple whose photo search fails and who declines the album; a declined folder with the album still saved; "unsure" answers at Step 0 (nothing is read); a couple with one partner kept for documents only (document-only gap labels); and a second run that reuses a confirmed line only for the same photo (same date and file name), still to be confirmed, and continues when the earlier index cannot be read; a possible match the user leaves unanswered is never linked or copied; a couple who say photos are not needed (no photo steps, no album, no Photo descriptions file); a failed Photo descriptions save that leaves the working notes saved; a common-law couple whose photos do not fill months without a same-address document; and a married couple who answer yes to all four checklist questions, told no additional proof is needed at this time, who either stop before anything is read or continue with documents only; common-law single-name documents at the same address that fill a month and are copied; a dropped one that is not copied and reopens the month; a joint lease that is not counted twice; and a common-law family whose letter naming one partner and a child pairs with the other partner's bill at the same address; a married couple whose bills in each name at the same address fill a month with no photos and are copied; a listed photo the user does not answer about, held out of the pack; a photographed print, held out until the user gives its real date and then kept under that date (it moves to that month, or leaves the pack when the date is outside the period); and the adults-only offer, made once for a family of four and never for two adults with a documents-only baby; a family of four who choose to search photos of the couple, where only the two partners are searched, the adults-only offer is never made, the gap label says "of the couple", and both children's birth certificates still link; and a taken folder name after a failed listing, where nothing is written into the earlier pack; a month the timeline summary leaves out, sent to the sample search, shown as "unresolved" and never counted as a gap; an empty month the timeline leaves out that the sample search lists as none, which becomes a gap, and a month it recovers, counted as "at least N (sample search)" and planned; a failed sample search that keeps the timeline's own sample photos, or skips the photo check when there are none; two empty months and one month with photos that the timeline leaves out, where the sample search lists the two as none (a gap) and recovers the third, and every month it answers leaves the not-returned list; the same with a failed sample search, where all three stay "unresolved", none is a gap, and the two with no document are listed as "photos not returned and no linking document" to check by hand and in the final summary; a timeline that replies "no results" for the whole period, where every month is 0, no sample search is sent, the photo check is skipped and the months with no document are gaps; counted months the timeline returns without samples, each sent to the sample search, where a month it leaves out or lists as none keeps its count, is never planned, and shows "no sample returned"; a failed photo-check call whose months are sent again one month per call, with a month that still fails shown as "photo check failed" and not counted as a failed rule; a photo whose named people from face grouping leave out a partner, dropped as failing rule 1; and documents added for the gap months (Step 6a): a skip that changes nothing, bills that close every gap month and are copied with the other documents, a month still empty that stays open and is not offered again, a mismatch on an added bill that is noted, an empty Add here folder that changes nothing, a spelling variant on an added bill that closes its month once confirmed in Step 7 (the redo keeps every "you added" month), dropped or unreadable added documents that count for nothing, an added scan of a photographed document kept once, a file Step 5a already read skipped, and photographed documents sent to text recognition, with a folder over 60 files cut off and the rest counted, and a cancelled or failed add-documents listing that goes on to Step 7 with the gaps as they were, and a save that waits for the user's answer, answered in the same call and never sent again, so the whole pack is saved. In every scenario nothing is written before its approval. This checks the written control flow, not how Uliya or the agents behave on a NAS.

## Test cases (rules MEASURED as above; NAS run PLANNED for the finalist day, also the demo script)

All data is synthetic: stand-in people (a couple, and a family of four), photos with set capture dates, and made-up scanned and photographed documents.

1. **Core: the gap list.** About 18 months of photos of both partners with a planted 4-month hole. Expected: up to 20 photos chosen across months, and a gap list naming exactly those 4 months.
2. **Core: joint documents.** A scanned lease and two utility bills naming both people, one with a different spelling of the address, plus a phone photo of an insurance letter naming both. Expected: all four found, the photo labelled `from a photo of a document`, the mismatch noted, nothing corrected.
3. **Edge: no padding and unfit photos.** Only 9 qualifying photos, plus planted decoys (a screenshot, a photo of a screen, a photo with one partner). Expected: 9 kept, decoys counted by the rule they failed, none shown.
4. **Edge: face-grouping miss.** One month where one partner faces away. Expected: that month appears as a gap with the face-grouping label, never as "not together".
5. **Edge: person not named in Photos.** Expected: the Skill asks the user to name them, keep them for documents only (a baby with no face group), or remove them, and waits.
6. **Core: a family of four.** Two parents and two children, about 12 months, with a marriage certificate and two birth certificates (one photographed) and one date-of-birth mismatch. Expected: photos of all four by month, the three certificates listed with the people each names, the mismatch noted, nothing corrected.
7. **Edge: one person, run twice.** Expected: no Photos name needed, no photos chosen and no album; documents naming the person listed by month with "no linking document found" gaps; the second run on the same day saves to a new folder name and never reads the first pack as evidence.
8. **Core: a common-law couple.** Photos every month; a lease naming both for three months; then one month covered only by two single-name documents at the same address; then a joint statement with no address. Expected: the same-address column fills the lease months and the paired month, the rest is a gap labelled "no document showing you both at the same address found", the two single-name documents are copied, and the footer says the table does not decide the 12-month rule.

9. **Core: documents added for a gap.** The case 1 gap, then three bills for the first three gap months put in an `Add here` folder. Expected: those three months show "covered by electricity bill you added", the last stays open with "Still open: check by hand.", and the bills are copied, not moved, after approval.

## Behaviour on the NAS (NOT VERIFIED)

- Whether the timeline summary returns sample photo paths that the vision check can read.
- Whether the album accepts the exact chosen photos.
- Whether the index read-back returns the full text. The catalog's save-text action takes a path; whether it writes a plain file there is not verified, so Step 9 reads the path save-text returns.
- Where Uliya's local-model setting is shown on the test NAS.
- Whether the file agent can rename a file while copying it (the Skill falls back to the original name and records the upload order in the index).
- Whether the photo agent returns the named people face grouping found in each photo it checks in Step 4 (the Skill drops a photo whose named people leave someone out; a photo with none returned keeps the Step 2 search that found it).
- How many photos the vision check handles in one call (the Skill sends at most 15 per call).
- Whether a delegate instruction is read like a shell argument, so the apostrophe escape '"'"' becomes a plain apostrophe in the saved index (check one context line with an apostrophe after saving; Step 9 compares the full saved text and reports any line where the escape survived).
- Whether Uliya reads the reference files SKILL.md links to (the same-address rules, the common-law rules, the saving rules, the evidence rules, the working files in working-files.md and the empty and partial results in completion.md) when a step points to them (the Skill tells it to open every linked file before Step 1 and to stop, naming the file, if one cannot be read; the core common-law rule is also restated in SKILL.md Step 6).
- Whether the document agent matches printed names written with accents ("TRẦN Thị Linh") to names given without them.
- Whether the document agent reads files given by path from a folder the user has just made (Step 6a's `Add here`), and whether the photo agent's text recognition reads image files there that are not in the Photos library.
- Whether the agents honour "leave out paths in a Visa evidence folder" (the Skill also drops such paths itself before using any result).
