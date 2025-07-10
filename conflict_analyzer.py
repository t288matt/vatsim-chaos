#!/usr/bin/env python3
"""
Flight Plan Conflict Analyzer for ATC Training
Analyzes multiple flight plans to find crossing points and suggests departure times
to create maximum conflicts for air traffic controller training.
"""

import xml.etree.ElementTree as ET
import os
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import math
from collections import defaultdict

class FlightPlan:
    def __init__(self, origin: str, destination: str, route: str = ""):
        self.origin = origin
        self.destination = destination
        self.route = route
        self.waypoints: List[Waypoint] = []
        self.departure: Optional[Waypoint] = None
        self.arrival: Optional[Waypoint] = None
        
    def add_waypoint(self, waypoint):
        self.waypoints.append(waypoint)
    
    def set_departure(self, waypoint):
        self.departure = waypoint
        
    def set_arrival(self, waypoint):
        self.arrival = waypoint
    
    def get_all_waypoints(self) -> List['Waypoint']:
        """Get all waypoints including departure and arrival"""
        all_wps = []
        if self.departure:
            all_wps.append(self.departure)
        all_wps.extend(self.waypoints)
        if self.arrival:
            all_wps.append(self.arrival)
        return all_wps

class Waypoint:
    def __init__(self, name: str, lat: float, lon: float, altitude: int, 
                 time_total: int = 0, stage: str = "", waypoint_type: str = ""):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.altitude = altitude
        self.time_total = time_total  # Total time in seconds or minutes
        self.stage = stage  # CLB, CRZ, DES
        self.waypoint_type = waypoint_type  # vor, ndb, wpt, etc.
    
    def get_time_formatted(self) -> str:
        """Convert total minutes from departure to elapsed time HH:MM format"""
        # SimBrief XML gives time_total in minutes (e.g., 1359 = 13 minutes 59 seconds)
        total_minutes = self.time_total
        if self.time_total > 10000:  # Heuristic: treat as seconds
            total_minutes = self.time_total // 60
        minutes = total_minutes // 100  # Extract minutes (first 2 digits)
        seconds = total_minutes % 100   # Extract seconds (last 2 digits)
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_time_minutes(self) -> float:
        """Get time in minutes as float"""
        # time_total is in seconds, so convert to minutes
        return self.time_total / 60.0

def abbreviate_waypoint_name(name: str) -> str:
    """Abbreviate common waypoint names for cleaner display"""
    abbreviations = {
        "TOP OF CLIMB": "TOC",
        "TOP OF DESCENT": "TOD"
    }
    return abbreviations.get(name, name)

def parse_waypoint_from_fix(fix_element) -> Optional[Waypoint]:
    """Parse a waypoint from a fix element in the XML"""
    try:
        # Extract basic information
        ident = fix_element.findtext('ident', '')
        long_name = fix_element.findtext('name', ident)
        waypoint_type = fix_element.findtext('type', '')
        stage = fix_element.findtext('stage', '')
        
        # Use short name (ident) if available, otherwise use long name (with abbreviation)
        if ident and ident.strip():
            name = ident.strip()
        else:
            name = abbreviate_waypoint_name(long_name)
        
        # Extract coordinates
        lat_str = fix_element.findtext('pos_lat')
        lon_str = fix_element.findtext('pos_long')
        
        if not lat_str or not lon_str:
            return None
            
        lat = float(lat_str)
        lon = float(lon_str)
        
        # Extract altitude
        alt_str = fix_element.findtext('altitude_feet', '0')
        altitude = int(float(alt_str))
        
        # Extract time (total time in seconds)
        time_str = fix_element.findtext('time_total', '0')
        time_total = int(float(time_str))
        
        return Waypoint(name, lat, lon, altitude, time_total, stage, waypoint_type)
        
    except (ValueError, TypeError) as e:
        print(f"⚠️  Error parsing waypoint {ident}: {e}")
        return None

