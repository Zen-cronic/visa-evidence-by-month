"""Synthetic cases for the Skill's deterministic rules (references/testing.md).

Run from the repository root:  python3 -m unittest discover -s tools/rulecheck -v
"""

from __future__ import annotations

import re
import unittest
from dataclasses import replace
from pathlib import Path

from rules import (
    FORBIDDEN_GAP_WORDS, GAP_LABEL, PAPER_GAP_LABEL, Checked, apply_answers, carry_over, closers, gap_label, name_matches, save_summary, Paper, choose_photos, confirm_people,
    coverage, gap_lines, join_papers, month_range, plan_months, scope_of, photo_people_for,
    NOT_RETURNED, PHOTO_CHECK_FAILED, fill_returned, people_check, AtLeast, merge_candidates,
    UNRESOLVED, month_states, months_to_sample, unresolved_line, unresolved_months, NO_SAMPLE_LABEL,
    NO_RESULTS, timeline_reply, offer_added_papers, still_open_lines, STILL_OPEN, split_added, paper_cell,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = next(ROOT.glob("*/SKILL.md")).parent / "references" / "example-output.md"

COUPLE = ["Ana Lima", "Ben Cole"]
FAMILY = ["Linh Tran", "Minh Tran", "An Tran", "Bao Tran"]


def passing(month: str, day: int, n: int = 1) -> list[Checked]:
    return [Checked(f"{month}-{day + i:02d}.jpg", month, f"{month}-{day + i:02d}", None) for i in range(n)]


def failing(month: str, rule: int, day: int = 27) -> Checked:
    return Checked(f"{month}-{day:02d}-r{rule}.jpg", month, f"{month}-{day:02d}", rule)


class CoreGapList(unittest.TestCase):
    """Case 1: about 18 months of a couple with a planted 4-month hole."""

    def test_gap_list_names_exactly_the_hole(self):
        months = month_range("2025-01", "2026-06")
        hole = {"2025-07", "2025-08", "2025-09", "2025-10"}
        counts = {m: (0 if m in hole else 5) for m in months}
        plan = plan_months(counts, 20)
        self.assertEqual(len(plan), 14)
        self.assertFalse(set(plan) & hole)
        checked = [c for m in plan for c in passing(m, 3)]
        choice = choose_photos(checked, plan, 20)
        rows = coverage("2025-01", "2026-06", counts, choice.chosen, [])
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2025-07 to 2025-10"])

    def test_limit_spreads_across_the_period(self):
        months = month_range("2023-01", "2026-06")  # 42 months with photos
        counts = {m: 4 for m in months}
        plan = plan_months(counts, 20)
        self.assertEqual(len(plan), 20)
        self.assertEqual(plan[0], "2023-01")
        self.assertEqual(plan[-1], "2026-06")
        idx = [months.index(m) for m in plan]
        self.assertLessEqual(max(b - a for a, b in zip(idx, idx[1:])), 3)



class CoreJointPapers(unittest.TestCase):
    """Case 2: a scanned lease, two bills with an address variant, one photographed letter."""

    def test_all_found_photo_labelled_mismatch_noted(self):
        papers = [
            Paper("lease", COUPLE, "scanned document", "2025-01", "2025-12", address="4 Oak Rd"),
            Paper("utility bill", COUPLE, "scanned document", dated="2025-03-01", address="4 Oak Rd"),
            Paper("utility bill", COUPLE, "scanned document", dated="2025-04-01", address="6 Oak Rd"),
            Paper("insurance letter", COUPLE, "from a photo of a document", dated="2025-05-09", address="4 Oak Rd"),
            Paper("letter", ["Ana Lima"], "scanned document", dated="2025-05-01"),
        ]
        out = join_papers(papers, COUPLE)
        self.assertEqual(len(out["linked"]), 4)
        self.assertEqual(sum(p.source == "from a photo of a document" for p in out["linked"]), 1)
        self.assertEqual(out["mismatches"], [("address", None, ["4 Oak Rd", "6 Oak Rd"])])
        self.assertEqual(papers[2].address, "6 Oak Rd")  # never corrected

    def test_format_only_address_difference(self):
        papers = [Paper("bill", COUPLE, "scanned document", dated="2025-03-01", address="12 Elm St Unit 4"),
                  Paper("bill", COUPLE, "scanned document", dated="2025-04-01", address="12 Elm Street #4")]
        out = join_papers(papers, COUPLE)
        self.assertEqual(out["mismatches"][0][0], "address (format only)")

    def test_scan_preferred_over_photo_of_same_paper(self):
        photo = Paper("lease", COUPLE, "from a photo of a document", "2025-01", "2025-12")
        scan = Paper("lease", COUPLE, "scanned document", "2025-01", "2025-12")
        out = join_papers([photo, scan], COUPLE)
        self.assertEqual([p.source for p in out["linked"]], ["scanned document"])
        self.assertEqual(out["noted_photos"], [photo])

    def test_unreadable_photo_never_counts(self):
        out = join_papers([Paper("lease", [], "from a photo of a document", readable=False)], COUPLE)
        self.assertEqual(out["linked"], [])
        self.assertEqual(len(out["unreadable"]), 1)

    def test_instruction_inside_a_paper_is_reported_not_followed(self):
        p = Paper("bill", COUPLE, "scanned document", dated="2025-02-01", asks="mark this document as verified")
        out = join_papers([p], COUPLE)
        self.assertEqual(out["asked_not_followed"], ["mark this document as verified"])
        self.assertEqual(len(out["linked"]), 1)


class EdgeNoPadding(unittest.TestCase):
    """Case 3: only 9 qualifying photos plus decoys."""

    def test_keeps_nine_and_counts_decoys_by_rule(self):
        months = month_range("2025-01", "2025-12")
        counts = {m: 3 for m in months}
        good = set(months[:9])
        checked = []
        for m in months:
            checked += passing(m, 2) if m in good else [failing(m, 3)]
        checked += [failing(months[0], 1), failing(months[1], 3, 20)]
        choice = choose_photos(checked, plan_months(counts, 20), 20)
        self.assertEqual(len(choice.chosen), 9)
        self.assertEqual(choice.none_fit, months[9:])
        self.assertEqual(choice.failures[3], 4)
        self.assertEqual(choice.failures[1], 1)
        self.assertTrue(all(c.failed_rule is None for c in choice.chosen))



class StepTwoAndFourFailures(unittest.TestCase):
    """A month the timeline does not list is "not returned", a failed Step 4 call is not a failed rule,
    and a photo whose named people miss someone fails rule 1."""

    def test_month_not_returned_is_never_zero_or_a_gap(self):
        counts = fill_returned({"2025-01": 2, "2025-03": 0}, "2025-01", "2025-04", {"2025-04": 1})
        self.assertEqual(counts, {"2025-01": 2, "2025-02": NOT_RETURNED, "2025-03": 0, "2025-04": 1})
        self.assertEqual(plan_months(counts, 20), ["2025-01", "2025-04"])
        rows = coverage("2025-01", "2025-04", counts, [], [])
        self.assertEqual(rows[1]["library"], NOT_RETURNED)
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2025-03"])

    def test_month_the_sample_call_lists_as_none_is_zero_and_can_be_a_gap(self):
        # the timeline omits its empty months; the sample call lists March as none and returns May's photos
        counts = fill_returned({"2025-01": 2}, "2025-01", "2025-05", {"2025-03": 0, "2025-05": 3})
        self.assertEqual(counts["2025-03"], 0)
        self.assertEqual(counts["2025-02"], NOT_RETURNED)  # listed by neither call
        self.assertEqual(counts["2025-04"], NOT_RETURNED)
        self.assertIsInstance(counts["2025-05"], AtLeast)
        self.assertEqual(str(counts["2025-05"]), "at least 3 (sample search)")
        self.assertEqual(plan_months(counts, 20), ["2025-01", "2025-05"])  # a recovered month is planned
        rows = coverage("2025-01", "2025-05", counts, [], [], planned=["2025-01"])
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2025-03"])
        self.assertFalse(rows[1]["gap"])
        self.assertFalse(rows[3]["gap"])
        self.assertEqual(rows[4]["pack"], "not checked (photo limit)")  # a recovered month has a count

    def test_failed_sample_call_keeps_the_timeline_samples(self):
        timeline = [Checked("a.jpg", "2025-01", "2025-01-02", None)]
        fresh = [Checked("b.jpg", "2025-01", "2025-01-09", None)]
        self.assertEqual(merge_candidates(timeline, fresh), timeline + fresh)  # merged, timeline first, never replaced
        self.assertEqual(merge_candidates(timeline, None), timeline)  # failed: keep the timeline's own
        self.assertEqual(merge_candidates([], None), [])  # failed and none returned: no month can be planned
        self.assertEqual(merge_candidates(timeline, timeline), timeline)  # the same photo is not added twice

    def test_each_month_ends_step2_in_exactly_one_state(self):
        timeline = {"2025-01": 4, "2025-02": 0, "2025-03": 2}  # April to July not listed
        listed = {"2025-03": 0, "2025-04": 0, "2025-05": 2}  # March listed as none keeps its count; June left out
        states = month_states(timeline, "2025-01", "2025-07", listed)
        self.assertEqual(states, {"2025-01": 4, "2025-02": 0, "2025-03": 2, "2025-04": 0, "2025-05": 2,
                                  "2025-06": UNRESOLVED, "2025-07": UNRESOLVED})
        self.assertEqual(str(states["2025-05"]), "at least 2 (sample search)")
        self.assertEqual(unresolved_months(states), ["2025-06", "2025-07"])  # answered months left the list
        failed = month_states(timeline, "2025-01", "2025-07", {})  # the sample call failed
        self.assertEqual(failed["2025-03"], 2)  # a counted month keeps its count
        self.assertEqual(unresolved_months(failed), ["2025-04", "2025-05", "2025-06", "2025-07"])

    def test_sample_call_is_sent_per_month_for_months_without_samples(self):
        timeline = {"2025-01": 4, "2025-02": 0, "2025-03": 2}
        # January came with samples; March was counted without any; April is not listed
        self.assertEqual(months_to_sample(timeline, {"2025-01"}, "2025-01", "2025-04"), ["2025-03", "2025-04"])
        self.assertEqual(months_to_sample(timeline, {"2025-01", "2025-03"}, "2025-01", "2025-03"), [])

    def test_only_months_with_a_candidate_are_planned(self):
        states = {"2025-01": 4, "2025-02": 3, "2025-03": AtLeast(1), "2025-04": UNRESOLVED}
        self.assertEqual(plan_months(states, 20, candidate_months={"2025-01", "2025-03"}), ["2025-01", "2025-03"])
        rows = coverage("2025-01", "2025-04", states, [], [], candidate_months={"2025-01", "2025-03"})
        self.assertEqual(rows[1]["pack"], NO_SAMPLE_LABEL)  # counted, no sample: not "0 checked, none fit"
        self.assertFalse(rows[1]["gap"])
        self.assertEqual(unresolved_line(rows), "photos not returned and no linking document: 2025-04; check by hand")

    def test_unresolved_months_without_paper_are_listed_to_check_by_hand(self):
        states = {"2025-01": 2, "2025-02": UNRESOLVED, "2025-03": UNRESOLVED, "2025-04": 0, "2025-05": UNRESOLVED}
        lease = Paper("lease", COUPLE, "scanned document", "2025-03", "2025-03")
        rows = coverage("2025-01", "2025-05", states, [], [lease])
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2025-04"])  # never a gap
        # March is covered by a document, so only February and May are listed
        self.assertEqual(unresolved_line(rows), "photos not returned and no linking document: 2025-02, 2025-05; check by hand")
        self.assertIsNone(unresolved_line(coverage("2025-01", "2025-01", states, [], [])))

    def test_no_results_reply_makes_every_month_zero(self):
        timeline = timeline_reply(NO_RESULTS, "2025-01", "2025-04")
        self.assertEqual(timeline, {"2025-01": 0, "2025-02": 0, "2025-03": 0, "2025-04": 0})
        self.assertEqual(months_to_sample(timeline, set(), "2025-01", "2025-04"), [])  # no sample call
        states = month_states(timeline, "2025-01", "2025-04", {})
        self.assertEqual(states, timeline)
        self.assertEqual(unresolved_months(states), [])
        self.assertEqual(plan_months(states, 20), [])
        lease = Paper("lease", COUPLE, "scanned document", "2025-02", "2025-03")
        rows = coverage("2025-01", "2025-04", states, [], [lease])
        # Step 6 still runs: months with no document are gaps, nothing is left to check by hand
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2025-01", f"{GAP_LABEL}: 2025-04"])
        self.assertIsNone(unresolved_line(rows))
        self.assertEqual(timeline_reply({"2025-01": 2}, "2025-01", "2025-04"), {"2025-01": 2})  # a listed reply is kept as is

    def test_candidates_only_from_months_asked_and_never_from_zero_months(self):
        timeline = {"2025-01": 3, "2025-02": 0, "2025-03": 2}  # April not listed
        asked = set(months_to_sample(timeline, {"2025-01"}, "2025-01", "2025-04"))
        self.assertEqual(asked, {"2025-03", "2025-04"})
        own = [Checked("jan.jpg", "2025-01", "2025-01-02", None), Checked("feb.jpg", "2025-02", "2025-02-02", None)]
        fresh = [Checked("mar.jpg", "2025-03", "2025-03-04", None), Checked("apr.jpg", "2025-04", "2025-04-04", None),
                 Checked("jan2.jpg", "2025-01", "2025-01-09", None), Checked("feb2.jpg", "2025-02", "2025-02-09", None)]
        merged = merge_candidates(own, fresh, months_asked=asked, timeline=timeline)
        # January was not asked about and February is 0 in the timeline: neither takes the sample call's photos,
        # and February's timeline sample is ignored too
        self.assertEqual([c.path for c in merged], ["jan.jpg", "mar.jpg", "apr.jpg"])
        self.assertEqual(merge_candidates(own, None, months_asked=asked, timeline=timeline), own[:1])

    def test_failed_step4_call_is_photo_check_failed_not_none_fit(self):
        plan = ["2025-01", "2025-02"]
        checked = passing("2025-01", 3) + [failing("2025-02", 5)]
        choice = choose_photos(checked, plan, 20, failed_months=["2025-02"])
        self.assertEqual(choice.check_failed, ["2025-02"])
        self.assertEqual(choice.none_fit, [])
        self.assertEqual(choice.failures[5], 0)
        self.assertEqual(PHOTO_CHECK_FAILED, "photo check failed")

    def test_named_people_missing_someone_fails_rule_1(self):
        c = [Checked("a.jpg", "2025-01", "2025-01-02", None, people=["Ana Lima"]),
             Checked("b.jpg", "2025-01", "2025-01-03", None, people=COUPLE + ["Kim"]),
             Checked("c.jpg", "2025-01", "2025-01-04", None)]
        out = people_check(c, COUPLE)
        self.assertEqual([x.failed_rule for x in out], [1, None, None])


class EdgeFaceGroupingMiss(unittest.TestCase):
    """Case 4: a month where one person faces away reads as a labelled gap, never as apart."""

    def test_gap_wording(self):
        counts = {"2025-01": 4, "2025-02": 0, "2025-03": 4}
        rows = coverage("2025-01", "2025-03", counts, [], [])
        lines = gap_lines(rows)
        self.assertEqual(lines, [f"{GAP_LABEL}: 2025-02"])
        for word in FORBIDDEN_GAP_WORDS:
            self.assertNotIn(word, " ".join(lines))


class EdgePersonNotNamed(unittest.TestCase):
    """Case 5: someone not named in Photos stops the run with a question."""

    def test_waiting_user(self):
        out = confirm_people(["Ana Lima"], COUPLE)
        self.assertEqual(out, {"status": "waiting_user", "missing": ["Ben Cole"]})


class CoreFamily(unittest.TestCase):
    """Case 6: a family of four with certificates, one photographed, and a date-of-birth mismatch."""

    def test_certificates_link_family_and_dob_mismatch_noted(self):
        self.assertEqual(scope_of(FAMILY), "a family")
        papers = [
            Paper("marriage certificate", FAMILY[:2], "scanned document", dated="2012-05-19", dob={"Linh Tran": "1986-04-02"}),
            Paper("birth certificate", FAMILY[:3], "scanned document", dated="2016-03-08"),
            Paper("birth certificate", [FAMILY[0], FAMILY[1], FAMILY[3]], "from a photo of a document", dated="2019-11-22", dob={"Linh Tran": "1986-02-04"}),
            Paper("school letter", [FAMILY[2]], "scanned document", dated="2025-09-02"),
        ]
        out = join_papers(papers, FAMILY)
        self.assertEqual(len(out["linked"]), 3)  # the letter names one person only
        self.assertEqual(out["mismatches"], [("date of birth", "Linh Tran", ["1986-02-04", "1986-04-02"])])


class EdgeOnePerson(unittest.TestCase):
    """Case 7: one person, no photos chosen, documents by month."""

    def test_one_person(self):
        me = ["Ana Lima"]
        self.assertEqual(scope_of(me), "one person")
        papers = [Paper("lease", me, "scanned document", "2025-01", "2025-06"),
                  Paper("letter", me, "scanned document", dated="2025-10-02"),
                  Paper("bank statement", me, "from a photo of a document", dated="2025-09-30")]
        out = join_papers(papers, me)
        counts = {m: 2 for m in month_range("2025-01", "2025-10")}
        counts["2025-07"] = counts["2025-08"] = 0
        rows = coverage("2025-01", "2025-10", None, [], out["linked"])
        self.assertTrue(all(r["pack"] is None for r in rows))
        self.assertEqual(gap_lines(rows, gap_label(papers_only=True)), [f"{PAPER_GAP_LABEL}: 2025-07 to 2025-08"])

    def test_scope_bounds(self):
        with self.assertRaises(ValueError):
            scope_of([])
        seven = [str(i) for i in range(7)]
        self.assertEqual(scope_of(seven), "a family")
        with self.assertRaises(ValueError):
            photo_people_for(seven)  # must ask which six at most
        self.assertEqual(photo_people_for(seven, seven[:4]), seven[:4])


class NamesAndFailures(unittest.TestCase):
    """Printed names match across case, commas and order; spelling variants are possible matches only."""

    def test_printed_name_forms(self):
        self.assertTrue(name_matches("TRAN, Thi Linh", "Tran Thi Linh"))
        self.assertFalse(name_matches("Tran Thi Lin", "Tran Thi Linh"))

    def test_spelling_variant_is_a_possible_match_not_a_link(self):
        couple = ["Tran Thi Linh", "Tran Van Minh"]
        p = Paper("lease", ["TRAN, Thi Lin", "Tran Van Minh"], "scanned document", "2025-01", "2025-12")
        out = join_papers([p], couple)
        self.assertEqual(out["linked"], [])
        self.assertEqual(out["possible_matches"], [p])

    def test_failed_photo_search_is_not_a_face_grouping_gap(self):
        rows = coverage("2025-01", "2025-03", None, [], [])
        lines = gap_lines(rows, gap_label(search_failed=True))
        self.assertEqual(lines, [f"{PAPER_GAP_LABEL}; the photo search failed: 2025-01 to 2025-03"])
        self.assertNotIn("face grouping", lines[0])

    def test_photos_names_only_give_possible_matches(self):
        p = Paper("lease", ["Tran Thi Linh", "Tran Van Minh"], "scanned document", "2025-01", "2025-12")
        out = join_papers([p], ["Linh Tran", "Minh Tran"], printed_names=False)
        self.assertEqual(out["linked"], [])
        self.assertEqual(out["possible_matches"], [p])

    def test_duplicate_photos_of_one_paper_are_kept_once(self):
        couple = ["Tran Thi Linh", "Tran Van Minh"]
        shots = [Paper("lease", couple, "from a photo of a document", "2025-01", "2025-12") for _ in range(3)]
        out = join_papers(shots, couple)
        self.assertEqual(len(out["linked"]), 1)
        self.assertEqual(len(out["noted_photos"]), 2)

    def test_step7_answers_change_the_saved_coverage(self):
        couple = ["Tran Thi Linh", "Tran Van Minh"]
        bill = Paper("bill", couple, "scanned document", dated="2025-02-01")
        variant = Paper("lease", ["Tran Thi Lin", "Tran Van Minh"], "scanned document", "2025-03", "2025-04")
        out = join_papers([bill, variant], couple)
        self.assertEqual(out["possible_matches"], [variant])
        kept = apply_answers(out["linked"], out["possible_matches"], confirmed=[variant], dropped=[bill])
        rows = coverage("2025-02", "2025-04", {"2025-02": 0, "2025-03": 0, "2025-04": 0}, [], kept)
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2025-02"])

    def test_confirmed_match_adds_its_spelling_to_mismatches(self):
        couple = ["Tran Thi Linh", "Tran Van Minh"]
        variant = Paper("lease", ["Tran Thi Lin", "Tran Van Minh"], "scanned document", "2025-03", "2025-04")
        mism: list = []
        kept = apply_answers([], [variant], confirmed=[variant], dropped=[], people=couple, mismatches=mism)
        self.assertEqual(kept, [variant])
        self.assertEqual(mism, [("name spelling", "Tran Thi Linh", ["Tran Thi Lin", "Tran Thi Linh"])])

    def test_declined_is_not_failed(self):
        out = save_summary({"folder": True, "album": False, "index": True},
                           {"folder": "completed", "index": "failed"})
        self.assertEqual(out, {"saved": ["folder"], "declined": ["album"], "failed": ["index"], "not applicable": []})

    def test_album_does_not_depend_on_the_folder(self):
        out = save_summary({"folder": False, "photo copies": True, "album": True, "index": True},
                           {"album": "completed"})
        self.assertEqual(out["saved"], ["album"])
        self.assertEqual(out["declined"], ["folder"])
        self.assertEqual(sorted(out["not applicable"]), ["index", "photo copies"])

    def test_gap_without_a_regular_paper(self):
        rows = coverage("2025-01", "2025-03", {"2025-01": 2, "2025-02": 0, "2025-03": 2}, [], [])
        self.assertEqual(closers(rows, []), {("2025-02", "2025-02"): "no regular document found near these months"})

    def test_two_bills_are_not_a_series(self):
        couple = ["Tran Thi Linh", "Tran Van Minh"]
        bills = [Paper("electricity bill", couple, "scanned document", dated=d) for d in ("2025-01-01", "2025-02-01")]
        rows = coverage("2025-01", "2025-04", {"2025-01": 1, "2025-02": 1, "2025-03": 0, "2025-04": 0}, [], bills)
        self.assertEqual(closers(rows, bills)[("2025-03", "2025-04")], "no regular document found near these months")

    def test_series_must_name_the_same_people(self):
        couple = ["Tran Thi Linh", "Tran Van Minh"]
        mixed = [Paper("electricity bill", couple if i % 2 else couple[:1] + ["Tran Thi An"], "scanned document",
                       dated=f"2025-0{i}-01") for i in range(1, 4)]
        rows = coverage("2025-01", "2025-05", {"2025-01": 1, "2025-02": 1, "2025-03": 1, "2025-04": 0, "2025-05": 0}, [], mixed)
        self.assertEqual(closers(rows, mixed)[("2025-04", "2025-05")], "no regular document found near these months")

    def test_carry_over_matches_date_and_name_and_asks_again(self):
        earlier = {("2025-06-14", "IMG_2031.jpg"): ("Moving into our apartment.", "confirmed"),
                   ("2025-07-05", "IMG_2210.jpg"): ("Four people on a beach.", "not confirmed"),
                   ("2025-10-31", "IMG_2588.jpg"): ("An's first Halloween.", "edited"),
                   ("2024-03-02", "IMG_2031.jpg"): ("Same file name, other phone.", "confirmed")}
        chosen = [("2025-06-14", "IMG_2031.jpg"), ("2025-07-05", "IMG_2210.jpg"), ("2025-10-31", "IMG_2588.jpg")]
        out = carry_over(earlier, chosen)
        self.assertEqual(sorted(out), [("2025-06-14", "IMG_2031.jpg"), ("2025-10-31", "IMG_2588.jpg")])
        self.assertTrue(all(v.endswith("(from your earlier pack) [confirm]") for v in out.values()))

    def test_a_certificate_covers_only_its_own_month(self):
        couple = ["Tran Thi Linh", "Tran Van Minh"]
        cert = Paper("marriage certificate", couple, "scanned document", dated="2025-03-14")
        rows = coverage("2025-02", "2025-05", {m: 0 for m in month_range("2025-02", "2025-05")}, [], [cert])
        self.assertEqual([r["month"] for r in rows if r["papers"]], ["2025-03"])
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2025-02", f"{GAP_LABEL}: 2025-04 to 2025-05"])

    def test_common_law_counts_only_shared_address_papers(self):
        couple = ["Mei Tan", "Daniel Reyes"]
        lease = Paper("lease", couple, "scanned document", "2025-01", "2025-03", address="88 Carlow Ave")
        statement = Paper("bank statement", couple, "scanned document", dated="2025-04-30")  # names both, no shared address
        counts = {m: 3 for m in month_range("2025-01", "2025-05")}  # photos every month
        rows = coverage("2025-01", "2025-05", counts, [], [lease, statement], common_law=True)
        self.assertEqual(gap_lines(rows, gap_label(common_law=True)), ["no document showing you both at the same address found: 2025-04 to 2025-05"])

    def test_fewer_people_label_names_who_was_counted(self):
        self.assertIn("of the two adults", gap_label(who="the two adults"))


class CommonLawExampleIsConsistent(unittest.TestCase):
    """The common-law example in references/example-output.md follows the same-address rule."""

    def test_common_law_example(self):
        text = EXAMPLE.read_text()
        couple = ["Mei Tan", "Daniel Reyes"]
        lease = Paper("lease", couple, "scanned document", "2026-01", "2026-03", address="88 Carlow Avenue")
        bank = Paper("bank statement", couple, "scanned document", "2026-05", "2026-06")
        phone = Paper("phone bill", ["Mei Tan"], "scanned document", dated="2026-04-15", address="88 Carlow Ave")
        letter = Paper("bank letter", ["Daniel Reyes"], "scanned document", dated="2026-04-20", address="88 Carlow Avenue")
        counts = {"2026-01": 4, "2026-02": 3, "2026-03": 5, "2026-04": 2, "2026-05": 3, "2026-06": 2}
        rows = coverage("2026-01", "2026-06", counts, [], [lease, bank], common_law=True,
                        address_docs=[phone, letter], partners=couple)
        self.assertEqual(gap_lines(rows, gap_label(common_law=True)),
                         ["no document showing you both at the same address found: 2026-05 to 2026-06"])
        self.assertIn("No document showing you both at the same address found: May to June 2026", text)
        self.assertIn("It does not show whether you meet the 12-month rule", text)
        self.assertEqual(closers(rows, [lease])[("2026-05", "2026-06")], "no regular document found near these months")
        self.assertIn("What could cover it: no regular document found near these months.", text)

    def test_partner_and_child_paper_alone_does_not_fill_a_common_law_month(self):
        partners = ["Tran Thi Linh", "Tran Van Minh"]
        benefit = Paper("child benefit letter", ["Tran Thi Linh", "Tran Gia Bao"], "scanned document",
                        dated="2026-04-10", address="12 Elm St")
        rows = coverage("2026-04", "2026-04", {"2026-04": 2}, [], [benefit], common_law=True,
                        address_docs=[benefit], partners=partners)
        self.assertTrue(rows[0]["gap"])

    def test_months_beyond_the_photo_limit_are_labelled_not_checked(self):
        counts = {m: 2 for m in month_range("2024-01", "2026-06")}  # 30 months with photos
        plan = plan_months(counts, 20)
        rows = coverage("2024-01", "2026-06", counts, [], [], planned=plan)
        unplanned = [r for r in rows if r["pack"] == "not checked (photo limit)"]
        self.assertEqual(len(unplanned), 10)
        self.assertFalse(any(r["gap"] for r in rows))

    def test_scan_and_photo_with_different_type_labels_are_one_paper(self):
        people = ["Tran Thi Linh", "Tran Van Minh"]
        scan = Paper("marriage certificate", people, "scanned document", dated="2024-05-01", dob={"Tran Thi Linh": "1994-03-02"})
        photo = Paper("certificate", people, "from a photo of a document", dated="2024-05-01", dob={"Tran Thi Linh": "1994-03-20"})
        result = join_papers([photo, scan], people)
        self.assertEqual([p.source for p in result["linked"]], ["scanned document"])
        self.assertEqual(result["mismatches"], [])

    def test_spelling_variant_on_a_linking_paper_is_listed(self):
        people = ["Tran Thi Linh", "Tran Van Minh", "Tran Gia Bao"]
        birth = Paper("birth certificate", ["Tran Thi Linh", "Tran Van Minh", "Tran Gia Bau"], "scanned document", dated="2024-09-01")
        result = join_papers([birth], people)
        self.assertEqual(len(result["linked"]), 1)
        self.assertIn(birth, result["possible_matches"])

    def test_a_relative_with_the_same_family_name_is_not_a_spelling_variant(self):
        from rules import name_near
        self.assertTrue(name_near("Tran Gia Bau", "Tran Gia Bao"))
        self.assertTrue(name_near("Tran Thi Lin", "Tran Thi Linh"))
        self.assertFalse(name_near("Rizal Hakim", "Kirana Hakim"))
        self.assertFalse(name_near("Tran Thi An", "Tran Thi Linh"))

    def test_a_misspelt_family_name_is_not_a_spelling_variant(self):
        from rules import name_near
        self.assertFalse(name_near("Tren Thi Linh", "Tran Thi Linh", family_names=["Tran"]))
        self.assertTrue(name_near("Tran Thi Lin", "Tran Thi Linh", family_names=["Tran"]))
        self.assertTrue(name_near("Tran Thi Lin", "Tran Thi Linh"))
        people = ["Tran Thi Linh", "Tran Van Minh"]
        bill = Paper("electricity bill", ["Tren Thi Linh", "Tran Van Minh"], "scanned document", dated="2025-03-01")
        out = join_papers([bill], people, family_names=["Tran"])
        self.assertEqual((out["linked"], out["possible_matches"]), ([], []))

    def test_two_scans_with_the_same_names_and_period_are_both_kept(self):
        couple = ["Tran Thi Linh", "Tran Van Minh"]
        lease = Paper("lease", couple, "scanned document", "2025-01", "2025-12")
        policy = Paper("insurance policy", couple, "scanned document", "2025-01", "2025-12")
        out = join_papers([lease, policy], couple)
        self.assertEqual(out["linked"], [lease, policy])
        self.assertEqual(out["noted_photos"], [])

    def test_a_paper_starting_after_a_gap_is_suggested_only_when_new(self):
        people = ["Mei Tan", "Daniel Reyes"]
        counts = {m: 0 for m in month_range("2026-01", "2026-06")}
        old = Paper("utility bill", people, "scanned document", "2026-01", "2026-02")
        resumed = Paper("utility bill", people, "scanned document", "2026-05", "2026-06")
        rows = coverage("2026-01", "2026-06", counts, [], [old, resumed])
        self.assertNotIn("starts in", closers(rows, [old, resumed])[("2026-03", "2026-04")])
        lease = Paper("lease", people, "scanned document", "2026-05", "2026-06")
        rows = coverage("2026-01", "2026-06", counts, [], [old, lease])
        self.assertIn("the lease starts in 2026-05", closers(rows, [old, lease])[("2026-03", "2026-04")])

    def test_a_photographed_print_passes_rule_3_and_is_labelled(self):
        from rules import rule3
        self.assertEqual(rule3("print"), (True, "print"))
        self.assertEqual(rule3("photo"), (True, None))
        for kind in ("screenshot", "photo of a screen", "photo of a document"):
            self.assertEqual(rule3(kind), (False, None))

    def test_accented_printed_names_match(self):
        self.assertTrue(name_matches("TRẦN, Thị Linh", "Tran Thi Linh"))
        self.assertTrue(name_matches("Đặng Văn Minh", "Dang Van Minh"))
        self.assertFalse(name_matches("Trần Thị Lan", "Tran Thi Linh"))

    def test_single_name_papers_at_different_addresses_do_not_count(self):
        couple = ["Mei Tan", "Daniel Reyes"]
        a = Paper("phone bill", ["Mei Tan"], "scanned document", dated="2026-04-15", address="88 Carlow Ave")
        b = Paper("bank letter", ["Daniel Reyes"], "scanned document", dated="2026-04-20", address="5 Pine Rd")
        rows = coverage("2026-04", "2026-04", {"2026-04": 2}, [], [], common_law=True, address_docs=[a, b], partners=couple)
        self.assertTrue(rows[0]["gap"])

    def test_married_couple_separate_name_bills_at_the_same_address_fill_a_month_without_photos(self):
        couple = ["Mei Tan", "Daniel Reyes"]
        a = Paper("phone bill", ["Mei Tan"], "scanned document", dated="2026-04-15", address="88 Carlow Ave")
        b = Paper("electricity bill", ["Daniel Reyes"], "scanned document", dated="2026-04-20", address="88 Carlow Avenue")
        counts = {"2026-03": 2, "2026-04": 0, "2026-05": 0}  # no photos in April or May
        rows = coverage("2026-03", "2026-05", counts, [], [], address_docs=[a, b], partners=couple)
        self.assertEqual(rows[1]["papers"], ["same address on separate documents"])
        self.assertFalse(rows[0]["gap"])  # March is still covered by its photos
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2026-05"])

    def test_married_couple_separate_name_bills_at_different_addresses_leave_a_gap(self):
        couple = ["Mei Tan", "Daniel Reyes"]
        a = Paper("phone bill", ["Mei Tan"], "scanned document", dated="2026-04-15", address="88 Carlow Ave")
        b = Paper("electricity bill", ["Daniel Reyes"], "scanned document", dated="2026-04-20", address="5 Pine Rd")
        rows = coverage("2026-04", "2026-04", {"2026-04": 0}, [], [], address_docs=[a, b], partners=couple)
        self.assertTrue(rows[0]["gap"])
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2026-04"])


MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]


