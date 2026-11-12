---
name: relationship-evidence-pack
description: Relationship evidence pack for partner, spousal and common-law visa applications, built from the couple's own photos and documents on the NAS. It picks up to 20 photos that show both partners across the whole relationship, drafts a date, place, people and context line for each, finds joint documents that name both people, and lists the months that have no evidence yet. Use when a couple says things like "build our relationship evidence for the sponsorship application", "pick the 20 photos immigration asks for" or "which months can we not prove yet".
---

# Goal

Partner-visa applications ask couples to prove the relationship is genuine and continuous. A common request is up to 20 photos of the couple together, each with a short description, plus documents that show a shared life (a lease, utility bills, insurance). Canada's spousal and common-law sponsorship is the worked example: it asks for photos with descriptions, and common-law couples must show 12 continuous months together.

This Skill turns the photo library and scanned papers the couple already keeps on the NAS into one evidence pack:

1. An evidence folder in checklist order, with copies of the selected photos and joint documents.
2. A Photos album of the selected photos.
3. An evidence index: one confirmed line per photo (date, place, people, context), the joint documents found, and a month-by-month coverage table.
4. A gap list: the months between the relationship start and today that have no photo and no joint document.

Everything stays on the NAS. The Skill prepares evidence only. It does not judge eligibility, does not give legal advice, and does not submit anything. The couple must check the pack against the current official checklist for their own application.

See [references/evidence-rules.md](references/evidence-rules.md) for how photos are chosen, how months are counted and how each line is labelled. Read it before the selection and coverage steps.

# Required input

Ask only for what the parent workflow needs, in one message:

1. The two partners' names exactly as they are named in Photos (people albums). If the user does not know, the first step lists the named people for them to choose from.
2. The month the relationship started (year and month).
3. The folder that holds scanned joint documents (lease, bills, insurance, bank letters). Optional. If none is given, the document step is skipped and the index says so.
4. Where to save the evidence folder. If not given, ask; do not choose a location yourself.
5. The photo limit. Default 20.

Do not ask for passport numbers, application numbers, addresses or any other personal identifiers. They are not needed.

# Generation-time capability evidence

- `ug-photo` → `photo-agent`
- `ug-document` → `document-agent`
- `ug-filesystem` → `file-agent`
- `ug-knowledge` → `knowledge-agent`

# Orchestration

Run the steps in order. Each step uses only the real result returned by the previous step. If a step does not return `completed`, follow the Completion and failure rules and do not run steps that depend on it.

## Step 1. Confirm both partners in Photos

```
delegate --target photo-agent --instruction 'List the people albums in Photos that have a name. Check whether both partner names given by the user exist exactly. For each partner return the matching person name and person ID. If a name has no exact match, return the closest named people and the number of unnamed people albums, and do not guess. Read only. Do not rename, merge or change any album.'
```

If either partner is not found, return `waiting_user`: show the closest names and ask the user to pick one, or to name that person in Photos first and run the Skill again. Do not continue with one partner.

## Step 2. Find photos with both partners

```
delegate --target photo-agent --instruction 'Search Photos for pictures in which BOTH confirmed partners appear together, using the two confirmed person names with the AND method, from the first day of the relationship start month given by the user until today. Images only. For every match return the file path, the capture date and time, and the location name or GPS coordinates if present in the photo metadata. Say which fields are missing for each photo. Return every match, page through all results, and report the total. Read only. If there are no matches, say no results and stop.'
```

If the result is empty, report "no photos with both partners were found in this period" and stop. Do not widen the search to photos of one partner, other people or other dates.

## Step 3. Choose the photos (parent, no NAS call)

From the real list returned in Step 2, choose up to the photo limit using the selection rules in [references/evidence-rules.md](references/evidence-rules.md): spread across the relationship, at most one photo per month until every covered month has one, then prefer new places. Never pad: if fewer qualifying photos exist than the limit, keep the smaller number and say so. Photos without a capture date cannot be placed on the timeline; list them separately and do not choose them.

## Step 4. Draft a context line for each chosen photo

```
delegate --target photo-agent --instruction 'For each photo path in the chosen list, describe only what is visible: the setting (for example a kitchen, a beach, a restaurant, a wedding venue) and the activity. Answer in one short sentence per photo. Do not name people, do not guess dates, cities, event names or relationships, and do not invent details that are not visible. If the image is unclear, answer unclear. Read only.'
```

