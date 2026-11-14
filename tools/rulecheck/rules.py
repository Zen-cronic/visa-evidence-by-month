"""Reference implementation of the Skill's deterministic parent steps.

The Skill itself is Markdown that Uliya's assistant follows on the NAS. This module
restates the rules it gives for the steps that need no NAS call (planning months,
choosing photos, joining papers, coverage and gaps) so they can be checked on
synthetic cases. It does not call the NAS and does not prove runtime behaviour.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

GAP_LABEL = "no photo of everyone found by face grouping and no linking paper"
PAPER_GAP_LABEL = "no linking paper found"
FORBIDDEN_GAP_WORDS = ("no relationship", "not together", "not in the country", "apart")

RULES = {
    1: "the people the photo is about clearly visible in the foreground",
    2: "their faces visible and not covered",
    3: "a real photo, not a screenshot or a photo of a screen or paper (a photographed print of a photo passes)",
    4: "appropriate to send to a government officer",
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
    if not people:
        raise ValueError("at least one person")
    return {1: "one person", 2: "a couple"}.get(len(people), "a family")


PHOTO_SEARCH_MAX = 6  # more people than this: the user picks who is searched in photos together


def photo_people_for(people: list[str], picked: list[str] | None = None) -> list[str]:
    """Over six people, only the ones the user picked are searched in photos; the rest are papers-only."""
    if len(people) <= PHOTO_SEARCH_MAX:
        return list(people)
    if not picked or len(picked) > PHOTO_SEARCH_MAX:
        raise ValueError("ask which six at most to search in photos")
    return [p for p in people if p in picked]


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


def _fold(name: str) -> str:
    """Drop accents so "Trần Thị Linh" and "Tran Thi Linh" compare equal (đ has no decomposition)."""
    decomposed = unicodedata.normalize("NFD", name.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _words(name: str) -> list[str]:
    return sorted(re.sub(r"[,.]", " ", _fold(name)).lower().split())


def name_matches(printed: str, given: str) -> bool:
    """Same words, ignoring case, commas, accents and word order."""
    return _words(printed) == _words(given)


def name_near(printed: str, given: str) -> bool:
    """Same number of words and exactly one word spelled differently."""
    a, b = _words(printed), _words(given)
    return len(a) == len(b) >= 2 and len(set(a) ^ set(b)) == 2


def name_contains(printed: str, photos_name: str) -> bool:
    """Without printed names: the printed name holds every word of the Photos name. Possible match only."""
    return set(_words(photos_name)) <= set(_words(printed))


def _enough(named: int, people: list[str]) -> bool:
    if len(people) <= 2:
        return named == len(people)
    return named >= 2


def named_in(paper: Paper, people: list[str], near: bool = False) -> list[str]:
    hit = name_near if near else name_matches
    return [g for g in people if any(name_matches(n, g) or (near and hit(n, g)) for n in paper.names)]


def links(paper: Paper, people: list[str]) -> bool:
    return _enough(len(named_in(paper, people)), people)


ABBREVIATIONS = {"street": "st", "road": "rd", "avenue": "ave", "apartment": "unit", "apt": "unit", "suite": "unit"}


def normalise_address(address: str) -> str:
    """Abbreviation and punctuation differences only: "12 Elm Street #4" and "12 Elm St Unit 4" are the same."""
    s = address.lower().replace("#", " unit ")
    s = re.sub(r"[.,]", " ", s)
    return " ".join(ABBREVIATIONS.get(w, w) for w in s.split())


def join_papers(papers: list[Paper], people: list[str], printed_names: bool = True) -> dict:
    """Keep linking papers; prefer a scan over a photo of the same paper; note, never fix, mismatches."""
    unreadable = [p for p in papers if not p.readable]
    readable = [p for p in papers if p.readable]
    asked = [p.asks for p in readable if p.asks]
    linked: list[Paper] = []
    noted_photos: list[Paper] = []
    possible: list[Paper] = []
    for p in readable:
        if not printed_names:
            hits = [g for g in people if any(name_contains(n, g) for n in p.names)]
            if _enough(len(hits), people):
                possible.append(p)  # Photos names can never link a paper on their own
            continue
        if not links(p, people):
            if _enough(len(named_in(p, people, near=True)), people):
                possible.append(p)  # shown to the user, never linked on its own
            continue
        # a spelling variant on a paper that links through other names is still listed for that person
        if set(named_in(p, people, near=True)) - set(named_in(p, people)):
            possible.append(p)
        # same paper: the same people and the same printed date or period (type labels may differ)
        twin = next(
            (q for q in linked if sorted(named_in(q, people)) == sorted(named_in(p, people))
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
        same = len({normalise_address(a) for a in addresses}) == 1
        mismatches.append(("address (format only)" if same else "address", None, addresses))
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


NOT_PLANNED_LABEL = "not checked (photo limit)"


def coverage(start: str, end: str, month_counts: dict[str, int] | None, chosen: list[Checked], linked: list[Paper],
             common_law: bool = False, address_docs: list[Paper] | None = None, partners: list[str] | None = None,
             planned: list[str] | None = None) -> list[dict]:
    """month_counts is None for one person or when the photo search failed: gaps then use papers only.
    For any couple or family (partners given), separate papers, one naming each partner, showing the same address
    fill a month no single paper covers. For married and other couples photos still count; for common-law couples
    a month counts only by a paper showing both at the same address, and photos do not count."""
    if common_law:
        # alone, a paper counts only when it names both partners and shows an address
        linked = [p for p in linked if p.address and (not partners or len(named_in(p, partners)) == len(partners))]
        month_counts = None
    rows = []
    address_docs = address_docs or []
    numbers = {c.month: i + 1 for i, c in enumerate(chosen)}
    for month in month_range(start, end):
        papers = [p.kind for p in linked if paper_covers(p, month)]
        if partners and address_docs and not papers:
            # separate papers, one naming each partner, showing the same address that month
            by_partner = [{normalise_address(p.address) for p in address_docs
                           if p.address and paper_covers(p, month) and any(name_matches(n, who) for n in p.names)}
                          for who in partners]
            shared = set.intersection(*by_partner) if all(by_partner) else set()
            if shared:
                papers = ["same address on separate papers"]
        count = None if month_counts is None else month_counts.get(month, 0)
        rows.append({
            "month": month,
            "library": count,
            "pack": numbers.get(month) or (NOT_PLANNED_LABEL if planned is not None and count and month not in planned else None),
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


COMMON_LAW_GAP_LABEL = "no paper showing you both at the same address found"


def gap_label(papers_only: bool = False, search_failed: bool = False, who: str | None = None, common_law: bool = False) -> str:
    if common_law:
        return COMMON_LAW_GAP_LABEL
    if papers_only or search_failed:
        return PAPER_GAP_LABEL + ("; the photo search failed" if search_failed else "")
    return GAP_LABEL if who is None else GAP_LABEL.replace("of everyone", f"of {who}")


def gap_lines(rows: list[dict], label: str = GAP_LABEL) -> list[str]:
    return [f"{label}: {a} to {b}" if a != b else f"{label}: {a}" for a, b in group_gaps(rows)]


# Step 7

def apply_answers(linked: list[Paper], possible: list[Paper], confirmed: list[Paper], dropped: list[Paper],
                  people: list[str] | None = None, mismatches: list | None = None) -> list[Paper]:
    """Add the possible matches the user confirmed, remove dropped papers; Step 6 is then redone.

    When `people` and `mismatches` are given, each confirmed match adds its spelling difference to
    `mismatches` (the user linked it knowingly, and may need to explain it)."""
    added = [c for c in confirmed if c in possible]
    if people is not None and mismatches is not None:
        for c in added:
            for given in people:
                for printed in c.names:
                    if name_near(printed, given):
                        mismatches.append(("name spelling", given, sorted([printed, given])))
    new = [c for c in added if not any(c is q for q in linked)]  # a confirmed variant on an already-linked paper is not added twice
    return [p for p in linked + new if not any(p is d for d in dropped)]


def save_summary(approved: dict[str, bool], results: dict[str, str]) -> dict[str, list[str]]:
    """Step 8: each item has its own approval. Copies and the index need the folder; the album does not.
    A declined item is the user's choice, a failed one is a failure, and an item whose folder was not
    created is not applicable; all three are reported apart."""
    needs_folder = {"photo copies", "paper copies", "index", "descriptions"}
    folder_ok = approved.get("folder", False) and results.get("folder") == "completed"
    out = {"saved": [], "declined": [], "failed": [], "not applicable": []}
    for item, ok in approved.items():
        if not ok:
            out["declined"].append(item)
        elif item in needs_folder and not folder_ok:
            out["not applicable"].append(item)
        elif results.get(item) == "completed":
            out["saved"].append(item)
        else:
            out["failed"].append(item)
    return out


def closers(rows: list[dict], linked: list[Paper], address_docs: list[Paper] | None = None,
            partners: list[str] | None = None, labels: dict[str, str] | None = None) -> dict[tuple[str, str], str]:
    """Step 6: for each gap, from linking papers only: a series of at least 3 papers of the same type naming
    the same people, one each month up to the month before the gap; and a covering paper that starts the
    month after it. Suggests only; never claims the paper exists.

    same-address.md: with partners and single-name address_docs, a series of same-address pairs (one type per
    partner, the same address each month) names both types; when only one partner's papers form a series,
    the line names the missing half. `labels` gives the short name shown for each partner (default: as given)."""
    out = {}
    months = [r["month"] for r in rows]
    series: dict[tuple[str, tuple[str, ...]], set[str]] = {}
    for p in linked:
        if p.dated:
            series.setdefault((p.kind, tuple(sorted(p.names))), set()).add(p.dated[:7])

    def prev(m: str) -> str:
        y, mo = map(int, m.split("-"))
        return f"{y - 1:04d}-12" if mo == 1 else f"{y:04d}-{mo - 1:02d}"

    for a, b in group_gaps(rows):
        ia, ib = months.index(a), months.index(b)
        before = prev(a)
        after = months[ib + 1] if ib + 1 < len(months) else None
        lines = []
        for (kind, _), ms in sorted(series.items()):
            run, m = 0, before
            while m in ms:
                run, m = run + 1, prev(m)
            if run >= 3:
                lines.append(f"{kind}s came every month until {before}; {kind}s for {a} to {b} would add evidence for these months, if you have them")
        if partners and len(partners) == 2 and address_docs:
            lines.extend(_address_series(address_docs, partners, labels or {}, before, a, b, prev))
        for p in linked:
            if p.start and after and p.start == after:
                lines.append(f"the {p.kind} starts in {after}")
        out[(a, b)] = "; ".join(lines) if lines else "no regular paper found near these months"
    return out


def _address_series(address_docs: list[Paper], partners: list[str], labels: dict[str, str], before: str,
                    a: str, b: str, prev) -> list[str]:
    """same-address.md, what could cover each gap: runs of single-name papers ending the month before the gap."""
    # per partner and type: month -> normalised addresses on that partner's papers of that type
    by: dict[tuple[str, str], dict[str, set[str]]] = {}
    for p in address_docs:
        if not (p.dated and p.address):
            continue
        who = [g for g in partners if any(name_matches(n, g) for n in p.names)]
        if len(who) == 1:
            by.setdefault((who[0], p.kind), {}).setdefault(p.dated[:7], set()).add(normalise_address(p.address))

    def run(months: dict[str, set[str]], other: dict[str, set[str]] | None = None) -> int:
        n, m = 0, before
        while m in months and (other is None or (m in other and months[m] & other[m])):
            n, m = n + 1, prev(m)
        return n

    first, second = partners
    name = {g: labels.get(g, g) for g in partners}
    lines, paired = [], set()
    for (pa, ka), ma in sorted(by.items()):
        if pa != first:
            continue
        for (pb, kb), mb in sorted(by.items()):
            if pb == second and run(ma, mb) >= 3:
                both = f"{ka}s ({name[first]}) and {kb}s ({name[second]})"
                lines.append(f"{both} came every month until {before}; {both} for {a} to {b} would add evidence for these months, if you have them")
                paired |= {(pa, ka), (pb, kb)}
    for (who, kind), months in sorted(by.items(), key=lambda kv: (partners.index(kv[0][0]), kv[0][1])):
        if (who, kind) not in paired and run(months) >= 3:
            other = second if who == first else first
            lines.append(f"{kind}s in {name[who]}'s name came every month until {before}; a paper in {name[other]}'s name "
                         f"at the same address for {a} to {b} would add evidence, if you have one")
    return lines


def carry_over(earlier_lines: dict[tuple[str, str], tuple[str, str]], chosen: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
    """Step 7: reuse only (confirmed) or (edited) context lines from an earlier index, only for photos chosen
    again, matched on (capture date, original file name). A reused line is still shown as [confirm]."""
    return {key: f"{line} (from your earlier pack) [confirm]"
            for key, (line, status) in earlier_lines.items()
            if key in chosen and status in ("confirmed", "edited")}
