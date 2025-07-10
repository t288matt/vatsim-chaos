import json

with open('web_visualization/animation_data.json') as f:
    data = json.load(f)

print('FLIGHT CHECK:')
for flight in data['flights']:
    badwps = [wp for wp in flight.get('waypoints', []) if not (isinstance(wp.get('lat'), (int, float)) and isinstance(wp.get('lon'), (int, float)) and isinstance(wp.get('altitude'), (int, float)))]
    print(f'{flight["flight_id"]}: {len(flight.get("waypoints", []))} waypoints, bad: {len(badwps)}')
    if badwps:
        for wp in badwps:
            print('  Bad waypoint:', wp) 