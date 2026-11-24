# re:Invent Campus Compass

A one-page planner for AWS re:Invent 2026 (Las Vegas, Nov 30 – Dec 4). It lays out each day's sessions
by **time** (itinerary and day strip) and by **distance** (a map of the Strip), and works out how long each
hop between venues takes.

## What it does

- **Itinerary per day.** Sessions in order, with a travel leg between each pair: walk, badge shuttle,
  monorail and taxi estimates, a recommended mode, and a "leave by" time.
- **Connection check.** Each leg is marked OK, Tight (inside your buffer) or Won't make it (gap shorter than the trip, or sessions overlap).
  Days with problems get a dot in the day bar.
- **Strip map.** The six 2026 campus venues (Venetian, Wynn, Encore, Caesars Forum, Caesars Palace, MGM Grand),
  your hotel, the monorail, and the day's route colored by connection status.
- **Now panel.** During event week it tells you when to leave for your next session.
- **Paste import.** Paste sessions from the catalog (blank line between sessions); it picks out the day, time range, venue, room and title.
- **Export.** Copy a plain-text itinerary, or download an `.ics` file with a reminder at each leave-by time.
- **Venue-to-venue table** and a short guide to each venue.

Travel times are hand-tuned planning estimates that include getting through the casino to the meeting space.
Use the official re:Invent app for live shuttle times.

## Files

- `src/planner.html` is the page source (an HTML fragment, published as a claude.ai Artifact).
- `docs/index.html` is the standalone version for static hosting. Rebuild it with `scripts/build.sh`.

Open `docs/index.html` in a browser to use it locally. Your plan is saved in browser storage.
