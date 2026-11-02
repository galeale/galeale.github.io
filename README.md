# Alessandro Galeazzi — personal website

Static site for GitHub Pages: no build step, plain HTML, CSS and JavaScript.

| Page | File | Data |
|---|---|---|
| Home: bio, network of papers, summaries, contact | `index.html`, `assets/graph.js`, `assets/sections.js` | `data/papers.json`, `data/citations.csv`, `data/teaching.json`, `data/engagement.json`, `data/cycling-summary.json`, `assets/rides-thumb.png` |
| Publications | `publications.html` | `data/papers.json`, `data/citations.csv` |
| Teaching | `teaching.html` | `data/teaching.json` |
| Public engagement | `engagement.html` | `data/engagement.json` |
| Off the desk (cycling heatmap and CO₂) | `cycling.html` | `data/cycling-data.json` |

## Everyday updates

**Citations.** Edit `data/citations.csv` (one row per paper: `key,citations,title`). Leave the number empty if you don't
want to show one. Node sizes and the publications page update on the next page load.

**Public engagement.** Add entries to `data/engagement.json`. `group` is `talks`, `press` or `policy`; `url` is optional
and turns the title into a link. The section and its menu link stay hidden while the list is empty.

```json
{"group": "talks", "date": "2026", "title": "Chi ha paura di ChatGPT?", "where": "Science4All, Padova", "url": "https://..."}
```

**Teaching.** One entry per course in `data/teaching.json`; add the new academic year to `years`.

**Contact.** The email address is written in the "Get in touch" section of `index.html`.

**A new paper.** Add it to `data/publications.bib`, give it a theme in `THEME` in `scripts/build_papers.py`
(if it is the published version of a preprint, also add `"preprint_key": "published_key"` to `MERGE`), then run

```bash
python scripts/build_papers.py
```

and add its row to `data/citations.csv`.

## Rebuilding the cycling data

The Strava export and the home location never go in the repository (`private/` is git-ignored).

1. Download the archive from Strava (Settings → My Account → Download or delete your account) and unzip it outside the repo.
2. Create `private/config.json` with approximate coordinates of home and work:
   `{"home_guess": [lat, lon], "work_guess": [45.411, 11.887]}`
3. Run, from the repository root:

```bash
pip install fitdecode
python scripts/parse_tracks.py /path/to/strava_export private/tracks.pkl
python scripts/build_cycling.py private/tracks.pkl data/cycling-data.json
python scripts/add_food.py /path/to/strava_export/activities.csv data/cycling-data.json
pip install numpy opencv-python pillow
python scripts/make_thumb.py
```

`add_food.py` also writes `data/cycling-summary.json` (the numbers on the homepage); `make_thumb.py` redraws the
homepage heatmap image.

New conference trips go in `CONF` in `scripts/build_cycling.py` (their ride names must contain "biking"), and their
EcoPassenger figures in `ECO` in `scripts/add_food.py`.

Privacy: the first and last 2–3 km of every ride are cut (random per ride) and every point within 2.5 km of home is dropped.

## Method for the CO₂ figures

- Train, car and plane: [EcoPassenger](https://ecopassenger.org/) (UIC, ifeu), per passenger, car driven alone,
  flights with the climate factor and the drive to and from the airport, rail on the national electricity mix.
- Bike: only the food beyond a normal training day; zero for commuting. Extra calories are valued as an equal mix of
  wheat, cane sugar and beet sugar ([Poore & Nemecek 2018](https://ourworldindata.org/grapher/ghg-kcal-poore)).

## Local preview

```bash
python -m http.server 8000   # then open http://localhost:8000
```

Pages load their data with `fetch`, so opening the HTML files directly from disk does not work.