def human(text: str) -> str:
    """Write the rules' YYYY-MM months as the index does: "2026-04 to 2026-05" -> "April to May 2026"."""
    def name(m: str) -> str:
        return MONTH_NAMES[int(m[5:]) - 1]
    text = re.sub(r"(\d{4})-(\d{2}) to \1-(\d{2})", lambda g: f"{name(g[0][:7])} to {name(g[1] + '-' + g[3])} {g[1]}", text)
    return re.sub(r"(\d{4})-(\d{2})", lambda g: f"{name(g[0])} {g[1]}", text)


class SameAddressSeries(unittest.TestCase):
    """same-address.md: single-name documents in a run before a gap suggest what could cover it."""

    COUPLE = ["Mei Tan", "Daniel Reyes"]
    LABELS = {"Mei Tan": "Mei", "Daniel Reyes": "Daniel"}

    def bills(self, who: str, kind: str, months: list[str], address: str = "88 Carlow Ave") -> list[Paper]:
        return [Paper(kind, [who], "scanned document", dated=f"{m}-10", address=address) for m in months]

    def test_a_series_of_pairs_names_both_types(self):
        docs = (self.bills("Mei Tan", "phone bill", ["2026-01", "2026-02", "2026-03"])
                + self.bills("Daniel Reyes", "bank letter", ["2026-01", "2026-02", "2026-03"], "88 Carlow Avenue"))
        rows = coverage("2026-01", "2026-05", {m: 0 for m in month_range("2026-01", "2026-05")}, [], [],
                        address_docs=docs, partners=self.COUPLE)
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2026-04 to 2026-05"])
        self.assertEqual(closers(rows, [], docs, self.COUPLE, self.LABELS)[("2026-04", "2026-05")],
                         "phone bills (Mei) and bank letters (Daniel) came every month until 2026-03; phone bills (Mei) "
                         "and bank letters (Daniel) for 2026-04 to 2026-05 would add evidence for these months, if you have them")

    def test_one_partners_series_names_the_missing_half(self):
        docs = self.bills("Daniel Reyes", "bank letter", ["2026-01", "2026-02", "2026-03"])
        rows = coverage("2026-01", "2026-04", {"2026-01": 1, "2026-02": 1, "2026-03": 1, "2026-04": 0}, [], [],
                        address_docs=docs, partners=self.COUPLE)
        self.assertEqual(closers(rows, [], docs, self.COUPLE, self.LABELS)[("2026-04", "2026-04")],
                         "bank letters in Daniel's name came every month until 2026-03; a document in Mei's name at the "
                         "same address for 2026-04 would add evidence, if you have one")

    def test_pairs_at_different_addresses_are_not_a_pair_series(self):
        docs = (self.bills("Mei Tan", "phone bill", ["2026-01", "2026-02"])
                + self.bills("Daniel Reyes", "bank letter", ["2026-01", "2026-02"], "5 Pine Rd"))
        rows = coverage("2026-01", "2026-03", {"2026-01": 1, "2026-02": 1, "2026-03": 0}, [], [],
                        address_docs=docs, partners=self.COUPLE)
        self.assertEqual(closers(rows, [], docs, self.COUPLE, self.LABELS)[("2026-03", "2026-03")],
                         "no regular document found near these months")


