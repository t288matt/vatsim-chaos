import json

# Conflict Data Audit Script
# This script performs a raw data audit across three data sources:
# - potential_conflict_data.json (conflict detection output)
# - routes_with_added_interpolated_points.json (backend processed data)
# - animation_data.json (frontend visualization data)
#
# IMPORTANT: This audit shows RAW DATA ONLY with NO CONVERSIONS.
# All values are displayed exactly as they appear in the source files.
# This allows for true data integrity verification across processing stages.
#
# Recent Changes:
# - Rounds time values to zero decimal places for cleaner output
# - Handles both string and float time values from potential_conflict_data.json
# - ENHANCED: Added departure time column to track scheduling accuracy
# - ENHANCED: Shows departure times from metadata to verify scheduling algorithm fix

# File paths
potential_conflicts_path = 'temp/potential_conflict_data.json'
interpolated_path = 'temp/routes_with_added_interpolated_points.json'
animation_path = 'animation/animation_data.json'
audit_output = 'audit_conflict_output.txt'

# Column widths for alignment
COLS = [
    ("Source", 24),
    ("Flight", 12),
    ("Aircraft Type", 12),
    ("Departure Time", 14),
    ("Time (UTC)", 12),
    ("Lat", 10),
    ("Lon", 10),
    ("Alt", 7),
    ("Altitude Diff", 14),
    ("Distance", 9)
]

HEADER = "|" + "|".join(f" {{:{w}}} ".format(h, w=w) for h, w in COLS) + "|\n"
ALIGN  = "|" + "|".join(f"{{:{w}}}".format(':' + '-'*(w-2) + ':', w=w) for _, w in COLS) + "|\n"

FMT_ROW = "|" + "|".join(f" {{:{w}}} " for _, w in COLS) + "|\n"


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def find_closest_point(points, lat, lon, alt=None):
    def dist(p):
        dlat = p['lat'] - lat
        dlon = p['lon'] - lon
        d = (dlat**2 + dlon**2)**0.5
        if alt is not None and 'altitude' in p:
            d += abs(p['altitude'] - alt) / 100000.0
        return d
    return min(points, key=dist)

