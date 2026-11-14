# Common-law rules

Apply these rules only when `{RELATIONSHIP}` is common-law, for a couple or a family. SKILL.md points here at Step 5c, Step 6 and Step 7. For every other case, skip this file.

`{PARTNERS}` is asked in Required input: for a common-law family, the two people the user names as the partners; for a couple, `{PARTNERS}` is the two people. After Step 1, each checked name in `{PARTNERS}` is the exact Photos name returned or picked.

## Step 5c: single-name papers at an address

When `{RELATIONSHIP}` is common-law, for a couple or a family, also keep, as `{ADDRESS_DOCS}`, every paper that names exactly one of `{PARTNERS}` (matched by their names in `{MATCH_NAMES}`; a child named on it does not matter) and shows an address. A joint paper naming both partners is never in this list. Canada's spouse checklist (IMM 5533) accepts "documents issued to you or your sponsor showing the same address, whether the accounts are held jointly or not"; the common-law checklist was not read for this Skill (see [sources.md](sources.md)).

Label and dedupe `{ADDRESS_DOCS}` with the same 5c rules as `{LINKED_DOCS}` (scan or photo, the same paper kept once), and include them in the 5c comparison of names, dates of birth and addresses, so the draft in Step 7 shows their mismatches.

## Step 6: coverage, gaps and footer

When `{RELATIONSHIP}` is common-law, a month counts as covered only when the partners are shown at the same address: by one paper naming both `{PARTNERS}` with an address, or by papers from `{ADDRESS_DOCS}` dated in or covering that month, one naming each partner, showing the same address (ignoring format differences). Photos are shown but do not count, and papers naming both partners without an address are listed but do not count.

When `{RELATIONSHIP}` is common-law, add a fourth column, "Same address shown (counts)", naming the paper or papers that show it, and a gap is a month where the partners are not shown at the same address, whatever the photos. Group consecutive gap months and label them "no paper showing you both at the same address found: April to June 2026" (the months as they apply). `{SAME_ADDRESS_DOCS}` is the papers from `{ADDRESS_DOCS}` that actually fill a month this way; from here on they are handled like `{LINKED_DOCS}` (the papers table, labelled "one name, same address"; the drop question; the comparison of names, dates of birth and addresses; and `{PAPER_COPIES}`). Papers from `{ADDRESS_DOCS}` that fill no month are listed only in the working notes and are not copied. The gap rule and gap label for everyone else in SKILL.md Step 6 do not apply.

What could cover each gap: use only papers in `{LINKED_DOCS}`, or for common-law also `{ADDRESS_DOCS}` (a series in which each month's papers show both partners at the same address, jointly or as one paper per partner; when one paper per partner, each partner's papers are one type, and the line names both types, such as "phone bills (Mei) and bank letters (Daniel) came every month until …"). The rest of that rule (the series of at least 3 papers, the paper whose period starts the month after the gap, the wording, and "no regular paper found near these months") is in SKILL.md Step 6 and is unchanged.

Under the gap list, always add, when it is common-law: "This table shows which months have papers showing you both at the same address. It does not show whether you meet the 12-month rule; check the official rules or ask a licensed consultant. Photos and other papers stay in the pack; they just do not fill a month for this check."

## Step 7: drops, comparison and paper copies

A confirmed possible match on a paper that names one partner goes to `{ADDRESS_DOCS}`, not `{LINKED_DOCS}`.

After the answers, remove every dropped paper from `{ADDRESS_DOCS}` as well as from `{LINKED_DOCS}`; redoing Step 6 with these values rebuilds `{SAME_ADDRESS_DOCS}`. Then redo the 5c comparison of names, dates of birth and addresses across the updated `{LINKED_DOCS}` and `{SAME_ADDRESS_DOCS}` (mismatches from dropped papers go).

`{PAPER_COPIES}` has one line per distinct paper file in `{LINKED_DOCS}` and `{SAME_ADDRESS_DOCS}` (a file in both is copied once), in the same form and with the same copy names as SKILL.md Step 7 gives.

In `{INDEX_TEXT}`, after the coverage table, the gap list and what could cover each gap, list the single-name papers that filled no month (listed, not copied).
