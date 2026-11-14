# User guide

See which months your photos and papers prove you were together, find out what would fill each gap, and get an upload-ready folder, without your family's photos and papers leaving your NAS.

It answers one question: **which months can we not prove yet?** For each month it shows the photos of everyone together, the paper that covers that month (a lease, a bill, a certificate), and, for any month with neither, what could close the gap. See [example-output.md](example-output.md).

## Before you start

1. **Name the people in Photos.** Open Photos, find each person's people album and give it a name. Face grouping finds photos only of named people. A baby without a face group yet can still be on the application for papers only.
2. **Know each person's name as printed on their papers**, such as "Tran Thi Linh". Papers are matched on these names, not on Photos nicknames.
3. **Put scanned papers in one folder**, if you have any: leases, bills, bank statements, marriage and birth certificates, letters. Photos of papers taken with your phone are found in the photo library; you do not need to move them.
4. **Pick where to save the pack.** Any folder outside the papers folder.
5. **Check Uliya's model setting** if you can, so nothing you share leaves the NAS. The Skill asks about it first; if you are not sure, it explains and asks whether to continue.

## What to ask

- A couple: "Build our relationship evidence for the sponsorship application. Linh Tran and Minh Tran, covering June 2025 to now. Save in /Family/Visa." It then asks for your names as printed on papers and your papers folder.
- A family: "Get our family's evidence ready for the visa: Linh, Minh, An and Bao Tran, covering June 2025 to now. An and Bao are our children." If a child has no face group yet, such as a newborn, say "keep them for papers only". If Uliya does not show today's date, say it too.
- One person: "Which months can I not prove with my papers? Siti Rahman, covering December 2025 to now."

It asks only for what it needs, when it needs it, and asks once before saving anything.

Words you will see: **face grouping** is how Photos recognises the same person across photos; a **linking paper** is a paper that names the people on your application (a lease naming you both, a birth certificate naming a parent and child); a **possible match** is a paper where a name is spelled slightly differently, which you confirm or reject.

## What you get

- **A coverage table** with one row per month: photos of everyone found by face grouping (or of the people searched together, named in the label), the photo chosen for the pack, and the paper that covers the month.
- **A gap list**: the months with no photo of everyone (or of the people searched together) and no linking paper. A gap means the Skill found nothing, not that you were apart. Each gap also says what could close it, such as "bills for February to May 2026", based on the linking papers it already found.
- **Up to 20 photos**, one per month, each checked as fit to send, each with a line for date, place, people and context. You can confirm or edit each context line; any you skip are saved as `[not confirmed]`. The Skill never writes what a moment was.
- **The papers that link you**, with any difference in a name, birth date or address noted, never changed.
- **A folder, an album and an index file** saved on the NAS, each only if you approve it, then read back to check they match.

A worked example with a made-up family is in [example-output.md](example-output.md).

## Check yourself before you submit

- Every `[not confirmed]` line: confirm it, edit it, or drop the photo.
- Every gap month: look through those months by hand. Face grouping can miss a turned head, a new haircut, or photos in a library your account cannot open.
- Every possible match and mismatch: decide whether you need to explain it in your application.
- Photos of papers: upload a clean scan or the original if the officer needs it.
- The current official checklist for your application. Rules differ by country and change over time; this Skill does not give legal advice.

## Limits

- Only people named in Photos can be found in photos; only papers on this NAS can be found.
- Up to 3 sample photos a month are checked; a month where all fail is labelled "3 samples checked, none fit to send", and other photos from that month may still be usable.
- Photo descriptions come from the vision model and can be wrong, which is why you confirm each one.
- A second run offers to reuse the context lines you confirmed in your latest earlier pack, for the same photos (same date and file name), marked "from your earlier pack" and shown for you to confirm again; everything else is found again from your library and papers.
