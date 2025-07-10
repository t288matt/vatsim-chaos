#!/usr/bin/env python3
"""
Merged Conflict Analyzer and Reporter for ATC Event Scenarios

This script analyzes SimBrief XML flight plans to identify potential conflicts
and generates comprehensive reports for event scenario creation.

Features:
- 3D spatial conflict detection (lateral and vertical separation)
- Both waypoint and enroute conflict analysis
- Automatic phase detection (climb/cruise/descent)
- Optimized departure time calculation for maximum conflicts
- Formatted conflict reporting with location details
- Google Earth KML visualization support

Author: ATC Event Scenario System
Version: 1.0
"""

import xml.etree.ElementTree as ET
import os
import json
import math
import logging
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Conflict detection parameters
LATERAL_SEPARATION_THRESHOLD = 3.0  # nautical miles
VERTICAL_SEPARATION_THRESHOLD = 900  # feet
MIN_ALTITUDE_THRESHOLD = 2500  # feet
DUPLICATE_FILTER_DISTANCE = 4.0  # nautical miles

# Route interpolation settings
INTERPOLATION_POINTS = 10  # points between waypoints

# Time optimization settings
MAX_DEPARTURE_TIME = 120  # minutes
DEPARTURE_TIME_STEP = 5  # minutes
TIME_TOLERANCE = 2  # minutes

# File paths
TEMP_DIRECTORY = "temp"
CONFLICT_ANALYSIS_FILE = "conflict_analysis.json"
CONFLICT_LIST_FILE = "conflict_list.txt"

# Earth radius for distance calculations
EARTH_RADIUS_NM = 3440.065

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Waypoint:
    """Represents a navigation waypoint with coordinates and flight data."""
    name: str
    lat: float
    lon: float
    altitude: int
    time_total: int = 0
    stage: str = ""
    waypoint_type: str = ""
    
    def get_time_formatted(self) -> str:
        """Convert total time to HH:MM format."""
        total_minutes = self.time_total
        if self.time_total > 10000:  # Heuristic: treat as seconds
            total_minutes = self.time_total // 60
        minutes = total_minutes // 100
        seconds = total_minutes % 100
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_time_minutes(self) -> float:
        """Get time in minutes as float."""
        return self.time_total / 60.0

class FlightPlan:
    """Represents a complete flight plan with route and waypoints."""
    
    def __init__(self, origin: str, destination: str, route: str = ""):
        self.origin = origin
        self.destination = destination
        self.route = route
        self.waypoints: List[Waypoint] = []
        self.departure: Optional[Waypoint] = None
        self.arrival: Optional[Waypoint] = None
    
    def add_waypoint(self, waypoint: Waypoint) -> None:
        """Add a waypoint to the flight plan."""
        self.waypoints.append(waypoint)
    
    def set_departure(self, waypoint: Waypoint) -> None:
        """Set the departure airport waypoint."""
        self.departure = waypoint
    
    def set_arrival(self, waypoint: Waypoint) -> None:
        """Set the arrival airport waypoint."""
        self.arrival = waypoint
    
    def get_all_waypoints(self) -> List[Waypoint]:
        """Get all waypoints including departure and arrival."""
        all_wps = []
        if self.departure:
            all_wps.append(self.departure)
        all_wps.extend(self.waypoints)
        if self.arrival:
            all_wps.append(self.arrival)
        return all_wps
    
    def get_route_identifier(self) -> str:
        """Get the route identifier (origin-destination)."""
        return f"{self.origin}-{self.destination}"

@dataclass
class Conflict:
    """Represents a detected conflict between two aircraft."""
    flight1: str
    flight2: str
    lat1: float
    lon1: float
    lat2: float
    lon2: float
    alt1: int
    alt2: int
    distance: float
    altitude_diff: int
    time1: float
    time2: float
    stage1: str
    stage2: str
    is_waypoint: bool
    waypoint1: str = ""
    waypoint2: str = ""
    segment1: str = ""
    segment2: str = ""
    flight1_arrival: Optional[float] = None
    flight2_arrival: Optional[float] = None
    time_diff: Optional[float] = None

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('conflict_analysis.log')
        ]
    )

