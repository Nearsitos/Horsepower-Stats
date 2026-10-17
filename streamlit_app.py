"""Streamlit website for the Horsepower Stats F1 + MotoGP analysis project.

Run: python -m streamlit run streamlit_app.py
"""
from __future__ import annotations

import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app import DB, connect, get_data, import_real, load_demo, competitor_analysis, team_analysis, manufacturer_analysis

st.set_page_config(page_title="Horsepower Stats | Motorsport Analytics", page_icon="🏁", layout="wide")
st.markdown("""
<style>
    .stApp { background: #0b101a; color: #e8edf7; }
    [data-testid="stSidebar"] { background: #121a28; }
    h1, h2, h3 { letter-spacing: -0.035em; }
    .eyebrow { color: #ef5862; text-transform: uppercase; letter-spacing: .2em;
               font-weight: 800; font-size: .8rem; }
    .subhead { color: #aebad0; margin-top: -.6rem; }
    [data-testid="stMetric"] { background: #172235; border: 1px solid #28364b;
                               border-radius: 12px; padding: 15px 18px; }
    [data-testid="stMetricValue"] { color: #f3f6fc; }
    div.stButton > button[kind="primary"] { background: #d83646; border-color: #d83646; }
</style>
""", unsafe_allow_html=True)


def dataset_catalog() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query("""
            SELECT series, season, data_type, COUNT(DISTINCT race_key) AS races,
                   COUNT(*) AS results
            FROM results GROUP BY series, season, data_type
            ORDER BY season DESC, series, data_type
        """, conn)


def points_figure(frame: pd.DataFrame, series: str, season: int):
    scores = (frame.groupby("competitor")["points"].sum()
              .nlargest(10).sort_values())
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(scores.index, scores.values, color="#ed4657")
    ax.set_title(f"Top competitors by race points — {series} {season}")
    ax.set_xlabel("Main-race points (not official season totals)")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    return fig


def team_figure(teams: pd.DataFrame):
    top = teams.nlargest(10, "points_per_race").sort_values("points_per_race")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(top["team"], top["points_per_race"], color="#5ea7eb")
    ax.set_title("Team performance")
    ax.set_xlabel("Average team points per Grand Prix")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    return fig


def show_fig(fig):
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


st.sidebar.markdown("## 🏁 Horsepower Stats")
st.sidebar.caption("Formula 1 + MotoGP • One SQLite database")

with st.sidebar.expander("Add race data", expanded=False):
    st.caption("Import official-style results from the public MotoDB repository. Internet required.")
    year_to_import = st.number_input("Season to import", min_value=2015, max_value=2026,
                                     value=2025, step=1)
    max_races = st.number_input("Max races per championship (0 = all)",
                                min_value=0, max_value=30, value=0, step=1)
    if st.button("Import real race data", use_container_width=True):
        try:
            with st.spinner("Downloading race results. This can take a while..."):
                with connect() as conn:
                    import_real(conn, int(year_to_import), int(max_races) or None)
            st.success("Import completed. Check the dataset selector below.")
        except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
            st.error(f"Import could not finish: {exc}")
    if st.button("Load sample data (synthetic)", use_container_width=True):
        with connect() as conn:
            load_demo(conn)
        st.success("Practice data loaded. It is NOT real race data.")

catalog = dataset_catalog()
st.markdown('<div class="eyebrow">Motorsport intelligence</div>', unsafe_allow_html=True)
st.title("Horsepower Stats 🏁")
st.markdown('<p class="subhead">Analyze drivers, riders, teams and manufacturers across Formula 1 and MotoGP.</p>', unsafe_allow_html=True)

if catalog.empty:
    st.info("Your database is empty. Open **Add race data** in the sidebar to import a season or load the synthetic demo.")
    st.code(r'.\.venv\Scripts\python.exe app.py import-real --season 2025', language="powershell")
    st.stop()

with st.sidebar:
    st.divider()
    st.subheader("Analysis filters")
    series = st.selectbox("Championship", catalog["series"].unique().tolist())
    subset = catalog[catalog["series"] == series]
    season = st.selectbox("Season", sorted(subset["season"].unique().tolist(), reverse=True))
    subset = subset[subset["season"] == season]
    data_type = st.selectbox("Dataset", sorted(subset["data_type"].unique().tolist()))

with connect() as conn:
    full_df = get_data(conn, series, int(season), data_type)

if full_df.empty:
    st.warning("No results found for this selection.")
    st.stop()