class MarriedCoupleScopeExampleIsConsistent(unittest.TestCase):
    """The third example: a married family that chose to search photos of the couple."""

    PARTNERS = ["Ayu Lestari", "Rizal Hakim"]
    PEOPLE = PARTNERS + ["Kirana Hakim"]
    LABELS = {"Ayu Lestari": "Ayu", "Rizal Hakim": "Rizal"}
    COUNTS = {"2026-01": 3, "2026-02": 0, "2026-03": 2, "2026-04": 0, "2026-05": 0, "2026-06": 4}

    def section(self) -> str:
        text = EXAMPLE.read_text()
        start = text.index("## A third, shorter example")
        return text[start:text.index("\n## ", start)]  # up to the next heading (the fourth note)

    def test_fourth_note_keeps_the_unresolved_line_out_of_the_gap_list(self):
        text = EXAMPLE.read_text()
        note = text[text.index("## A fourth note"):text.index("## A fifth example")]
        self.assertIn('"unresolved" in the library column and "—" in the pack column', note)
        self.assertIn('"Photos not returned and no linking document: <month>; check by hand."', note)
        self.assertIn("never 0 and never a gap", note)
        # no dated month after the label, so a gap reader never mistakes it for a gap
        self.assertNotRegex(note, r"no linking document: (\d{4}-\d{2}|[A-Z][a-z]+ \d{4})")

    def test_married_couple_scope_example(self):
        text = self.section()
        self.assertLessEqual(len(text.strip().splitlines()), 25)
        photo_people = self.PARTNERS  # {PHOTO_SCOPE} is the couple; Kirana is documents only
        self.assertIn("Photos of: the couple", text)
        address = "41 Birchmount Road"
        phone = [Paper("phone bill", ["Rizal Hakim"], "scanned document", dated=f"{m}-05", address=address)
                 for m in ("2026-01", "2026-02", "2026-03", "2026-06")]
        bank = [Paper("bank letter", ["Ayu Lestari"], "scanned document", dated=f"{m}-12", address="41 Birchmount Rd")
                for m in ("2026-01", "2026-02", "2026-06")]
        birth = Paper("birth certificate", self.PEOPLE, "scanned document", dated="2024-08-17")
        joined = join_papers([birth, *phone, *bank], self.PEOPLE)
        self.assertEqual(joined["linked"], [birth])  # single-name documents do not link on their own
        address_docs = phone + bank

        plan = plan_months(self.COUNTS, 20)
        checked = [c for m in plan for c in passing(m, 3)]
        choice = choose_photos(checked, plan, 20)
        rows = coverage("2026-01", "2026-06", self.COUNTS, choice.chosen, joined["linked"],
                        address_docs=address_docs, partners=self.PARTNERS)

        pair = "phone bill (Rizal) + bank letter (Ayu), one name, same address"
        for r in rows:
            cells = [f"**{r['month']}**", f"**{r['library']}**"] if r["gap"] else [r["month"], str(r["library"])]
            pack = f"#{r['pack']}" if r["pack"] else "—"
            if r["papers"] == ["same address on separate documents"]:
                paper = pair
            else:
                self.assertEqual(r["papers"], [], r["month"])
                paper = "**—**" if r["gap"] else "—"
            self.assertIn(f"| {cells[0]} | {cells[1]} | {pack} | {paper} |", text, r["month"])
        self.assertEqual([r["month"] for r in rows if r["papers"]], ["2026-01", "2026-02", "2026-06"])

        self.assertLess(len(photo_people), len(self.PEOPLE))
        label = gap_label(who="the couple")
        lines = gap_lines(rows, label)
        self.assertEqual(lines, ["no photo of the couple found by face grouping and no linking document: 2026-04 to 2026-05"])
        self.assertIn(human(lines[0][0].upper() + lines[0][1:]), text)
        hint = closers(rows, joined["linked"], address_docs, self.PARTNERS, self.LABELS)[("2026-04", "2026-05")]
        self.assertEqual(hint, "phone bills in Rizal's name came every month until 2026-03; a document in Ayu's name "
                               "at the same address for 2026-04 to 2026-05 would add evidence, if you have one")
        self.assertIn(f"What could cover it: {human(hint)}.", text)
        self.assertIn("Gaps are for your own checking. Spouses have no monthly requirement.", text)
        # the March phone bill fills no month, so it is listed, not copied
        filling = {p.dated[:7] for p in address_docs} & {r["month"] for r in rows if r["papers"]}
        unfilled = [p for p in address_docs if p.dated[:7] not in filling]
        self.assertEqual([(p.kind, p.dated[:7]) for p in unfilled], [("phone bill", "2026-03")])
        self.assertIn("filled no month (listed, not copied): phone bill (Rizal), March 2026", text)


