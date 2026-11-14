# Testing

Each line says whether it is MEASURED, PLANNED or NOT VERIFIED. Nothing here has run on a UGREEN NAS yet.

## Static check (MEASURED, 2026-11-12)

UGREEN's checker from uliya-skill-kit 0.7.7 (catalog 2.2.0): `static-pass`, 0 errors, 0 warnings.

## Capability trace (MEASURED, 2026-11-13)

The Skill sends plain-language instructions; each one maps to actions in the kit's capability catalog 2.2.0, and those actions were checked against the catalog: they exist for the agent named and take the inputs the instruction relies on (such as several person names with the AND method, month grouping, and text-in-photo search). Steps 1 to 6 map only to actions the catalog marks as read; the 4 writes are all in Step 8 and each has an approval gate.

| Step | Agent | Catalog actions |
|---|---|---|
| 1 | photo-agent | figure-albums |
| 2 | photo-agent | timeline-summary |
| 4 | photo-agent | meta, vision-vlm |
| 5a | document-agent | extract, reconcile |
| 5b | photo-agent | search-picture, search-screen, vision-ocr |
| 8 | file-agent, photo-agent, knowledge-agent | mkdir, cpmv (copy), create-album, save-text |
| 9 | file-agent, photo-agent | ls, cat, album-detail |

## Rule checks (MEASURED, 2026-11-13)

The steps that need no NAS call (planning months, choosing photos, joining papers, coverage and gaps) were restated as a small reference program, kept in the project's source repository outside this package, and run on the synthetic cases below plus the worked example in [example-output.md](example-output.md): 13 checks, all passed. This confirms the written rules are complete and consistent and that the worked example follows them. It does not show how the Skill behaves on a NAS.

## Test cases (rules MEASURED as above; NAS run PLANNED for the finalist day, also the demo script)

All data is synthetic: stand-in people (a couple, and a family of four), photos with set capture dates, and made-up scanned and photographed papers.

1. **Core: the gap list.** About 18 months of photos of both partners with a planted 4-month hole. Expected: up to 20 photos chosen across months, and a gap list naming exactly those 4 months.
2. **Core: joint documents.** A scanned lease and two utility bills naming both people, one with a different spelling of the address, plus a phone photo of an insurance letter naming both. Expected: all four found, the photo labelled `from a photo of a document`, the mismatch noted, nothing corrected.
3. **Edge: no padding and unfit photos.** Only 9 qualifying photos, plus planted decoys (a screenshot, a photo of a screen, a photo with one partner). Expected: 9 kept, decoys counted by the rule they failed, none shown.
4. **Edge: face-grouping miss.** One month where one partner faces away. Expected: that month appears as a gap with the face-grouping label, never as "not together".
5. **Edge: person not named.** Expected: the Skill asks the user to name the person in Photos and stops.
6. **Core: a family of four.** Two parents and two children, about 12 months, with a marriage certificate and two birth certificates (one photographed) and one date-of-birth mismatch. Expected: photos of all four by month, the three certificates listed with the people each names, the mismatch noted, nothing corrected.
7. **Edge: one person.** Expected: no photos chosen and no album; papers naming the person listed by month, with the gap list.

## Behaviour on the NAS (NOT VERIFIED)

- Whether the timeline summary returns sample photo paths that the vision check can read.
- Whether the album accepts the exact chosen photos.
- Whether the index read-back returns the full text.