race_count = int(full_df["race_key"].nunique())
with st.sidebar:
    teams = sorted(full_df["team"].dropna().unique().tolist())
    selected_teams = st.multiselect("Teams (optional)", teams, default=[])
    min_starts = st.slider("Minimum races entered", 1, max(1, race_count),
                           min(race_count, max(1, (race_count + 1) // 2)))
    st.caption("Choose no teams to include everyone. Minimum races filters the consistency table.")

df = full_df[full_df["team"].isin(selected_teams)].copy() if selected_teams else full_df.copy()
if df.empty:
    st.warning("No matching data. Clear the team filter.")
    st.stop()

if data_type == "synthetic":
    st.warning("**Synthetic demonstration data** — invented racers and results for offline testing, not real statistics.")
else:
    st.caption("Real-data import • Main Grand Prix races only; sprint races are excluded.")

st.subheader(f"{series} / {season} season overview")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Grand Prix races", f"{df['race_key'].nunique():,}")
m2.metric("Competitors", f"{df['competitor'].nunique():,}")
m3.metric("Teams", f"{df['team'].nunique():,}")
m4.metric("Results", f"{len(df):,}")

competitors = competitor_analysis(df)
competitors = competitors[competitors["starts"] >= min_starts]
team_stats = team_analysis(df)
manufacturer_stats = manufacturer_analysis(df)

overview_tab, competitor_tab, team_tab, compare_tab, raw_tab = st.tabs(
    ["Overview", "Competitors", "Teams & manufacturers", "F1 vs MotoGP", "Explore data"])

with overview_tab:
    st.markdown("### The two analysis questions")
    left, right = st.columns(2)
    with left:
        st.markdown("**1. Who finishes most consistently?**")
        st.caption("Average classified finishing position, sorted lowest first. Unclassified finishes are excluded from the average.")
        if not competitors.empty:
            st.dataframe(competitors[["competitor", "starts", "average_finish", "wins", "podiums"]]
                         .head(8).round(2), hide_index=True, use_container_width=True)
        else:
            st.info("No competitors meet the minimum-races filter.")
    with right:
        st.markdown("**2. Which teams earn the most points per race?**")
        st.caption("Sum of points divided by distinct Grand Prix races, sorted highest first.")
        st.dataframe(team_stats[["team", "races", "total_points", "points_per_race"]]
                     .head(8).round(2), hide_index=True, use_container_width=True)
    st.markdown("### Stretch challenge: visualize the results")
    show_fig(points_figure(df, series, int(season)))

with competitor_tab:
    st.markdown("### Driver / rider consistency rankings")
    st.caption("**Filter:** championship, season, team, minimum starts. **Aggregation:** average finish, wins, podiums, total points. **Sort:** best average finish first.")
    if competitors.empty:
        st.info("Try reducing the minimum races entered.")
    else:
        st.dataframe(competitors.round(2), hide_index=True, use_container_width=True)
        st.download_button("Download competitor rankings (CSV)", competitors.to_csv(index=False),
                           file_name=f"{series.lower().replace(' ', '_')}_{season}_competitors.csv", mime="text/csv")

with team_tab:
    st.markdown("### Team performance")
    st.dataframe(team_stats.round(2), hide_index=True, use_container_width=True)
    show_fig(team_figure(team_stats))
    st.markdown("### Manufacturer / constructor performance")
    st.dataframe(manufacturer_stats.round(2), hide_index=True, use_container_width=True)

with compare_tab:
    st.markdown("### F1 vs MotoGP: win-rate comparison")
    st.caption("Win rate is wins ÷ races entered × 100. Comparing percentages is more meaningful than raw points across different scoring systems.")
    with connect() as conn:
        all_year = get_data(conn, season=int(season), data_type=data_type)
    if all_year["series"].nunique() < 2:
        st.info(f"Both Formula 1 and MotoGP {season} ({data_type}) must be imported to compare them.")
    else:
        rate_stats = (all_year.groupby(["series", "competitor"])
                      .agg(starts=("race_key", "nunique"),
                           wins=("position", lambda x: (x == 1).sum()),
                           podiums=("position", lambda x: x.isin([1, 2, 3]).sum()))
                      .reset_index())
        rate_stats["win_rate_pct"] = 100 * rate_stats["wins"] / rate_stats["starts"]
        rate_stats = (rate_stats.sort_values(["series", "win_rate_pct", "wins"],
                                             ascending=[True, False, False])
                      .groupby("series").head(5))
        st.dataframe(rate_stats.round(2), hide_index=True, use_container_width=True)
        leaders = (rate_stats.sort_values("win_rate_pct", ascending=False)
                   .groupby("series").head(1))
        st.bar_chart(leaders.set_index("series")["win_rate_pct"],
                     x_label="Championship", y_label="Top competitor win rate (%)")

with raw_tab:
    st.markdown("### Explore the underlying race results")
    st.caption("The table below is filtered by your sidebar selections. Use it to verify the source data behind the calculations.")
    st.dataframe(df.sort_values(["race_date", "race_name", "position"],
                                na_position="last"), hide_index=True, use_container_width=True)
    st.download_button("Download filtered results (CSV)", df.to_csv(index=False),
                       file_name=f"Horsepower Stats_{series.lower().replace(' ', '_')}_{season}.csv", mime="text/csv")

st.divider()
st.caption(f"Horsepower Stats • Pandas + SQLite + Matplotlib + Streamlit • Database: {DB.name} • Main-race points only")