def calculate_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two lat/lon points in nautical miles.
    
    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point
    
    Returns:
        Distance in nautical miles
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return EARTH_RADIUS_NM * c

def get_compass_direction(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """
    Get compass direction from point 1 to point 2.
    
    Args:
        lat1, lon1: Starting coordinates
        lat2, lon2: Ending coordinates
    
    Returns:
        Compass direction (N, NE, E, SE, S, SW, W, NW)
    """
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
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

def abbreviate_waypoint_name(name: str) -> str:
    """Abbreviate common waypoint names for cleaner display."""
    abbreviations = {
        "TOP OF CLIMB": "TOC",
        "TOP OF DESCENT": "TOD"
    }
    return abbreviations.get(name, name)

# =============================================================================
# XML PARSING FUNCTIONS
# =============================================================================

def parse_waypoint_from_fix(fix_element) -> Optional[Waypoint]:
    """
    Parse a waypoint from a fix element in the XML.
    
    Args:
        fix_element: XML element containing waypoint data
    
    Returns:
        Waypoint object or None if parsing fails
    """
    try:
        # Extract basic information
        ident = fix_element.findtext('ident', '')
        long_name = fix_element.findtext('name', ident)
        waypoint_type = fix_element.findtext('type', '')
        stage = fix_element.findtext('stage', '')
        
        # Use short name (ident) if available, otherwise use long name
        if ident and ident.strip():
            name = ident.strip()
        else:
            name = abbreviate_waypoint_name(long_name)
        
        # Extract coordinates
        lat_str = fix_element.findtext('pos_lat')
        lon_str = fix_element.findtext('pos_long')
        
        if not lat_str or not lon_str:
            logging.warning(f"Missing coordinates for waypoint {name}")
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
        logging.error(f"Error parsing waypoint {ident}: {e}")
        return None

def parse_airport_info(airport_element) -> Optional[Waypoint]:
    """
    Parse airport information from origin/destination elements.
    
    Args:
        airport_element: XML element containing airport data
    
    Returns:
        Waypoint object representing the airport or None if parsing fails
    """
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
            logging.warning(f"Missing coordinates for airport {name}")
            return None
            
        lat = float(lat_str)
        lon = float(lon_str)
        elevation = int(float(elevation_str))
        
        return Waypoint(name, lat, lon, elevation, 0, "DEP", "airport")
        
    except (ValueError, TypeError) as e:
        logging.error(f"Error parsing airport {icao}: {e}")
        return None

def extract_flight_plan_from_xml(xml_file: str) -> Optional[FlightPlan]:
    """
    Extract flight plan from SimBrief XML file.
    
    Args:
        xml_file: Path to the XML file
    
    Returns:
        FlightPlan object or None if extraction fails
    """
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
                    flight_plan.add_waypoint(waypoint)
        
        return flight_plan
        
    except Exception as e:
        logging.error(f"Error parsing XML file {xml_file}: {e}")
        return None

# =============================================================================
# CONFLICT DETECTION FUNCTIONS
# =============================================================================

def interpolate_route_segments(waypoints: List[Waypoint]) -> List[Dict[str, Any]]:
    """
    Interpolate route segments between waypoints to find potential crossing points.
    
    Args:
        waypoints: List of waypoints to interpolate between
    
    Returns:
        List of interpolated segment points
    """
    segments = []
    
    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i + 1]
        
        # Create interpolation points along this segment
        for j in range(1, INTERPOLATION_POINTS):
            t = j / INTERPOLATION_POINTS
            
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

def get_phase_for_time(waypoints: List[Waypoint], time_min: float) -> str:
    """
    Determine phase (climb, cruise, descent) for a given time based on TOC/TOD.
    
    Args:
        waypoints: List of waypoints in the flight plan
        time_min: Time in minutes from departure
    
    Returns:
        Flight phase: 'climb', 'cruise', or 'descent'
    """
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

