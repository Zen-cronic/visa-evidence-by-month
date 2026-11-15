"""The traced scenarios, run end to end against the mock NAS.

Run from the repository root:  python3 -m unittest discover -s tools/simrun -v
"""

import unittest

from simulate import MockNAS, User, run, R

COUPLE_PHOTOS = ["Mei Tan", "Daniel Reyes"]
COUPLE_PRINTED = ["Mei Tan", "Daniel Reyes"]
FAMILY = ["Linh Tran", "Minh Tran", "An Tran", "Bao Tran"]
FAMILY_PRINTED = ["Tran Thi Linh", "Tran Van Minh", "Tran Thi An", "Tran Gia Bao"]


def months(start, end, n=2, skip=()):
    return {m: (0 if m in skip else n) for m in R.month_range(start, end)}


def samples(counts):
    return [R.Checked(f"{m}.jpg", m, f"{m}-10", None) for m, n in counts.items() if n]


class Scenarios(unittest.TestCase):
    def test_a_couple_everything_works(self):
        counts = months("2025-12", "2026-11", skip={"2026-03"})
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts),
                      [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2025-12", "2026-11")])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-11", nas, User())
        self.assertIsNone(log["stopped"])
        self.assertEqual(log["writes_before_approval"], [])
        self.assertEqual(log["chosen"], 11)
        self.assertEqual(log["gaps"], [])  # the lease covers March
        self.assertEqual(sorted(log["summary"]["saved"]), ["album", "descriptions", "folder", "index", "paper copies", "photo copies"])

    def test_b_family_with_a_papers_only_baby(self):
        counts = months("2025-06", "2026-11", skip={"2026-02", "2026-03", "2026-04", "2026-05"})
        papers = ([R.Paper("birth certificate", FAMILY_PRINTED[:2] + ["Tran Gia Bao"], "from a photo of a document", dated="2025-08-20")]
                  + [R.Paper("electricity bill", FAMILY_PRINTED[:2], "scanned document", dated=f"{m}-01")
                     for m in R.month_range("2025-06", "2026-01")])
        nas = MockNAS(FAMILY[:3], counts, samples(counts), papers)  # Bao has no face group
        log = run(FAMILY, FAMILY_PRINTED, "2025-06", "2026-11", nas, User(papers_only=["Bao Tran"]))
        self.assertIsNone(log["stopped"])  # Step 1 does not ask about Bao again
        self.assertEqual(log["gaps"], [f"{R.GAP_LABEL}: 2026-02 to 2026-05"])
        self.assertEqual(log["linked"], 9)

    def test_b2_family_without_marking_the_baby_waits(self):
        counts = months("2025-06", "2026-11")
        nas = MockNAS(FAMILY[:3], counts, samples(counts), [])
        log = run(FAMILY, FAMILY_PRINTED, "2025-06", "2026-11", nas, User())
        self.assertEqual(log["stopped"], "step 1: waiting for Bao Tran")
        self.assertEqual(nas.written, [])

    def test_c_one_person_second_run(self):
        me, printed = ["Siti Rahman"], ["Siti binti Rahman"]
        papers = [R.Paper("bank statement", printed, "scanned document", dated="2025-12-31"),
                  R.Paper("lease", printed, "scanned document", "2026-04", "2027-03")]
        nas = MockNAS([], None, [], papers, existing=["Visa evidence Siti Rahman"])
        log = run(me, printed, "2025-12", "2026-11", nas, User())
        self.assertIsNone(log["stopped"])
        self.assertNotIn(("photo-agent", "timeline-summary"), nas.calls)  # no photo steps for one person
        self.assertEqual(log["folder_name"], "Visa evidence Siti Rahman 2026-11-14")
        self.assertEqual(log["gaps"], [f"{R.PAPER_GAP_LABEL}: 2026-01 to 2026-03"])
        self.assertNotIn("album", log["summary"]["saved"] + log["summary"]["declined"])

    def test_d_couple_photo_search_fails_and_album_declined(self):
        nas = MockNAS(COUPLE_PHOTOS, None, [],
                      [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-06")])
        user = User(approve={"folder": True, "album": False, "index": True})
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-11", nas, user)
        self.assertIsNone(log["stopped"])
        self.assertTrue(all("photo search failed" in g for g in log["gaps"]))
        self.assertNotIn("face grouping", " ".join(log["gaps"]))
        self.assertNotIn("album", nas.written)
        self.assertEqual(sorted(log["summary"]["saved"]), ["folder", "index", "paper copies"])

    def test_e_declined_folder_keeps_the_album(self):
        counts = months("2025-12", "2026-11")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2025-12", "2026-11")])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-11", nas,
                  User(approve={"folder": False, "album": True, "index": True, "descriptions": True}))
        self.assertEqual(nas.written, ["album"])
        self.assertEqual(log["summary"]["declined"], ["folder"])
        self.assertIn("index", log["summary"]["not applicable"])
        self.assertIn("descriptions", log["summary"]["not applicable"])

    def test_h_couple_with_one_partner_papers_only_gets_paper_gap_labels(self):
        nas = MockNAS(["Mei Tan"], {}, [], [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-06")])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-11", nas, User(papers_only=["Daniel Reyes"]))
        self.assertNotIn(("photo-agent", "timeline-summary"), nas.calls)
        self.assertTrue(log["gaps"])
        self.assertTrue(all(g.startswith(R.PAPER_GAP_LABEL) for g in log["gaps"]))

    def _second_run(self, earlier, read="completed"):
        counts = months("2025-12", "2026-02")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts),
                      [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2025-12", "2026-02")],
                      existing=["Visa evidence Mei Tan and Daniel Reyes"], earlier_index=earlier, earlier_read=read)
        return nas, run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-02", nas, User())

    def test_i_second_run_reuses_confirmed_lines_for_the_same_photo_only(self):
        earlier = {("2025-12-10", "2025-12.jpg"): ("Our first winter.", "confirmed"),
                   ("2024-12-10", "2025-12.jpg"): ("Other phone, same name.", "confirmed"),
                   ("2026-01-10", "2026-01.jpg"): ("Skating.", "not confirmed")}
        nas, log = self._second_run(earlier)
        self.assertIsNone(log["stopped"])
        self.assertEqual(log["reused"], {("2025-12-10", "2025-12.jpg"): "Our first winter. (from your earlier pack) [confirm]"})
        self.assertEqual(log["folder_name"], "Visa evidence Mei Tan and Daniel Reyes 2026-11-14")

    def test_j_failed_or_cancelled_earlier_read_continues(self):
        for state in ("failed", "cancelled"):
            nas, log = self._second_run({("2025-12-10", "2025-12.jpg"): ("x", "confirmed")}, read=state)
            self.assertIsNone(log["stopped"])
            self.assertEqual(log["reused"], {})
            self.assertIn(state, log["reuse_note"])
            self.assertIn("index", log["summary"]["saved"])

    def test_k_unanswered_possible_match_is_never_linked(self):
        counts = months("2025-12", "2026-02")
        variant = R.Paper("lease", ["Mei Tann", "Daniel Reyes"], "scanned document", "2025-12", "2026-02")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [variant])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-02", nas, User(confirm_matches=False))
        self.assertEqual(log["linked"], 0)
        self.assertNotIn("paper copies", log["summary"]["saved"])

    def test_l_photos_not_needed_skips_photo_steps_and_files(self):
        nas = MockNAS([], months("2025-12", "2026-02"), [], [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2025-12", "2026-01")])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-02", nas, User(photos_needed=False))
        self.assertIsNone(log["stopped"])  # no face groups needed
        self.assertNotIn(("photo-agent", "figure-albums"), nas.calls)
        self.assertNotIn(("photo-agent", "timeline-summary"), nas.calls)
        self.assertEqual(log["gaps"], [f"{R.PAPER_GAP_LABEL}: 2026-02"])
        self.assertNotIn("descriptions", log["summary"]["saved"] + log["summary"]["failed"])

    def test_m_failed_descriptions_save_keeps_the_index(self):
        counts = months("2025-12", "2026-02")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2025-12", "2026-02")],
                      write_results={"descriptions": "failed"})
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-02", nas, User())
        self.assertIn("index", log["summary"]["saved"])
        self.assertEqual(log["summary"]["failed"], ["descriptions"])

    def test_n_common_law_photos_do_not_fill_months(self):
        counts = months("2025-01", "2025-06")  # photos of both every month
        lease = R.Paper("lease", COUPLE_PRINTED, "scanned document", "2025-01", "2025-03", address="88 Carlow Ave")
        statement = R.Paper("bank statement", COUPLE_PRINTED, "scanned document", dated="2025-05-31")  # no shared address
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [lease, statement])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-01", "2025-06", nas, User(relationship="common-law"))
        self.assertIsNone(log["stopped"])
        self.assertEqual(log["gaps"], [f"{R.COMMON_LAW_GAP_LABEL}: 2025-04 to 2025-06"])
        self.assertGreater(log["chosen"], 0)  # photos are still chosen for the pack

    def test_o_four_yes_and_stop_reads_nothing(self):
        nas = MockNAS(COUPLE_PHOTOS, {}, [], [])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-01", "2025-06", nas, User(four_yes=True, continue_if_not_needed=False))
        self.assertIn("at this time", log["notice"])
        self.assertTrue(log["stopped"].startswith("step 0"))
        self.assertEqual(nas.calls, [])

    def test_p_four_yes_and_continue_builds_papers_only(self):
        nas = MockNAS(COUPLE_PHOTOS, months("2025-01", "2025-02"), [], [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2025-01", "2025-02")])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-01", "2025-02", nas, User(four_yes=True))
        self.assertNotIn(("photo-agent", "timeline-summary"), nas.calls)
        self.assertEqual(log["gaps"], [])

    def test_q_common_law_single_name_papers_fill_a_month_and_are_copied(self):
        counts = months("2026-04", "2026-04")
        phone = R.Paper("phone bill", ["Mei Tan"], "scanned document", dated="2026-04-15", address="88 Carlow Ave")
        letter = R.Paper("bank letter", ["Daniel Reyes"], "scanned document", dated="2026-04-20", address="88 Carlow Avenue")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [phone, letter])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-04", "2026-04", nas, User(relationship="common-law"))
        self.assertEqual(log["gaps"], [])
        self.assertEqual(log["same_address_docs"], 2)
        self.assertIn("paper copies", log["summary"]["saved"])

    def test_r_dropped_same_address_paper_is_not_copied_and_month_reopens(self):
        counts = months("2026-04", "2026-04")
        phone = R.Paper("phone bill", ["Mei Tan"], "scanned document", dated="2026-04-15", address="88 Carlow Ave")
        letter = R.Paper("bank letter", ["Daniel Reyes"], "scanned document", dated="2026-04-20", address="88 Carlow Avenue")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [phone, letter])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-04", "2026-04", nas, User(relationship="common-law", drop_papers=[letter]))
        self.assertEqual(log["same_address_docs"], 0)
        self.assertEqual(log["gaps"], [f"{R.COMMON_LAW_GAP_LABEL}: 2026-04"])
        self.assertNotIn("paper copies", log["summary"]["saved"])

    def test_s_joint_lease_is_not_also_a_single_name_paper(self):
        counts = months("2026-01", "2026-01")
        lease = R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-01", address="88 Carlow Ave")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [lease])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-01", nas, User(relationship="common-law"))
        self.assertEqual(log["same_address_docs"], 0)
        self.assertEqual(log["linked"], 1)

    def test_t_common_law_family_partner_and_child_letter_pairs(self):
        counts = months("2026-04", "2026-04")
        benefit = R.Paper("child benefit letter", ["Tran Thi Linh", "Tran Gia Bao"], "scanned document",
                          dated="2026-04-10", address="12 Elm St")
        bill = R.Paper("phone bill", ["Tran Van Minh"], "scanned document", dated="2026-04-18", address="12 Elm Street")
        nas = MockNAS(FAMILY, counts, samples(counts), [benefit, bill])
        log = run(FAMILY, FAMILY_PRINTED, "2026-04", "2026-04", nas, User(relationship="common-law"))
        self.assertEqual(log["gaps"], [])
        self.assertEqual(log["same_address_docs"], 2)

    def test_t2_married_couple_single_name_papers_fill_a_month_and_are_copied(self):
        counts = months("2026-03", "2026-04", skip={"2026-04"})  # no photos in April
        phone = R.Paper("phone bill", ["Mei Tan"], "scanned document", dated="2026-04-15", address="88 Carlow Ave")
        bill = R.Paper("electricity bill", ["Daniel Reyes"], "scanned document", dated="2026-04-20", address="88 Carlow Avenue")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [phone, bill])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-03", "2026-04", nas, User(relationship="married"))
        self.assertIsNone(log["stopped"])
        self.assertEqual(log["linked"], 0)  # neither paper names both
        self.assertEqual(log["gaps"], [])  # March by its photo, April by the same-address pair
        self.assertEqual(log["same_address_docs"], 2)
        self.assertIn("paper copies", log["summary"]["saved"])
        self.assertEqual(log["writes_before_approval"], [])

    def test_u_unanswered_listed_photo_is_held_out_of_the_pack(self):
        counts = months("2026-01", "2026-03")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts),
                      [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-03")])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-03", nas, User(unanswered_photos=["2026-02.jpg"]))
        self.assertEqual(log["chosen"], 2)
        self.assertEqual(log["waiting_for_answer"], ["2026-02.jpg"])
        self.assertEqual(log["gaps"], [])  # the lease still covers February

    def test_v_adults_offer_is_not_repeated_when_the_baby_is_papers_only(self):
        counts = months("2026-01", "2026-03", skip={"2026-02"})
        family3 = FAMILY[:2] + [FAMILY[3]]
        nas = MockNAS(family3, counts, samples(counts),
                      [R.Paper("birth certificate", [FAMILY_PRINTED[0], FAMILY_PRINTED[3]], "scanned document", dated="2026-01-05")])
        log = run(family3, FAMILY_PRINTED[:2] + [FAMILY_PRINTED[3]], "2026-01", "2026-03", nas,
                  User(papers_only=[FAMILY[3]], children=[FAMILY[3]]))
        self.assertEqual(log["adults_offered"], 0)
        self.assertEqual(sum(1 for c in nas.calls if c[1] == "timeline-summary"), 1)

    def test_w_adults_offer_made_once_for_a_family_of_four(self):
        counts = months("2026-01", "2026-03", skip={"2026-02"})
        nas = MockNAS(FAMILY, counts, samples(counts), [])
        log = run(FAMILY, FAMILY_PRINTED, "2026-01", "2026-03", nas, User(children=FAMILY[2:]))
        self.assertEqual(log["adults_offered"], 1)
        self.assertEqual(sum(1 for c in nas.calls if c[1] == "timeline-summary"), 2)

    def test_z_family_of_four_choosing_the_couple_searches_two_people(self):
        counts = months("2026-01", "2026-03", skip={"2026-02"})
        papers = [R.Paper("birth certificate", FAMILY_PRINTED[:2] + [FAMILY_PRINTED[2]], "scanned document", dated="2026-01-05"),
                  R.Paper("birth certificate", FAMILY_PRINTED[:2] + [FAMILY_PRINTED[3]], "scanned document", dated="2026-03-09")]
        nas = MockNAS(FAMILY[:2], counts, samples(counts), papers)  # the children have no face groups; not needed
        log = run(FAMILY, FAMILY_PRINTED, "2026-01", "2026-03", nas, User(photo_scope="the couple", children=FAMILY[2:]))
        self.assertIsNone(log["stopped"])  # Step 1 checks only the partners
        self.assertEqual(log["photo_people"], FAMILY[:2])
        self.assertEqual(log["adults_offered"], 0)
        self.assertEqual(sum(1 for c in nas.calls if c[1] == "timeline-summary"), 1)
        self.assertEqual(log["linked"], 2)  # both children's birth certificates still link
        self.assertEqual(log["gaps"], [R.GAP_LABEL.replace("of everyone", "of the couple") + ": 2026-02"])
        self.assertEqual(log["writes_before_approval"], [])

    def test_x_failed_listing_and_taken_name_never_writes_into_the_old_pack(self):
        counts = months("2026-01", "2026-03")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts),
                      [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-03")],
                      existing=["Visa evidence Mei Tan and Daniel Reyes"], list_read="failed")
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-03", nas, User())
        self.assertNotIn(("file-agent", "cpmv"), nas.calls)
        self.assertNotIn("photo copies", log["summary"]["saved"])

    def test_y_accented_printed_names_link_a_paper_and_fill_months(self):
        counts = months("2026-03", "2026-04", skip={"2026-03", "2026-04"})  # no photos at all
        lease = R.Paper("lease", ["TRẦN Thị Linh", "TRẦN Văn Minh"], "scanned document", "2026-03", "2026-04")
        nas = MockNAS(FAMILY[:2], counts, samples(counts), [lease])
        log = run(FAMILY[:2], FAMILY_PRINTED[:2], "2026-03", "2026-04", nas, User())
        self.assertEqual(log["linked"], 1)
        self.assertEqual(log["gaps"], [])

    def test_z2_married_family_couple_photos_with_same_address_pairs_matches_the_example(self):
        people = ["Ayu Lestari", "Rizal Hakim", "Kirana Hakim"]
        counts = {"2026-01": 3, "2026-02": 0, "2026-03": 2, "2026-04": 0, "2026-05": 0, "2026-06": 4}
        addr = "41 Birchmount Road"
        papers = [R.Paper("birth certificate", people, "scanned document", dated="2024-08-12")]
        papers += [R.Paper("phone bill", ["Rizal Hakim"], "scanned document", dated=f"{m}-10", address=addr)
                   for m in ("2026-01", "2026-02", "2026-03", "2026-06")]
        papers += [R.Paper("bank letter", ["Ayu Lestari"], "scanned document", dated=f"{m}-20", address=addr)
                   for m in ("2026-01", "2026-02", "2026-06")]
        nas = MockNAS(people[:2], counts, samples(counts), papers)  # Kirana has no face group
        log = run(people, people, "2026-01", "2026-06", nas,
                  User(relationship="married", photo_scope="the couple", papers_only=[people[2]], children=[people[2]]))
        self.assertIsNone(log["stopped"])
        self.assertEqual(log["photo_people"], people[:2])
        self.assertEqual(log["gaps"], [R.GAP_LABEL.replace("of everyone", "of the couple") + ": 2026-04 to 2026-05"])
        self.assertEqual(log["same_address_docs"], 6)  # Jan, Feb and Jun pairs; March's lone bill is not copied
        self.assertEqual(log["writes_before_approval"], [])

    def test_p2_photographed_print_needs_its_real_date(self):
        counts = months("2026-01", "2026-02")
        smp = samples(counts)
        smp[0].kind = "print"  # January's chosen photo is a photo of an old print
        papers = [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-02")]
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-02", MockNAS(COUPLE_PHOTOS, counts, smp, papers), User())
        self.assertEqual(log["waiting_for_answer"], [smp[0].path])  # held out until dated
        self.assertEqual(log["chosen"], 1)
        smp = samples(counts); smp[0].kind = "print"
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-02", MockNAS(COUPLE_PHOTOS, counts, smp, papers),
                  User(print_dates={smp[0].path: "2015-08-01"}))
        # re-dated to 2015-08-01, outside the 2026-01 to 2026-02 period: it leaves the pack and January has no pack photo
        self.assertEqual(log["waiting_for_answer"], [])
        self.assertEqual(log["chosen"], 1)
        self.assertNotIn("2015-08-01", log["chosen_dates"])
        self.assertEqual(log["pack_months"], ["2026-02"])
        self.assertEqual(smp[0].date, "2026-01-10")  # the NAS sample itself is not changed
        self.assertEqual(smp[0].month, "2026-01")
        # re-dated inside the period: kept under its real date and moved to that month
        counts = months("2026-01", "2026-03", skip={"2026-02"})
        smp = samples(counts); smp[0].kind = "print"
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-03", MockNAS(COUPLE_PHOTOS, counts, smp, papers),
                  User(print_dates={smp[0].path: "2026-02-14"}))
        self.assertEqual(log["chosen"], 2)
        self.assertIn("2026-02-14", log["chosen_dates"])
        self.assertEqual(log["pack_months"], ["2026-02", "2026-03"])

    def test_n2_month_missing_from_the_timeline_is_not_returned_never_a_gap(self):
        counts = months("2026-01", "2026-06")
        # March and May are left out of the timeline reply; the sample call finds May's photos, not March's
        nas = MockNAS(COUPLE_PHOTOS, counts, [c for c in samples(counts) if c.month != "2026-03"], [],
                      timeline_missing=["2026-03", "2026-05"], sample_counts={"2026-05": 2})
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-06", nas, User())
        self.assertIsNone(log["stopped"])
        self.assertIn(("photo-agent", "search-picture"), nas.calls[:nas.calls.index(("photo-agent", "vision-vlm"))])
        self.assertEqual(log["not_returned"], ["2026-03"])
        self.assertEqual(log["library"]["2026-03"], R.NOT_RETURNED)
        self.assertEqual(log["gaps"], [])  # no paper at all, yet March is not a gap
        self.assertIn("2026-05", log["pack_months"])
        self.assertEqual(log["chosen"], 5)

    def test_n2b_empty_month_left_out_of_the_timeline_becomes_a_gap_when_the_sample_call_lists_none(self):
        counts = months("2026-01", "2026-06", skip={"2026-03"})
        # the timeline leaves out its empty months (March) and also May; the sample call lists March as none
        # and returns May's photos; June's empty month is listed by neither call
        counts["2026-06"] = 0
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [],
                      timeline_missing=["2026-03", "2026-05", "2026-06"], sample_counts={"2026-03": 0, "2026-05": 2})
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-06", nas, User())
        self.assertEqual(log["library"]["2026-03"], 0)
        self.assertEqual(log["gaps"], [f"{R.GAP_LABEL}: 2026-03"])  # March is a gap
        self.assertEqual(log["not_returned"], ["2026-06"])  # June stays "not returned", not a gap
        self.assertEqual(log["recovered"], {"2026-05": "at least 2 (sample search)"})
        self.assertIn("2026-05", log["pack_months"])  # the recovered month is planned and checked

    def test_n2c_failed_sample_call_keeps_the_timeline_samples(self):
        counts = months("2026-01", "2026-04")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [], timeline_missing=["2026-04"], sample_fail=True)
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-04", nas, User())
        self.assertEqual(log["not_returned"], ["2026-04"])
        self.assertIsNone(log["chosen_column"])
        self.assertEqual(log["pack_months"], ["2026-01", "2026-02", "2026-03"])  # Steps 3-4 ran on the timeline's samples
        self.assertEqual(log["gaps"], [])
        # no timeline samples and a failed sample call: Steps 3 and 4 are skipped
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [], sample_fail=True, timeline_samples=False)
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-04", nas, User())
        self.assertEqual(log["chosen_column"], "sample search failed")
        self.assertNotIn(("photo-agent", "vision-vlm"), nas.calls)
        self.assertEqual(log["chosen"], 0)
        self.assertEqual(log["writes_before_approval"], [])

    def test_n2d_sample_call_settles_months_the_timeline_left_out(self):
        # (b) the timeline leaves out two empty months (March, April) and one with photos (May);
        # the sample call lists the two as none and returns photos for May
        counts = months("2026-01", "2026-06", skip={"2026-03", "2026-04"})
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [],
                      timeline_missing=["2026-03", "2026-04", "2026-05"],
                      sample_counts={"2026-03": 0, "2026-04": 0, "2026-05": 2})
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-06", nas, User())
        self.assertEqual(nas.calls.count(("photo-agent", "search-picture")), 2)  # the sample call, then 5b
        self.assertEqual(log["not_returned"], [])  # every month the sample call answered left the list
        self.assertEqual((log["library"]["2026-03"], log["library"]["2026-04"]), (0, 0))
        self.assertEqual(log["recovered"], {"2026-05": "at least 2 (sample search)"})
        self.assertEqual(log["gaps"], [f"{R.GAP_LABEL}: 2026-03 to 2026-04"])
        self.assertEqual(log["pack_months"], ["2026-01", "2026-02", "2026-05", "2026-06"])
        self.assertIsNone(log["check_by_hand"])
        self.assertEqual(log["writes_before_approval"], [])

    def test_n2e_failed_sample_call_leaves_the_left_out_months_unresolved(self):
        # (c) as (b), but the sample call fails: the three months are unresolved, never 0 and never gaps
        counts = months("2026-01", "2026-06", skip={"2026-03", "2026-04"})
        lease = R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-05", "2026-05")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [lease],
                      timeline_missing=["2026-03", "2026-04", "2026-05"], sample_fail=True)
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-06", nas, User())
        self.assertEqual(log["not_returned"], ["2026-03", "2026-04", "2026-05"])
        self.assertTrue(all(log["library"][m] == R.UNRESOLVED for m in log["not_returned"]))
        self.assertEqual(log["gaps"], [])
        self.assertEqual(log["pack_months"], ["2026-01", "2026-02", "2026-06"])  # the timeline's samples still checked
        # May has the lease; March and April have no paper and are listed to check by hand
        line = "photos not returned and no linking paper: 2026-03 to 2026-04; check by hand"
        self.assertEqual(log["check_by_hand"], line)
        self.assertIn(line, log["final_summary_lists"])

    def test_n2e2_common_law_unresolved_months_are_gaps_with_no_check_by_hand_line(self):
        # as (c), but common-law: photos never decide a month, so the unresolved months without a same-address paper are gaps
        counts = months("2026-01", "2026-06", skip={"2026-03", "2026-04"})
        lease = R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-02", address="88 Carlow Ave")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [lease],
                      timeline_missing=["2026-03", "2026-04", "2026-05"], sample_fail=True)
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-06", nas, User(relationship="common-law"))
        self.assertEqual(log["gaps"], [f"{R.COMMON_LAW_GAP_LABEL}: 2026-03 to 2026-06"])
        self.assertIsNone(log["check_by_hand"])
        self.assertEqual(log["final_summary_lists"], log["gaps"])

    def test_n2e3_common_law_failed_timeline_uses_the_common_law_label_and_dashes_the_pack(self):
        lease = R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-03", address="88 Carlow Ave")
        nas = MockNAS(COUPLE_PHOTOS, None, [], [lease])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-06", nas, User(relationship="common-law"))
        self.assertIsNone(log["stopped"])
        self.assertEqual(log["gaps"], [f"{R.COMMON_LAW_GAP_LABEL}: 2026-04 to 2026-06"])
        self.assertNotIn("photo search failed", " ".join(log["gaps"]))
        self.assertIsNone(log["check_by_hand"])
        self.assertTrue(all(p is None for p in log["pack"].values()))  # "—" in every month

    def test_n2f_counted_month_without_a_sample_is_never_planned(self):
        # (d) the timeline counts every month but returns no samples; the sample call is sent for each counted
        # month, leaves out March and lists April as none: both keep their counts and have no candidates
        counts = months("2026-01", "2026-05")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [], timeline_samples=False,
                      sample_omit=["2026-03"], sample_counts={"2026-04": 0})
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-05", nas, User())
        self.assertEqual(log["library"]["2026-03"], 2)
        self.assertEqual(log["library"]["2026-04"], 2)
        self.assertEqual(log["not_returned"], [])
        self.assertEqual(log["plan"], ["2026-01", "2026-02", "2026-05"])  # no plan slot spent on them
        self.assertEqual(log["pack"]["2026-03"], R.NO_SAMPLE_LABEL)
        self.assertEqual(log["pack"]["2026-04"], R.NO_SAMPLE_LABEL)
        self.assertEqual(log["none_fit"], [])  # never "0 samples checked, none fit to send"
        self.assertEqual(log["gaps"], [])
        self.assertEqual(log["chosen"], 3)

    def test_n2g_no_results_timeline_makes_every_month_zero_and_paperless_months_gaps(self):
        # the timeline replies "no results" for the whole period; a lease covers February and March only
        counts = months("2026-01", "2026-04")
        lease = R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-02", "2026-03")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [lease], timeline_no_results=True)
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-04", nas, User())
        self.assertIsNone(log["stopped"])
        self.assertEqual(log["no_results_message"],
                         "Photos face grouping found no photo of all these people in this period")
        self.assertEqual(nas.calls.count(("photo-agent", "search-picture")), 1)  # only 5b: no sample call
        self.assertNotIn(("photo-agent", "vision-vlm"), nas.calls)  # Steps 3 and 4 skipped
        self.assertEqual(log["library"], {m: 0 for m in R.month_range("2026-01", "2026-04")})
        self.assertEqual(log["not_returned"], [])
        self.assertEqual(log["gaps"], [f"{R.GAP_LABEL}: 2026-01", f"{R.GAP_LABEL}: 2026-04"])
        self.assertIsNone(log["check_by_hand"])
        self.assertEqual(log["chosen"], 0)
        self.assertEqual(log["writes_before_approval"], [])

    def test_n3_failed_step4_call_is_resent_one_month_per_call(self):
        counts = months("2026-01", "2026-06")
        nas = MockNAS(COUPLE_PHOTOS, counts, samples(counts), [],
                      vision_batch_fail={"2026-02", "2026-03", "2026-04"}, vision_retry_fail={"2026-03"})
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-06", nas, User())
        self.assertEqual(nas.calls.count(("photo-agent", "vision-vlm")), 1 + 3)  # one batch, then one call per month
        self.assertEqual(log["photo_check_failed"], ["2026-03"])
        self.assertEqual(log["none_fit"], [])  # a failed call is not a failed rule
        self.assertEqual(sum(log["failures"].values()), 0)
        self.assertNotIn("2026-03", log["pack_months"])
        self.assertEqual(log["chosen"], 5)

    def test_n4_photo_whose_named_people_miss_a_partner_fails_rule_1(self):
        counts = months("2026-01", "2026-02")
        wrong = R.Checked("2026-01-a.jpg", "2026-01", "2026-01-05", None, people=["Mei Tan"])
        right = R.Checked("2026-01-b.jpg", "2026-01", "2026-01-09", None, people=COUPLE_PHOTOS + ["Sam Lee"])
        feb = R.Checked("2026-02-a.jpg", "2026-02", "2026-02-03", None, people=["Daniel Reyes", "Sam Lee"])
        nas = MockNAS(COUPLE_PHOTOS, counts, [wrong, right, feb], [])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2026-01", "2026-02", nas, User())
        self.assertEqual(log["chosen_dates"], ["2026-01-09"])
        self.assertEqual(log["failures"][1], 2)
        self.assertEqual(log["none_fit"], ["2026-02"])

    def test_f_unsure_about_consent_stops_before_reading(self):
        nas = MockNAS(COUPLE_PHOTOS, {}, [], [])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-11", nas, User(consent="unsure"))
        self.assertEqual(log["stopped"], "step 0")
        self.assertEqual(nas.calls, [])

    def test_g_unsure_about_the_model_continues_only_on_yes(self):
        nas = MockNAS(COUPLE_PHOTOS, {}, [], [])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-11", nas, User(local_model="unsure", continue_if_unsure=False))
        self.assertEqual(log["stopped"], "step 0")
        self.assertEqual(nas.calls, [])


if __name__ == "__main__":
    unittest.main()
