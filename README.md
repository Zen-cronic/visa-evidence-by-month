# Relationship evidence for visa applications, from your NAS

A Skill for UGREEN AI NAS that answers one question for a couple or family preparing a partner or spouse visa application, including their children: **"Which months can we not prove yet?"**

Before: scrolling years of photos and papers month by month, by hand. After: "February to May 2026: no photo of everyone and no linking paper found; electricity bills for those months would cover it", plus a folder ready to upload, saved only after you approve it.

It works from the photos and papers already on the NAS:

- finds photos where everyone on the application appears together, month by month, and checks each one is fit to send;
- finds the papers that link the people (leases, bills, marriage and birth certificates, scanned or photographed) and notes every name, birth date and address mismatch without changing it;
- lists the months with no evidence yet, and which of your regular papers could cover each one;
- saves an evidence folder ready to upload, only after you approve it.

It also prepares one person's own papers. Every step asks Uliya to use only the on-device model; nothing is saved until you approve it, and each save is read back.

It prepares evidence only. It does not judge eligibility, give legal advice or submit anything.

## What you get

An excerpt from the worked example (a synthetic family of four; the full run is in [`references/example-output.md`](relationship-evidence-pack/references/example-output.md)):

| Month | Photos of all four in the library | In the pack | Linking paper |
|---|---|---|---|
| 2025-12 | 15 | #5 | electricity bill |
| 2026-01 | 1 | 1 sample checked, none fit to send | electricity bill |
| **2026-02** | **0** | — | **—** |
| **2026-03** | **0** | — | **—** |
| **2026-04** | **0** | — | **—** |
| **2026-05** | **0** | — | **—** |
| 2026-06 | 5 | #6 | lease |

- **No photo of everyone found by face grouping and no linking paper: February to May 2026.**
  What could cover it: electricity bills came every month until January 2026; electricity bills for February to May 2026 would cover these months, if you have them; the lease starts in June 2026.

A gap means nothing was found, never that the family was apart. With your approval, the Skill saves the chosen photos, the papers, a Photo descriptions file to upload and working notes for you, then reads each one back.

What it saves, after you approve each item:

```
Visa evidence Linh Tran, Minh Tran, An Tran and Bao Tran/
  01 Photos/            chosen photos, renamed 01 2025-06-14 IMG_2031.jpg ...
  02 Papers/            linking papers, renamed in date order
  Photo descriptions    one line per photo, for upload
  Evidence index        working notes for you: coverage, gaps, mismatches
```

Canada's spouse checklist is the worked example. Other countries' partner visas also ask for proof of a shared life over time; check your own country's checklist for what it accepts.

## What's here

| Path | What it is |
|---|---|
| `relationship-evidence-pack/` | The Skill: `SKILL.md` plus `references/` (rules, common-law rules, saving, user guide, worked example, sources, safety, testing, disclosures). This folder is the upload package. |
| `tools/rulecheck/` | A small reference program that restates the Skill's steps that need no NAS call (planning months, choosing photos, joining papers, coverage and gaps) and checks them on synthetic cases, including the worked example. |
| `tools/capcheck/` | Checks every action the Skill relies on against the UGREEN capability catalog: it exists, takes the inputs used, Steps 1 to 7 only read, and every write is behind approval. |
| `scripts/build-package.sh` | Runs the checks and builds the upload ZIP. |
| `scripts/rename-skill.sh` | Renames the Skill folder and its frontmatter together, then rebuilds. |
| `.github/workflows/check.yml` | Runs the same checks on every push, with the official kit downloaded and its checksum verified. |

## Check and build

Needs Node.js, Python 3 and the unpacked `uliya-skill-kit` (0.7.7):

```
KIT=/path/to/uliya-skill-kit scripts/build-package.sh
```

It runs the rule checks, UGREEN's static checker (must report `static-pass` with no errors or warnings), the capability trace and the package checks (Markdown only, size limits, no scripts or secrets), then writes `dist/<skill-name>.zip`.

To rename the Skill:

```
KIT=/path/to/uliya-skill-kit scripts/rename-skill.sh new-skill-name
```

## Using it on the NAS

See `relationship-evidence-pack/references/user-guide.md`: name the people in Photos, have each person's printed name ready, put scanned papers in one folder, pick a save location outside it, then ask Uliya in plain words.

## Status

The Skill passes the static checker and the rule and capability checks. It has not yet run on a UGREEN AI NAS; `relationship-evidence-pack/references/testing.md` lists what is measured and what is not.

## License

MIT. All people, papers and photos in the examples are made up.
