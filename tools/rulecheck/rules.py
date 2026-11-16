"""Reference implementation of the Skill's deterministic parent steps.

The Skill itself is Markdown that Uliya's assistant follows on the NAS. This module
restates the rules it gives for the steps that need no NAS call (planning months,
choosing photos, joining documents, coverage and gaps) so they can be checked on
synthetic cases. It does not call the NAS and does not prove runtime behaviour.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

GAP_LABEL = "no photo of everyone found by face grouping and no linking document"
PAPER_GAP_LABEL = "no linking document found"
FORBIDDEN_GAP_WORDS = ("no relationship", "not together", "not in the country", "apart")

RULES = {
    1: "the people the photo is about clearly visible in the foreground",
    2: "their faces visible and not covered",
    3: "a real photo, not a screenshot or a photo of a screen or document (a photographed print of a photo passes)",
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
    """Over six people, only the ones the user picked are searched in photos; the rest are documents-only."""
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


# Step 2

UNRESOLVED = "unresolved"
NOT_RETURNED = UNRESOLVED  # the state of a month neither Step 2 call answered for


class AtLeast(int):
    """A month the timeline did not list but the sample call found photos for: its count is only a floor."""

    def __str__(self) -> str:
        return f"at least {int(self)} (sample search)"


NO_RESULTS = "no results"


def timeline_reply(reply: dict[str, int] | str, start: str, end: str) -> dict[str, int]:
    """The timeline call's month counts. A "no results" reply lists every month in the period as 0, so no
    month is left for the sample call."""
    if reply == NO_RESULTS:
        return {m: 0 for m in month_range(start, end)}
    return dict(reply)


def month_states(timeline: dict[str, int], start: str, end: str, sample_listed: dict[str, int] | None = None) -> dict:
    """{MONTH_STATES}: each month in the period ends Step 2 in exactly one state.
    The timeline's count N when the timeline listed it (a counted month the sample call lists as none, leaves
    out or fails for keeps its count and has no candidates); "at least N (sample search)" when only the sample
    call listed it with N photos; 0 when the timeline listed 0 or only the sample call listed it, as none;
    "unresolved" when the timeline did not list it and the sample call left it out or failed (sample_listed
    holds only what a completed sample call listed: {} when it failed)."""
    sample_listed = sample_listed or {}
    out = {}
    for m in month_range(start, end):
        if m in timeline:
            out[m] = timeline[m]
        elif m in sample_listed:
            n = sample_listed[m]
            out[m] = AtLeast(n) if n > 0 else 0
        else:
            out[m] = UNRESOLVED
    return out


fill_returned = month_states  # older name


def months_to_sample(timeline: dict[str, int], timeline_sample_months: set[str], start: str, end: str) -> list[str]:
    """{MONTHS_TO_SAMPLE}: the sample call is sent, per month, for each month the timeline counted photos for
    but returned no sample photo, and for each month the timeline did not list."""
    return [m for m in month_range(start, end)
            if m not in timeline or (timeline[m] > 0 and m not in timeline_sample_months)]


def merge_candidates(timeline_samples: list, sample_result: list | None, months_asked: set[str] | None = None,
                     timeline: dict[str, int] | None = None) -> list:
    """{CANDIDATES}: the sample call's photos are added per month after the timeline's samples, never replacing
    them; a failed sample call (None) adds nothing. When months_asked ({MONTHS_TO_SAMPLE}) is given, only the
    sample call's photos for those months are added; when timeline is given, samples for a month it lists as 0
    are ignored."""
    zero = {m for m, n in (timeline or {}).items() if n == 0}
    out = [c for c in timeline_samples or [] if c.month not in zero]
    seen = {c.path for c in out}
    for c in sample_result or []:
        if months_asked is not None and c.month not in months_asked:
            continue
        if c.month in zero:
            continue
        if c.path not in seen:
            out.append(c)
            seen.add(c.path)
    return out


def months_not_returned(timeline: dict[str, int], start: str, end: str) -> list[str]:
    return [m for m in month_range(start, end) if m not in timeline]


def unresolved_months(states: dict) -> list[str]:
    """{MONTHS_NOT_RETURNED} after Step 2: exactly the unresolved months."""
    return [m for m, s in states.items() if s == UNRESOLVED]


# Step 3

def plan_months(month_counts: dict[str, int], limit: int, candidate_months: set[str] | None = None) -> list[str]:
    """Spread up to `limit` months across the period; never plan a zero or unresolved month, and, when
    candidate_months is given, never a month without at least one candidate."""
    month_counts = {m: n for m, n in month_counts.items() if isinstance(n, int)}
    with_photos = sorted(m for m, n in month_counts.items()
                         if n > 0 and (candidate_months is None or m in candidate_months))
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
    kind: str = "photo"  # what the vision check says it is: photo, print, screenshot, ...
    people: list[str] | None = None  # the named people face grouping found in the photo; None if not returned


def people_check(checked: list[Checked], photo_people: list[str]) -> list[Checked]:
    """Step 4: a photo whose named people from face grouping do not include everyone in {PHOTO_PEOPLE}
    is dropped as failing rule 1."""
    out = []
    for c in checked:
        if c.failed_rule is None and c.people is not None and not set(photo_people) <= set(c.people):
            c = Checked(c.path, c.month, c.date, 1, c.kind, c.people)
        out.append(c)
    return out


@dataclass
class Choice:
    chosen: list[Checked] = field(default_factory=list)
    none_fit: list[str] = field(default_factory=list)
    check_failed: list[str] = field(default_factory=list)  # planned months whose Step 4 call failed
    failures: dict[int, int] = field(default_factory=lambda: {r: 0 for r in RULES})


RULE3_FAILS = {"screenshot", "photo of a screen", "photo of a document"}


def rule3(kind: str) -> tuple[bool, str | None]:
    """Step 4 rule 3: what the vision check says the image is -> (passes, label for the photo line).
    A photographed print of a photo passes and is labelled "print"; a screenshot, a photo of a screen
    or a photo of a document fails."""
    if kind in RULE3_FAILS:
        return False, None
    return True, ("print" if kind == "print" else None)


PHOTO_CHECK_FAILED = "photo check failed"


def choose_photos(checked: list[Checked], plan: list[str], limit: int, failed_months: list[str] | None = None) -> Choice:
    """First passing photo per planned month, one per month, never padded. A planned month whose
    Step 4 call failed (after the one-month retry) is "photo check failed", not "none fit to send"."""
    result = Choice()
    failed_months = set(failed_months or [])
    checked = [c for c in checked if c.month not in failed_months]
    for c in checked:
        if c.failed_rule is not None:
            result.failures[c.failed_rule] += 1
    for month in plan:
        if month in failed_months:
            result.check_failed.append(month)
            continue
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
    dated: str | None = None  # YYYY-MM-DD for one-off documents
    address: str | None = None
    dob: dict[str, str] = field(default_factory=dict)
    readable: bool = True
    asks: str | None = None  # an instruction found inside the document
    path: str | None = None  # the file path, when known
    added: bool = False  # Step 6a: put in the Add here folder by the user; kept with the document on every redo


PHOTO_SOURCE = "from a photo of a document"


def _fold(name: str) -> str:
    """Drop accents so "Trần Thị Linh" and "Tran Thi Linh" compare equal (đ has no decomposition)."""
    decomposed = unicodedata.normalize("NFD", name.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _words(name: str) -> list[str]:
    return sorted(re.sub(r"[,.]", " ", _fold(name)).lower().split())


def name_matches(printed: str, given: str) -> bool:
    """Same words, ignoring case, commas, accents and word order."""
    return _words(printed) == _words(given)


def _edits(x: str, y: str) -> int:
    """Levenshtein distance."""
    prev = list(range(len(y) + 1))
    for i, cx in enumerate(x, 1):
        cur = [i]
        for j, cy in enumerate(y, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (cx != cy)))
        prev = cur
    return prev[-1]


def name_near(printed: str, given: str, family_names: list[str] | None = None) -> bool:
    """Same number of words and exactly one word spelled slightly differently ("Bau" for "Bao", "Lin" for "Linh");
    every other word, the family name included, is identical. A different name with the same family name
    ("Rizal Hakim" vs "Kirana Hakim") is not a spelling variant. When family_names is given, the word that differs
    must not be a family name: "Tren Thi Linh" for "Tran Thi Linh" is a different family, not a variant."""
    a, b = _words(printed), _words(given)
    if not (len(a) == len(b) >= 2 and len(set(a) ^ set(b)) == 2):
        return False
    x, = set(a) - set(b)
    y, = set(b) - set(a)
    if family_names:
        families = {w for f in family_names for w in _words(f)}
        if x in families or y in families:
            return False
    return _edits(x, y) <= max(1, min(len(x), len(y)) // 3)


def name_contains(printed: str, photos_name: str) -> bool:
    """Without printed names: the printed name holds every word of the Photos name. Possible match only."""
    return set(_words(photos_name)) <= set(_words(printed))


def _enough(named: int, people: list[str]) -> bool:
    if len(people) <= 2:
        return named == len(people)
    return named >= 2


def named_in(paper: Paper, people: list[str], near: bool = False, family_names: list[str] | None = None) -> list[str]:
    return [g for g in people
            if any(name_matches(n, g) or (near and name_near(n, g, family_names)) for n in paper.names)]


def links(paper: Paper, people: list[str]) -> bool:
    return _enough(len(named_in(paper, people)), people)


ABBREVIATIONS = {"street": "st", "road": "rd", "avenue": "ave", "apartment": "unit", "apt": "unit", "suite": "unit"}


def normalise_address(address: str) -> str:
    """Abbreviation and punctuation differences only: "12 Elm Street #4" and "12 Elm St Unit 4" are the same."""
    s = address.lower().replace("#", " unit ")
    s = re.sub(r"[.,]", " ", s)
    return " ".join(ABBREVIATIONS.get(w, w) for w in s.split())


def join_papers(papers: list[Paper], people: list[str], printed_names: bool = True,
                family_names: list[str] | None = None) -> dict:
    """Keep linking documents; prefer a scan over a photo of the same document; note, never fix, mismatches.
    Only a scan and photos of it, or several photos, are merged as one document: two scans always stay separate."""
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
                possible.append(p)  # Photos names can never link a document on their own
            continue
        if not links(p, people):
            if _enough(len(named_in(p, people, near=True, family_names=family_names)), people):
                possible.append(p)  # shown to the user, never linked on its own
            continue
        # a spelling variant on a document that links through other names is still listed for that person
        if set(named_in(p, people, near=True, family_names=family_names)) - set(named_in(p, people)):
            possible.append(p)
        # same document: the same people and the same printed date or period (type labels may differ),
        # and at least one of the two is a photo of a document (two different scans are never merged)
        twin = next(
            (q for q in linked if PHOTO_SOURCE in (q.source, p.source)
             and sorted(named_in(q, people)) == sorted(named_in(p, people))
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
NO_SAMPLE_LABEL = "no sample returned"
SAMPLE_FAILED_LABEL = "sample search failed"


def coverage(start: str, end: str, month_counts: dict[str, int] | None, chosen: list[Checked], linked: list[Paper],
             common_law: bool = False, address_docs: list[Paper] | None = None, partners: list[str] | None = None,
             planned: list[str] | None = None, candidate_months: set[str] | None = None,
             no_sample_label: str = NO_SAMPLE_LABEL) -> list[dict]:
    """month_counts is None for one person or when the photo search failed: gaps then use documents only.
    For any couple or family (partners given), separate documents, one naming each partner, showing the same address
    fill a month no single document covers. For married and other couples photos still count; for common-law couples
    a month counts only by a document showing both at the same address, and photos do not count."""
    if common_law:
        # alone, a document counts only when it names both partners and shows an address
        linked = [p for p in linked if p.address and (not partners or len(named_in(p, partners)) == len(partners))]
        month_counts = None
    rows = []
    address_docs = address_docs or []
    numbers = {c.month: i + 1 for i, c in enumerate(chosen)}
    own_linked = [p for p in linked if not p.added]
    own_address = [p for p in address_docs if not p.added]
    any_added = len(own_linked) < len(linked) or len(own_address) < len(address_docs)

    def month_papers(month: str, linked_docs: list[Paper], address_list: list[Paper]) -> list[str]:
        papers = [p.kind for p in linked_docs if paper_covers(p, month)]
        if partners and address_list and not papers:
            # separate documents, one naming each partner, showing the same address that month
            by_partner = [{normalise_address(p.address) for p in address_list
                           if p.address and paper_covers(p, month) and any(name_matches(n, who) for n in p.names)}
                          for who in partners]
            shared = set.intersection(*by_partner) if all(by_partner) else set()
            if shared:
                papers = ["same address on separate documents"]
        return papers

    for month in month_range(start, end):
        papers = month_papers(month, own_linked, own_address)
        added = False
        if not papers and any_added:  # Step 6a: an added document counts only in a month no other document covers
            papers = month_papers(month, linked, address_docs)
            added = bool(papers)
        count = None if month_counts is None else month_counts.get(month, 0)
        if count == NOT_RETURNED:  # never 0 and never a gap
            rows.append({"month": month, "library": NOT_RETURNED, "pack": numbers.get(month), "papers": papers, "gap": False,
                         "added": added})
            continue
        if numbers.get(month):
            pack = numbers[month]
        elif candidate_months is not None and count and month not in candidate_months:
            pack = no_sample_label  # photos counted, but no sample to check
        elif planned is not None and count and month not in planned:
            pack = NOT_PLANNED_LABEL
        else:
            pack = None
        rows.append({
            "month": month,
            "library": count,
            "pack": pack,
            "papers": papers,
            "gap": (count in (None, 0)) and not papers,
            "added": added,
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


COMMON_LAW_GAP_LABEL = "no document showing you both at the same address found"


def gap_label(papers_only: bool = False, search_failed: bool = False, who: str | None = None, common_law: bool = False) -> str:
    if common_law:
        return COMMON_LAW_GAP_LABEL
    if papers_only or search_failed:
        return PAPER_GAP_LABEL + ("; the photo search failed" if search_failed else "")
    return GAP_LABEL if who is None else GAP_LABEL.replace("of everyone", f"of {who}")


def gap_lines(rows: list[dict], label: str = GAP_LABEL) -> list[str]:
    return [f"{label}: {a} to {b}" if a != b else f"{label}: {a}" for a, b in group_gaps(rows)]


UNRESOLVED_LABEL = "photos not returned and no linking document"


def unresolved_line(rows: list[dict]) -> str | None:
    """Step 6: unresolved months with no linking document and no same-address pair are never gaps; they are listed
    under the gap list (consecutive months grouped as for gaps), in the check-by-hand line and in the summary."""
    flagged = [{"month": r["month"], "gap": r["library"] == UNRESOLVED and not r["papers"]} for r in rows]
    runs = group_gaps(flagged)
    if not runs:
        return None
    return f"{UNRESOLVED_LABEL}: " + ", ".join(f"{a} to {b}" if a != b else a for a, b in runs) + "; check by hand"


# Step 7

def apply_answers(linked: list[Paper], possible: list[Paper], confirmed: list[Paper], dropped: list[Paper],
                  people: list[str] | None = None, mismatches: list | None = None) -> list[Paper]:
    """Add the possible matches the user confirmed, remove dropped documents; Step 6 is then redone.

    When `people` and `mismatches` are given, each confirmed match adds its spelling difference to
    `mismatches` (the user linked it knowingly, and may need to explain it)."""
    added = [c for c in confirmed if c in possible]
    if people is not None and mismatches is not None:
        for c in added:
            for given in people:
                for printed in c.names:
                    if name_near(printed, given):
                        mismatches.append(("name spelling", given, sorted([printed, given])))
    new = [c for c in added if not any(c is q for q in linked)]  # a confirmed variant on an already-linked document is not added twice
    return [p for p in linked + new if not any(p is d for d in dropped)]


def save_summary(approved: dict[str, bool], results: dict[str, str]) -> dict[str, list[str]]:
    """Step 8: each item has its own approval. Copies and the index need the folder; the album does not.
    A declined item is the user's choice, a failed one is a failure, and an item whose folder was not
    created is not applicable; all three are reported apart."""
    needs_folder = {"photo copies", "document copies", "index", "descriptions"}
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
    """Step 6: for each gap, from linking documents only: a series of at least 3 documents of the same type naming
    the same people, one each month up to the month before the gap; and a covering document that starts the
    month after it. Suggests only; never claims the document exists.

    same-address.md: with partners and single-name address_docs, a series of same-address pairs (one type per
    partner, the same address each month) names both types; when only one partner's documents form a series,
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
        span = a if a == b else f"{a} to {b}"  # a one-month gap is written as that month alone
        ia, ib = months.index(a), months.index(b)
        before = prev(a)
        after = months[ib + 1] if ib + 1 < len(months) else None
        lines = []
        for (kind, _), ms in sorted(series.items()):
            run, m = 0, before
            while m in ms:
                run, m = run + 1, prev(m)
            if run >= 3:
                lines.append(f"{kind}s came every month until {before}; {kind}s for {span} would add evidence for these months, if you have them")
        if partners and len(partners) == 2 and address_docs:
            lines.extend(_address_series(address_docs, partners, labels or {}, before, a, b, prev))
        for p in linked:
            if p.start and after and p.start == after:
                # only a document that is new after the gap, not a regular one of the same kind resuming
                seen_before = any(q is not p and q.kind == p.kind and sorted(q.names) == sorted(p.names)
                                  and ((q.dated and q.dated[:7] < a) or (q.end and q.end < a)) for q in linked)
                if not seen_before:
                    lines.append(f"the {p.kind} starts in {after}")
        out[(a, b)] = "; ".join(lines) if lines else "no regular document found near these months"
    return out


