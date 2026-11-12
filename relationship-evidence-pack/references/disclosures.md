# Disclosures

## Third-party components and open-source libraries

None. This Skill is Markdown only. It uses UGOS capabilities through UGREEN's registered expert agents (photo-agent, document-agent, file-agent, knowledge-agent) and includes no scripts, binaries, libraries or external services.

## Functionality developed for this Hackathon

All of it, written for the UGREEN Hackathon 2026 on AI NAS:

- counting photos of both partners per month and choosing up to 20, spread across the relationship and checked as fit to send;
- the labelled per-photo line (date, place, people, confirmed context);
- finding and reconciling joint documents that name both partners;
- the month-by-month coverage table and gap list;
- writing the evidence folder, album and index back to the NAS.

## AI tools used

- UGOS Skill Creation Tool (uliya-skill-kit 0.7.7) and its static checker: Skill structure and checks.
- Claude Code (Anthropic): research on the problem and on existing tools, comparing idea options, drafting and checking this Skill's Markdown against the kit's rules, and mock reviews against the judging criteria. The author chose the concept from those options, set its scope, named the Skill, wrote the 10-question PDF answers and reviewed the final package.

## Data

The Skill reads only files the user points it to on their own NAS and writes only to the location the user confirms. It sends nothing off the NAS. Test data used during development is synthetic; no real personal data is included in this package.
