import unittest
from namematch import namematcher


class TestNameMatcher(unittest.TestCase):
    def test_empty(self):
        matcher = namematcher.NameMatcher([])
        matches = matcher.match('foo')
        self.assertEqual([], matches)

    def test_kope_01(self):
        name = namematcher.Name(1, 'Christian', None, None, 'Köpe', [])
        self.assertMatch(name, 'Köpe, Christian')

    def test_kope_02(self):
        name = namematcher.Name(1, 'Christian', None, None, 'K[oö]pe', [])
        self.assertMatch(name, 'Köpe, Christian')
        self.assertMatch(name, 'Kope, Christian')

    def test_kope_03(self):
        name = namematcher.Name(1, '(?:Christian|Karoly)', None, None, 'K[oö]pe', [])
        self.assertMatch(name, 'Köpe, Christian')
        self.assertMatch(name, 'Kope, Christian')
        self.assertMatch(name, 'Kope, Karoly')
        self.assertMatch(name, 'Kope, Karoly Christian')
        self.assertMatch(name, 'Kope, Karoly Christian Dr.')
        self.assertMatch(name, 'Kope, Christian Karoly')

    def test_kope_04(self):
        name = namematcher.Name(1, '(?:Christian|Karoly)', None, None, 'K[oö]pe', ['Zürich'])
        self.assertFullMatch(name, 'Kope, Karoly Christian Dr., genannt Dr. Köpe Christian, von Zürich')
        self.assertFullMatch(name, 'Köpe, Christian Karoly, da Zurigo')
        self.assertFullMatch(name, 'Köpe, Christian Karoly, de Zurich')

    def assertFullMatch(self, name, str):
        self.assertMatch(name, str, end=len(str))

    def assertMatch(self, name, str, end=None):
        matcher = namematcher.NameMatcher([name])
        matches = matcher.match(str)
        self.assertEqual(1, len(matches))
        self.assertEqual(name, matches[0].name)
        self.assertEqual(0, matches[0].start)
        if end:
            self.assertEqual(end, matches[0].end)

if __name__ == '__main__':
    unittest.main()
