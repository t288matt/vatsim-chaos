#!/usr/bin/env python3
"""
Simple conflict lister - shows conflicts in the requested format
"""

import json
import math

def distance_nm(lat1, lon1, lat2, lon2):
    """Calculate distance between two lat/lon points in nautical miles"""
    R = 3440.065
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_compass_direction(lat1, lon1, lat2, lon2):
    """Get compass direction from point 1 to point 2"""
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Calculate bearing
    bearing = math.degrees(math.atan2(dlon, dlat))
    if bearing < 0:
        bearing += 360
    
    # Convert to 8-point compass
    if 337.5 <= bearing or bearing < 22.5:
        return "N"
    elif 22.5 <= bearing < 67.5:
        return "NE"
    elif 67.5 <= bearing < 112.5:
        return "E"
    elif 112.5 <= bearing < 157.5:
        return "SE"
    elif 157.5 <= bearing < 202.5:
        return "S"
    elif 202.5 <= bearing < 247.5:
        return "SW"
    elif 247.5 <= bearing < 292.5:
        return "W"
    else:  # 292.5 <= bearing < 337.5
        return "NW"

def build_route_waypoints(conflicts):
    """Build a database of waypoints organized by route"""
    route_waypoints = {}
    
    for conflict in conflicts:
        if conflict.get('is_waypoint', True):
            route1 = conflict['flight1']
            route2 = conflict['flight2']
            wp1 = conflict['waypoint1']
            wp2 = conflict['waypoint2']
            lat1, lon1 = conflict['lat1'], conflict['lon1']
            lat2, lon2 = conflict['lat2'], conflict['lon2']
            
            # Add waypoints to their respective routes
            if route1 not in route_waypoints:
                route_waypoints[route1] = {}
            if route2 not in route_waypoints:
                route_waypoints[route2] = {}
            
            route_waypoints[route1][wp1] = (lat1, lon1)
            route_waypoints[route2][wp2] = (lat2, lon2)
    
    return route_waypoints

def find_nearest_waypoint_from_routes(lat, lon, route1, route2, route_waypoints):
    """Find the nearest waypoint from the two routes involved in the conflict"""
    min_distance = float('inf')
    nearest_waypoint = "UNKNOWN"
    
    # Check waypoints from both routes
    for route in [route1, route2]:
        if route in route_waypoints:
            for wp_name, (wp_lat, wp_lon) in route_waypoints[route].items():
                distance = distance_nm(lat, lon, wp_lat, wp_lon)
                if distance < min_distance:
                    min_distance = distance
                    nearest_waypoint = wp_name
    
    return nearest_waypoint, min_distance

def format_location(conflict, all_conflicts):
    """Format location as distance and direction from nearest waypoint"""
    if conflict.get('is_waypoint', True):
        return f"{conflict['waypoint1']}/{conflict['waypoint2']}"
    else:
        # For interpolated conflicts, find nearest waypoint from the two routes
        lat = conflict['lat1']
        lon = conflict['lon1']
        route1 = conflict['flight1']
        route2 = conflict['flight2']
        
        # Build route waypoints database
        route_waypoints = build_route_waypoints(all_conflicts)
        nearest_wp, distance = find_nearest_waypoint_from_routes(lat, lon, route1, route2, route_waypoints)
        
        if nearest_wp != "UNKNOWN":
            # Get waypoint coordinates from the route it belongs to
            wp_lat, wp_lon = None, None
            for route in [route1, route2]:
                if route in route_waypoints and nearest_wp in route_waypoints[route]:
                    wp_lat, wp_lon = route_waypoints[route][nearest_wp]
                    break
            
            if wp_lat is not None and wp_lon is not None:
                direction = get_compass_direction(wp_lat, wp_lon, lat, lon)
                return f"{distance:.1f} nm {direction} of {nearest_wp}"
        
        return f"{lat:.4f},{lon:.4f}"