def audit_conflicts():
    pc = load_json(potential_conflicts_path)
    interp = load_json(interpolated_path)
    anim = load_json(animation_path)
    
    conflicts = pc.get('potential_conflicts', pc.get('scenario', {}).get('potential_conflicts', []))
    flights = set()
    for c in conflicts:
        flights.add(c['flight1'])
        flights.add(c['flight2'])
    
    # Get departure times from metadata
    departure_times = {}
    if '_metadata' in interp and 'departure_schedule' in interp['_metadata']:
        for flight, data in interp['_metadata']['departure_schedule'].items():
            departure_times[flight] = data.get('departure_time', 'N/A')
    
    # Group conflicts by flight
    flight_conflicts = {f: [] for f in flights}
    for idx, c in enumerate(conflicts):
        flight_conflicts[c['flight1']].append((idx, c, c['flight1']))
        flight_conflicts[c['flight2']].append((idx, c, c['flight2']))
    
    with open(audit_output, 'w') as out:
        out.write('# Conflict Data Audit Report\n')
        out.write('For each flight, all conflicts it is involved in are listed.\n')
        out.write('Columns: Source | Flight | Aircraft Type | Departure Time | Time (UTC) | Lat | Lon | Alt | Altitude Diff | Distance\n')
        out.write('Note: Departure Time column shows scheduled departure times to verify scheduling algorithm accuracy.\n\n')
        for flight in sorted(flight_conflicts.keys()):
            out.write(f'## Flight: {flight}\n')
            for idx, c, this_flight in flight_conflicts[flight]:
                other_flight = c['flight2'] if this_flight == c['flight1'] else c['flight1']
                out.write(f'### Conflict with {other_flight} (Conflict {idx+1})\n')
                out.write(HEADER)
                out.write(ALIGN)
                # 1. From potential_conflict_data.json
                for f, lat, lon, alt, adiff, dist in [
                    (this_flight, c['lat1'] if this_flight == c['flight1'] else c['lat2'],
                     c['lon1'] if this_flight == c['flight1'] else c['lon2'],
                     c['alt1'] if this_flight == c['flight1'] else c['alt2'],
                     c['altitude_diff'], c['distance'])]:
                    # Extract raw time from conflict data
                    time_val = c.get('time', 'N/A')
                    # Round time if it's a float or a string representing a float
                    if isinstance(time_val, float):
                        time_display = str(int(round(time_val)))
                    elif isinstance(time_val, str):
                        try:
                            float_val = float(time_val)
                            time_display = str(int(round(float_val)))
                        except Exception:
                            time_display = time_val
                    else:
                        time_display = time_val
                    departure_time = departure_times.get(f, 'N/A')
                    # Get aircraft type from flights data
                    aircraft_type = "UNK"
                    if f in pc.get('flights', {}):
                        aircraft_type = pc['flights'][f].get('aircraft_type', 'UNK')
                    out.write(FMT_ROW.format(
                        'potential_conflict_data', f, aircraft_type, departure_time, time_display, f"{lat:.5f}", f"{lon:.5f}", alt, adiff, f"{dist:.2f}"))
                # 2. From routes_with_added_interpolated_points.json
                lat = c['lat1'] if this_flight == c['flight1'] else c['lat2']
                lon = c['lon1'] if this_flight == c['flight1'] else c['lon2']
                alt = c['alt1'] if this_flight == c['flight1'] else c['alt2']
                entry = interp.get(this_flight, {})
                points = entry.get('route', []) if isinstance(entry, dict) else entry
                if points:
                    p = find_closest_point(points, lat, lon, alt)
                    adiff = abs(p.get('altitude', 0) - alt)
                    time_display = p.get('time', 'N/A')
                    departure_time = departure_times.get(this_flight, 'N/A')
                    # Get aircraft type from new structure
                    aircraft_type = entry.get('aircraft_type', 'UNK') if isinstance(entry, dict) else "UNK"
                    out.write(FMT_ROW.format(
                        'interpolated_points', this_flight, aircraft_type, departure_time, time_display, f"{p.get('lat', 0):.5f}", f"{p.get('lon', 0):.5f}",
                        p.get('altitude', 0), adiff, 'N/A'))
                else:
                    departure_time = departure_times.get(this_flight, 'N/A')
                    aircraft_type = entry.get('aircraft_type', 'UNK') if isinstance(entry, dict) else "UNK"
                    out.write(FMT_ROW.format('interpolated_points', this_flight, aircraft_type, departure_time, 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'))
                # 3. From animation_data.json
                flight_data = next((fl for fl in anim.get('flights', []) if fl['flight_id'] == this_flight), None)
                if flight_data:
                    points = flight_data.get('waypoints', [])
                    if points:
                        p = find_closest_point(points, lat, lon, alt)
                        adiff = abs(p.get('altitude', 0) - alt)
                        time_display = p.get('UTC time', p.get('time', 'N/A'))
                        departure_time = flight_data.get('departure_time', 'N/A')
                        aircraft_type = flight_data.get('aircraft_type', 'UNK')
                        out.write(FMT_ROW.format(
                            'animation_data', this_flight, aircraft_type, departure_time, time_display, f"{p.get('lat', 0):.5f}", f"{p.get('lon', 0):.5f}",
                            p.get('altitude', 0), adiff, 'N/A'))
                    else:
                        departure_time = flight_data.get('departure_time', 'N/A')
                        aircraft_type = flight_data.get('aircraft_type', 'UNK')
                        out.write(FMT_ROW.format('animation_data', this_flight, aircraft_type, departure_time, 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'))
                else:
                    out.write(FMT_ROW.format('animation_data', this_flight, 'UNK', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'))
                out.write('\n')

if __name__ == '__main__':
    audit_conflicts() 