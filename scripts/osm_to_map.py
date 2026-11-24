#!/usr/bin/env python3
"""Turn an Overpass (OpenStreetMap) JSON export of the Las Vegas Strip into the
compact map file the planner draws: src/strip-map.json.

Usage: python3 scripts/osm_to_map.py <overpass.json> [out.json]

Coordinates are converted to whole metres on a local plane (x east, y south)
from the bbox's north-west corner, and simplified, so the file stays small.
It also precomputes walking routes along the OSM path network between every
campus venue and from every hotel to every venue.

Map data (c) OpenStreetMap contributors, ODbL.
"""
import heapq
import json
import math
import re
import sys

S, W, N, E = 36.084, -115.188, 36.147, -115.148
LAT0 = (S + N) / 2
MX = 111320 * math.cos(math.radians(LAT0))  # metres per degree lon
MY = 110574                                  # metres per degree lat

# Entrance points used for routing. Keep in sync with VENUES / HOTELS in src/planner.html.
VENUES = {
    "VEN": (36.1219, -115.1668), "WYN": (36.1263, -115.1655), "ENC": (36.1287, -115.1645),
    "CFO": (36.1188, -115.1664), "CPL": (36.1170, -115.1765), "MGM": (36.1045, -115.1650),
}
# OSM building names that make up each venue (highlighted on the map).
VENUE_BUILDINGS = {
    "VEN": ["Venetian Expo"], "WYN": ["Wynn Las Vegas"], "ENC": ["Encore"],
    "CFO": ["Caesars Forum"], "CPL": ["Caesars Palace Hotel and Casino", "Forum Tower"], "MGM": ["MGM Grand Conference Center"],
}
HOTELS = {
    "VEN": (36.1212, -115.1697), "PAL": (36.1240, -115.1688), "WYN": (36.1265, -115.1660), "ENC": (36.1288, -115.1648),
    "TI": (36.1247, -115.1721), "HAR": (36.1196, -115.1714), "LNQ": (36.1176, -115.1708), "FLA": (36.1162, -115.1709),
    "CPL": (36.1162, -115.1745), "HSB": (36.1137, -115.1700), "PAR": (36.1125, -115.1707), "BEL": (36.1126, -115.1767),
    "PH": (36.1100, -115.1716), "COS": (36.1097, -115.1740), "VDA": (36.1093, -115.1780), "ARI": (36.1072, -115.1765),
    "PMG": (36.1025, -115.1765), "NYN": (36.1023, -115.1745), "MGM": (36.1024, -115.1700), "SIG": (36.1010, -115.1640),
    "EXC": (36.0988, -115.1754), "LUX": (36.0955, -115.1761), "MBY": (36.0909, -115.1750), "RW": (36.1340, -115.1660),
    "FTB": (36.1385, -115.1597), "SAH": (36.1420, -115.1565), "WGT": (36.1350, -115.1532),
}

MAJOR = {"motorway", "trunk", "primary", "secondary"}
MOTOR = {"motorway", "motorway_link", "trunk", "trunk_link"}
MINOR = {"tertiary", "residential", "unclassified", "living_street", "primary_link", "secondary_link", "tertiary_link"}
FOOT = {"footway", "pedestrian", "path", "steps", "corridor", "cycleway"}
NOWALK = MOTOR | {"construction", "proposed", "raceway", "bus_guideway", "elevator"}


def xy(lat, lon):
    return ((lon - W) * MX, (N - lat) * MY)