def main():
    output = []
    try:
        output.append("Loading conflict analysis...")
        print("Loading conflict analysis...")
        with open('temp/conflict_analysis.json', 'r') as f:
            data = json.load(f)
        
        output.append("Data loaded successfully")
        print("Data loaded successfully")
        output.append(f"Keys in data: {list(data.keys())}")
        print(f"Keys in data: {list(data.keys())}")
        
        # Get the scenario data
        scenario = data.get('scenario', {})
        output.append(f"Scenario keys: {list(scenario.keys())}")
        print(f"Scenario keys: {list(scenario.keys())}")
        
        conflicts = scenario.get('actual_conflicts', [])
        output.append(f"Number of conflicts found: {len(conflicts)}")
        print(f"Number of conflicts found: {len(conflicts)}")
        
        output.append("Conflicts Found:")
        output.append("=" * 50)
        print("Conflicts Found:")
        print("=" * 50)
        
        if not conflicts:
            output.append("No conflicts found with current criteria.")
            print("No conflicts found with current criteria.")
            return "\n".join(output)
        
        last_conflict_location = {}
        filtered_conflicts = []
        for conflict in conflicts:
            # Route pair key (order independent)
            route_pair = tuple(sorted([conflict['flight1'], conflict['flight2']]))
            lat = conflict['lat1']
            lon = conflict['lon1']
            prev = last_conflict_location.get(route_pair)
            if prev:
                prev_lat, prev_lon = prev
                if distance_nm(lat, lon, prev_lat, prev_lon) < 4.0:
                    continue  # Skip this conflict, too close to previous
            filtered_conflicts.append(conflict)
            last_conflict_location[route_pair] = (lat, lon)
        output.append("")
        output.append(f"Total Conflicts: {len(filtered_conflicts)}")
        output.append("")
        print()
        print(f"Total Conflicts: {len(filtered_conflicts)}")
        print()
        
        for i, conflict in enumerate(filtered_conflicts, 1):
            conflict_output = []
            conflict_output.append(f"{i}. {conflict['flight1']} & {conflict['flight2']}")
            
            # Show location info using the new format function
            location_str = format_location(conflict, conflicts)
            is_waypoint = conflict.get('is_waypoint', True)
            if is_waypoint:
                conflict_type = "at waypoint"
            else:
                conflict_type = "between waypoints"
                segment1 = conflict.get('segment1', '')
                segment2 = conflict.get('segment2', '')
                if segment1 and segment2:
                    location_str += f" (segments: {segment1}/{segment2})"
            conflict_output.append(f"   Location: {location_str}")
            conflict_output.append(f"   Conflict Type: {conflict_type}")
            conflict_output.append(f"   Distance: {conflict['distance']:.1f} nm")
            conflict_output.append(f"   Altitudes: {conflict['alt1']}/{conflict['alt2']} ft")
            conflict_output.append(f"   Altitude Diff: {conflict['altitude_diff']} ft")
            f1 = conflict.get('flight1_arrival', 'N/A')
            f2 = conflict.get('flight2_arrival', 'N/A')
            try:
                f1_disp = str(int(round(f1))) if isinstance(f1, (int, float)) else str(f1)
                f2_disp = str(int(round(f2))) if isinstance(f2, (int, float)) else str(f2)
            except Exception:
                f1_disp = str(f1)
                f2_disp = str(f2)
            conflict_output.append(f"   Arrival Times: {f1_disp} vs {f2_disp} min")
            # Use new phase fields
            phase1 = conflict.get('stage1', '?')
            phase2 = conflict.get('stage2', '?')
            conflict_output.append(f"   Phase: {phase1}/{phase2}")
            conflict_output.append("")
            
            # Print to terminal
            for line in conflict_output:
                print(line)
            
            # Add to output
            output.extend(conflict_output)
        
        # Departure schedule section removed
        
        # --- Add logic to show routes with no conflicts ---
        all_routes = set(data.get('flight_plans', []))
        routes_with_conflicts = set()
        for conflict in conflicts:
            routes_with_conflicts.add(conflict['flight1'])
            routes_with_conflicts.add(conflict['flight2'])
        routes_without_conflicts = sorted(all_routes - routes_with_conflicts)
        output.append("")
        output.append("The following routes do not have any conflicts:")
        print("")
        print("The following routes do not have any conflicts:")
        if routes_without_conflicts:
            for route in routes_without_conflicts:
                output.append(route)
                print(route)
        else:
            output.append("(All routes have at least one conflict)")
            print("(All routes have at least one conflict)")
        
        return "\n".join(output)
        
    except FileNotFoundError:
        error_msg = "Error: temp/conflict_analysis.json not found. Run conflict_analyzer.py first."
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return error_msg

if __name__ == "__main__":
    output = main()
    with open("conflict_list.txt", "w", encoding="utf-8") as f:
        f.write(output) 