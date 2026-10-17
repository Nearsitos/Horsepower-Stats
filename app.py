"""Horsepower Stats: F1 + MotoGP race analytics in one SQLite database.

Run:
  python app.py demo
  python app.py import-real --season 2025
  python app.py
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from urllib.request import Request, urlopen
import json
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'motorsport.db'
CHAMPIONSHIPS = ('Formula 1', 'MotoGP')
BASE = 'https://raw.githubusercontent.com/vishwapramuditha/moto-db/main/data'
COLUMNS = ['series', 'season', 'race_key', 'race_name', 'race_date', 'competitor',
           'team', 'manufacturer', 'position', 'points', 'status', 'data_type']


def connect():
    connection = sqlite3.connect(DB)
    connection.execute('''CREATE TABLE IF NOT EXISTS results (
        series TEXT NOT NULL CHECK(series IN ('Formula 1', 'MotoGP')),
        season INTEGER NOT NULL,
        race_key TEXT NOT NULL,
        race_name TEXT NOT NULL,
        race_date TEXT NOT NULL,
        competitor TEXT NOT NULL,
        team TEXT NOT NULL,
        manufacturer TEXT NOT NULL,
        position INTEGER,
        points REAL NOT NULL,
        status TEXT NOT NULL,
        data_type TEXT NOT NULL CHECK(data_type IN ('real', 'synthetic')),
        PRIMARY KEY(series, season, race_key, competitor)
    )''')
    connection.commit()
    return connection


def safe_int(value):
    try:
        number = int(value)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def fetch_json(url):
    request = Request(url, headers={'User-Agent': 'RaceData-Student-Analytics/1.0'})
    with urlopen(request, timeout=18) as response:
        return json.load(response)


def parse_f1(data, year):
    rows = []
    race_key = str(data['round'])
    for entry in data.get('results', []):
        driver = entry.get('Driver') or {}
        constructor = entry.get('Constructor') or {}
        name = ' '.join([driver.get('givenName', ''), driver.get('familyName', '')]).strip()
        if not name:
            continue
        rows.append(('Formula 1', year, race_key, data['raceName'], data['date'], name,
                     constructor.get('name', 'Unknown'), constructor.get('name', 'Unknown'),
                     (safe_int(entry.get('position')) if
                      (str(entry.get('status', '')).lower() == 'finished' or
                       str(entry.get('status', '')).startswith('+')) else None),
                     float(entry.get('points') or 0),
                     str(entry.get('status') or 'Unknown'), 'real'))
    return rows


def parse_motogp(data, year):
    rows = []
    event = data['event']
    race_key = event['short_name']
    for entry in data.get('results', []):
        rider = entry.get('rider') or {}
        name = rider.get('full_name')
        if not name:
            continue
        rows.append(('MotoGP', year, race_key, event['name'],
                     (data.get('session') or {}).get('date', event.get('date_end', ''))[:10],
                     name, (entry.get('team') or {}).get('name', 'Unknown'),
                     (entry.get('constructor') or {}).get('name', 'Unknown'),
                     safe_int(entry.get('position')),
                     float(entry.get('points') or 0),
                     str(entry.get('status') or 'Unknown'), 'real'))
    return rows


def save_rows(connection, rows):
    connection.executemany('''INSERT OR REPLACE INTO results
        (series, season, race_key, race_name, race_date, competitor, team,
         manufacturer, position, points, status, data_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', rows)
    connection.commit()


def import_real(connection, year, limit=None):
    """Import GP race results only (not sprint races) for a selected season."""
    total = 0
    f1_schedule = fetch_json(f'{BASE}/f1/{year}/schedule.json')
    f1_races = f1_schedule.get('races', [])
    if limit is not None:
        f1_races = f1_races[:limit]
    for race in f1_races:
        round_number = race['round']
        try:
            rows = parse_f1(fetch_json(f'{BASE}/f1/{year}/results_{round_number}.json'), year)
            if rows:
                save_rows(connection, rows)
                total += len(rows)
                print(f'F1 round {round_number}: {len(rows)} results')
        except (OSError, ValueError, KeyError) as exc:
            print(f'Skipped F1 round {round_number}: {exc}')

    gp_schedule = fetch_json(f'{BASE}/motogp/{year}/schedule.json')
    events = [e for e in gp_schedule.get('events', [])
              if not e.get('test') and e.get('status') == 'FINISHED'
              and any(s.get('type') == 'RAC' and s.get('category') == 'motogp'
                      for s in e.get('sessions', []))]
    if limit is not None:
        events = events[:limit]
    for event in events:
        code = event.get('short_name')
        if not code:
            continue
        try:
            rows = parse_motogp(fetch_json(f'{BASE}/motogp/{year}/{code}/motogp_RAC.json'), year)
            if rows:
                save_rows(connection, rows)
                total += len(rows)
                print(f'MotoGP {code}: {len(rows)} results')
        except (OSError, ValueError, KeyError) as exc:
            print(f'Skipped MotoGP {code}: {exc}')
    print(f'Import finished: {total} race-result rows loaded or updated.')
    if total == 0:
        print('No results imported. Try another year or use the demo dataset.')


def load_demo(connection):
    """Create an explicitly synthetic dataset for offline testing."""
    sample = {
        'Formula 1': [('Orion Racing', 'Avery Lane', 'Blake Reed'),
                      ('Falcon GP', 'Casey Hart', 'Drew Parker'),
                      ('Nova Motorsport', 'Elliot Stone', 'Finley Ross')],
        'MotoGP': [('Apex Bikes', 'Riley Cruz', 'Jordan Vale'),
                   ('Velocity Racing', 'Morgan Blake', 'Taylor Quinn'),
                   ('Horizon Motors', 'Skyler Dean', 'Alex Rowan')],
    }
    rows = []
    for series, teams in sample.items():
        people = [(team, name) for team, *members in teams for name in members]
        for race in range(1, 7):
            order = sorted(range(6), key=lambda i: ((i * 3 + race * 5 + i * race) % 11, i))
            for pos, index in enumerate(order, start=1):
                team, name = people[index]
                scale = [25, 18, 15, 12, 10, 8][pos - 1] if series == 'Formula 1' else [25, 20, 16, 13, 11, 10][pos - 1]
                rows.append((series, 2025, f'DEMO-{race}', f'Demo Grand Prix {race}',
                             f'2025-0{race}-15', name, team, team, pos, float(scale),
                             'Finished', 'synthetic'))
    # Replace existing synthetic rows; never silently overwrite real results.
    connection.execute("DELETE FROM results WHERE data_type = 'synthetic'")
    save_rows(connection, rows)
    print(f'Loaded {len(rows)} SYNTHETIC practice rows for both championships.')


def get_data(connection, series=None, season=None, data_type=None):
    sql = 'SELECT * FROM results WHERE 1=1'
    args = []
    if series:
        sql += ' AND series = ?'
        args.append(series)
    if season:
        sql += ' AND season = ?'
        args.append(season)
    if data_type:
        sql += ' AND data_type = ?'
        args.append(data_type)
    return pd.read_sql_query(sql, connection, params=args)


def choose_scope(connection):
    available = pd.read_sql_query('''SELECT series, season, data_type,
        COUNT(DISTINCT race_key) AS races, COUNT(*) AS results
        FROM results GROUP BY series, season, data_type
        ORDER BY season DESC, series, data_type''', connection)
    if available.empty:
        print('Database is empty. Run "python app.py import-real --season 2025" or "python app.py demo".')
        return None
    print('\nAvailable datasets:')
    for i, item in available.iterrows():
        print(f"{i+1}. {item['series']} | {item['season']} | {item['data_type']} "
              f"| {item['races']} races | {item['results']} results")
    while True:
        choice = input('Choose a dataset number (or Q to quit): ').strip()
        if choice.lower() == 'q':
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(available):
            row = available.iloc[int(choice)-1]
            return get_data(connection, row['series'], int(row['season']), row['data_type'])
        print('Please choose a valid number.')


def competitor_analysis(df):
    """Question 1: Which competitors have the best race consistency?"""
    # Unclassified positions (DNF/DNS) are excluded from mean finish but counted in starts.
    grouped = df.groupby('competitor').agg(
        starts=('race_key', 'nunique'),
        classified_finishes=('position', 'count'),
        average_finish=('position', 'mean'),
        wins=('position', lambda x: (x == 1).sum()),
        podiums=('position', lambda x: x.isin([1, 2, 3]).sum()),
        total_points=('points', 'sum'),
    ).reset_index()
    grouped['podium_rate_pct'] = grouped['podiums'] / grouped['starts'] * 100
    # Filter out drivers/riders with very few starts for fairer comparisons.
    min_starts = max(1, (df['race_key'].nunique() + 1) // 2)
    filtered = grouped[grouped['starts'] >= min_starts]
    return filtered.sort_values(['average_finish', 'total_points'], ascending=[True, False])


def team_analysis(df):
    """Question 2: Which teams score the most points per Grand Prix?"""
    grouped = df.groupby('team').agg(
        total_points=('points', 'sum'),
        races=('race_key', 'nunique'),
        podiums=('position', lambda x: x.isin([1, 2, 3]).sum()),
    ).reset_index()
    grouped['points_per_race'] = grouped['total_points'] / grouped['races']
    return grouped.sort_values('points_per_race', ascending=False)


def manufacturer_analysis(df):
    """Bonus: Compare MotoGP motorcycle manufacturers (or F1 constructors)."""
    grouped = df.groupby('manufacturer').agg(
        points=('points', 'sum'), races=('race_key', 'nunique'),
        wins=('position', lambda x: (x == 1).sum())
    ).reset_index()
    grouped['points_per_race'] = grouped['points'] / grouped['races']
    return grouped.sort_values('points_per_race', ascending=False)


def print_table(df, columns, max_rows=15):
    if df.empty:
        print('No matching results.')
    else:
        print(df[columns].head(max_rows).round(2).to_string(index=False))


def plot_points(df):
    import matplotlib.pyplot as plt
    scores = df.groupby('competitor')['points'].sum().nlargest(10).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    scores.plot(kind='barh', ax=ax)
    ax.set_title(f"Top 10 by race points: {df['series'].iloc[0]} {df['season'].iloc[0]}")
    ax.set_xlabel('Points from main races only')
    ax.set_ylabel('Competitor')
    fig.tight_layout()
    output = ROOT / f"chart_{df['series'].iloc[0].lower().replace(' ', '_')}_{df['season'].iloc[0]}_{df['data_type'].iloc[0]}.png"
    fig.savefig(output, dpi=150)
    print(f'Graph saved to: {output}')
    plt.show()


def compare_series(connection):
    # Compare rates, not raw point totals (different scoring and number of races).
    df = get_data(connection)
    if df.empty:
        print('No data loaded.')
        return
    for (season, data_type), subset in df.groupby(['season', 'data_type']):
        if subset['series'].nunique() < 2:
            continue
        print(f'\n{season} {data_type.upper()} | race win rates by competitor')
        stats = subset.groupby(['series', 'competitor']).agg(
            starts=('race_key', 'nunique'),
            wins=('position', lambda x: (x == 1).sum()),
            podiums=('position', lambda x: x.isin([1, 2, 3]).sum())
        ).reset_index()
        stats['win_rate_pct'] = 100 * stats['wins'] / stats['starts']
        leaders = stats.sort_values(['series', 'win_rate_pct'], ascending=[True, False]).groupby('series').head(3)
        print_table(leaders, ['series', 'competitor', 'starts', 'wins', 'win_rate_pct', 'podiums'])


def interactive(connection):
    while True:
        print('\n=== Horsepower Stats | FORMULA 1 + MOTOGP ===')
        print('1. Analyze a championship / season')
        print('2. Compare F1 and MotoGP win rates')
        print('3. Import real race results')
        print('4. Load synthetic offline demo')
        print('5. Exit')
        option = input('Select: ').strip()
        if option == '1':
            df = choose_scope(connection)
            if df is None or df.empty:
                continue
            print(f"\nAnalyzing {df['series'].iloc[0]} {df['season'].iloc[0]} ({df['data_type'].iloc[0]} data)")
            print('\nQUESTION 1: Which competitors have the most consistent finishes?')
            print('Minimum races entered: half of the loaded races (rounded up).')
            print('Average finish excludes unclassified results; lower is better.')
            print_table(competitor_analysis(df),
                        ['competitor', 'starts', 'classified_finishes', 'average_finish',
                         'wins', 'podiums', 'podium_rate_pct', 'total_points'])
            print('\nQUESTION 2: Which teams earn the most points per race?')
            print_table(team_analysis(df), ['team', 'races', 'total_points', 'points_per_race', 'podiums'])
            print('\nBONUS: Manufacturer/constructor rankings')
            print_table(manufacturer_analysis(df), ['manufacturer', 'races', 'points', 'points_per_race', 'wins'])
            if input('\nGenerate the stretch-challenge graph? (y/n): ').strip().lower() == 'y':
                plot_points(df)
        elif option == '2':
            compare_series(connection)
        elif option == '3':
            value = input('Season (e.g., 2025): ').strip()
            if value.isdigit() and 1950 <= int(value) <= 2100:
                try:
                    import_real(connection, int(value))
                except (OSError, ValueError, KeyError) as exc:
                    print(f'Unable to download schedule: {exc}')
            else:
                print('Enter a valid season.')
        elif option == '4':
            load_demo(connection)
        elif option == '5':
            break
        else:
            print('Invalid option.')


def main():
    parser = argparse.ArgumentParser(description='F1 and MotoGP Data Analysis')
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('demo', help='Load synthetic offline practice data')
    imp = sub.add_parser('import-real', help='Download and import real F1 and MotoGP data')
    imp.add_argument('--season', type=int, default=2025)
    imp.add_argument('--max-races', type=int, default=None, help='Limit races per series for quick testing')
    args = parser.parse_args()
    with connect() as connection:
        if args.command == 'demo':
            load_demo(connection)
        elif args.command == 'import-real':
            try:
                import_real(connection, args.season, args.max_races)
            except (OSError, ValueError, KeyError) as exc:
                print(f'Download failed: {exc}')
                sys.exit(1)
        else:
            interactive(connection)


if __name__ == '__main__':
    main()