def dp(pts, tol):
    """Douglas-Peucker simplification on a list of (x, y)."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / L if L > 1e-6 else math.hypot(px - ax, py - ay)
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True
            stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def flat(pts):
    out = []
    for x, y in pts:
        out += [round(x), round(y)]
    return out


def area(pts):
    s = 0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def centroid(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def inside(pt, poly):
    x, y = pt
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


def main(src, dst):
    data = json.load(open(src))
    els = data["elements"]
    roads = {"motor": [], "major": [], "minor": [], "service": [], "foot": [], "bridge": []}
    names = {}
    buildings, green, water, parking, rail, stations = [], [], [], [], [], []
    graph = {}
    coords = {}

    def add_edge(a, b, w):
        graph.setdefault(a, []).append((b, w))
        graph.setdefault(b, []).append((a, w))

    for el in els:
        t = el.get("tags", {})
        if el["type"] == "node":
            if t.get("railway") == "station" or t.get("public_transport") == "station":
                if "monorail" in (t.get("station", "") + t.get("name", "").lower() + t.get("network", "").lower()) or t.get("railway") == "station":
                    x, y = xy(el["lat"], el["lon"])
                    stations.append({"n": t.get("name", ""), "x": round(x), "y": round(y)})
            continue
        geoms = []
        if el["type"] == "way" and "geometry" in el:
            geoms = [el["geometry"]]
        elif el["type"] == "relation":
            geoms = [m["geometry"] for m in el.get("members", []) if m.get("role") == "outer" and "geometry" in m]
        for g in geoms:
            pts = [xy(p["lat"], p["lon"]) for p in g if p]
            if len(pts) < 2:
                continue
            hw = t.get("highway")
            if hw:
                if hw in ("construction", "proposed"):
                    continue
                simple = dp(pts, 1.5)
                is_bridge = t.get("bridge") not in (None, "no") and hw in FOOT
                cls = ("bridge" if is_bridge else "motor" if hw in MOTOR else "major" if hw in MAJOR else
                       "minor" if hw in MINOR else "foot" if hw in FOOT or t.get("footway") else "service")
                roads[cls].append(flat(simple))
                nm = t.get("name")
                if nm and cls in ("major", "minor", "motor"):
                    L = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
                    names.setdefault(nm, []).append((L, pts))
                if hw not in NOWALK and t.get("access") not in ("no", "private") and t.get("foot") != "no" and el["type"] == "way":
                    ids = el.get("nodes", [])
                    for i in range(len(ids) - 1):
                        a, b = ids[i], ids[i + 1]
                        coords[a], coords[b] = pts[i], pts[i + 1]
                        add_edge(a, b, math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
                continue
            if t.get("railway") in ("monorail", "tram", "light_rail"):
                rail.append(flat(dp(pts, 1.5)))
                continue
            if len(pts) < 4:
                continue
            ring = dp(pts, 1.2)
            if len(ring) < 4:
                continue
            A = area(ring)
            if "building" in t:
                if A < 120:
                    continue
                buildings.append({"p": flat(ring[:-1] if ring[0] == ring[-1] else ring), "a": round(A),
                                  "n": t.get("name") or None, "_ring": ring})
            elif t.get("natural") == "water":
                water.append(flat(ring))
            elif t.get("leisure"):
                green.append(flat(ring))
            elif t.get("amenity") == "parking" and A > 4000:
                parking.append(flat(ring))

    # mark campus venue buildings: by name, plus the building containing the venue point
    for key, (lat, lon) in VENUES.items():
        p = xy(lat, lon)
        for b in buildings:
            if b.get("n") in VENUE_BUILDINGS[key] or (not b.get("v") and b["a"] > 3000 and inside(p, b["_ring"])):
                b["v"] = key
    labels = []
    for b in buildings:
        if b.get("n") and b["a"] > 9000 and not re.search(r"parking|garage", b["n"], re.I):
            cx, cy = centroid(b["_ring"])
            labels.append({"n": b["n"], "x": round(cx), "y": round(cy), "a": b["a"]})
        del b["_ring"]

    street_labels = []
    for nm, segs in names.items():
        L, pts = max(segs, key=lambda s: s[0])
        if L < 250:
            continue
        mid = len(pts) // 2
        (x1, y1), (x2, y2) = pts[max(0, mid - 1)], pts[min(len(pts) - 1, mid + 1)]
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        if ang > 90:
            ang -= 180
        if ang < -90:
            ang += 180
        street_labels.append({"n": nm, "x": round(pts[mid][0]), "y": round(pts[mid][1]), "r": round(ang), "L": round(L)})

    # walking routes
    # route only on the largest connected part of the network (skips isolated parking aisles)
    seen, best = set(), set()
    for start in coords:
        if start in seen:
            continue
        comp, stack = {start}, [start]
        while stack:
            u = stack.pop()
            for v, _ in graph.get(u, ()):
                if v not in comp:
                    comp.add(v)
                    stack.append(v)
        seen |= comp
        if len(comp) > len(best):
            best = comp
    node_list = [(n, coords[n]) for n in best]

    def nearest(p):
        return min(node_list, key=lambda kv: (kv[1][0] - p[0]) ** 2 + (kv[1][1] - p[1]) ** 2)

    def dijkstra(src):
        dist = {src: 0}
        prev = {}
        pq = [(0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, 1e18):
                continue
            for v, w in graph.get(u, ()):
                nd = d + w
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        return dist, prev

    def path_to(prev, src, dst):
        out = [dst]
        while out[-1] != src:
            if out[-1] not in prev:
                return None
            out.append(prev[out[-1]])
        return out[::-1]

    routes = {}
    origins = [("v:" + k, VENUES[k]) for k in VENUES] + [("h:" + k, HOTELS[k]) for k in HOTELS]
    targets = {k: nearest(xy(*VENUES[k])) for k in VENUES}
    for okey, (lat, lon) in origins:
        p = xy(lat, lon)
        nid, npt = nearest(p)
        dist, prev = dijkstra(nid)
        for vk, (tid, tpt) in targets.items():
            if okey == "v:" + vk:
                continue
            if okey.startswith("v:") and okey[2:] > vk:
                continue  # venue pairs stored once
            pth = path_to(prev, nid, tid)
            if not pth:
                continue
            pts = [p] + [coords[n] for n in pth] + [xy(*VENUES[vk])]
            L = math.hypot(npt[0] - p[0], npt[1] - p[1]) + dist[tid] + math.hypot(tpt[0] - pts[-1][0], tpt[1] - pts[-1][1])
            routes[okey + ">" + vk] = {"m": round(L), "p": flat(dp(pts, 3))}

    out = {
        "attribution": "Map data © OpenStreetMap contributors (ODbL)",
        "bbox": [S, W, N, E], "mx": round(MX, 3), "my": MY,
        "size": [round((E - W) * MX), round((N - S) * MY)],
        "roads": roads, "buildings": buildings, "labels": labels, "streets": street_labels,
        "green": green, "water": water, "parking": parking, "rail": rail, "stations": stations,
        "routes": routes,
    }
    json.dump(out, open(dst, "w"), separators=(",", ":"))
    print("buildings", len(buildings), "labels", len(labels), "roads", {k: len(v) for k, v in roads.items()},
          "rail", len(rail), "stations", len(stations), "routes", len(routes), "graph nodes", len(coords))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "src/strip-map.json")
