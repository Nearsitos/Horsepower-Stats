"""Run `python -m unittest -v` to verify parsing and Pandas analysis."""
import unittest
import pandas as pd
from app import COLUMNS, parse_f1, parse_motogp, competitor_analysis, team_analysis


class RaceDataTests(unittest.TestCase):
    def test_parse_f1_and_dnf(self):
        data = {'round': '1', 'raceName': 'Example GP', 'date': '2025-01-01', 'results': [
            {'Driver': {'givenName': 'Alex', 'familyName': 'One'},
             'Constructor': {'name': 'Team A'}, 'position': '1', 'points': '25', 'status': 'Finished'},
            {'Driver': {'givenName': 'Sam', 'familyName': 'Two'},
             'Constructor': {'name': 'Team B'}, 'position': '18', 'points': '0', 'status': 'Collision'}]}
        rows = parse_f1(data, 2025)
        self.assertEqual(rows[0][5], 'Alex One')
        self.assertEqual(rows[0][8], 1)
        self.assertIsNone(rows[1][8])

    def test_parse_motogp(self):
        data = {'event': {'short_name': 'EX', 'name': 'Example GP', 'date_end': '2025-01-02'},
                'session': {'date': '2025-01-02T10:00:00Z'},
                'results': [{'rider': {'full_name': 'Rider One'},
                             'team': {'name': 'Team C'}, 'constructor': {'name': 'Maker'},
                             'position': 1, 'points': 25, 'status': 'INSTND'}]}
        rows = parse_motogp(data, 2025)
        self.assertEqual(rows[0][0], 'MotoGP')
        self.assertEqual(rows[0][7], 'Maker')

    def test_analysis_sort_aggregate(self):
        rows = [
            ('Formula 1', 2025, '1', 'GP 1', '2025-01-01', 'Alex', 'A', 'A', 1, 25., 'Finished', 'real'),
            ('Formula 1', 2025, '1', 'GP 1', '2025-01-01', 'Sam', 'B', 'B', 2, 18., 'Finished', 'real'),
            ('Formula 1', 2025, '2', 'GP 2', '2025-01-08', 'Alex', 'A', 'A', 2, 18., 'Finished', 'real'),
            ('Formula 1', 2025, '2', 'GP 2', '2025-01-08', 'Sam', 'B', 'B', 1, 25., 'Finished', 'real'),
        ]
        frame = pd.DataFrame(rows, columns=COLUMNS)
        comp = competitor_analysis(frame)
        self.assertEqual(comp['competitor'].tolist(), ['Alex', 'Sam'])
        self.assertEqual(comp.iloc[0]['average_finish'], 1.5)
        teams = team_analysis(frame)
        self.assertEqual(teams['total_points'].sum(), 86)
        self.assertEqual(teams['points_per_race'].tolist(), [21.5, 21.5])


if __name__ == '__main__':
    unittest.main()
