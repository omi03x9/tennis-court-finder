import unittest
from sources import court, slot
from planner import plan_results, plan_facility


def c(name, *times, facility='テスト施設', city='nagareyama'):
    return court(city, facility, name, [slot(s * 60, e * 60, '空き') for s, e in times])


class PlannerTests(unittest.TestCase):
    def test_continuous_court_wins_even_with_extra_booking(self):
        courts = [c('A', (18, 19)), c('B', (19, 20)), c('C', (17, 21))]
        plan = plan_facility(courts, 18 * 60, 20 * 60)
        self.assertEqual(plan['changes'], 0)
        self.assertEqual(plan['segments'][0]['court'], 'C')
        self.assertEqual(plan['extraMinutes'], 120)

    def test_switching_courts_without_a_gap(self):
        plan = plan_facility([c('A', (18, 19)), c('B', (19, 20))], 18 * 60, 20 * 60)
        self.assertEqual(plan['changes'], 1)
        self.assertEqual([s['court'] for s in plan['segments']], ['A', 'B'])

    def test_gap_does_not_qualify(self):
        self.assertIsNone(plan_facility([c('A', (18, 19)), c('B', (20, 21))], 18 * 60, 21 * 60))

    def test_facilities_cannot_be_combined(self):
        plans = plan_results([{'courts': [c('A', (18, 19), facility='東'), c('B', (19, 20), facility='西')]}], 1080, 1200)
        self.assertEqual(plans, [])

    def test_booking_slots_round_outward(self):
        plan = plan_facility([c('A', (17, 19), (19, 21))], 18 * 60, 20 * 60)
        self.assertEqual(plan['segments'][0]['bookingStart'], '17:00')
        self.assertEqual(plan['segments'][0]['bookingEnd'], '21:00')
        self.assertEqual(plan['extraMinutes'], 120)

    def test_all_continuous_courts_are_returned(self):
        plans = plan_results([{'courts': [c('A', (18, 20)), c('B', (18, 20))]}], 1080, 1200)
        self.assertEqual(len(plans), 1)
        self.assertEqual(len(plans[0]['alternatives']), 1)

    def test_abiko_three_hour_maximum_per_booking(self):
        plan = plan_facility([c('A', (9, 10), (10, 11), (11, 12), (12, 13), city='abiko')], 9 * 60, 13 * 60)
        self.assertEqual(plan['segments'][0]['bookingUnits'], [{'start': '09:00', 'end': '12:00'}, {'start': '12:00', 'end': '13:00'}])

    def test_reserved_slots_are_never_candidates(self):
        reserved = court('nagareyama', 'テスト', 'A', [slot(1080, 1200, '予約あり')])
        self.assertIsNone(plan_facility([reserved], 1080, 1200))


if __name__ == '__main__':
    unittest.main()
