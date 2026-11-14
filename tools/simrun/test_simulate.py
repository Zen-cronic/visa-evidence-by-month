"""The four traced scenarios, run end to end against the mock NAS.

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
        self.assertEqual(sorted(log["summary"]["saved"]), ["album", "folder", "index", "paper copies", "photo copies"])

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
                  User(approve={"folder": False, "album": True, "index": True}))
        self.assertEqual(nas.written, ["album"])
        self.assertEqual(log["summary"]["declined"], ["folder"])
        self.assertIn("index", log["summary"]["not applicable"])

    def test_h_couple_with_one_partner_papers_only_gets_paper_gap_labels(self):
        nas = MockNAS(["Mei Tan"], {}, [], [R.Paper("lease", COUPLE_PRINTED, "scanned document", "2026-01", "2026-06")])
        log = run(COUPLE_PHOTOS, COUPLE_PRINTED, "2025-12", "2026-11", nas, User(papers_only=["Daniel Reyes"]))
        self.assertNotIn(("photo-agent", "timeline-summary"), nas.calls)
        self.assertTrue(log["gaps"])
        self.assertTrue(all(g.startswith(R.PAPER_GAP_LABEL) for g in log["gaps"]))

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
