# Same-address papers

Apply these rules to a couple or a family, whatever `{RELATIONSHIP}` is: married, common-law or other. Skip this file for one person. SKILL.md points here at Step 5c, Step 6 and Step 7. What is different for common-law partners (photos do not fill a month, the extra column, the gap label and the footer) is in [common-law.md](common-law.md).

`{PARTNERS}` is asked in Required input: for a family, the two people the user names as the partners; for a couple, `{PARTNERS}` is the two people. After Step 1, each checked name in `{PARTNERS}` is the exact Photos name returned or picked.

Canada's spouse checklist (IMM 5533), in its list of proof that a couple lives together, accepts "other documents issued to you or your sponsor showing the same address, whether the accounts are held jointly or not". The Skill uses this to show months a couple lived at the same address; it is a planning aid, not a ruling on what an officer will accept. The common-law checklist was not read for this Skill (see [sources.md](sources.md)).

## Step 5c: single-name papers at an address

Also keep, as `{ADDRESS_DOCS}`, every paper that names exactly one of `{PARTNERS}` (matched by their names in `{MATCH_NAMES}`; a child named on it does not matter) and shows an address, and, unless `{RELATIONSHIP}` is common-law, is not already in `{LINKED_DOCS}`. A joint paper naming both partners is never in this list.

Label and dedupe `{ADDRESS_DOCS}` with the same 5c rules as `{LINKED_DOCS}` (scan or photo, the same paper kept once). After Step 6, include `{SAME_ADDRESS_DOCS}` (the ones that fill a month) in the comparison of names, dates of birth and addresses, so the draft in Step 7 shows their mismatches; papers listed only in the notes are not compared.

## Step 6: same-address pairs

A same-address pair is papers from `{ADDRESS_DOCS}` dated in or covering one month, one naming each partner, that show the same address (ignoring format differences). A pair fills a month only when no single paper already covers that month (a linking paper, or for common-law a paper naming both partners with an address); photos do not change this.

When `{RELATIONSHIP}` is married or other, a month is covered by a photo of `{PHOTO_PEOPLE}`, by a linking paper, or by a same-address pair. Show a pair in the linking paper column, naming both papers, such as "phone bill (Mei) + bank letter (Daniel), one name, same address". A gap is a month with none of the three; its label is the one SKILL.md Step 6 gives. When `{RELATIONSHIP}` is common-law, [common-law.md](common-law.md) sets what counts instead.

`{SAME_ADDRESS_DOCS}` is the papers from `{ADDRESS_DOCS}` that actually fill a month this way; from here on they are handled like `{LINKED_DOCS}` (the papers table, labelled "one name, same address"; the drop question; the comparison of names, dates of birth and addresses; and `{PAPER_COPIES}`). Papers from `{ADDRESS_DOCS}` that fill no month are listed only in the working notes and are not copied.

What could cover each gap: use only papers in `{LINKED_DOCS}` or `{ADDRESS_DOCS}` (from `{ADDRESS_DOCS}`, a series in which each month's papers show both partners at the same address, as one paper per partner; each partner's papers are one type, and the line names both types, such as "phone bills (Mei) and bank letters (Daniel) came every month until …"). When only one partner's papers form such a series, say so and name the missing half: "<type>s in <name>'s name came every month until <month>; a paper in <other>'s name at the same address for <gap months> would add evidence, if you have one". The rest of that rule (the series of at least 3 papers, the paper whose period starts the month after the gap, the wording, and "no regular paper found near these months") is in SKILL.md Step 6 and is unchanged.

## Step 7: drops, comparison and paper copies

A confirmed possible match on a paper that names one partner goes to `{ADDRESS_DOCS}`, not `{LINKED_DOCS}`.

After the answers, remove every dropped paper from `{ADDRESS_DOCS}` as well as from `{LINKED_DOCS}`; redoing Step 6 with these values rebuilds `{SAME_ADDRESS_DOCS}`. Then redo the 5c comparison of names, dates of birth and addresses across the updated `{LINKED_DOCS}` and `{SAME_ADDRESS_DOCS}` (mismatches from dropped papers go).

`{PAPER_COPIES}` has one line per distinct paper file in `{LINKED_DOCS}` and `{SAME_ADDRESS_DOCS}` (a file in both is copied once), in the same form and with the same copy names as SKILL.md Step 7 gives.

In `{INDEX_TEXT}`, after the coverage table, the gap list and what could cover each gap, list the single-name papers that filled no month (listed, not copied).