def _address_series(address_docs: list[Paper], partners: list[str], labels: dict[str, str], before: str,
                    a: str, b: str, prev) -> list[str]:
    """same-address.md, what could cover each gap: runs of single-name documents ending the month before the gap."""
    # per partner and type: month -> normalised addresses on that partner's documents of that type
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
    span = a if a == b else f"{a} to {b}"
    name = {g: labels.get(g, g) for g in partners}
    lines, paired = [], set()
    for (pa, ka), ma in sorted(by.items()):
        if pa != first:
            continue
        for (pb, kb), mb in sorted(by.items()):
            if pb == second and run(ma, mb) >= 3:
                both = f"{ka}s ({name[first]}) and {kb}s ({name[second]})"
                lines.append(f"{both} came every month until {before}; {both} for {span} would add evidence for these months, if you have them")
                paired |= {(pa, ka), (pb, kb)}
    for (who, kind), months in sorted(by.items(), key=lambda kv: (partners.index(kv[0][0]), kv[0][1])):
        if (who, kind) not in paired and run(months) >= 3:
            other = second if who == first else first
            lines.append(f"{kind}s in {name[who]}'s name came every month until {before}; a document in {name[other]}'s name "
                         f"at the same address for {span} would add evidence, if you have one")
    return lines


def carry_over(earlier_lines: dict[tuple[str, str], tuple[str, str]], chosen: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
    """Step 7: reuse only (confirmed) or (edited) context lines from an earlier index, only for photos chosen
    again, matched on (capture date, original file name). A reused line is still shown as [confirm]."""
    return {key: f"{line} (from your earlier pack) [confirm]"
            for key, (line, status) in earlier_lines.items()
            if key in chosen and status in ("confirmed", "edited")}


# Step 6a: documents the user adds for the gap months (optional, once)

ADDED_LABEL = "you added"
STILL_OPEN = "Still open: check by hand."
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".heic")
ADDED_READ_MAX = 60


