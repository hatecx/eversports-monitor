import unittest
from datetime import date

from monitor import qualifies


class CourseFilterTests(unittest.TestCase):
    def setUp(self):
        self.start, self.end = date(2026, 11, 22), date(2026, 12, 12)

    def accepts(self, name, date, time, availability="1/4 spots available"):
        return qualifies(dict(name=name, date=date, time=time, availability=availability), self.start, self.end)

    def test_relevant_classes(self):
        self.assertTrue(self.accepts("Reformer Pilates - Beginner Flow", "Thursday, 10/12/2026", "18:30 ● 60 Min"))
        self.assertTrue(self.accepts("Gingerbread House & Reformer Pilates", "Sunday, 06/12/2026", "16:00 ● 120 Min"))
        self.assertTrue(self.accepts("Movie Night Pilates - Event (Reformer)", "Saturday, 28/11/2026", "16:30 ● 270 Min"))

    def test_not_bookable_or_not_matching(self):
        self.assertFalse(self.accepts("Reformer Pilates - Beginner Flow", "Tuesday, 24/11/2026", "18:00 ● 60 Min", "sold out"))
        self.assertFalse(self.accepts("Reformer Pilates - Beginner Flow", "Saturday, 12/12/2026", "18:30 ● 60 Min"))
        self.assertFalse(self.accepts("Reformer Pilates - Jumpboard", "Sunday, 29/11/2026", "15:40 ● 60 Min"))
        self.assertFalse(self.accepts("Reformer Pilates- First Time", "Tuesday, 01/12/2026", "18:30 ● 60 Min"))
        self.assertFalse(self.accepts("Mat Pilates", "Thursday, 03/12/2026", "19:00 ● 60 Min"))
        self.assertFalse(self.accepts("Reformer Pilates - Beginner Flow", "Thursday, 10/12/2026", "18:30 ● 60 Min", "0/4 spots available"))


if __name__ == "__main__":
    unittest.main()
