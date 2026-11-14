# Relationship evidence for visa applications, from your NAS

A Skill for UGREEN AI NAS that answers one question for a couple or family preparing a partner or spouse visa application, including their children: **"Which months can we not prove yet?"**

It works from the photos and papers already on the NAS:

- finds photos where everyone on the application appears together, month by month, and checks each one is fit to send;
- finds the papers that link the people (leases, bills, marriage and birth certificates, scanned or photographed) and notes every name, birth date and address mismatch without changing it;
- lists the months with no evidence yet, and which of your regular papers could cover each one;
- saves an evidence folder ready to upload, only after you approve it.

It also prepares one person's own papers. Every step asks Uliya to use only the on-device model; nothing is saved until you approve it, and each save is read back.

It prepares evidence only. It does not judge eligibility, give legal advice or submit anything.

## What's here

| Path | What it is |
|---|---|
| `relationship-evidence-pack/` | The Skill: `SKILL.md` plus `references/` (rules, user guide, worked example, sources, safety, testing, disclosures). This folder is the upload package. |
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
