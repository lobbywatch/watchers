import unittest
from namematch import namematcher


class TestNameMatcher(unittest.TestCase):
    def test_empty(self):
        matcher = namematcher.NameMatcher([])
        matches = matcher.match(b'foo')
        self.assertEqual([], matches)

    def test_kope_01(self):
        name = namematcher.Name(1, 'Christian', None, None, 'Köpe', None)
        self.assertMatch(name, 'Köpe, Christian')

    def test_kope_02(self):
        name = namematcher.Name(1, 'Christian', None, None, 'K(?:o|ö)pe', None)
        self.assertMatch(name, 'Köpe, Christian')
        self.assertMatch(name, 'Kope, Christian')

    def test_kope_03(self):
        name = namematcher.Name(1, '(?:Christian|Karoly)', None, None, 'K(?:o|ö)pe', None)
        self.assertMatch(name, 'Kope, Christian')
        self.assertMatch(name, 'Köpe, Christian')
        self.assertMatch(name, 'Kope, Karoly')
        self.assertMatch(name, 'Kope, Karoly Christian')
        self.assertMatch(name, 'Kope, Karoly Christian Dr.')
        self.assertMatch(name, 'Kope, Christian Karoly')

    def test_kope_04(self):
        name = namematcher.Name(1, '(?:Christian|Karoly)', None, None, 'K(?:o|ö)pe', ('Zürich',))
        self.assertFullMatch(name, 'Kope, Karoly Christian Dr., genannt Dr. Köpe Christian, von Zürich')
        self.assertFullMatch(name, 'Köpe, Christian Karoly, da Zurigo')
        self.assertFullMatch(name, 'Köpe, Christian Karoly, de Zurich')

    def test_bellaiche(self):
        name = namematcher.Name(1, 'Judith', None, None, 'Bellaiche', ('Binningen',))
        self.assertFullMatch(name, 'Bellaïche Jäger, Judith, von Binningen')

    def test_wehrli_1004645045(self):
        name = namematcher.Name(1, 'Laurent', None, None, 'Wehrli', ('Montreux', 'Küttigen'))
        self.assertFullMatch(name, 'Wehrli Laurent, de et à Montreux', format='vd')

    @unittest.expectedFailure
    def test_hayoz_1004707520(self):
        name = namematcher.Name(1, 'Jérôme', None, None, 'Hayoz', ('Kleinbösingen',))
        self.assertMatch(name, "Lassausaie Gwenaël, maintenant domicilié à Ville-la-Grand, F, président, et Hayoz Jérôme, jusqu'ici gérants, lesquels continuent de signer individuellement", format='vd')

    def test_feri_1004666922(self):
        name = namematcher.Name(1, 'Yvonne', None, None, 'Feri', ('Hedingen',))
        self.assertMatch(name, "Feri Yvonne, de Hedingen, à Wettingen", format='vd')

    def test_jenny_1004646888(self):
        name = namematcher.Name(1, 'René', None, None, 'Jenny', ('Tentlingen',))
        self.assertMatch(name, "Jenny René, de Tentlingen", format='vd')

    def assertFullMatch(self, name, str, format='std'):
        self.assertMatch(name, str, end=len(str.encode('utf-8')), format=format)

    def assertMatch(self, name, str, end=None, format='std'):
        matcher = namematcher.NameMatcher([name])
        print(str.encode(encoding='utf-8'))
        matches = matcher.match_content(str.encode(encoding='utf-8'), label=None, offset=0, format=format)
        self.assertEqual(1, len(matches))
        self.assertEqual(name, matches[0].name)
        self.assertEqual(0, matches[0].start)
        if end:
            self.assertEqual(end, matches[0].end)

if __name__ == '__main__':
    unittest.main()
