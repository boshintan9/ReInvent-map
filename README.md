# re:Invent Campus Compass

A one-page planner for AWS re:Invent 2026 (Las Vegas, Nov 30 – Dec 4). It lays out each day's sessions
by **time** (itinerary and day strip) and by **distance** (a map of the Strip), and works out how long each
hop between venues takes.

## What it does

- **Itinerary per day.** Sessions in order, with a travel leg between each pair: walk, badge shuttle,
  monorail and taxi estimates, a recommended mode, and a "leave by" time.
- **Connection check.** Each leg is marked OK, Tight (inside your buffer) or Won't make it (gap shorter than the trip, or sessions overlap).
  Days with problems get a dot in the day bar.
- **Strip map.** A zoomable map built from OpenStreetMap: building footprints, streets, footpaths, pedestrian
  bridges and the monorail. It highlights the six 2026 campus venues (Venetian, Wynn, Encore, Caesars Forum,
  Caesars Palace, MGM Grand) and your hotel. Walking legs follow real paths and use the real route distance.
- **Now panel.** During event week it tells you when to leave for your next session.
- **Paste import.** Paste sessions from the catalog (blank line between sessions); it picks out the day, time range, venue, room and title.
- **Export.** Copy a plain-text itinerary, or download an `.ics` file with a reminder at each leave-by time.
- **Venue-to-venue table** and a short guide to each venue.

Travel times are hand-tuned planning estimates that include getting through the casino to the meeting space.
Use the official re:Invent app for live shuttle times.

## Files

- `src/planner.html` is the page source (an HTML fragment, published as a claude.ai Artifact).
- `src/strip-map.json` is the map data (OpenStreetMap, simplified, with precomputed walking routes). The page loads it from the same folder.
- `docs/` is the standalone version for static hosting. Rebuild it with `scripts/build.sh`.

### GitHub Pages

`.github/workflows/pages.yml` rebuilds `docs/` from `src/` and deploys it on every push that touches `src/`.
One-time setup: in the repo's **Settings → Pages**, set **Source** to **GitHub Actions**.
The site is public, but each visitor's schedule stays in their own browser.

### Rebuilding the map data

1. Download the area from the OSM API in tiles (`https://api.openstreetmap.org/api/0.6/map?bbox=W,S,E,N`;
   the build used a 5×3 grid over 36.084–36.147 N, 115.188–115.148 W).
2. `python3 scripts/osm_tiles_to_json.py strip.json tiles/*.osm`
3. `python3 scripts/osm_to_map.py strip.json src/strip-map.json`, then `scripts/build.sh`.

Map data © OpenStreetMap contributors, available under the Open Database License (ODbL).

To use it locally, serve the folder over HTTP (for example `python3 -m http.server -d docs`) and open http://localhost:8000. Opened straight from disk, the browser blocks the map data and the page falls back to a simple schematic map. Your plan is saved in browser storage.