def parse_airport_info(airport_element) -> Optional[Waypoint]:
    """Parse airport information from origin/destination elements"""
    try:
        icao = airport_element.findtext('icao_code', '')
        long_name = airport_element.findtext('name', icao)
        lat_str = airport_element.findtext('pos_lat')
        lon_str = airport_element.findtext('pos_long')
        elevation_str = airport_element.findtext('elevation', '0')
        
        # Use ICAO code as name if available, otherwise use long name
        if icao and icao.strip():
            name = icao.strip()
        else:
            name = long_name
        
        if not lat_str or not lon_str:
            return None
            
        lat = float(lat_str)
        lon = float(lon_str)
        elevation = int(float(elevation_str))
        
        return Waypoint(name, lat, lon, elevation, 0, "DEP", "airport")
        
    except (ValueError, TypeError) as e:
        print(f"⚠️  Error parsing airport {icao}: {e}")
        return None

def extract_flight_plan_from_xml(xml_file: str) -> Optional[FlightPlan]:
    """Extract flight plan from SimBrief XML file"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Extract basic flight information
        origin_elem = root.find('origin')
        dest_elem = root.find('destination')
        route_elem = root.find('.//route')
        
        origin_code = origin_elem.findtext('icao_code', '') if origin_elem is not None else 'UNKNOWN'
        dest_code = dest_elem.findtext('icao_code', '') if dest_elem is not None else 'UNKNOWN'
        route = route_elem.text if (route_elem is not None and route_elem.text is not None) else ""
        
        flight_plan = FlightPlan(origin_code, dest_code, route)
        
        # Parse departure airport
        if origin_elem is not None:
            departure = parse_airport_info(origin_elem)
            if departure:
                flight_plan.set_departure(departure)
        
        # Parse arrival airport
        if dest_elem is not None:
            arrival = parse_airport_info(dest_elem)
            if arrival:
                flight_plan.set_arrival(arrival)
        
        # Parse main navlog waypoints
        navlog = root.find('navlog')
        if navlog is not None:
            for fix in navlog.findall('fix'):
                waypoint = parse_waypoint_from_fix(fix)
                if waypoint:
                    # Include all waypoints including TOC and TOD for phase determination
                    flight_plan.add_waypoint(waypoint)
        
        return flight_plan
        
    except Exception as e:
        print(f"❌ Error parsing XML file {xml_file}: {e}")
        return None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in nautical miles"""
    R = 3440.065  # Earth radius in nautical miles
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def interpolate_route_segments(waypoints: List[Waypoint]) -> List[Dict]:
    """Interpolate route segments between waypoints to find potential crossing points"""
    segments = []
    
    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i + 1]
        
        # Create interpolation points along this segment
        num_points = 10  # Number of interpolation points
        for j in range(1, num_points):  # Skip first and last points (waypoints)
            t = j / num_points
            
            # Linear interpolation of lat/lon
            lat = wp1.lat + t * (wp2.lat - wp1.lat)
            lon = wp1.lon + t * (wp2.lon - wp1.lon)
            
            # Linear interpolation of altitude
            alt = int(wp1.altitude + t * (wp2.altitude - wp1.altitude))
            
            # Linear interpolation of time
            time = wp1.get_time_minutes() + t * (wp2.get_time_minutes() - wp1.get_time_minutes())
            
            segments.append({
                'lat': lat,
                'lon': lon,
                'altitude': alt,
                'time': time,
                'segment': f"{wp1.name}-{wp2.name}",
                'interpolation_point': j
            })
    
    return segments

def get_phase_for_time(waypoints, time_min):
    """Determine phase (climb, cruise, descent) for a given time in minutes based on TOC/TOD"""
    toc_time = None
    tod_time = None
    for wp in waypoints:
        if wp.name.upper() == 'TOC':
            toc_time = wp.get_time_minutes()
        if wp.name.upper() == 'TOD':
            tod_time = wp.get_time_minutes()
    if toc_time is None:
        toc_time = float('inf')  # If no TOC, treat all as climb
    if tod_time is None:
        tod_time = float('inf')  # If no TOD, treat all as cruise after TOC
    if time_min < toc_time:
        return 'climb'
    elif time_min < tod_time:
        return 'cruise'
    else:
        return 'descent'

