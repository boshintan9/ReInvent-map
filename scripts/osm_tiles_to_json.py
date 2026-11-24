#!/usr/bin/env python3
"""Merge OSM API XML tiles (/api/0.6/map) into the Overpass-style JSON that
osm_to_map.py reads (ways/relations with inline geometry, filtered to the
features the map draws).

Usage: python3 scripts/osm_tiles_to_json.py out.json tile1.osm tile2.osm ...
Fetch tiles with: https://api.openstreetmap.org/api/0.6/map?bbox=W,S,E,N
"""
import json
import re
import sys
import xml.etree.ElementTree as ET

KEEP_WAY = [
    lambda t: "highway" in t,
    lambda t: "building" in t,
    lambda t: re.fullmatch(r"monorail|tram|light_rail", t.get("railway", "")),
    lambda t: re.fullmatch(r"park|golf_course|pitch|garden", t.get("leisure", "")),
    lambda t: t.get("natural") == "water",
    lambda t: t.get("amenity") == "parking",
]

nodes, ways, rels = {}, {}, {}
for f in sys.argv[2:]:
    for el in ET.parse(f).getroot():
        tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
        i = int(el.get("id", 0))
        if el.tag == "node":
            nodes[i] = (float(el.get("lat")), float(el.get("lon")), tags)
        elif el.tag == "way":
            ways[i] = ([int(n.get("ref")) for n in el.findall("nd")], tags)
        elif el.tag == "relation":
            rels[i] = ([(m.get("type"), int(m.get("ref")), m.get("role")) for m in el.findall("member")], tags)

out = []
for i, (lat, lon, t) in nodes.items():
    if t.get("railway") == "station" or t.get("public_transport") == "station":
        out.append({"type": "node", "id": i, "lat": lat, "lon": lon, "tags": t})


def geom(refs):
    return [{"lat": nodes[r][0], "lon": nodes[r][1]} if r in nodes else None for r in refs]


for i, (refs, t) in ways.items():
    if any(k(t) for k in KEEP_WAY) and all(r in nodes for r in refs):
        out.append({"type": "way", "id": i, "nodes": refs, "geometry": geom(refs), "tags": t})
for i, (mem, t) in rels.items():
    if "building" in t:
        ms = [{"type": "way", "ref": r, "role": role, "geometry": geom(ways[r][0])}
              for ty, r, role in mem if ty == "way" and r in ways and all(n in nodes for n in ways[r][0])]
        if ms:
            out.append({"type": "relation", "id": i, "members": ms, "tags": t})
json.dump({"elements": out}, open(sys.argv[1], "w"))
print("elements", len(out))