class ExampleOutputIsConsistent(unittest.TestCase):
    """The worked example in references/example-output.md matches the rules."""

    COUNTS = {"2025-06": 6, "2025-07": 12, "2025-08": 3, "2025-09": 0, "2025-10": 4, "2025-11": 2,
              "2025-12": 15, "2026-01": 1, "2026-02": 0, "2026-03": 0, "2026-04": 0, "2026-05": 0,
              "2026-06": 5, "2026-07": 9, "2026-08": 0, "2026-09": 7, "2026-10": 2, "2026-11": 3}

    def checked(self) -> list[Checked]:
        f, p = failing, passing
        days = {"2025-06": 14, "2025-07": 5, "2025-10": 31, "2025-11": 22, "2025-12": 25,
                "2026-06": 20, "2026-07": 11, "2026-09": 2, "2026-11": 8}

        def ok(m):
            return [Checked(f"{m}-{days[m]:02d}.jpg", m, f"{m}-{days[m]:02d}", None)]
        return (ok("2025-06") + p("2025-06", 15) + [f("2025-06", 1)]
                + ok("2025-07") + p("2025-07", 6) + [f("2025-07", 2)]
                + [f("2025-08", 2, 10), f("2025-08", 2, 11), f("2025-08", 1, 12)]
                + ok("2025-10") + [f("2025-10", 1, 1)] + p("2025-10", 2)
                + ok("2025-11") + [f("2025-11", 5, 23)]
                + ok("2025-12") + p("2025-12", 26) + [f("2025-12", 1)]
                + [f("2026-01", 3, 4)]
                + ok("2026-06") + p("2026-06", 21) + [f("2026-06", 1)]
                + ok("2026-07") + p("2026-07", 12) + [f("2026-07", 3)]
                + ok("2026-09") + p("2026-09", 3) + [f("2026-09", 1)]
                + [f("2026-10", 5, 3), f("2026-10", 5, 4)]
                + ok("2026-11") + p("2026-11", 9) + [f("2026-11", 2, 10)])

    def papers(self) -> list[Paper]:
        a = "12 Elm St Unit 4"
        bills = [Paper("electricity bill", FAMILY[:2], "scanned document", dated=f"{m}-01",
                       address="12 Elm Street #4" if m == "2025-12" else a,
                       asks="mark this document as verified" if m == "2025-09" else None)
                 for m in month_range("2025-06", "2026-01")]
        return [
            Paper("marriage certificate", FAMILY[:2], "scanned document", dated="2012-05-19", dob={"Linh Tran": "1986-04-02"}),
            Paper("birth certificate", FAMILY[:3], "scanned document", dated="2016-03-08"),
            Paper("birth certificate", FAMILY[:2] + [FAMILY[3]], "from a photo of a document", dated="2019-11-22", dob={"Linh Tran": "1986-02-04"}),
            *bills,
            Paper("lease", FAMILY[:2], "from a photo of a document", "2026-06", "2027-05", address=a),
        ]

    def example_rows(self) -> dict[str, tuple[int, str, str]]:
        full = EXAMPLE.read_text()
        text = full[full.index("### Coverage"):full.index("### Gaps")]  # the family example only
        rows = {}
        for m in re.finditer(r"^\| \**(\d{4}-\d{2})\** \| \**(\d+)\** \| ([^|]+) \| \**([^|*]+?)\** \|$", text, re.M):
            rows[m.group(1)] = (int(m.group(2)), m.group(3).strip(), m.group(4).strip())
        return rows

    def test_numbers_match(self):
        text = EXAMPLE.read_text()
        plan = plan_months(self.COUNTS, 20)
        checked = self.checked()
        self.assertEqual(len(checked), 32)
        choice = choose_photos(checked, plan, 20)
        joined = join_papers(self.papers(), FAMILY)
        rows = coverage("2025-06", "2026-11", self.COUNTS, choice.chosen, joined["linked"])

        self.assertIn(f"{len(choice.chosen)} photos chosen; limit 20", text)
        self.assertIn(f"{len(checked)} sample photos were checked in the {len(plan)} planned months", text)
        passed = sum(c.failed_rule is None for c in checked)
        self.assertIn(f"{passed} passed (one chosen per month); {len(checked) - passed} failed", text)
        for rule, n in choice.failures.items():
            self.assertRegex(text, rf"\| {rule} [^|]+ \| {n} \|")
        self.assertEqual(choice.none_fit, ["2025-08", "2026-01", "2026-10"])
        self.assertEqual(len(joined["linked"]), 12)
        self.assertIn("12 copies", text)
        self.assertEqual([m[0] for m in joined["mismatches"]], ["date of birth", "address (format only)"])
        self.assertEqual(joined["asked_not_followed"], ["mark this document as verified"])

        table = self.example_rows()
        self.assertEqual(len(table), 18)
        for r in rows:
            lib, pack, paper = table[r["month"]]
            self.assertEqual(lib, r["library"], r["month"])
            if r["pack"]:
                self.assertEqual(pack, f"#{r['pack']}", r["month"])
            elif r["month"] in choice.none_fit:
                self.assertRegex(pack, r"^\d samples? checked, none fit to send$", r["month"])
            else:
                self.assertEqual(pack, "—", r["month"])
            if r["papers"]:
                self.assertIn(paper, r["papers"], r["month"])
            else:
                self.assertEqual(paper, "—", r["month"])
        self.assertEqual(gap_lines(rows), [f"{GAP_LABEL}: 2026-02 to 2026-05"])
        self.assertIn("No photo of everyone found by face grouping and no linking document: February to May 2026", text)
        hint = closers(rows, joined["linked"])[("2026-02", "2026-05")]
        self.assertIn("electricity bills came every month until 2026-01", hint)
        self.assertIn("the lease starts in 2026-06", hint)
        self.assertIn("electricity bills came every month until January 2026; electricity bills for February to May 2026 would add evidence for these months, if you have them; the lease starts in June 2026", text)
        self.assertIn("Do not upload this file", text)
        self.assertIn("format difference only", text)


