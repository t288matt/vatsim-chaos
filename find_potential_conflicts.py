#!/usr/bin/env python3
"""
Find Potential Conflicts for ATC Event Scenarios

This script analyzes SimBrief XML flight plans to identify potential conflicts
and generates comprehensive reports for event scenario creation.

FLIGHT ID SYSTEM:
- Uses unique flight IDs (FLT0001, FLT0002, etc.) for conflict tracking
- Flight IDs are maintained throughout the entire workflow
- Route information (origin-destination) is preserved for separation rules
- Enables tracking of "first conflicts" between unique aircraft pairs
- Supports separation enforcement for flights with same origin-destination

SEPARATION RULES:
- MIN_DEPARTURE_SEPARATION_MINUTES: Minimum time between departures from same airport
- MIN_SAME_ROUTE_SEPARATION_MINUTES: Minimum time between flights with same origin-destination
- These rules prevent aircraft with identical routes from departing too close together

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
from env import LATERAL_SEPARATION_THRESHOLD, VERTICAL_SEPARATION_THRESHOLD, MIN_ALTITUDE_THRESHOLD, MIN_DEPARTURE_SEPARATION_MINUTES
from env import INTERPOLATION_SPACING_NM
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
import logging
from env import (LATERAL_SEPARATION_THRESHOLD, VERTICAL_SEPARATION_THRESHOLD, 
                MIN_ALTITUDE_THRESHOLD, NO_CONFLICT_AIRPORT_DISTANCES)
from generate_schedule_conflicts import generate_conflict_scenario
from shared_types import FlightPlan, Waypoint

# =============================================================================
# CONFIGURATION
# =============================================================================

def load_airport_coordinates(json_path="airports.json") -> dict:
    """Load airport coordinates from a JSON file."""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Airport coordinates file not found: {json_path}")
    with open(json_path, "r") as f:
        return json.load(f)

AIRPORT_COORDINATES = load_airport_coordinates()

def parse_no_conflict_zones() -> Dict[str, float]:
    """Parse NO_CONFLICT_AIRPORT_DISTANCES into airport code -> distance mapping."""
    zones = {}
    for zone in NO_CONFLICT_AIRPORT_DISTANCES:
        if '/' in zone:
            airport_code, distance_str = zone.split('/')
            try:
                distance = float(distance_str)
                zones[airport_code] = distance
            except ValueError:
                print(f"Warning: Invalid distance format in {zone}")
        else:
            print(f"Warning: Invalid zone format: {zone}")
    return zones

# =============================================================================
# ATC Conflict Detection Script
#
# INTERNAL TIME HANDLING:
#   - All calculations, conflict detection, and sorting use minutes after departure (float/int).
#   - Do NOT use or enforce UTC 'HHMM' string formatting internally.
#   - Only output files for the frontend (e.g., interpolation, animation) should convert times to UTC 'HHMM' strings.
# =============================================================================

# Time optimization settings - moved to env.py and generate_schedule_conflicts.py

# File paths
TEMP_DIRECTORY = "temp"
CONFLICT_ANALYSIS_FILE = "potential_conflict_data.json"
CONFLICT_LIST_FILE = "conflict_list.txt"

# Earth radius for distance calculations
EARTH_RADIUS_NM = 3440.065

# =============================================================================
# DATA MODELS - Moved to shared_types.py
# =============================================================================

@dataclass
class Conflict:
    """
    Represents a detected conflict between two aircraft.
    
    FLIGHT ID SYSTEM:
    - flight1 and flight2 contain flight IDs (FLT0001, FLT0002, etc.)
    - Enables tracking of "first conflicts" between unique aircraft pairs
    - Route information is preserved for separation rule enforcement
    """
    flight1: str  # Flight ID of first aircraft (FLT0001, FLT0002, etc.)
    flight2: str  # Flight ID of second aircraft (FLT0001, FLT0002, etc.)
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
    # Ensure temp directory exists
    os.makedirs('temp', exist_ok=True)
    
    # Clear the log file at the start of each run
    with open('temp/conflict_analysis.log', 'w') as f:
        f.write('')  # Clear the file
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('temp/conflict_analysis.log')
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

def minutes_to_utc_hhmm(minutes: float) -> str:
    """Convert minutes since midnight UTC to zero-padded 4-digit HHMM string."""
    total_minutes = int(round(minutes))
    hours = (total_minutes // 60) % 24
    mins = total_minutes % 60
    return f"{hours:02d}{mins:02d}"

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

def extract_flight_plan_from_xml(xml_file: str, flight_id: str = "") -> Optional[FlightPlan]:
    """
    Extract flight plan from SimBrief XML file.
    
    Args:
        xml_file: Path to the XML file
        flight_id: Optional flight ID to assign to this flight plan
    
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
        
        flight_plan = FlightPlan(origin_code, dest_code, route, flight_id)
        
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
    Interpolate route segments between waypoints to find potential conflicts.
    Adds points every ~INTERPOLATION_SPACING_NM along each segment.
    Args:
        waypoints: List of waypoints to interpolate between
    Returns:
        List of interpolated segment points
    """
    segments = []
    spacing_nm = INTERPOLATION_SPACING_NM  # Interpolate every X nautical miles (from env.py)
    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i + 1]
        segment_distance = calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
        if segment_distance == 0:
            continue
        num_points = max(1, int(segment_distance // spacing_nm))
        for j in range(1, num_points + 1):
            t = j / (num_points + 1)
            lat = wp1.lat + t * (wp2.lat - wp1.lat)
            lon = wp1.lon + t * (wp2.lon - wp1.lon)
            alt = int(wp1.altitude + t * (wp2.altitude - wp1.altitude))
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
    # Basic conflict criteria
    basic_conflict = (distance < LATERAL_SEPARATION_THRESHOLD and
                     altitude_diff < VERTICAL_SEPARATION_THRESHOLD and
                     wp1.altitude > MIN_ALTITUDE_THRESHOLD and
                     wp2.altitude > MIN_ALTITUDE_THRESHOLD)
    
    if not basic_conflict:
        return False
    
    # Check if conflict is within no-conflict zones around airports
    no_conflict_zones = parse_no_conflict_zones()
    
    for airport_code, max_distance in no_conflict_zones.items():
        if airport_code in AIRPORT_COORDINATES:
            airport_lat, airport_lon = AIRPORT_COORDINATES[airport_code]
            
            # Check if either waypoint is within the no-conflict zone
            airport_lat = AIRPORT_COORDINATES[airport_code]["lat"]
            airport_lon = AIRPORT_COORDINATES[airport_code]["lon"]
            dist1 = calculate_distance_nm(wp1.lat, wp1.lon, airport_lat, airport_lon)
            dist2 = calculate_distance_nm(wp2.lat, wp2.lon, airport_lat, airport_lon)
            
            if dist1 < max_distance or dist2 < max_distance:
                return False  # Conflict is within no-conflict zone
    
    return True

def is_conflict_valid_segment(seg1: Dict, seg2: Dict, distance: float, altitude_diff: int) -> bool:
    """
    Check if a potential conflict between route segments meets the criteria.
    
    Args:
        seg1, seg2: Route segments to check
        distance: Lateral separation in nautical miles
        altitude_diff: Vertical separation in feet
    
    Returns:
        True if conflict criteria are met
    """
    # Basic conflict criteria
    basic_conflict = (distance < LATERAL_SEPARATION_THRESHOLD and
                     altitude_diff < VERTICAL_SEPARATION_THRESHOLD and
                     seg1['altitude'] > MIN_ALTITUDE_THRESHOLD and
                     seg2['altitude'] > MIN_ALTITUDE_THRESHOLD)
    
    if not basic_conflict:
        return False
    
    # Check if conflict is within no-conflict zones around airports
    no_conflict_zones = parse_no_conflict_zones()
    
    for airport_code, max_distance in no_conflict_zones.items():
        if airport_code in AIRPORT_COORDINATES:
            airport_lat, airport_lon = AIRPORT_COORDINATES[airport_code]
            
            # Check if either segment is within the no-conflict zone
            airport_lat = AIRPORT_COORDINATES[airport_code]["lat"]
            airport_lon = AIRPORT_COORDINATES[airport_code]["lon"]
            dist1 = calculate_distance_nm(seg1['lat'], seg1['lon'], airport_lat, airport_lon)
            dist2 = calculate_distance_nm(seg2['lat'], seg2['lon'], airport_lat, airport_lon)
            
            if dist1 < max_distance or dist2 < max_distance:
                return False  # Conflict is within no-conflict zone
    
    return True

def find_potential_conflicts(flight_plans: List[FlightPlan]) -> List[Dict[str, Any]]:
    """
    Find potential conflicts between flight plans using conflict criteria.
    Only returns the FIRST conflict between each aircraft pair.
    
    Args:
        flight_plans: List of flight plans to analyze
    
    Returns:
        List of detected first conflicts
    """
    potential_conflicts = []
    first_conflicts = {}  # Track first conflict for each aircraft pair
    
    for i, fp1 in enumerate(flight_plans):
        for j, fp2 in enumerate(flight_plans):
            if i >= j:  # Avoid duplicate comparisons
                continue
                
            waypoints1 = fp1.get_all_waypoints()
            waypoints2 = fp2.get_all_waypoints()
            
            print(f"Checking {fp1.get_route_identifier()} vs {fp2.get_route_identifier()}")
            
            # Check each waypoint pair for conflicts
            for wp1 in waypoints1:
                for wp2 in waypoints2:
                    # Skip TOC and TOD waypoints for conflict detection
                    if wp1.name in ("TOC", "TOD") or wp2.name in ("TOC", "TOD"):
                        continue
                        
                    distance = calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
                    altitude_diff = abs(wp1.altitude - wp2.altitude)
                    
                    print(f"  Waypoint check: {wp1.name} vs {wp2.name} - Distance: {distance:.1f}nm, Alt diff: {altitude_diff}ft")
                    
                    if is_conflict_valid(wp1, wp2, distance, altitude_diff):
                        phase1 = get_phase_for_time(waypoints1, wp1.get_time_minutes())
                        phase2 = get_phase_for_time(waypoints2, wp2.get_time_minutes())
                        
                        conflict_time = min(wp1.get_time_minutes(), wp2.get_time_minutes())
                        aircraft_pair = (i, j)
                        
                        # Only add if this is the first conflict for this aircraft pair
                        if aircraft_pair not in first_conflicts or conflict_time < first_conflicts[aircraft_pair]['time']:
                            conflict = {
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
                                'is_waypoint': True,
                                'time': conflict_time
                            }
                            first_conflicts[aircraft_pair] = conflict
            
            # Check interpolated segments for conflicts
            segments1 = interpolate_route_segments(waypoints1)
            segments2 = interpolate_route_segments(waypoints2)
            
            print(f"  Checking {len(segments1)} segments vs {len(segments2)} segments")
            
            segment_conflicts = 0
            for seg1 in segments1:
                for seg2 in segments2:
                    distance = calculate_distance_nm(seg1['lat'], seg1['lon'], seg2['lat'], seg2['lon'])
                    altitude_diff = abs(seg1['altitude'] - seg2['altitude'])
                    
                    # Use the same conflict validation logic for segments
                    if is_conflict_valid_segment(seg1, seg2, distance, altitude_diff):
                        
                        segment_conflicts += 1
                        phase1 = get_phase_for_time(waypoints1, seg1['time'])
                        phase2 = get_phase_for_time(waypoints2, seg2['time'])
                        
                        conflict_time = min(seg1['time'], seg2['time'])
                        aircraft_pair = (i, j)
                        
                        # Only add if this is the first conflict for this aircraft pair
                        if aircraft_pair not in first_conflicts or conflict_time < first_conflicts[aircraft_pair]['time']:
                            conflict = {
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
                                'segment2': seg2['segment'],
                                'time': conflict_time
                            }
                            first_conflicts[aircraft_pair] = conflict
            
            print(f"  Found {segment_conflicts} segment conflicts")
    
    # Convert first_conflicts dict to list
    potential_conflicts = list(first_conflicts.values())
    return potential_conflicts

def add_conflict_specific_points(interpolated_data: Dict[str, List[Dict]], conflicts: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
    """
    Add interpolation points at exact conflict times to ensure animation accuracy.
    Args:
        interpolated_data: The existing interpolated route data
        conflicts: List of detected conflicts
    Returns:
        Updated interpolated data with conflict-specific points added
    """
    from copy import deepcopy
    updated_data = deepcopy(interpolated_data)

    def calculate_distance_from_origin(point, origin_point=None):
        """Calculate distance from origin for a waypoint."""
        if origin_point is None:
            # Use first waypoint as origin if not provided
            return 0.0
        return calculate_distance_nm(origin_point['lat'], origin_point['lon'], 
                                   point['lat'], point['lon'])

    def insert_by_distance(route, conflict_point):
        """Insert conflict point at correct position based on distance from origin."""
        if not route:
            route.append(conflict_point)
            return
            
        # Use first waypoint as origin reference
        origin = route[0]
        
        # Find the actual destination (last waypoint with a name that's not a conflict)
        destination_index = -1
        for i in range(len(route) - 1, -1, -1):
            waypoint = route[i]
            if waypoint.get('name') and not waypoint.get('name', '').startswith('CONFLICT_'):
                destination_index = i
                break
        
        # Calculate distance from origin for conflict point
        conflict_distance = calculate_distance_from_origin(conflict_point, origin)
        
        # Find correct insertion position based on distance, but never after destination
        for i, waypoint in enumerate(route):
            waypoint_distance = calculate_distance_from_origin(waypoint, origin)
            if conflict_distance < waypoint_distance:
                # Don't insert after the destination
                if destination_index >= 0 and i > destination_index:
                    continue
                route.insert(i, conflict_point)
                return
        
        # If conflict is beyond all waypoints but before destination, insert before destination
        if destination_index >= 0:
            route.insert(destination_index, conflict_point)
        else:
            # Fallback: append if no destination found
            route.append(conflict_point)

    for conflict in conflicts:
        flight1 = conflict.get('flight1', '')
        flight2 = conflict.get('flight2', '')
        time1 = conflict.get('time1', 0)
        time2 = conflict.get('time2', 0)
        lat1 = conflict.get('lat1', 0)
        lon1 = conflict.get('lon1', 0)
        lat2 = conflict.get('lat2', 0)
        lon2 = conflict.get('lon2', 0)
        alt1 = conflict.get('alt1', 0)
        alt2 = conflict.get('alt2', 0)

        # Event starts at 14:00 (840 minutes), so add conflict minutes to get UTC
        event_start_minutes = 14 * 60  # 14:00 = 840 minutes
        utc_time1 = minutes_to_utc_hhmm(time1 + event_start_minutes)
        utc_time2 = minutes_to_utc_hhmm(time2 + event_start_minutes)

        # Insert conflict point for flight1 at correct distance position
        if flight1 in updated_data:
            conflict_point1 = {
                'lat': lat1,
                'lon': lon1,
                'altitude': alt1,
                'time': utc_time1,
                'name': f"CONFLICT_{flight2}",
                'segment': 'conflict_point',
                'interpolation_point': 999
            }
            insert_by_distance(updated_data[flight1], conflict_point1)
        # Insert conflict point for flight2 at correct distance position
        if flight2 in updated_data:
            conflict_point2 = {
                'lat': lat2,
                'lon': lon2,
                'altitude': alt2,
                'time': utc_time2,
                'name': f"CONFLICT_{flight1}",
                'segment': 'conflict_point',
                'interpolation_point': 999
            }
            insert_by_distance(updated_data[flight2], conflict_point2)
    return updated_data

# =============================================================================
# OPTIMIZATION FUNCTIONS
# =============================================================================

# Scheduling functions moved to generate_schedule_conflicts.py

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



def print_and_write_conflict_report(data: Dict[str, Any], output_file: str = CONFLICT_LIST_FILE) -> None:
    """
    Print and write a formatted conflict report.
    Only reports the FIRST conflict between each aircraft pair.
    
    Args:
        data: Analysis data containing conflicts
        output_file: Output file path for the report
    """
    scenario = data.get('scenario', {})
    conflicts = scenario.get('potential_conflicts', [])
    all_routes = set(data.get('flight_plans', []))

    output = []
    print("First Conflicts Found:")
    print("=" * 50)
    output.append("First Conflicts Found:")
    output.append("=" * 50)

    if not conflicts:
        print("No first conflicts found with current criteria.")
        output.append("No first conflicts found with current criteria.")
        # Always write the file, even if no conflicts
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        logging.info(f"Conflict report written to {output_file}")
        return

    # Use conflicts directly since "first conflict" logic already handles duplicates
    filtered_conflicts = conflicts
    
    print(f"\nTotal First Conflicts: {len(filtered_conflicts)}\n")
    output.append("")
    output.append(f"Total First Conflicts: {len(filtered_conflicts)}")
    output.append("")
    
    # Get aircraft types for display
    flights_dict = data.get('flights', {})
    
    # Print each conflict
    for i, conflict in enumerate(filtered_conflicts, 1):
        conflict_output = []
        
        # Get aircraft types
        flight1_type = flights_dict.get(conflict['flight1'], {}).get('aircraft_type', 'UNK')
        flight2_type = flights_dict.get(conflict['flight2'], {}).get('aircraft_type', 'UNK')
        
        conflict_output.append(f"{i}. {conflict['flight1']} ({flight1_type}) & {conflict['flight2']} ({flight2_type})")
        
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
    print("The following routes do not have any first conflicts:")
    output.append("")
    output.append("The following routes do not have any first conflicts:")
    
    if routes_without_conflicts:
        for route in routes_without_conflicts:
            print(route)
            output.append(route)
    else:
        print("(All routes have at least one first conflict)")
        output.append("(All routes have at least one first conflict)")
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    logging.info(f"Conflict report written to {output_file}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def extract_flight_plans() -> List[FlightPlan]:
    """
    Extract flight plans from individual JSON files in temp directory.
    
    Args:
        xml_files: List of XML file paths (used for reference only)
    
    Returns:
        List of extracted flight plans
    """
    flight_plans = []
    
    # Look for individual flight JSON files in temp directory
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        logging.error(f"Temp directory {temp_dir} not found. Run extract_simbrief_xml_flightplan.py first.")
        return flight_plans
    
    # Find all FLT*_data.json files
    json_files = [f for f in os.listdir(temp_dir) if f.endswith('_data.json') and f.startswith('FLT')]
    json_files.sort()  # Sort to ensure consistent order
    
    if not json_files:
        logging.error(f"No flight data JSON files found in {temp_dir}. Run extract_simbrief_xml_flightplan.py first.")
        return flight_plans
    
    for json_file in json_files:
        json_path = os.path.join(temp_dir, json_file)
        logging.info(f"Loading flight data from {json_file}...")
        print(f"\nLoading {json_file}...")
        
        try:
            with open(json_path, 'r') as f:
                flight_data = json.load(f)
            
            # Extract flight information
            origin = flight_data.get('origin', 'UNKNOWN')
            destination = flight_data.get('destination', 'UNKNOWN')
            route = flight_data.get('route', '')
            flight_id = flight_data.get('flight_id', '')
            aircraft_type = flight_data.get('aircraft_type', 'UNK')
            
            # Create flight plan
            flight_plan = FlightPlan(origin, destination, route, flight_id, aircraft_type)
            
            # Add departure waypoint
            if 'departure' in flight_data and flight_data['departure']:
                dep_data = flight_data['departure']
                departure = Waypoint(
                    dep_data['name'], dep_data['lat'], dep_data['lon'], 
                    dep_data['altitude'], dep_data.get('time_seconds', 0),
                    dep_data.get('stage', ''), dep_data.get('type', '')
                )
                flight_plan.set_departure(departure)
            
            # Add waypoints
            for wp_data in flight_data.get('waypoints', []):
                waypoint = Waypoint(
                    wp_data['name'], wp_data['lat'], wp_data['lon'],
                    wp_data['altitude'], wp_data.get('time_seconds', 0),
                    wp_data.get('stage', ''), wp_data.get('type', '')
                )
                flight_plan.add_waypoint(waypoint)
            
            # Add arrival waypoint
            if 'arrival' in flight_data and flight_data['arrival']:
                arr_data = flight_data['arrival']
                arrival = Waypoint(
                    arr_data['name'], arr_data['lat'], arr_data['lon'],
                    arr_data['altitude'], arr_data.get('time_seconds', 0),
                    arr_data.get('stage', ''), arr_data.get('type', '')
                )
                flight_plan.set_arrival(arrival)
            
            flight_plans.append(flight_plan)
            print(f"   {flight_id}: {origin} to {destination} ({aircraft_type})")
            print(f"   {len(flight_plan.get_all_waypoints())} waypoints")
            
        except Exception as e:
            logging.error(f"Failed to load flight data from {json_file}: {e}")
            print(f"   Error loading {json_file}: {e}")
    
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
    
    print("Find Potential Conflicts for ATC Event Scenarios")
    print("=" * 60)
    
    # Extract flight plans from processed JSON files
    flight_plans = extract_flight_plans()
    
    # Store all routes with interpolated points for animation accuracy
    routes_with_interpolated = {}
    for fp in flight_plans:
        waypoints = fp.get_all_waypoints()
        # Include original waypoints as first points
        route_points = [
            {
                'lat': wp.lat,
                'lon': wp.lon,
                'altitude': wp.altitude,
                'time': wp.get_time_minutes(),
                'name': wp.name
            } for wp in waypoints
        ]
        # Add interpolated points
        interpolated = interpolate_route_segments(waypoints)
        route_points.extend(interpolated)
        routes_with_interpolated[fp.get_route_identifier()] = route_points
    
    # Keep times as minutes after departure for internal processing
    
    # Write to temp file
    temp_dir = 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    with open(os.path.join(temp_dir, 'routes_with_added_interpolated_points.json'), 'w') as f:
        json.dump(routes_with_interpolated, f, indent=2)
    
    if len(flight_plans) < 2:
        print("Need at least 2 flight plans to analyze conflicts")
        logging.error("Insufficient flight plans for analysis")
        return
    
    print(f"\nAnalyzing {len(flight_plans)} flight plans for conflicts...")
    
    # Find potential conflicts
    potential_conflicts = find_potential_conflicts(flight_plans)
    
    print(f"Found {len(potential_conflicts)} potential conflicts")
    print(f"   (Criteria: <{VERTICAL_SEPARATION_THRESHOLD}ft vertical, <{LATERAL_SEPARATION_THRESHOLD}NM lateral, >{MIN_ALTITUDE_THRESHOLD}ft altitude)")
    
    # Add conflict-specific interpolation points and update the file
    routes_with_interpolated = add_conflict_specific_points(routes_with_interpolated, potential_conflicts)
    with open(os.path.join(temp_dir, 'routes_with_added_interpolated_points.json'), 'w') as f:
        json.dump(routes_with_interpolated, f, indent=2)
    
    # Generate conflict scenario
    scenario = generate_conflict_scenario(flight_plans, potential_conflicts)
    
    # Save analysis data
    flights_dict = {}
    for fp in flight_plans:
        flights_dict[fp.get_route_identifier()] = {
            'aircraft_type': fp.aircraft_type,
            'waypoints': [
                {
                    'name': wp.name,
                    'lat': wp.lat,
                    'lon': wp.lon,
                    'altitude': wp.altitude,
                    'time_total': wp.time_total,
                    'stage': wp.stage,
                    'type': wp.waypoint_type
                } for wp in fp.get_all_waypoints()
            ]
        }
    analysis = {
        'flight_plans': [fp.get_route_identifier() for fp in flight_plans],
        'potential_conflicts': potential_conflicts,
        'scenario': scenario,
        'flights': flights_dict
    }
    save_analysis_data(analysis)
    
    # Generate and display conflict report
    print_and_write_conflict_report(analysis)
    
    print(f"\nAnalysis complete! Check {CONFLICT_LIST_FILE} for detailed report.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error in find_potential_conflicts: {e}")
        import traceback
        traceback.print_exc()
        exit(2) 