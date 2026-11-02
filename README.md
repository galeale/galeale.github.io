# Alessandro Galeazzi — personal website

Static site for GitHub Pages: no build step, plain HTML, CSS and JavaScript.

| Page | File | Data |
|---|---|---|
| Home: bio, network of papers, summaries, contact | `index.html`, `assets/graph.js`, `assets/sections.js` | `data/papers.json`, `data/citations.csv`, `data/teaching.json`, `data/engagement.json`, `data/cycling-summary.json`, `assets/rides-thumb.png` |
| Research (summary + all papers) | `research.html` (`publications.html` redirects here) | `data/papers.json`, `data/citations.csv` |
| Teaching | `teaching.html` | `data/teaching.json` |
| Public engagement | `engagement.html` | `data/engagement.json` |
| Off the desk (cycling heatmap and CO₂) | `cycling.html` | `data/cycling-data.json`, `data/borders.json`, `data/trip-photos.json` |

## Everyday updates

**Your photo.** Save it as `assets/photo.jpg` (portrait, about 600×720 px). Until the file exists the homepage shows your initials.

**Photos of the rides to conferences.** Put the images in `assets/trips/` and list them in `data/trip-photos.json`, by trip:

```json
{
  "c72h2026": [{"src": "assets/trips/c72h2026/andermatt.jpg", "caption": "Day 2, Andermatt"}],
  "netsci2025": [], "netsci2023": [], "cs2ita2025": []
}
```

They appear in the panel that opens when someone clicks a green route on the map. Stage names are worked out by
`scripts/build_trips.py`; fix any of them in its `OVERRIDES`.

**Citations.** Edit `data/citations.csv` (one row per paper: `key,citations,title`). Leave the number empty if you don't
want to show one. They size the nodes of the network on the homepage.

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
pip install fitdecode numpy opencv-python pillow
npm install world-atlas@2.0.2 topojson-client@3.1.0 all-the-cities@3.1.0
python scripts/parse_tracks.py /path/to/strava_export private/tracks.pkl
python scripts/build_cycling.py private/tracks.pkl data/cycling-data.json
node scripts/make_geo.js                       # borders, towns near the rides, private/cities1000.json
python scripts/build_trips.py /path/to/strava_export private/cities1000.json data/cycling-data.json
python scripts/add_food.py /path/to/strava_export/activities.csv data/cycling-data.json
python scripts/make_thumb.py
```

- `build_trips.py` splits the rides to conferences into daily stages (wherever the clock stops for more than 3 hours),
  names each stage after the nearest town (GeoNames) and adds the elevation profiles. Names it cannot guess go in
  `OVERRIDES`.
- `make_geo.js` writes the world outlines (Natural Earth) and `data/places.json`, the towns within about 10 km of a ride;
  the map shows them by population as you zoom in.
- `add_food.py` also writes `data/cycling-summary.json` (the numbers on the homepage); `make_thumb.py` redraws the
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
