# Disclosures

## Third-party components and open-source libraries

None. This Skill is Markdown only. It uses UGOS capabilities through UGREEN's registered expert agents (photo-agent, document-agent, file-agent, knowledge-agent) and includes no scripts, binaries, libraries or external services.

## Functionality developed for this Hackathon

All of it, written for the UGREEN Hackathon 2026 on AI NAS:

- a scope that follows the people named: one person, a couple or a family;
- counting photos of everyone named per month and choosing up to 20, spread across the period and checked as fit to send;
- the labelled per-photo line (date, place, people, confirmed context);
- finding and reconciling the papers that link the people, scanned or photographed;
- the month-by-month coverage table and gap list;
- writing the evidence folder, album and index back to the NAS.

## AI tools used

- UGOS Skill Creation Tool (uliya-skill-kit 0.7.7) and its static checker: Skill structure and checks.
- Claude Code (Anthropic): research on the problem and on existing tools, comparing idea options, drafting and checking this Skill's Markdown against the kit's rules, and mock reviews against the judging criteria. The author chose the concept from those options, set its scope, named the Skill, wrote the 10-question PDF answers and reviewed the final package.

## Data

The Skill reads only files the user points it to on their own NAS and writes only to the location the user confirms. It is designed to send nothing off the NAS: every step asks the experts to use only the local model, and the user confirms Uliya's model setting first. Test data and the worked example use made-up people; no real personal data is included in this package.