Build one draft line per photo with each field labelled by its source, as defined in the reference: date and place from metadata, people from the confirmed person names, context from the visual description. Mark every context as `[confirm]`.

## Step 5. Find joint documents

Skip this step if the user gave no documents folder.

```
delegate --target document-agent --instruction 'In the documents folder given by the user, extract from each document: the document type (lease, utility bill, insurance, bank statement, other), every person name it shows, the address it shows, and the date or period it covers. Then reconcile the results: say which documents name both partners, and whether the names and addresses match across documents. Report documents that could not be read as failures. Read only. If no document names both partners, say no matching documents were found.'
```

Keep only documents that name both partners. Note any name or address mismatch in the index; do not correct it.

## Step 6. Count covered months (parent, no NAS call)

List every month from the relationship start to the current month. A month is covered by a photo if a chosen or unchosen both-partner photo has a capture date in it, and covered by a document if a joint document is dated in it or its period includes it. Report photo coverage and document coverage separately. Every month with neither is a gap. Group consecutive gap months into ranges, for example "no evidence: March to June 2025".

## Step 7. Confirm the lines with the user

Return `waiting_user` with the draft index: the chosen photos with their labelled lines, the joint documents, the coverage table and the gap list. Ask the user to confirm, edit or replace each `[confirm]` context (for example "first trip to Banff together" in place of "two people on a mountain trail"). Only lines the user confirms or edits are written. Lines the user does not confirm stay marked `[not confirmed]` in the saved index.

## Step 8. Write the evidence pack

Every write below is a state change and goes through approval. Show the exact folder name and the number of files before asking.

```
delegate --target file-agent --instruction 'Create the evidence folder at the save location the user confirmed, named Relationship evidence followed by the two partner names, with two subfolders named 01 Photos and 02 Joint documents. Then copy, never move, each chosen photo into 01 Photos and each joint document into 02 Joint documents, keeping the original files where they are. Prefix each photo copy with its order number and capture date so the folder sorts in timeline order. Do not overwrite existing files. Report every created path and every copy that failed.'
```

```
delegate --target photo-agent --instruction 'Create a custom album named Relationship evidence followed by the two partner names, and add exactly the chosen photos listed by path. Do not add any other photo. Return the album ID and the number of photos added, and list any photo that could not be added.'
```

```
delegate --target knowledge-agent --instruction 'Save the confirmed evidence index text supplied in this request as a Markdown file named Evidence index in the evidence folder created by the file step. Save the text exactly as supplied, without rewriting, summarising or adding content. Return the saved file path and confirm it was verified.'
```

The evidence index text passed to the save step contains, in this order: the partner names and relationship start month; the photo table (order, file name, date, place, people, confirmed context, source labels); the joint documents table (type, date or period, names shown, match notes); the coverage table and the gap list; the counts (both-partner photos found, chosen, excluded for missing dates, documents read, documents failed); and this note: "Prepared from files on this NAS. Not legal advice. Check against the current official checklist before submitting."

# Completion and failure

Report a result only after the delegated expert returns `completed`, and report only what it returned.

- `completed`: use the real result. For the final summary, show the evidence folder path, the album name and photo count, the index file path, the number of photos chosen against the limit, the number of joint documents, and the gap list.
- `failed`: say which step failed and why, in plain words. Stop every later step that needs its result. If a write step fails after others succeeded, list what was already created so nothing is left unexplained, and do not delete it.
- `cancelled`: stop and report which steps finished and which were not run.
- `waiting_user`: pass the expert's question to the user, wait for the answer, then repeat only that step.
- `waiting_approval`: show what will be written or copied and wait. If the user declines, skip that write, keep the other results, and say the pack is incomplete.

Empty and partial results:

- No named partner found: ask the user to name both people in Photos first. Do not continue.
- No photos with both partners: report no results and stop. Do not substitute photos of one partner.
- Fewer qualifying photos than the limit: keep them all, state the number, and do not pad.
- No joint documents, or no documents folder given: say so in the index and keep the photo evidence.
- Some documents unreadable: list them as failed and continue with the rest.
- Photos without a capture date: list them separately as "date unknown"; never assign a date.

Never invent NAS data, a date, a place, a name or a context. Never move or delete the user's original files.

# Disclosures

See [references/disclosures.md](references/disclosures.md) for third-party components, AI tools used and the functionality developed for this Hackathon.
