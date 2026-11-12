# Disclosures

## Third-party components and open-source libraries

None. This Skill is Markdown only. It uses UGOS capabilities through UGREEN's registered expert agents (photo-agent, document-agent, file-agent, knowledge-agent) and includes no scripts, binaries, libraries or external services.

## Functionality developed for this Hackathon

All of it, written for the UGREEN Hackathon 2026 on AI NAS:

- choosing up to 20 photos that show both partners, spread across the relationship;
- the labelled per-photo line (date, place, people, confirmed context);
- finding and reconciling joint documents that name both partners;
- the month-by-month coverage table and gap list;
- writing the evidence folder, album and index back to the NAS.

## AI tools used

- UGOS Skill Creation Tool (uliya-skill-kit 0.7.3) and its static checker: Skill structure and checks.
- Claude Code (Anthropic): helped draft and check the Skill's Markdown structure and wording against the kit's rules. The concept, its scope and the final review are the author's.

## Data

The Skill reads only files the user points it to on their own NAS and writes only to the location the user confirms. It sends nothing off the NAS. Test data used during development is synthetic; no real personal data is included in this package.