def offer_added_papers(rows: list[dict]) -> bool:
    """Step 6a is offered only when the gap list is not empty (the caller asks it once in a run)."""
    return any(r["gap"] for r in rows)


def split_added(listed: list[Paper], read_paths: set[str]) -> tuple[list[Paper], list[Paper], int]:
    """Step 6a: the listing is cut off at 60 files (the third value is how many were left out); a path in a
    Visa evidence folder or already read in Step 5 is left out; image files go to text recognition (as in 5b),
    the rest to document extraction (as in 5a)."""
    kept = [p for p in listed[:ADDED_READ_MAX]
            if p.path not in read_paths and not any(part.startswith("Visa evidence") for part in (p.path or "").split("/"))]
    images = [p for p in kept if (p.path or "").lower().endswith(IMAGE_TYPES)]
    return [p for p in kept if p not in images], images, max(0, len(listed) - ADDED_READ_MAX)


def paper_cell(row: dict) -> str:
    """The coverage table's document column: a month only an added document covers reads "covered by <type> you added"."""
    if not row["papers"]:
        return "—"
    kinds = " and ".join(dict.fromkeys(row["papers"]))
    return f"covered by {kinds} {ADDED_LABEL}" if row.get("added") else kinds


def still_open_lines(rows: list[dict], label: str = GAP_LABEL) -> list[str]:
    """After Step 6a, on any redo of Step 6, each gap line ends with "Still open: check by hand."."""
    return [f"{line}. {STILL_OPEN}" for line in gap_lines(rows, label)]