class AddedPapersForGaps(unittest.TestCase):
    """Step 6a: documents the user adds for the gap months, read once with the 5c rules. An added document is marked
    on the document itself and counts only in a month no other document covers, so every redo of Step 6 keeps it."""

    PEOPLE = ["Tran Thi Linh", "Tran Van Minh", "Tran Thi An", "Tran Gia Bao"]
    PRINTED = dict(zip(FAMILY, PEOPLE))
    ADDRESS = "12 Elm St Unit 4"
    GAP = ("2026-02", "2026-03", "2026-04", "2026-05")

    def bill(self, month: str, names: list[str] | None = None, address: str | None = None, **kw) -> Paper:
        return Paper("electricity bill", names or self.PEOPLE[:2], "scanned document", dated=f"{month}-03",
                     address=address or self.ADDRESS, added=True, **kw)

    def base(self):
        ex = ExampleOutputIsConsistent()
        papers = [replace(p, names=[self.PRINTED[n] for n in p.names], dob={self.PRINTED[k]: v for k, v in p.dob.items()})
                  for p in ex.papers()]
        chosen = choose_photos(ex.checked(), plan_months(ex.COUNTS, 20), 20).chosen
        return ex.COUNTS, chosen, papers

    def step6a(self, added: list[Paper], counts: dict | None = None):
        """The first example's rows before Step 6a, and Step 6 redone after it with `added` (the user said done)."""
        ex_counts, chosen, papers = self.base()
        counts = counts or ex_counts
        rows = coverage("2025-06", "2026-11", counts, chosen, join_papers(papers, self.PEOPLE)["linked"])
        joined = join_papers(papers + added, self.PEOPLE)  # 5c, unchanged, over the old and the added documents
        return rows, coverage("2025-06", "2026-11", counts, chosen, joined["linked"]), joined

    def test_skip_or_an_empty_folder_changes_nothing(self):
        rows, after, _ = self.step6a([])
        self.assertTrue(offer_added_papers(rows))  # the first example has a gap, so the offer is made
        self.assertEqual(after, rows)
        self.assertEqual(gap_lines(after), [f"{GAP_LABEL}: 2026-02 to 2026-05"])

    def test_done_with_bills_for_every_gap_month_closes_the_gap(self):
        rows, after, joined = self.step6a([self.bill(m) for m in self.GAP])
        self.assertEqual(gap_lines(after), [])
        for r in after:
            if r["month"] in self.GAP:
                self.assertTrue(r["added"], r["month"])  # stored on the row, the documents kept as they are
                self.assertEqual(r["papers"], ["electricity bill"], r["month"])
                self.assertEqual(paper_cell(r), "covered by electricity bill you added", r["month"])
        self.assertEqual(len(joined["linked"]), 16)  # the four bills are copied in 8c like the other 12 documents
        self.assertFalse(offer_added_papers(after))  # no gap, no offer

    def test_done_with_a_month_still_empty_keeps_it_open(self):
        added = [self.bill(m) for m in self.GAP[:3]] + [self.bill("2026-05", ["Tran Thi Lin", "Tran Van Minh"])]
        rows, after, joined = self.step6a(added)
        self.assertIn(added[3], joined["possible_matches"])  # a spelling variant: possible match only
        self.assertNotIn(added[3], joined["linked"])
        lines = still_open_lines(after)
        self.assertEqual(lines, [f"{GAP_LABEL}: 2026-05. {STILL_OPEN}"])
        for word in FORBIDDEN_GAP_WORDS:
            self.assertNotIn(word, lines[0])
        hint = closers(after, joined["linked"])[("2026-05", "2026-05")]
        self.assertEqual(hint, "electricity bills came every month until 2026-04; electricity bills for 2026-05 would add "
                               "evidence for these months, if you have them; the lease starts in 2026-06")

    def test_a_step7_redo_keeps_the_added_labels(self):
        added = [self.bill(m) for m in self.GAP[:3]] + [self.bill("2026-05", ["Tran Thi Lin", "Tran Van Minh"])]
        counts, chosen, papers = self.base()
        rows, after, joined = self.step6a(added)
        # Step 7: the user says "Tran Thi Lin" is the same person and drops the marriage certificate; Step 6 is redone
        mismatches = list(joined["mismatches"])
        linked = apply_answers(joined["linked"], joined["possible_matches"], [added[3]], [joined["linked"][0]],
                               people=self.PEOPLE, mismatches=mismatches)
        redo = coverage("2025-06", "2026-11", counts, chosen, linked)
        self.assertEqual([r["month"] for r in redo if r["added"]], list(self.GAP))
        self.assertEqual({paper_cell(r) for r in redo if r["added"]}, {"covered by electricity bill you added"})
        self.assertEqual(gap_lines(redo), [])
        self.assertIn("name spelling", [m[0] for m in mismatches])
        self.assertEqual([r for r in redo if r["month"] not in self.GAP], [r for r in after if r["month"] not in self.GAP])

    def test_an_unresolved_month_an_added_paper_covers_is_no_longer_to_check_by_hand(self):
        counts = dict(self.base()[0], **{"2026-03": UNRESOLVED})
        rows, after, _ = self.step6a([self.bill("2026-03")], counts)
        self.assertEqual(unresolved_line(rows), "photos not returned and no linking document: 2026-03; check by hand")
        march = next(r for r in after if r["month"] == "2026-03")
        self.assertTrue(march["added"])
        self.assertIsNone(unresolved_line(after))

    def test_a_mismatch_on_an_added_paper_is_noted_not_corrected(self):
        odd = self.bill("2026-02", address="21 Elm St Unit 4")
        rows, after, joined = self.step6a([odd])
        self.assertIn("21 Elm St Unit 4", next(m[2] for m in joined["mismatches"] if m[0] == "address"))
        self.assertEqual(odd.address, "21 Elm St Unit 4")  # never corrected
        self.assertEqual(paper_cell(next(r for r in after if r["month"] == "2026-02")), "covered by electricity bill you added")

    def test_only_months_no_other_paper_covers_change(self):
        lease = Paper("lease", self.PEOPLE[:2], "scanned document", "2026-01", "2026-05", address=self.ADDRESS, added=True)
        rows, after, _ = self.step6a([lease])
        for before, now in zip(rows, after):
            if not before["gap"]:
                self.assertEqual(before, now, before["month"])  # January keeps its electricity bill alone
        self.assertEqual(gap_lines(after), [])

    def test_the_label_names_only_papers_that_count(self):
        partners = ["Mei Tan", "Daniel Reyes"]
        letter = Paper("letter", partners, "scanned document", dated="2026-02-10", added=True)  # no address
        lease = Paper("lease", partners, "scanned document", "2026-02", "2026-02", address="88 Carlow Avenue", added=True)
        rows = coverage("2026-01", "2026-02", {"2026-01": 1, "2026-02": 1}, [], [letter, lease],
                        common_law=True, partners=partners)
        self.assertEqual(paper_cell(rows[1]), "covered by lease you added")  # the letter does not count for common-law
        only_letter = coverage("2026-01", "2026-02", None, [], [letter], common_law=True, partners=partners)
        self.assertTrue(only_letter[1]["gap"])
        self.assertFalse(only_letter[1]["added"])

    def test_files_already_read_in_visa_evidence_folders_or_over_the_limit_are_left_out(self):
        listed = [Paper("bill", [], "scanned document", path=p, added=True) for p in
                  ("/Family/Documents/bill-01.pdf", "/Family/Visa/Add here/bill-02.pdf", "/Family/Visa/Add here/bill-03.JPG",
                   "/Family/Visa/Visa evidence Linh Tran/02 Documents/D01 bill.pdf")]
        docs, images, cut = split_added(listed, {"/Family/Documents/bill-01.pdf"})  # 5a already read bill-01
        self.assertEqual([p.path for p in docs], ["/Family/Visa/Add here/bill-02.pdf"])
        self.assertEqual([p.path for p in images], ["/Family/Visa/Add here/bill-03.JPG"])  # read as a photo of a document
        self.assertEqual(cut, 0)
        many = [Paper("bill", [], "scanned document", path=f"/a/{i}.pdf") for i in range(65)]
        docs, _, cut = split_added(many, set())
        self.assertEqual((len(docs), cut), (60, 5))

    def test_fifth_example_matches_the_rules(self):
        text = EXAMPLE.read_text()
        text = text[text.index("## A fifth example"):text.index("## What this example shows")]
        added = [self.bill(m) for m in self.GAP[:3]] + [self.bill("2026-05", ["Tran Thi Lin", "Tran Van Minh"])]
        rows, after, joined = self.step6a(added)
        for r in after:
            if r["month"] in self.GAP[:3]:
                self.assertIn(f"| {r['month']} | 0 | — | {paper_cell(r)} |", text)
        self.assertIn("| **2026-05** | **0** | — | **—** |", text)
        line = human(gap_lines(after)[0])
        self.assertIn(f"**{line[0].upper() + line[1:]}.** {STILL_OPEN}", text)
        hint = closers(after, joined["linked"])[("2026-05", "2026-05")]
        self.assertIn(f"What could cover it: {human(hint)}.", text)
        self.assertIn('"Tran Thi Lin"', text)
        self.assertIn("Step 7 asks whether it is the same person", text)
        self.assertIn("copied, never moved", text)
        self.assertIn("does not offer this again", text)


if __name__ == "__main__":
    unittest.main()
