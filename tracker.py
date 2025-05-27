#!/usr/bin/env python3
"""
tracker_and_tour_and_path.py

1) Fetch ISS TLE → loop every 5 s → update track.kml.
2) Accumulate positions → on exit:
   • write tour.kml (gx:Tour),
   • write path.kml (LineString),
   • auto-launch Google Earth Pro with all three.
"""

import time
import requests
import atexit
import subprocess
from skyfield.api import load, EarthSatellite, wgs84
import simplekml

TLE_URL = "https://celestrak.com/NORAD/elements/stations.txt"
positions = []  # will hold (lat, lon, alt_km)

def fetch_iss_tle():
    r = requests.get(TLE_URL, timeout=10)
    lines = r.text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("ISS (ZARYA)"):
            return lines[i+1].strip(), lines[i+2].strip()
    raise RuntimeError("ISS TLE not found")

def get_sat_position(line1, line2):
    ts  = load.timescale()
    sat = EarthSatellite(line1, line2, name="ISS", ts=ts)
    t   = ts.now()
    geo = sat.at(t)
    lat, lon   = wgs84.latlon_of(geo)
    alt_km     = wgs84.height_of(geo).km
    return float(lat.degrees), float(lon.degrees), alt_km, t.utc_datetime()

def write_track_kml(lat, lon, alt_km):
    kml = simplekml.Kml()
    p = kml.newpoint(name="ISS", coords=[(lon, lat, alt_km)])
    p.altitudemode = "relativeToGround"
    p.lookat = simplekml.LookAt(
        latitude=lat, longitude=lon, altitude=alt_km,
        range=700_000, tilt=0, heading=0
    )
    nl = kml.newnetworklink(name="ISS Tracker")
    nl.link.href            = "track.kml"
    nl.link.refreshmode     = "onInterval"
    nl.link.refreshinterval = 5
    kml.save("track.kml")

def write_tour_kml():
    kml = simplekml.Kml()
    tr = kml.newgxtour(name="ISS Flight Tour")
    pl = tr.newgxplaylist()
    for lat, lon, alt_km in positions:
        flyto = pl.newgxflyto(gxduration=2.0, gxflytomode="bounce")
        flyto.lookat = simplekml.LookAt(
            latitude=lat, longitude=lon, altitude=alt_km,
            range=700_000, tilt=0, heading=0
        )
        pl.newgxwait(gxduration=1.0)
    kml.save("tour.kml")
    print(f"▶️ Saved tour.kml with {len(positions)} steps.")

def write_path_kml():
    kml = simplekml.Kml()
    ls = kml.newlinestring(name="ISS Path",
        coords=[(lon, lat, alt) for lat, lon, alt in positions]
    )
    ls.altitudemode = "relativeToGround"
    ls.extrude = 1
    ls.tessellate = 1
    kml.save("path.kml")
    print("🛣️ Saved path.kml.")

def launch_earth():
    # On macOS, use the `open` command to launch Google Earth Pro with multiple files.
    subprocess.call([
        "open",
        "-a", "Google Earth Pro",
        "track.kml",
        "tour.kml",
        "path.kml"
    ])
    print("🌍 Launched Google Earth Pro with track.kml, tour.kml, path.kml.")

def main():
    print("Fetching ISS TLE…")
    line1, line2 = fetch_iss_tle()
    print("TLE acquired. Looping—Ctrl+C to stop.\n")

    # Register exit handler
    atexit.register(write_tour_kml)
    atexit.register(write_path_kml)
    atexit.register(launch_earth)

    try:
        while True:
            lat, lon, alt_km, ts = get_sat_position(line1, line2)
            positions.append((lat, lon, alt_km))
            print(f"{ts:%Y-%m-%d %H:%M:%S UTC} → "
                  f"Lat {lat:.4f}°, Lon {lon:.4f}°, Alt {alt_km:.0f} km")
            write_track_kml(lat, lon, alt_km)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Stopping. Generating tour, path, and launching Google Earth…")

if __name__ == "__main__":
    main()