def find_crossing_points(flight_plans: List[FlightPlan]) -> List[Dict]:
    """Find potential crossing points between flight plans using refined conflict criteria"""
    crossing_points = []
    
    for i, fp1 in enumerate(flight_plans):
        for j, fp2 in enumerate(flight_plans):
            if i >= j:  # Avoid duplicate comparisons
                continue
                
            waypoints1 = fp1.get_all_waypoints()
            waypoints2 = fp2.get_all_waypoints()
            
            # Check each waypoint pair for conflicts
            for wp1 in waypoints1:
                for wp2 in waypoints2:
                    # Skip TOC and TOD waypoints for conflict detection
                    if wp1.name in ("TOC", "TOD") or wp2.name in ("TOC", "TOD"):
                        continue
                        
                    distance = calculate_distance(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
                    altitude_diff = abs(wp1.altitude - wp2.altitude)
                    
                    # Conflict if: lateral <3NM, vertical <900ft, neither at or below 2500ft
                    if (distance < 3.0 and
                        altitude_diff < 900 and
                        wp1.altitude > 2500 and
                        wp2.altitude > 2500):
                        phase1 = get_phase_for_time(waypoints1, wp1.get_time_minutes())
                        phase2 = get_phase_for_time(waypoints2, wp2.get_time_minutes())
                        crossing_points.append({
                            'flight1': f"{fp1.origin}-{fp1.destination}",
                            'flight2': f"{fp2.origin}-{fp2.destination}",
                            'flight1_idx': i,
                            'flight2_idx': j,
                            'waypoint1': wp1.name,
                            'waypoint2': wp2.name,
                            'lat1': wp1.lat,
                            'lon1': wp1.lon,
                            'lat2': wp2.lat,
                            'lon2': wp2.lon,
                            'alt1': wp1.altitude,
                            'alt2': wp2.altitude,
                            'stage1': phase1,
                            'stage2': phase2,
                            'time1': wp1.get_time_minutes(),
                            'time2': wp2.get_time_minutes(),
                            'distance': distance,
                            'altitude_diff': altitude_diff,
                            'conflict_type': 'enroute',
                            'is_waypoint': True
                        })
            
            # Check interpolated segments for conflicts
            segments1 = interpolate_route_segments(waypoints1)
            segments2 = interpolate_route_segments(waypoints2)
            
            for seg1 in segments1:
                for seg2 in segments2:
                    distance = calculate_distance(seg1['lat'], seg1['lon'], seg2['lat'], seg2['lon'])
                    altitude_diff = abs(seg1['altitude'] - seg2['altitude'])
                    
                    # Conflict if: lateral <3NM, vertical <900ft, neither at or below 2500ft
                    if (distance < 3.0 and
                        altitude_diff < 900 and
                        seg1['altitude'] > 2500 and
                        seg2['altitude'] > 2500):
                        phase1 = get_phase_for_time(waypoints1, seg1['time'])
                        phase2 = get_phase_for_time(waypoints2, seg2['time'])
                        crossing_points.append({
                            'flight1': f"{fp1.origin}-{fp1.destination}",
                            'flight2': f"{fp2.origin}-{fp2.destination}",
                            'flight1_idx': i,
                            'flight2_idx': j,
                            'waypoint1': f"{seg1['lat']:.4f},{seg1['lon']:.4f}",
                            'waypoint2': f"{seg2['lat']:.4f},{seg2['lon']:.4f}",
                            'lat1': seg1['lat'],
                            'lon1': seg1['lon'],
                            'lat2': seg2['lat'],
                            'lon2': seg2['lon'],
                            'alt1': seg1['altitude'],
                            'alt2': seg2['altitude'],
                            'stage1': phase1,
                            'stage2': phase2,
                            'time1': seg1['time'],
                            'time2': seg2['time'],
                            'distance': distance,
                            'altitude_diff': altitude_diff,
                            'conflict_type': 'enroute',
                            'is_waypoint': False,
                            'segment1': seg1['segment'],
                            'segment2': seg2['segment']
                        })
    
    return crossing_points

def optimize_departure_times(flight_plans: List[FlightPlan], crossing_points: List[Dict]) -> Dict:
    """
    Optimize departure times to maximize conflicts.
    Returns a dictionary with flight indices and their suggested departure times.
    """
    # Group conflicts by flight pairs
    conflict_groups = defaultdict(list)
    for crossing in crossing_points:
        key = (crossing['flight1_idx'], crossing['flight2_idx'])
        conflict_groups[key].append(crossing)
    
    # Start with first flight at time 0
    departure_times = {0: 0}
    conflict_scores = defaultdict(int)
    
    # For each flight pair, find the best departure time for the second flight
    for (flight1_idx, flight2_idx), conflicts in conflict_groups.items():
        if flight1_idx == 0:  # First flight is our reference
            # Find the time difference that creates the most conflicts
            time_diffs = []
            for conflict in conflicts:
                time_diff = abs(conflict['time1'] - conflict['time2'])
                time_diffs.append(time_diff)
            
            # Use the most common time difference, or average if multiple
            if time_diffs:
                suggested_time = sum(time_diffs) / len(time_diffs)
                departure_times[flight2_idx] = int(suggested_time)
                
                # Count how many conflicts this creates
                for conflict in conflicts:
                    conflict_scores[flight2_idx] += 1
    
    # For remaining flights, find best departure times
    remaining_flights = set(range(len(flight_plans))) - set(departure_times.keys())
    
    for flight_idx in remaining_flights:
        best_time = 0
        best_score = 0
        
        # Try different departure times and see which creates most conflicts
        for test_time in range(0, 120, 5):  # Test every 5 minutes up to 2 hours
            score = 0
            for crossing in crossing_points:
                if crossing['flight1_idx'] == flight_idx or crossing['flight2_idx'] == flight_idx:
                    other_flight = crossing['flight2_idx'] if crossing['flight1_idx'] == flight_idx else crossing['flight1_idx']
                    if other_flight in departure_times:
                        other_time = departure_times[other_flight]
                        flight_time = crossing['time1'] if crossing['flight1_idx'] == flight_idx else crossing['time2']
                        other_crossing_time = crossing['time2'] if crossing['flight1_idx'] == flight_idx else crossing['time1']
                        
                        # Calculate when this flight should depart to create conflict
                        if crossing['flight1_idx'] == flight_idx:
                            conflict_time = other_time + other_crossing_time
                            suggested_departure = conflict_time - flight_time
                        else:
                            conflict_time = other_time + other_crossing_time
                            suggested_departure = conflict_time - flight_time
                        
                        if abs(test_time - suggested_departure) < 2:  # Within 2 minutes
                            score += 1
            
            if score > best_score:
                best_score = score
                best_time = test_time
        
        departure_times[flight_idx] = int(best_time)
        conflict_scores[flight_idx] = best_score
    
    return {
        'departure_times': departure_times,
        'conflict_scores': conflict_scores
    }

def generate_conflict_scenario(flight_plans: List[FlightPlan], crossing_points: List[Dict]) -> Dict:
    """Generate a complete conflict scenario with departure times"""
    
    # Optimize departure times
    optimization = optimize_departure_times(flight_plans, crossing_points)
    departure_times = optimization['departure_times']
    conflict_scores = optimization['conflict_scores']
    
    # For the new definition, all crossing_points are actual conflicts
    actual_conflicts = []
    for crossing in crossing_points:
        flight1_idx = crossing['flight1_idx']
        flight2_idx = crossing['flight2_idx']
        if flight1_idx in departure_times and flight2_idx in departure_times:
            # Calculate when each aircraft reaches the crossing point
            flight1_arrival = departure_times[flight1_idx] + crossing['time1']
            flight2_arrival = departure_times[flight2_idx] + crossing['time2']
            conflict = dict(crossing)
            conflict['flight1_arrival'] = flight1_arrival
            conflict['flight2_arrival'] = flight2_arrival
            conflict['time_diff'] = abs(flight1_arrival - flight2_arrival)
            actual_conflicts.append(conflict)
    
    return {
        'departure_schedule': [
            {
                'flight': f"{flight_plans[i].origin}-{flight_plans[i].destination}",
                'departure_time': departure_times[i],
                'conflict_score': conflict_scores.get(i, 0)
            }
            for i in range(len(flight_plans))
        ],
        'actual_conflicts': actual_conflicts,
        'total_conflicts': len(actual_conflicts)
    }

def main():
    """Main function to analyze flight plans for conflicts"""
    
    print("🎯 Flight Plan Conflict Analyzer for ATC Training")
    print("=" * 60)
    
    # Find all XML files
    xml_files = [f for f in os.listdir('.') if f.endswith('.xml')]
    
    if not xml_files:
        print("❌ No XML files found in the current directory")
        return
    
    print(f"📁 Found {len(xml_files)} XML files to analyze:")
    for xml_file in xml_files:
        print(f"   • {xml_file}")
    
    print("\n" + "=" * 60)
    
    # Extract flight plans
    flight_plans = []
    for xml_file in xml_files:
        print(f"\n🔄 Analyzing {xml_file}...")
        flight_plan = extract_flight_plan_from_xml(xml_file)
        if flight_plan:
            flight_plans.append(flight_plan)
            print(f"   ✅ {flight_plan.origin} → {flight_plan.destination}")
            print(f"   📍 {len(flight_plan.get_all_waypoints())} waypoints")
    
    if len(flight_plans) < 2:
        print("❌ Need at least 2 flight plans to analyze conflicts")
        return
    
    print(f"\n📊 Analyzing {len(flight_plans)} flight plans for conflicts...")
    
    # Find crossing points
    crossing_points = find_crossing_points(flight_plans)
    
    print(f"🎯 Found {len(crossing_points)} potential conflicts")
    print("   (Criteria: <900ft vertical, <3NM lateral, within 1min of takeoff/landing)")
    
    # Generate conflict scenario
    scenario = generate_conflict_scenario(flight_plans, crossing_points)
    
    print(f"\n🚁 Optimized Departure Schedule for Maximum Conflicts:")
    print("=" * 60)
    
    # Sort by departure time
    schedule = sorted(scenario['departure_schedule'], key=lambda x: x['departure_time'])
    
    for i, flight in enumerate(schedule, 1):
        print(f"{i}. {flight['flight']}: {flight['departure_time']:.1f} minutes")
        if flight['conflict_score'] > 0:
            print(f"   Potential conflicts: {flight['conflict_score']}")
    
    print(f"\n💥 Actual Conflicts Created: {scenario['total_conflicts']}")
    print("=" * 60)
    
    for conflict in scenario['actual_conflicts']:
        print(f"• {conflict['flight1']} & {conflict['flight2']}")
        print(f"  At: {conflict['waypoint1']}/{conflict['waypoint2']}")
        print(f"  Time: {conflict['flight1_arrival']:.1f} vs {conflict['flight2_arrival']:.1f} min")
        print(f"  Distance: {conflict['distance']:.1f} NM, Alt: {conflict['alt1']}/{conflict['alt2']} ft")
        print()
    
    # Save detailed analysis
    analysis = {
        'flight_plans': [f"{fp.origin}-{fp.destination}" for fp in flight_plans],
        'crossing_points': crossing_points,
        'scenario': scenario
    }
    
    # Create temp directory if it doesn't exist
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    with open(os.path.join(temp_dir, 'conflict_analysis.json'), 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"✅ Detailed analysis saved to temp/conflict_analysis.json")

if __name__ == "__main__":
    main() 