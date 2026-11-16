"""End-to-end simulation of the Skill's Steps 0 to 9 against a mock NAS.

The mock agents return canned results for four synthetic scenarios. The orchestration below restates
SKILL.md's control flow (which step runs, what it may send, what is skipped, what is reported) so the
safety properties can be checked as code: nothing is written before its approval, a declined item is
reported as declined, a failed photo search switches to papers-only gaps, and a repeat run gets a new
folder name. It does not show how Uliya or the expert agents behave on a real NAS.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
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
    timeline_missing: list = field(default_factory=list)  # months the timeline reply leaves out
    sample_counts: dict = field(default_factory=dict)  # months the Step 2 sample call lists: photos found, 0 = listed as none
    sample_omit: list = field(default_factory=list)  # counted months the Step 2 sample call leaves out of its reply
    sample_fail: bool = False  # the Step 2 sample call fails
    timeline_samples: bool = True  # the timeline reply came back with sample photos
    timeline_no_results: bool = False  # the timeline reply is "no results" for the whole period
    vision_batch_fail: set = field(default_factory=set)  # planned months whose batched Step 4 call fails
    vision_retry_fail: set = field(default_factory=set)  # of those, months whose one-month retry also fails
    added_papers: list = field(default_factory=list)  # files the user put in the Add here folder (Step 6a), with paths
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
    print_dates: dict = field(default_factory=dict)  # path -> real date the user gave for a photographed print
    unanswered_photos: list = field(default_factory=list)  # paths of listed photos the user does not answer about
    photo_scope: str = "everyone"  # for a family: "the couple" or "everyone" (the Skill asks; no default there)
    add_papers: str = "skip"  # Step 6a answer: "skip", or "done" after putting papers in the Add here folder


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
    couple_only = scope == "a family" and user.photo_scope == "the couple"
    # the couple: the two partners (listed first); everyone: all but papers-only people
    photo_people = people[:2] if couple_only else [p for p in people if p not in user.papers_only]

    # Step 1 (skipped for one person)
    if scope != "one person" and user.photos_needed:
        check = list(photo_people)
        nas.call("photo-agent", "figure-albums")
        missing = R.confirm_people(nas.named_people, check)["missing"]
        if missing:
            log["stopped"] = "step 1: waiting for " + ", ".join(missing)
            return log

    # Steps 2 to 4
    month_counts, chosen, timeline_failed = None, [], False
    candidate_months, no_sample_label = None, R.NO_SAMPLE_LABEL
    if scope != "one person" and user.photos_needed and len(photo_people) >= 2:
        nas.call("photo-agent", "timeline-summary")
        if nas.month_counts is None:
            timeline_failed = True
        else:
            if nas.timeline_no_results:  # every month is 0; no sample call is sent for it
                timeline = R.timeline_reply(R.NO_RESULTS, start, end)
                log["no_results_message"] = "Photos face grouping found no photo of all these people in this period"
            else:
                timeline = {m: n for m, n in nas.month_counts.items() if m not in nas.timeline_missing}
            # the timeline's own samples exist only for the months it counted photos for
            timeline_samples = [c for c in nas.samples if timeline.get(c.month, 0) > 0] if nas.timeline_samples else []
            to_sample = R.months_to_sample(timeline, {c.month for c in timeline_samples}, start, end)
            if to_sample:  # Step 2: the sample call, per month, for every month with no samples
                nas.call("photo-agent", "search-picture")
            listed, sample_photos = {}, None
            if to_sample and not nas.sample_fail:
                for m in to_sample:
                    if m in nas.sample_counts:
                        listed[m] = nas.sample_counts[m]
                    elif timeline.get(m, 0) > 0 and m not in nas.sample_omit:
                        listed[m] = sum(c.month == m for c in nas.samples)  # a counted month: its photos come back
                sample_photos = [c for c in nas.samples if listed.get(c.month, 0) > 0]
            month_counts = R.month_states(timeline, start, end, listed)  # {MONTH_STATES}
            log["not_returned"] = R.unresolved_months(month_counts)  # {MONTHS_NOT_RETURNED} after Step 2
            log["recovered"] = {m: str(n) for m, n in month_counts.items() if isinstance(n, R.AtLeast)}
            candidates = R.merge_candidates(timeline_samples, sample_photos, set(to_sample), timeline)
            candidate_months = {c.month for c in candidates}
            sample_failed = bool(to_sample) and nas.sample_fail
            no_sample_label = R.SAMPLE_FAILED_LABEL if sample_failed else R.NO_SAMPLE_LABEL
            log["chosen_column"] = R.SAMPLE_FAILED_LABEL if (not candidates and sample_failed) else None
            # Step 2 offer: count the adults only, never the same people again, never fewer than two
            adults = [p for p in photo_people if p not in user.children]
            log["adults_offered"] = 0
            if (scope == "a family" and not couple_only and any(n == 0 for n in month_counts.values())
                    and len(adults) >= 2 and adults != photo_people):
                log["adults_offered"] += 1
                if user.accept_adults:
                    photo_people = adults
                    nas.call("photo-agent", "timeline-summary")
            if candidates:  # Step 3 plans only months with at least one candidate
                plan = R.plan_months(month_counts, limit, candidate_months)
                log["plan"] = plan
                nas.call("photo-agent", "vision-vlm")
                batch_failed = [m for m in plan if m in nas.vision_batch_fail]
                for _ in batch_failed:  # Step 4: a failed call's months are sent again, one month per call
                    nas.call("photo-agent", "vision-vlm")
                still_failed = [m for m in batch_failed if m in nas.vision_retry_fail]
                checked = R.people_check(candidates, photo_people)
                choice = R.choose_photos(checked, plan, limit, failed_months=still_failed)
                chosen = choice.chosen
                log["photo_check_failed"] = choice.check_failed
                log["none_fit"] = choice.none_fit
                log["failures"] = choice.failures

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
    # a photographed print is listed for its real date: given -> re-dated and kept; not given -> held out
    # the real date sets the month too; a print dated outside the period leaves the pack (Step 6 uses the user's date)
    period = set(R.month_range(start, end))
    redated = []
    for c in chosen:
        if c.kind == "print" and c.path in user.print_dates:
            real = user.print_dates[c.path]
            c = replace(c, date=real, month=real[:7])  # a copy: the mock NAS samples stay as they were
            if c.month not in period:
                continue
        redated.append(c)
    chosen = redated
    held = set(user.unanswered_photos) | {c.path for c in chosen if c.kind == "print" and c.path not in user.print_dates}
    waiting = [c.path for c in chosen if c.path in held]
    chosen = [c for c in chosen if c.path not in held]

    # Step 6 (redone after Step 7's answers, here folded in)
    photo_steps_skipped = scope == "one person" or not user.photos_needed or len(photo_people) < 2
    papers_only = photo_steps_skipped or timeline_failed
    common_law = user.relationship == "common-law"
    partners = printed[:2]
    # any couple or family: exactly one partner named (a child named too does not matter); joint papers are never here
    def single_name(papers):
        return [p for p in papers if scope != "one person" and p.readable and p.address and len(R.named_in(p, partners)) == 1
                and not any(p is d for d in user.drop_papers)]
    address_docs = single_name(nas.papers)
    linked = [p for p in linked if not any(p is d for d in user.drop_papers)]
    def step6(linked_docs, address_list):
        return R.coverage(start, end, None if papers_only else month_counts, chosen, linked_docs, common_law=common_law,
                          address_docs=address_list, partners=partners, candidate_months=candidate_months,
                          no_sample_label=no_sample_label)
    rows = step6(linked, address_docs)
    # Step 6a: offered once in the run, only with a gap; skip changes nothing; done reads only the added papers
    # (images by text recognition, the rest by document extraction), joins them by the 5c rules and redoes Step 6
    log["add_offered"], log["added_linked"], log["added_cut_off"], rechecked = 0, 0, 0, False
    if R.offer_added_papers(rows):
        log["add_offered"] += 1
        if user.add_papers == "done":
            nas.call("file-agent", "ls")
            read_paths = {p.path for p in nas.papers if p.path}  # read in Step 5 already
            docs, images, log["added_cut_off"] = R.split_added(nas.added_papers, read_paths)
            if docs:
                nas.call("document-agent", "extract")
            if images:
                nas.call("photo-agent", "vision-ocr")
            added = [replace(p, added=True) for p in docs + images if not any(p is d for d in user.drop_papers)]
            if added:
                rechecked = True
                joined2 = R.join_papers(nas.papers + added, printed)  # 5c over everything: one copy of each paper
                mismatches = list(joined2["mismatches"])
                linked = joined2["linked"]
                if user.confirm_matches:  # Step 7 answers folded in, as for the Step 5 papers
                    possible = joined2["possible_matches"]
                    linked = R.apply_answers(linked, possible, possible, [], people=printed, mismatches=mismatches)
                linked = [p for p in linked if not any(p is d for d in user.drop_papers)]
                address_docs = single_name(nas.papers) + single_name(added)
                rows = step6(linked, address_docs)  # Step 7's redo gives the same rows; the offer is not made again
                log["added_linked"] = sum(p.added for p in linked)
    log["covered_by_added"] = [r["month"] for r in rows if r["added"]]
    same_address_docs = [p for p in address_docs
                         if any(r["papers"] == ["same address on separate papers"] and R.paper_covers(p, r["month"]) for r in rows)]
    if common_law:
        papers_only = True
    label = R.gap_label(papers_only=photo_steps_skipped, search_failed=timeline_failed, common_law=common_law,
                        who="the couple" if couple_only else None)
    gaps = (R.still_open_lines if rechecked else R.gap_lines)(rows, label)
    # Step 6: unresolved months with no paper, listed under the gaps, in the check-by-hand line and the summary
    check_by_hand = None if common_law else R.unresolved_line(rows)

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
               written=list(nas.written), chosen_dates=[c.date for c in chosen], reused=reused, reuse_note=reuse_note,
               same_address_docs=len(same_address_docs), waiting_for_answer=waiting, photo_people=photo_people,
               pack_months=[r["month"] for r in rows if isinstance(r["pack"], int)],
               library={r["month"]: r["library"] for r in rows}, pack={r["month"]: r["pack"] for r in rows},
               check_by_hand=check_by_hand, final_summary_lists=gaps + ([check_by_hand] if check_by_hand else []))
    return log
