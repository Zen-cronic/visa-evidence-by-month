"""Reference implementation of the Skill's deterministic parent steps.

The Skill itself is Markdown that Uliya's assistant follows on the NAS. This module
restates the rules it gives for the steps that need no NAS call (planning months,
choosing photos, joining papers, coverage and gaps) so they can be checked on
synthetic cases. It does not call the NAS and does not prove runtime behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field

GAP_LABEL = "no photo of everyone found by face grouping and no linking paper"
FORBIDDEN_GAP_WORDS = ("no relationship", "not together", "not in the country", "apart")

RULES = {
    1: "everyone named is visible",
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

def plan_months(month_counts: dict[str, int], limit: int, paper_months: set[str] | None = None) -> list[str]:
    """Spread up to `limit` months across the period; never plan a zero month."""
    paper_months = paper_months or set()
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
            # longest stretch first; inside it, prefer a month with no linking paper, then the middle
            pick = min(inside, key=lambda m: (m in paper_months, abs(idx[m] - mid), idx[m]))
            key = (idx[b] - idx[a], pick not in paper_months)
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
    """First passing photo per planned month, at most one per calendar day, never padded."""
    result = Choice()
    for c in checked:
        if c.failed_rule is not None:
            result.failures[c.failed_rule] += 1
    used_days: set[str] = set()
    for month in plan:
        pick = next(
            (c for c in checked if c.month == month and c.failed_rule is None and c.date not in used_days),
            None,
        )
        if pick is None:
            if any(c.month == month for c in checked):
                result.none_fit.append(month)
            continue
        if len(result.chosen) < limit:
            result.chosen.append(pick)
            used_days.add(pick.date)
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


def links(paper: Paper, people: list[str]) -> bool:
    named = [p for p in people if p in paper.names]
    if len(people) == 1:
        return len(named) == 1
    if len(people) == 2:
        return len(named) == 2
    return len(named) >= 2


def join_papers(papers: list[Paper], people: list[str]) -> dict:
    """Keep linking papers; prefer a scan over a photo of the same paper; note, never fix, mismatches."""
    unreadable = [p for p in papers if not p.readable]
    readable = [p for p in papers if p.readable]
    asked = [p.asks for p in readable if p.asks]
    linked: list[Paper] = []
    noted_photos: list[Paper] = []
    for p in readable:
        if not links(p, people):
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
        "unreadable": unreadable,
        "mismatches": mismatches,
        "asked_not_followed": asked,
    }


# Step 6

def paper_covers(paper: Paper, month: str) -> bool:
    if paper.start and paper.end:
        return paper.start <= month <= paper.end
    return bool(paper.dated) and paper.dated[:7] == month


def coverage(start: str, end: str, month_counts: dict[str, int], chosen: list[Checked], linked: list[Paper]) -> list[dict]:
    rows = []
    numbers = {c.month: i + 1 for i, c in enumerate(chosen)}
    for month in month_range(start, end):
        papers = [p.kind for p in linked if paper_covers(p, month)]
        count = month_counts.get(month, 0)
        rows.append({
            "month": month,
            "library": count,
            "pack": numbers.get(month),
            "papers": papers,
            "gap": count == 0 and not papers,
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


def gap_lines(rows: list[dict]) -> list[str]:
    return [f"{GAP_LABEL}: {a} to {b}" if a != b else f"{GAP_LABEL}: {a}" for a, b in group_gaps(rows)]
