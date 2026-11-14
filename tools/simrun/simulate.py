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
    approve: dict[str, bool] = field(default_factory=lambda: {"folder": True, "album": True, "index": True})
    reuse_lines: bool = True


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
    photo_people = [p for p in people if p not in user.papers_only]

    # Step 1 (skipped for one person)
    if scope != "one person":
        check = [p for p in people if p not in user.papers_only]
        nas.call("photo-agent", "figure-albums")
        missing = R.confirm_people(nas.named_people, check)["missing"]
        if missing:
            log["stopped"] = "step 1: waiting for " + ", ".join(missing)
            return log

    # Steps 2 to 4
    month_counts, chosen, timeline_failed = None, [], False
    if scope != "one person" and len(photo_people) >= 2:
        nas.call("photo-agent", "timeline-summary")
        if nas.month_counts is None:
            timeline_failed = True
        else:
            month_counts = nas.month_counts
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

    # Step 6 (redone after Step 7's answers, here folded in)
    photo_steps_skipped = scope == "one person" or len(photo_people) < 2
    papers_only = photo_steps_skipped or timeline_failed
    rows = R.coverage(start, end, None if papers_only else month_counts, chosen, linked)
    gaps = R.gap_lines(rows, R.gap_label(papers_only=photo_steps_skipped, search_failed=timeline_failed))

    # Step 7: read the save location, pick a free name
    nas.call("file-agent", "ls")
    nas.call("photo-agent", "albums")
    base = "Visa evidence " + " and ".join(people)
    name = base
    if name in nas.existing:
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
    log["approvals_asked"] = ["folder", "album", "index"]
    approved = {k: user.approve.get(k, False) for k in ("folder", "album", "index")}
    if not chosen:
        approved.pop("album")
    results = {}
    if approved.get("folder"):
        results["folder"] = nas.call("file-agent", "mkdir", write=True, item="folder")
    folder_ok = results.get("folder") == "completed"
    if approved.get("folder") and chosen and folder_ok:
        results["photo copies"] = nas.call("file-agent", "cpmv", write=True, item="photo copies")
    if approved.get("folder") and linked and folder_ok:
        results["paper copies"] = nas.call("file-agent", "cpmv", write=True, item="paper copies")
    if approved.get("album"):
        results["album"] = nas.call("photo-agent", "create-album", write=True, item="album")
    if approved.get("index") and folder_ok:
        results["index"] = nas.call("knowledge-agent", "save-text", write=True, item="index")
    items = dict(approved)
    if approved.get("folder"):
        if chosen:
            items["photo copies"] = True
        if linked:
            items["paper copies"] = True
    summary = R.save_summary(items, results)

    # Step 9: read back only what can exist
    if folder_ok:
        nas.call("file-agent", "ls")
    if results.get("album") == "completed":
        nas.call("photo-agent", "album-detail")

    log.update(scope=scope, chosen=len(chosen), linked=len(linked), mismatches=mismatches, gaps=gaps,
               folder_name=name, summary=summary, writes_before_approval=writes_before_approval,
               written=list(nas.written), reused=reused, reuse_note=reuse_note)
    return log
