"""End-to-end simulation of the Skill's Steps 0 to 9 against a mock NAS.

The mock agents return canned results for four synthetic scenarios. The orchestration below restates
SKILL.md's control flow (which step runs, what it may send, what is skipped, what is reported) so the
safety properties can be checked as code: nothing is written before its approval, a declined item is
reported as declined, a failed photo search switches to papers-only gaps, and a repeat run gets a new
folder name. It does not show how Uliya or the expert agents behave on a real NAS.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rulecheck"))
import rules as R  # noqa: E402


@dataclass
class MockNAS:
    named_people: list[str]
    month_counts: dict[str, int] | None  # None means the timeline call fails
    samples: list[R.Checked]
    papers: list[R.Paper]
    existing: list[str] = field(default_factory=list)
    write_results: dict[str, str] = field(default_factory=dict)  # item -> completed / failed
    earlier_index: dict | None = None  # (date, file name) -> (line, status); None = no earlier pack
    earlier_read: str = "completed"  # completed / failed / cancelled
    list_read: str = "completed"  # the Step 7 folder listing; failed means the user continues with the base name
    calls: list[tuple[str, str]] = field(default_factory=list)  # (agent, action) in order
    written: list[str] = field(default_factory=list)

    def call(self, agent: str, action: str, write: bool = False, item: str | None = None) -> str:
        self.calls.append((agent, action))
        if write:
            status = self.write_results.get(item or action, "completed")
            if status == "completed":
                self.written.append(item or action)
            return status
        return "completed"


@dataclass
class User:
    consent: str = "yes"  # yes / no / unsure
    local_model: str = "yes"  # yes / no / unsure
    continue_if_unsure: bool = True
    papers_only: list[str] = field(default_factory=list)
    confirm_matches: bool = True
    approve: dict[str, bool] = field(default_factory=lambda: {"folder": True, "album": True, "index": True, "descriptions": True})
    reuse_lines: bool = True
    photos_needed: bool = True
    relationship: str = "married"  # married / common-law / other
    four_yes: bool = False  # answered yes to all four spouse-checklist questions
    continue_if_not_needed: bool = True
    drop_papers: list = field(default_factory=list)  # papers the user drops in Step 7
    children: list = field(default_factory=list)  # Photos names of children, if given
    accept_adults: bool = True  # agrees to count the adults' photos when offered
    unanswered_photos: list = field(default_factory=list)  # paths of listed photos the user does not answer about


def run(people: list[str], printed: list[str], start: str, end: str, nas: MockNAS, user: User,
        limit: int = 20) -> dict:
    log: dict = {"stopped": None, "approvals_asked": [], "summary": {}}

    # Step 0
    if user.consent != "yes" or user.local_model == "no":
        log["stopped"] = "step 0"
        return log
    if user.local_model == "unsure" and not user.continue_if_unsure:
        log["stopped"] = "step 0"
        return log

    scope = R.scope_of(people)
    if scope != "one person" and user.relationship == "married" and user.four_yes:
        log["notice"] = "no additional proof of relationship is needed at this time; an officer can still ask later"
        if not user.continue_if_not_needed:
            log["stopped"] = "step 0: no additional proof needed; user chose to stop"
            return log
        user.photos_needed = False
    photo_people = [p for p in people if p not in user.papers_only]

    # Step 1 (skipped for one person)
    if scope != "one person" and user.photos_needed:
        check = [p for p in people if p not in user.papers_only]
        nas.call("photo-agent", "figure-albums")
        missing = R.confirm_people(nas.named_people, check)["missing"]
        if missing:
            log["stopped"] = "step 1: waiting for " + ", ".join(missing)
            return log

    # Steps 2 to 4
    month_counts, chosen, timeline_failed = None, [], False
    if scope != "one person" and user.photos_needed and len(photo_people) >= 2:
        nas.call("photo-agent", "timeline-summary")
        if nas.month_counts is None:
            timeline_failed = True
        else:
            month_counts = nas.month_counts
            # Step 2 offer: count the adults only, never the same people again, never fewer than two
            adults = [p for p in photo_people if p not in user.children]
            log["adults_offered"] = 0
            if (scope == "a family" and any(n == 0 for n in month_counts.values())
                    and len(adults) >= 2 and adults != photo_people):
                log["adults_offered"] += 1
                if user.accept_adults:
                    photo_people = adults
                    nas.call("photo-agent", "timeline-summary")
            plan = R.plan_months(month_counts, limit)
            nas.call("photo-agent", "vision-vlm")
            chosen = R.choose_photos(nas.samples, plan, limit).chosen

    # Step 5
    nas.call("document-agent", "extract")
    nas.call("photo-agent", "search-picture")
    joined = R.join_papers(nas.papers, printed)
    linked = joined["linked"]
    mismatches = list(joined["mismatches"])
    if user.confirm_matches:
        linked = R.apply_answers(linked, joined["possible_matches"], joined["possible_matches"], [],
                                 people=printed, mismatches=mismatches)

    # Step 7 answers folded in: listed photos left unanswered are removed before Step 6 is redone
    waiting = [c.path for c in chosen if c.path in user.unanswered_photos]
    chosen = [c for c in chosen if c.path not in user.unanswered_photos]

    # Step 6 (redone after Step 7's answers, here folded in)
    photo_steps_skipped = scope == "one person" or not user.photos_needed or len(photo_people) < 2
    papers_only = photo_steps_skipped or timeline_failed
    common_law = user.relationship == "common-law"
    partners = printed[:2]
    # exactly one partner named (a child named too does not matter); joint papers are never here
    address_docs = [p for p in nas.papers if common_law and p.address and len(R.named_in(p, partners)) == 1
                    and not any(p is d for d in user.drop_papers)]
    linked = [p for p in linked if not any(p is d for d in user.drop_papers)]
    rows = R.coverage(start, end, None if papers_only else month_counts, chosen, linked, common_law=common_law,
                      address_docs=address_docs, partners=partners)
    same_address_docs = [p for p in address_docs
                         if any(r["papers"] == ["same address on separate papers"] and R.paper_covers(p, r["month"]) for r in rows)]
    if common_law:
        papers_only = True
    gaps = R.gap_lines(rows, R.gap_label(papers_only=photo_steps_skipped, search_failed=timeline_failed, common_law=common_law))

    # Step 7: read the save location, pick a free name
    nas.call("file-agent", "ls")
    nas.call("photo-agent", "albums")
    base = "Visa evidence " + " and ".join(people)
    name = base
    if nas.list_read == "completed" and name in nas.existing:
        name = f"{base} 2026-11-14"
        n = 2
        while name in nas.existing:
            name, n = f"{base} 2026-11-14 {n}", n + 1

    reused, reuse_note = {}, None
    if nas.earlier_index is not None and user.reuse_lines:
        nas.call("file-agent", "cat")  # read the earlier pack's index (Step 7)
        if nas.earlier_read == "completed":
            reused = R.carry_over(nas.earlier_index, [(c.date, c.path) for c in chosen])
        else:
            reuse_note = f"earlier index read {nas.earlier_read}; continued without it"

    writes_before_approval = [c for c in nas.calls if c[1] in ("mkdir", "cpmv", "create-album", "save-text")]

    # Step 8: approval per item, then independent writes
    log["approvals_asked"] = [k for k in ("folder", "album", "index", "descriptions")]
    approved = {k: user.approve.get(k, False) for k in ("folder", "album", "index", "descriptions")}
    if not chosen:
        approved.pop("album")
        approved.pop("descriptions")
    results = {}
    if approved.get("folder"):
        if name in nas.existing:  # 8a never writes into an existing folder: it reports failed
            nas.write_results["folder"] = "failed"
        results["folder"] = nas.call("file-agent", "mkdir", write=True, item="folder")
    folder_ok = results.get("folder") == "completed"
    if approved.get("folder") and chosen and folder_ok:
        results["photo copies"] = nas.call("file-agent", "cpmv", write=True, item="photo copies")
    if approved.get("folder") and (linked or same_address_docs) and folder_ok:
        results["paper copies"] = nas.call("file-agent", "cpmv", write=True, item="paper copies")
    if approved.get("album"):
        results["album"] = nas.call("photo-agent", "create-album", write=True, item="album")
    if approved.get("index") and folder_ok:
        results["index"] = nas.call("knowledge-agent", "save-text", write=True, item="index")
    if approved.get("descriptions") and folder_ok:  # independent of the index save
        results["descriptions"] = nas.call("knowledge-agent", "save-text", write=True, item="descriptions")
    items = dict(approved)
    if approved.get("folder"):
        if chosen:
            items["photo copies"] = True
        if linked or same_address_docs:
            items["paper copies"] = True
    summary = R.save_summary(items, results)

    # Step 9: read back only what can exist
    if folder_ok:
        nas.call("file-agent", "ls")
    if results.get("album") == "completed":
        nas.call("photo-agent", "album-detail")

    log.update(scope=scope, chosen=len(chosen), linked=len(linked), mismatches=mismatches, gaps=gaps,
               folder_name=name, summary=summary, writes_before_approval=writes_before_approval,
               written=list(nas.written), reused=reused, reuse_note=reuse_note,
               same_address_docs=len(same_address_docs), waiting_for_answer=waiting)
    return log
