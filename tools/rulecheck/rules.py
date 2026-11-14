"""Reference implementation of the Skill's deterministic parent steps.

The Skill itself is Markdown that Uliya's assistant follows on the NAS. This module
restates the rules it gives for the steps that need no NAS call (planning months,
choosing photos, joining papers, coverage and gaps) so they can be checked on
synthetic cases. It does not call the NAS and does not prove runtime behaviour.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

GAP_LABEL = "no photo of everyone found by face grouping and no linking paper"
PAPER_GAP_LABEL = "no linking paper found"
FORBIDDEN_GAP_WORDS = ("no relationship", "not together", "not in the country", "apart")

RULES = {
    1: "everyone named clearly visible",
    2: "every face visible and not covered",
    3: "a real photo, not a screenshot or a photo of a screen, print or paper",
    4: "suitable to show a government officer",
    5: "not blurry",
}


def month_range(start: str, end: str) -> list[str]:
    """Months from start to end inclusive, as YYYY-MM."""
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def scope_of(people: list[str]) -> str:
    if not 1 <= len(people) <= 6:
        raise ValueError("one to six people")
    return {1: "one person", 2: "a couple"}.get(len(people), "a family")


def confirm_people(named_albums: list[str], people: list[str]) -> dict:
    """Step 1: every name must match exactly; otherwise ask, never drop anyone."""
    missing = [p for p in people if p not in named_albums]
    if missing:
        return {"status": "waiting_user", "missing": missing}
    return {"status": "completed", "missing": []}


# Step 3

def plan_months(month_counts: dict[str, int], limit: int) -> list[str]:
    """Spread up to `limit` months across the period; never plan a zero month."""
    with_photos = sorted(m for m, n in month_counts.items() if n > 0)
    if len(with_photos) <= limit:
        return with_photos
    order = sorted(month_counts)
    idx = {m: i for i, m in enumerate(order)}
    plan = {with_photos[0], with_photos[-1]}
    while len(plan) < limit:
        planned = sorted(plan, key=idx.get)
        best = None
        for a, b in zip(planned, planned[1:]):
            inside = [m for m in with_photos if idx[a] < idx[m] < idx[b]]
            if not inside:
                continue
            mid = (idx[a] + idx[b]) / 2
            # longest stretch first; inside it, the month nearest the middle
            pick = min(inside, key=lambda m: (abs(idx[m] - mid), idx[m]))
            key = idx[b] - idx[a]
            if best is None or key > best[0]:
                best = (key, pick)
        if best is None:
            break
        plan.add(best[1])
    return sorted(plan, key=idx.get)


# Step 4

@dataclass
class Checked:
    path: str
    month: str
    date: str  # YYYY-MM-DD
    failed_rule: int | None  # None means passed


@dataclass
class Choice:
    chosen: list[Checked] = field(default_factory=list)
    none_fit: list[str] = field(default_factory=list)
    failures: dict[int, int] = field(default_factory=lambda: {r: 0 for r in RULES})


def choose_photos(checked: list[Checked], plan: list[str], limit: int) -> Choice:
    """First passing photo per planned month, one per month, never padded."""
    result = Choice()
    for c in checked:
        if c.failed_rule is not None:
            result.failures[c.failed_rule] += 1
    for month in plan:
        pick = next((c for c in checked if c.month == month and c.failed_rule is None), None)
        if pick is None:
            if any(c.month == month for c in checked):
                result.none_fit.append(month)
            continue
        if len(result.chosen) < limit:
            result.chosen.append(pick)
    return result


# Step 5c

@dataclass
class Paper:
    kind: str
    names: list[str]
    source: str  # "scanned document" or "from a photo of a document"
    start: str | None = None  # YYYY-MM covered from
    end: str | None = None  # YYYY-MM covered to
    dated: str | None = None  # YYYY-MM-DD for one-off papers
    address: str | None = None
    dob: dict[str, str] = field(default_factory=dict)
    readable: bool = True
    asks: str | None = None  # an instruction found inside the paper


def _words(name: str) -> list[str]:
    return sorted(re.sub(r"[,.]", " ", name).lower().split())


def name_matches(printed: str, given: str) -> bool:
    """Same words, ignoring case, commas and word order."""
    return _words(printed) == _words(given)


def name_near(printed: str, given: str) -> bool:
    """Same number of words and exactly one word spelled differently."""
    a, b = _words(printed), _words(given)
    return len(a) == len(b) >= 2 and len(set(a) ^ set(b)) == 2


def _enough(named: int, people: list[str]) -> bool:
    if len(people) <= 2:
        return named == len(people)
    return named >= 2


def named_in(paper: Paper, people: list[str], near: bool = False) -> list[str]:
    hit = name_near if near else name_matches
    return [g for g in people if any(name_matches(n, g) or (near and hit(n, g)) for n in paper.names)]


def links(paper: Paper, people: list[str]) -> bool:
    return _enough(len(named_in(paper, people)), people)


def join_papers(papers: list[Paper], people: list[str]) -> dict:
    """Keep linking papers; prefer a scan over a photo of the same paper; note, never fix, mismatches."""
    unreadable = [p for p in papers if not p.readable]
    readable = [p for p in papers if p.readable]
    asked = [p.asks for p in readable if p.asks]
    linked: list[Paper] = []
    noted_photos: list[Paper] = []
    possible: list[Paper] = []
    for p in readable:
        if not links(p, people):
            if _enough(len(named_in(p, people, near=True)), people):
                possible.append(p)  # shown to the user, never linked on its own
            continue
        twin = next(
            (q for q in linked if q.kind == p.kind and sorted(q.names) == sorted(p.names)
             and (q.start, q.end, q.dated) == (p.start, p.end, p.dated)),
            None,
        )
        if twin is None:
            linked.append(p)
        elif twin.source != "scanned document" and p.source == "scanned document":
            linked[linked.index(twin)] = p
            noted_photos.append(twin)
        else:
            noted_photos.append(p)
    mismatches = []
    for person in people:
        dobs = sorted({p.dob[person] for p in linked if person in p.dob})
        if len(dobs) > 1:
            mismatches.append(("date of birth", person, dobs))
    addresses = sorted({p.address for p in linked if p.address})
    if len(addresses) > 1:
        mismatches.append(("address", None, addresses))
    return {
        "linked": linked,
        "noted_photos": noted_photos,
        "possible_matches": possible,
        "unreadable": unreadable,
        "mismatches": mismatches,
        "asked_not_followed": asked,
    }


# Step 6

def paper_covers(paper: Paper, month: str) -> bool:
    if paper.start and paper.end:
        return paper.start <= month <= paper.end
    return bool(paper.dated) and paper.dated[:7] == month


def coverage(start: str, end: str, month_counts: dict[str, int] | None, chosen: list[Checked], linked: list[Paper]) -> list[dict]:
    """month_counts is None for one person or when the photo search failed: gaps then use papers only."""
    rows = []
    numbers = {c.month: i + 1 for i, c in enumerate(chosen)}
    for month in month_range(start, end):
        papers = [p.kind for p in linked if paper_covers(p, month)]
        count = None if month_counts is None else month_counts.get(month, 0)
        rows.append({
            "month": month,
            "library": count,
            "pack": numbers.get(month),
            "papers": papers,
            "gap": (count in (None, 0)) and not papers,
        })
    return rows


def group_gaps(rows: list[dict]) -> list[tuple[str, str]]:
    runs, current = [], None
    for r in rows:
        if r["gap"]:
            current = [r["month"], r["month"]] if current is None else [current[0], r["month"]]
        elif current is not None:
            runs.append(tuple(current))
            current = None
    if current is not None:
        runs.append(tuple(current))
    return runs


def gap_label(papers_only: bool = False, search_failed: bool = False, who: str | None = None) -> str:
    if papers_only or search_failed:
        return PAPER_GAP_LABEL + ("; the photo search failed" if search_failed else "")
    return GAP_LABEL if who is None else GAP_LABEL.replace("of everyone", f"of {who}")


def gap_lines(rows: list[dict], label: str = GAP_LABEL) -> list[str]:
    return [f"{label}: {a} to {b}" if a != b else f"{label}: {a}" for a, b in group_gaps(rows)]
