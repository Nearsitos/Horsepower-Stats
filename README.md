# RaceData: Formula 1 and MotoGP Analytics

RaceData is an interactive Python web application that analyzes Formula 1 and MotoGP race results stored together in one SQLite database. The Streamlit dashboard uses Pandas to answer two questions: Which drivers or riders finish most consistently, and which teams score the most points per race? The app demonstrates filtering, sorting, aggregation, and a Matplotlib graph. It also compares win rates across championships. A command-line version is included in `app.py`.

## Instructions for Build and Use

Steps to build and/or run the software:

1. Install Python 3.12 and Visual Studio Code. Open the project folder in the VS Code PowerShell terminal.
2. Create a virtual environment: `py -3.12 -m venv .venv`
3. Install libraries: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
4. Start the website: `.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py`
5. Open the local website URL displayed in the terminal, usually `http://localhost:8501`.

Instructions for using the software:

1. In the sidebar, expand **Add race data** and import the 2025 season. This needs internet access and may take a while. Alternatively, load the **synthetic sample data** for an offline demo. You can also import from PowerShell with `.\.venv\Scripts\python.exe app.py import-real --season 2025`.
2. Select the championship, season, dataset type, and optionally filter teams and minimum races entered in the sidebar.
3. On **Overview**, see the two required analysis questions and the graph. **Competitors** shows sorted consistency statistics. **Teams & manufacturers** shows aggregated rankings.
4. On **F1 vs MotoGP**, compare competitor win percentages (both championships must be imported for the same year and data type). On **Explore data**, inspect or download the filtered rows.
5. Stop the website with `Ctrl+C` in the terminal. Results persist in `motorsport.db`. To run the original terminal app, use `.\.venv\Scripts\python.exe app.py`.

## Development Environment

To recreate the development environment, you need the following software and/or libraries with the specified versions:

* Python 3.12
* Visual Studio Code with the Python extension
* Pandas 2.x (`pandas>=2.0,<3`)
* Matplotlib 3.x (`matplotlib>=3.7,<4`)
* Streamlit 1.39 or later, below 2 (`streamlit>=1.39,<2`)
* SQLite through Python's built-in `sqlite3` library

## Useful Websites to Learn More

I found these websites useful in developing this software:

* [Pandas Getting Started Tutorials](https://pandas.pydata.org/docs/getting_started/intro_tutorials/)
* [Streamlit Documentation](https://docs.streamlit.io/)
* [Python sqlite3 Documentation](https://docs.python.org/3/library/sqlite3.html)
* [Matplotlib Tutorials](https://matplotlib.org/stable/tutorials/index.html)
* [MotoDB Motorsport Data Repository](https://github.com/vishwapramuditha/moto-db)

## Future Work

The following items I plan to fix, improve, and/or add to this project in the future:

* [ ] Include sprint races and points so the totals better match official season standings.
* [ ] Add head-to-head comparisons for specific drivers or riders.
* [ ] Add more seasons and additional race-by-race trend graphs.
* [ ] Improve handling of missing or changing source datasets.
