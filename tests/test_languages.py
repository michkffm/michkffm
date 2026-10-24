import unittest
from collections import Counter
from datetime import date
from xml.etree import ElementTree
from scripts.update_languages import collect, shares, chart


class LanguageTests(unittest.TestCase):
    def test_collects_public_originals_and_excludes_profile_forks_and_private(self):
        calls = []
        def fetch(path):
            calls.append(path)
            if '/users/' in path:
                return [{'name': 'michkffm'}, {'name': 'fork', 'fork': True}, {'name': 'secret', 'private': True}, {'name': 'game'}, {'name': 'empty'}]
            return {'JavaScript': 60, 'Python': 40} if '/game/' in path else {}
        totals, count = collect('michkffm', fetch)
        self.assertEqual(totals, {'JavaScript': 60, 'Python': 40})
        self.assertEqual(count, 1)
        self.assertEqual(len(calls), 3)

    def test_reads_all_repository_pages_and_combines_languages(self):
        def fetch(path):
            if '/users/' in path:
                return [{'name': f'repo{i}'} for i in range(100)] if path.endswith('&page=1') else [{'name': 'last'}]
            return {'Python': 10}
        totals, count = collect('michkffm', fetch)
        self.assertEqual(count, 101)
        self.assertEqual(totals['Python'], 1010)

    def test_rejects_partial_invalid_or_missing_data(self):
        with self.assertRaises(ValueError):
            collect('michkffm', lambda _: [])
        with self.assertRaises(ValueError):
            collect('michkffm', lambda path: [{'name': 'game'}] if '/users/' in path else {'Python': -1})
        with self.assertRaises(ConnectionError):
            def fail(path):
                raise ConnectionError('API unavailable')
            collect('michkffm', fail)

    def test_percentages_sum_to_100_and_are_sorted_by_code_size(self):
        rows = shares(Counter({'CSS': 1, 'JavaScript': 1, 'Python': 1}))
        self.assertAlmostEqual(sum(percent for _, _, percent in rows), 100)
        self.assertEqual([row[2] for row in rows], [33.4, 33.3, 33.3])
        self.assertEqual(shares(Counter({'CSS': 10, 'Python': 90}))[0], ('Python', 90, 90))

    def test_svg_is_valid_escaped_and_bilingual(self):
        for language, title in [('de', 'Meine Sprachen im Code'), ('en', 'My languages in code')]:
            svg = chart(Counter({'A&B <test>': 25, 'Python': 75}), 2, date(2026, 10, 24), language)
            root = ElementTree.fromstring(svg)
            self.assertIn(title, svg)
            self.assertIn('A&amp;B &lt;test&gt;', svg)
            self.assertIn('2026-10-24', svg)
            self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
            self.assertNotIn('<script', svg)


if __name__ == '__main__':
    unittest.main()