def is_conflict_valid(wp1: Waypoint, wp2: Waypoint, distance: float, altitude_diff: int) -> bool:
    """
    Check if a potential conflict meets the criteria.
    
    Args:
        wp1, wp2: Waypoints to check
        distance: Lateral separation in nautical miles
        altitude_diff: Vertical separation in feet
    
    Returns:
        True if conflict criteria are met
    """
    return (distance < LATERAL_SEPARATION_THRESHOLD and
            altitude_diff < VERTICAL_SEPARATION_THRESHOLD and
            wp1.altitude > MIN_ALTITUDE_THRESHOLD and
            wp2.altitude > MIN_ALTITUDE_THRESHOLD)

def find_crossing_points(flight_plans: List[FlightPlan]) -> List[Dict[str, Any]]:
    """
    Find potential crossing points between flight plans using conflict criteria.
    
    Args:
        flight_plans: List of flight plans to analyze
    
    Returns:
        List of detected conflicts
    """
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
                        
                    distance = calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
                    altitude_diff = abs(wp1.altitude - wp2.altitude)
                    
                    if is_conflict_valid(wp1, wp2, distance, altitude_diff):
                        phase1 = get_phase_for_time(waypoints1, wp1.get_time_minutes())
                        phase2 = get_phase_for_time(waypoints2, wp2.get_time_minutes())
                        
                        crossing_points.append({
                            'flight1': fp1.get_route_identifier(),
                            'flight2': fp2.get_route_identifier(),
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
                    distance = calculate_distance_nm(seg1['lat'], seg1['lon'], seg2['lat'], seg2['lon'])
                    altitude_diff = abs(seg1['altitude'] - seg2['altitude'])
                    
                    if (distance < LATERAL_SEPARATION_THRESHOLD and
                        altitude_diff < VERTICAL_SEPARATION_THRESHOLD and
                        seg1['altitude'] > MIN_ALTITUDE_THRESHOLD and
                        seg2['altitude'] > MIN_ALTITUDE_THRESHOLD):
                        
                        phase1 = get_phase_for_time(waypoints1, seg1['time'])
                        phase2 = get_phase_for_time(waypoints2, seg2['time'])
                        
                        crossing_points.append({
                            'flight1': fp1.get_route_identifier(),
                            'flight2': fp2.get_route_identifier(),
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

# =============================================================================
# OPTIMIZATION FUNCTIONS
# =============================================================================

def optimize_departure_times(flight_plans: List[FlightPlan], crossing_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Optimize departure times to maximize conflicts.
    
    Args:
        flight_plans: List of flight plans
        crossing_points: List of detected conflicts
    
    Returns:
        Dictionary with departure times and conflict scores
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
        for test_time in range(0, MAX_DEPARTURE_TIME, DEPARTURE_TIME_STEP):
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
                        
                        if abs(test_time - suggested_departure) < TIME_TOLERANCE:
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

def generate_conflict_scenario(flight_plans: List[FlightPlan], crossing_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a complete conflict scenario with departure times.
    
    Args:
        flight_plans: List of flight plans
        crossing_points: List of detected conflicts
    
    Returns:
        Complete conflict scenario with departure schedule and actual conflicts
    """
    # Optimize departure times
    optimization = optimize_departure_times(flight_plans, crossing_points)
    departure_times = optimization['departure_times']
    conflict_scores = optimization['conflict_scores']
    
    # Calculate actual conflicts with departure times
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

# =============================================================================
# REPORTING FUNCTIONS
# =============================================================================

def build_route_waypoints(conflicts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Tuple[float, float]]]:
    """
    Build a database of waypoints organized by route.
    
    Args:
        conflicts: List of conflicts to extract waypoints from
    
    Returns:
        Dictionary mapping routes to their waypoints
    """
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

def find_nearest_waypoint_from_routes(lat: float, lon: float, route1: str, route2: str, 
                                     route_waypoints: Dict[str, Dict[str, Tuple[float, float]]]) -> Tuple[str, float]:
    """
    Find the nearest waypoint from the two routes involved in the conflict.
    
    Args:
        lat, lon: Coordinates of the conflict point
        route1, route2: Route identifiers
        route_waypoints: Dictionary of route waypoints
    
    Returns:
        Tuple of (nearest waypoint name, distance)
    """
    min_distance = float('inf')
    nearest_waypoint = "UNKNOWN"
    
    # Check waypoints from both routes
    for route in [route1, route2]:
        if route in route_waypoints:
            for wp_name, (wp_lat, wp_lon) in route_waypoints[route].items():
                distance = calculate_distance_nm(lat, lon, wp_lat, wp_lon)
                if distance < min_distance:
                    min_distance = distance
                    nearest_waypoint = wp_name
    
    return nearest_waypoint, min_distance

def format_location(conflict: Dict[str, Any], all_conflicts: List[Dict[str, Any]]) -> str:
    """
    Format location as distance and direction from nearest waypoint.
    
    Args:
        conflict: Conflict to format location for
        all_conflicts: All conflicts for waypoint database
    
    Returns:
        Formatted location string
    """
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

def filter_duplicate_conflicts(conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out conflicts that are too close to previous conflicts between the same routes.
    
    Args:
        conflicts: List of conflicts to filter
    
    Returns:
        Filtered list of conflicts
    """
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
            if calculate_distance_nm(lat, lon, prev_lat, prev_lon) < DUPLICATE_FILTER_DISTANCE:
                continue  # Skip this conflict, too close to previous
        
        filtered_conflicts.append(conflict)
        last_conflict_location[route_pair] = (lat, lon)
    
    return filtered_conflicts

def print_and_write_conflict_report(data: Dict[str, Any], output_file: str = CONFLICT_LIST_FILE) -> None:
    """
    Print and write a formatted conflict report.
    
    Args:
        data: Analysis data containing conflicts
        output_file: Output file path for the report
    """
    scenario = data.get('scenario', {})
    conflicts = scenario.get('actual_conflicts', [])
    all_routes = set(data.get('flight_plans', []))
    
    output = []
    print("Conflicts Found:")
    print("=" * 50)
    output.append("Conflicts Found:")
    output.append("=" * 50)
    
    if not conflicts:
        print("No conflicts found with current criteria.")
        output.append("No conflicts found with current criteria.")
        return
    
    # Filter duplicate conflicts
    filtered_conflicts = filter_duplicate_conflicts(conflicts)
    
    print(f"\nTotal Conflicts: {len(filtered_conflicts)}\n")
    output.append("")
    output.append(f"Total Conflicts: {len(filtered_conflicts)}")
    output.append("")
    
    # Print each conflict
    for i, conflict in enumerate(filtered_conflicts, 1):
        conflict_output = []
        conflict_output.append(f"{i}. {conflict['flight1']} & {conflict['flight2']}")
        
        # Format location
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
        
        # Format arrival times
        f1 = conflict.get('flight1_arrival', 'N/A')
        f2 = conflict.get('flight2_arrival', 'N/A')
        try:
            f1_disp = str(int(round(f1))) if isinstance(f1, (int, float)) else str(f1)
            f2_disp = str(int(round(f2))) if isinstance(f2, (int, float)) else str(f2)
        except Exception:
            f1_disp = str(f1)
            f2_disp = str(f2)
        
        conflict_output.append(f"   Arrival Times: {f1_disp} vs {f2_disp} min")
        
        # Add phase information
        phase1 = conflict.get('stage1', '?')
        phase2 = conflict.get('stage2', '?')
        conflict_output.append(f"   Phase: {phase1}/{phase2}")
        conflict_output.append("")
        
        # Print to terminal
        for line in conflict_output:
            print(line)
        
        # Add to output for file
        output.extend(conflict_output)
    
    # Show routes without conflicts
    routes_with_conflicts = set()
    for conflict in conflicts:
        routes_with_conflicts.add(conflict['flight1'])
        routes_with_conflicts.add(conflict['flight2'])
    
    routes_without_conflicts = sorted(all_routes - routes_with_conflicts)
    
    print("")
    print("The following routes do not have any conflicts:")
    output.append("")
    output.append("The following routes do not have any conflicts:")
    
    if routes_without_conflicts:
        for route in routes_without_conflicts:
            print(route)
            output.append(route)
    else:
        print("(All routes have at least one conflict)")
        output.append("(All routes have at least one conflict)")
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    logging.info(f"Conflict report written to {output_file}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def find_xml_files() -> List[str]:
    """Find all XML files in the current directory."""
    xml_files = [f for f in os.listdir('.') if f.endswith('.xml')]
    return xml_files

def extract_flight_plans(xml_files: List[str]) -> List[FlightPlan]:
    """
    Extract flight plans from XML files.
    
    Args:
        xml_files: List of XML file paths
    
    Returns:
        List of extracted flight plans
    """
    flight_plans = []
    
    for xml_file in xml_files:
        logging.info(f"Analyzing {xml_file}...")
        print(f"\n🔄 Analyzing {xml_file}...")
        
        flight_plan = extract_flight_plan_from_xml(xml_file)
        if flight_plan:
            flight_plans.append(flight_plan)
            print(f"   ✅ {flight_plan.origin} → {flight_plan.destination}")
            print(f"   📍 {len(flight_plan.get_all_waypoints())} waypoints")
        else:
            logging.warning(f"Failed to extract flight plan from {xml_file}")
    
    return flight_plans

def save_analysis_data(analysis: Dict[str, Any]) -> None:
    """
    Save analysis data to JSON file.
    
    Args:
        analysis: Analysis data to save
    """
    # Create temp directory if it doesn't exist
    if not os.path.exists(TEMP_DIRECTORY):
        os.makedirs(TEMP_DIRECTORY)
        logging.info(f"Created temp directory: {TEMP_DIRECTORY}")
    
    analysis_file = os.path.join(TEMP_DIRECTORY, CONFLICT_ANALYSIS_FILE)
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    logging.info(f"Analysis data saved to {analysis_file}")

def main() -> None:
    """Main function to analyze flight plans and generate conflict reports."""
    # Setup logging
    setup_logging()
    
    print("🎯 Merged Conflict Analyzer and Reporter")
    print("=" * 60)
    
    # Find XML files
    xml_files = find_xml_files()
    if not xml_files:
        print("❌ No XML files found in the current directory")
        logging.error("No XML files found in current directory")
        return
    
    print(f"📁 Found {len(xml_files)} XML files to analyze:")
    for xml_file in xml_files:
        print(f"   • {xml_file}")
    
    print("\n" + "=" * 60)
    
    # Extract flight plans
    flight_plans = extract_flight_plans(xml_files)
    
    if len(flight_plans) < 2:
        print("❌ Need at least 2 flight plans to analyze conflicts")
        logging.error("Insufficient flight plans for analysis")
        return
    
    print(f"\n📊 Analyzing {len(flight_plans)} flight plans for conflicts...")
    
    # Find crossing points
    crossing_points = find_crossing_points(flight_plans)
    
    print(f"🎯 Found {len(crossing_points)} potential conflicts")
    print(f"   (Criteria: <{VERTICAL_SEPARATION_THRESHOLD}ft vertical, <{LATERAL_SEPARATION_THRESHOLD}NM lateral, >{MIN_ALTITUDE_THRESHOLD}ft altitude)")
    
    # Generate conflict scenario
    scenario = generate_conflict_scenario(flight_plans, crossing_points)
    
    # Save analysis data
    analysis = {
        'flight_plans': [fp.get_route_identifier() for fp in flight_plans],
        'crossing_points': crossing_points,
        'scenario': scenario
    }
    
    save_analysis_data(analysis)
    
    # Generate and display conflict report
    print_and_write_conflict_report(analysis)
    
    print(f"\n✅ Analysis complete! Check {CONFLICT_LIST_FILE} for detailed report.")

if __name__ == "__main__":
    main() 