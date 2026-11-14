# Completion

SKILL.md points here from Completion and failure. The status rules themselves stay in SKILL.md.

Empty and partial results:

- Someone not named in Photos: ask the user to name them, keep them for papers only, or remove them from `{PEOPLE}`; never drop them silently.
- No photo of the people in the period: report it; for a family, offer fewer names; for a couple, continue with papers only.
- Fewer fit photos than the limit: keep them, state the number and the failures by rule, never pad.
- No documents folder, or no paper naming the people: say so and keep the photo evidence.
- A photo of a paper whose names cannot be read: list it as unreadable; never count it as linking.
- Unreadable documents: list them as failed and continue.
- A read-back that does not match: report the exact difference and do not write again.
