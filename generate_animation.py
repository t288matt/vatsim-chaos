#!/usr/bin/env python3
"""
Animation Data Generator for ATC Conflict Analysis System

Reads existing ATC conflict analysis files and generates animation-ready data
for web visualization.

FLIGHT ID SYSTEM:
- Uses unique flight IDs (FLT0001, FLT0002, etc.) from conflict analysis data
- Flight IDs are maintained throughout the animation generation process
- Route information (origin-destination) is preserved for visualization
- Animation data uses flight IDs for consistent identification across all components

Recent Changes:
- Removed x/y projected coordinates (Cesium only uses lat/lon/altitude)
- Reads departure times from interpolated points metadata (not pilot_briefing.txt)
- Simplified data structure for cleaner output
- Eliminated circular dependency with scheduling
- Updated to handle new flight ID system instead of origin-destination pairs

Input files:
- temp/potential_conflict_data.json (flight plans and conflicts with flight IDs)
- temp/routes_with_added_interpolated_points.json (with departure metadata)

Output files:
- animation_data.json (complete animation data, simplified structure)
- conflict_points.json (conflict locations and timing)
"""

import json
import csv
import re
import os
import logging
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any
from env import MIN_ALTITUDE_THRESHOLD, LATERAL_SEPARATION_THRESHOLD, VERTICAL_SEPARATION_THRESHOLD
from collections import defaultdict

# =============================================================================
# Animation Data Generation Script
#
# TIME HANDLING:
#   - Expects all input and output times as UTC 'HHMM' strings (4-digit, zero-padded).
#   - Does NOT use minutes after departure internally.
#   - All animation logic and output must use UTC 'HHMM' strings for time fields.
# =============================================================================

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnimationDataGenerator:
    """Generates animation data from existing analysis for 3D visualization"""
    
    def __init__(self):
        self.flights = {}
        self.conflicts = []
        self.schedule = {}
        self.event_start_time = None
        self.animation_data = {
            'metadata': {
                'total_flights': 0,
                'total_conflicts': 0,
                'event_duration': 0,
                'export_time': datetime.now().isoformat()
            },
            'flights': [],
            'conflicts': [],
            'timeline': []
        }
    
    def load_conflict_analysis(self) -> bool:
        """Load flight plans and conflicts from existing analysis (fixed for new structure)"""
        try:
            with open('temp/potential_conflict_data.json', 'r') as f:
                data = json.load(f)

            # The new structure uses 'flight_plans' (list of flight names) and 'potential_conflicts' (list of conflicts)
            self.flight_names = data.get('flight_plans', [])
            self.conflicts = data.get('potential_conflicts', [])

            # Try to load detailed flight data if present (for waypoints, etc.)
            self.flights = data.get('flights', {})
            if not self.flights:
                # Warn if only flight names are present
                logging.warning("No detailed flight data found in potential_conflict_data.json. Only flight names will be available for animation.")

            logging.info(f"Loaded {len(self.flight_names)} flights and {len(self.conflicts)} conflicts")
            return True

        except FileNotFoundError:
            logging.error("temp/potential_conflict_data.json not found. Run analysis first.")
            return False
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing conflict analysis: {e}")
            return False
    
    def load_schedule(self) -> bool:
        """Load departure schedule from interpolated points file metadata"""
        try:
            interp_path = 'temp/routes_with_added_interpolated_points.json'
            if not os.path.exists(interp_path):
                logger.warning(f"Interpolated points file not found: {interp_path}")
                return False
                
            with open(interp_path, 'r') as f:
                routes = json.load(f)
            
            # Check if metadata exists
            if '_metadata' not in routes or 'departure_schedule' not in routes['_metadata']:
                logger.warning("No departure schedule metadata found in interpolated points file.")
                return False
            
            # Load departure times from metadata
            departure_schedule = routes['_metadata']['departure_schedule']
            for flight_id, schedule_data in departure_schedule.items():
                self.schedule[flight_id] = schedule_data['departure_time']
            
            if not self.schedule:
                logger.error("No departures found in schedule!")
                return False
            # Find earliest departure time
            self.event_start_time = min(self.schedule.values())
            logger.info(f"Loaded schedule for {len(self.schedule)} flights from interpolated points metadata. Event start time: {self.event_start_time}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load schedule from interpolated points: {e}")
            return False
    
    def parse_conflict_timing(self) -> Dict[str, List[Dict]]:
        """Extract conflict timing from interpolated points metadata"""
        conflict_timing = {}
        
        try:
            interp_path = 'temp/routes_with_added_interpolated_points.json'
            if not os.path.exists(interp_path):
                logger.warning(f"Interpolated points file not found: {interp_path}")
                return conflict_timing
                
            with open(interp_path, 'r') as f:
                routes = json.load(f)
            
            # Extract conflict timing from metadata if available
            if '_metadata' in routes and 'departure_schedule' in routes['_metadata']:
                logger.info("Using conflict timing from interpolated points metadata")
            
        except Exception as e:
            logger.warning(f"Could not parse conflict timing from interpolated points: {e}")
        
        return conflict_timing
    
    def parse_conflict_distances(self) -> Dict[Tuple[str, str, str], str]:
        """Parse conflict distances from interpolated points metadata"""
        conflict_distances = {}
        try:
            interp_path = 'temp/routes_with_added_interpolated_points.json'
            if not os.path.exists(interp_path):
                logger.warning(f"Interpolated points file not found: {interp_path}")
                return conflict_distances
                
            with open(interp_path, 'r') as f:
                routes = json.load(f)
            
            # Extract conflict distances from metadata if available
            if '_metadata' in routes:
                logger.info("Using conflict distances from interpolated points metadata")
                
        except Exception as e:
            logger.warning(f"Could not parse conflict distances from interpolated points: {e}")
        return conflict_distances


    
    def extract_waypoints_from_xml(self, flight_id: str) -> List[Dict]:
        """Extract waypoints from the corresponding XML file"""
        # Find the XML file for this flight
        xml_files = [f for f in os.listdir('.') if f.endswith('.xml')]
        target_file = None
        
        # Handle new flight ID format (FLT0001, FLT0002, etc.)
        if flight_id.startswith('FLT'):
            # For new flight IDs, we need to find the corresponding XML file
            # The flight data should contain the route information
            if flight_id in self.flights:
                flight_data = self.flights[flight_id]
                # Try to find XML file based on route information
                for xml_file in xml_files:
                    # Check if XML file contains the route information
                    if self._xml_matches_flight_data(xml_file, flight_data):
                        target_file = xml_file
                        break
        else:
            # Handle old format (YBBN-YCOM)
            for xml_file in xml_files:
                if flight_id.replace('-', '') in xml_file:
                    target_file = xml_file
                    break
        
        if not target_file:
            logger.warning(f"No XML file found for flight {flight_id}")
            return []
        
        try:
            tree = ET.parse(target_file)
            root = tree.getroot()
            
            waypoints = []
            
            # Extract waypoints from navlog section
            navlog = root.find('.//navlog')
            if navlog is not None:
                for fix in navlog.findall('fix'):
                    ident = fix.find('ident')
                    pos_lat = fix.find('pos_lat')
                    pos_long = fix.find('pos_long')
                    altitude_feet = fix.find('altitude_feet')
                    time_total = fix.find('time_total')
                    stage = fix.find('stage')
                    
                    if (ident is not None and pos_lat is not None and 
                        pos_long is not None and altitude_feet is not None and
                        ident.text is not None and pos_lat.text is not None and
                        pos_long.text is not None and altitude_feet.text is not None):
                        
                        waypoint = {
                            'name': ident.text,
                            'lat': float(pos_lat.text),
                            'lon': float(pos_long.text),
                            'altitude': int(altitude_feet.text),
                            'time_from_departure': int(time_total.text) / 60.0 if time_total is not None and time_total.text is not None else 0,
                            'stage': stage.text if stage is not None and stage.text is not None else 'cruise'
                        }
                        waypoints.append(waypoint)
            
            # Add departure and arrival waypoints
            origin = root.find('.//origin')
            destination = root.find('.//destination')
            
            if origin is not None:
                pos_lat = origin.find('pos_lat')
                pos_long = origin.find('pos_long')
                icao_code = origin.find('icao_code')
                
                if (pos_lat is not None and pos_long is not None and icao_code is not None and
                    pos_lat.text is not None and pos_long.text is not None and icao_code.text is not None):
                    departure_wp = {
                        'name': icao_code.text,
                        'lat': float(pos_lat.text),
                        'lon': float(pos_long.text),
                        'altitude': 0,
                        'time_from_departure': 0,
                        'stage': 'departure'
                    }
                    waypoints.insert(0, departure_wp)
            
            if destination is not None:
                pos_lat = destination.find('pos_lat')
                pos_long = destination.find('pos_long')
                icao_code = destination.find('icao_code')
                
                if (pos_lat is not None and pos_long is not None and icao_code is not None and
                    pos_lat.text is not None and pos_long.text is not None and icao_code.text is not None):
                    arrival_wp = {
                        'name': icao_code.text,
                        'lat': float(pos_lat.text),
                        'lon': float(pos_long.text),
                        'altitude': 0,
                        'time_from_departure': waypoints[-1]['time_from_departure'] + 10 if waypoints else 60,
                        'stage': 'arrival'
                    }
                    waypoints.append(arrival_wp)
            
            logger.info(f"Extracted {len(waypoints)} waypoints from {target_file}")
            return waypoints
            
        except Exception as e:
            logger.error(f"Error extracting waypoints from {target_file}: {e}")
            return []
    
    def _xml_matches_flight_data(self, xml_file: str, flight_data: Dict) -> bool:
        """Check if XML file matches the flight data"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Extract origin and destination from XML
            origin_elem = root.find('origin')
            dest_elem = root.find('destination')
            
            if origin_elem is None or dest_elem is None:
                return False
            
            xml_origin = origin_elem.findtext('icao_code', '')
            xml_dest = dest_elem.findtext('icao_code', '')
            
            # Get route info from flight data
            if 'waypoints' in flight_data and flight_data['waypoints']:
                flight_origin = flight_data['waypoints'][0].get('name', '')
                flight_dest = flight_data['waypoints'][-1].get('name', '') if len(flight_data['waypoints']) > 1 else ''
                
                # Check if origins and destinations match
                return (xml_origin == flight_origin and xml_dest == flight_dest)
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking XML match for {xml_file}: {e}")
            return False
    
    def generate_flight_tracks(self) -> List[Dict]:
        """Generate animation tracks for each flight from high-res interpolated points if available"""
        tracks = []
        # Try to load interpolated points from temp file
        interpolated_path = os.path.join('temp', 'routes_with_added_interpolated_points.json')
        interpolated_data = None
        if os.path.exists(interpolated_path):
            with open(interpolated_path, 'r') as f:
                interpolated_data = json.load(f)
                logger.info(f"Loaded interpolated data with {len(interpolated_data)} flights")
        else:
            logger.warning(f"Interpolated data file not found: {interpolated_path}")
        
        for flight_id in self.flight_names:
            if flight_id not in self.schedule:
                raise ValueError(f"Missing scheduled departure for flight {flight_id}!")
            # Handle new flight ID format (FLT0001, FLT0002, etc.)
            if flight_id.startswith('FLT'):
                # For new flight IDs, get route info from flight data
                departure = ''
                arrival = ''
                if flight_id in self.flights:
                    flight_data = self.flights[flight_id]
                    if 'waypoints' in flight_data and flight_data['waypoints']:
                        departure = flight_data['waypoints'][0].get('name', '')
                        arrival = flight_data['waypoints'][-1].get('name', '') if len(flight_data['waypoints']) > 1 else ''
            else:
                # Handle old format (YBBN-YCOM)
                parts = flight_id.split('-')
                departure = parts[0] if len(parts) > 0 else ''
                arrival = parts[1] if len(parts) > 1 else ''
            
            # Use interpolated points if available
            if interpolated_data and flight_id in interpolated_data and isinstance(interpolated_data[flight_id], dict) and 'route' in interpolated_data[flight_id]:
                waypoints = interpolated_data[flight_id]['route']
            elif interpolated_data and flight_id in interpolated_data and isinstance(interpolated_data[flight_id], list):
                waypoints = interpolated_data[flight_id]
            else:
                waypoints = self.extract_waypoints_from_xml(flight_id)
                logger.info(f"Using XML data for {flight_id}: {len(waypoints)} waypoints")
            track_waypoints = []
            for i, wp in enumerate(waypoints):
                # Get UTC time from interpolated data
                utc_time = wp.get('time', '')
                
                track_waypoints.append({
                    'index': i,
                    'name': wp.get('name', ''),
                    'lat': wp['lat'],
                    'lon': wp['lon'],
                    'altitude': wp['altitude'],
                    'UTC time': utc_time,
                    'stage': wp.get('stage', '')
                })
            # Get aircraft type from flight data
            aircraft_type = "UNK"
            if interpolated_data and flight_id in interpolated_data and isinstance(interpolated_data[flight_id], dict):
                aircraft_type = interpolated_data[flight_id].get('aircraft_type', 'UNK')
            elif flight_id in self.flights:
                aircraft_type = self.flights[flight_id].get('aircraft_type', 'UNK')
            else:
                aircraft_type = 'UNK'
            
            # Use scheduled departure time if available
            departure_time = self.schedule[flight_id]
            track = {
                'flight_id': flight_id,
                'departure': departure,
                'arrival': arrival,
                'departure_time': departure_time,
                'aircraft_type': aircraft_type,
                'waypoints': track_waypoints,
                'conflicts': []
            }
            tracks.append(track)
        # Ensure all flight_id values are unique by appending a suffix to duplicates
        flight_id_counts = defaultdict(int)
        for track in tracks:
            base_id = track['flight_id']
            flight_id_counts[base_id] += 1
            if flight_id_counts[base_id] > 1:
                track['flight_id'] = f"{base_id}-{flight_id_counts[base_id]}"
        return tracks
    
    def add_minutes_to_hhmm(self, hhmm: str, minutes: float) -> str:
        # Add float minutes to a HHMM string, return new HHMM string
        h = int(hhmm[:2])
        m = int(hhmm[2:])
        total = h * 60 + m + minutes
        total = int(round(total))
        hours = (total // 60) % 24
        mins = total % 60
        return f"{hours:02d}{mins:02d}"

    def minutes_to_utc_hhmm(self, minutes: float) -> str:
        if not self.event_start_time:
            raise ValueError("Event start time not set!")
        h = int(self.event_start_time[:2])
        m = int(self.event_start_time[2:])
        event_start_minutes = h * 60 + m
        total_minutes = int(round(minutes)) + event_start_minutes
        hours = (total_minutes // 60) % 24
        mins = total_minutes % 60
        return f"{hours:02d}{mins:02d}"

    def float_minutes_to_hhmm(self, minutes: float) -> str:
        """Convert float minutes to 4-digit UTC HHMM string (rounded to nearest minute)"""
        return self.minutes_to_utc_hhmm(minutes)

    def calculate_distance(self, lat1: float, lon1: float, alt1: float, 
                         lat2: float, lon2: float, alt2: float) -> float:
        """Calculate 3D distance between two points in nautical miles"""
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Calculate lateral distance using haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        lateral_distance = 3440.065 * c  # Convert to nautical miles
        
        # Calculate vertical distance
        vertical_distance = abs(alt2 - alt1) / 6076.12  # Convert feet to nautical miles
        
        # Calculate 3D distance (Pythagorean theorem)
        distance_3d = math.sqrt(lateral_distance**2 + vertical_distance**2)
        
        return distance_3d

    def generate_conflict_points(self) -> List[Dict]:
        """Generate conflict points for animation using interpolated route data"""
        conflict_points = []
        conflict_distances = self.parse_conflict_distances()
        
        # Load interpolated route data
        try:
            with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
                interpolated_routes = json.load(f)
        except FileNotFoundError:
            logger.error("Interpolated routes file not found")
            return conflict_points
        
        # Find actual conflicts by comparing interpolated positions at same times
        for i, conflict in enumerate(self.conflicts):
            flight1 = conflict.get('flight1', '')
            flight2 = conflict.get('flight2', '')
            
            if flight1 not in interpolated_routes or flight2 not in interpolated_routes:
                continue
                
            # --- PATCH: Robust handling for new structure ---
            # In generate_flight_tracks (waypoints assignment)
            if flight1 in interpolated_routes and isinstance(interpolated_routes[flight1], dict) and 'route' in interpolated_routes[flight1]:
                route1 = interpolated_routes[flight1]['route']
            elif flight1 in interpolated_routes and isinstance(interpolated_routes[flight1], list):
                route1 = interpolated_routes[flight1]
            else:
                continue
            if flight2 in interpolated_routes and isinstance(interpolated_routes[flight2], dict) and 'route' in interpolated_routes[flight2]:
                route2 = interpolated_routes[flight2]['route']
            elif flight2 in interpolated_routes and isinstance(interpolated_routes[flight2], list):
                route2 = interpolated_routes[flight2]
            else:
                continue
            
            # Find when both flights are at the same location at the same time
            for wp1 in route1:
                for wp2 in route2:
                    if wp1['time'] == wp2['time']:  # Same UTC time
                        # Calculate distance between positions
                        distance = self.calculate_distance(
                            wp1['lat'], wp1['lon'], wp1['altitude'],
                            wp2['lat'], wp2['lon'], wp2['altitude']
                        )
                        
                        # Check if this is a conflict (within separation thresholds)
                        if distance < LATERAL_SEPARATION_THRESHOLD and abs(wp1['altitude'] - wp2['altitude']) < VERTICAL_SEPARATION_THRESHOLD:
                            conflict_point = {
                                'id': f"conflict_{i}",
                                'location': f"{flight1}-{flight2}",
                                'lat': (wp1['lat'] + wp2['lat']) / 2,
                                'lon': (wp1['lon'] + wp2['lon']) / 2,
                                'altitude': (wp1['altitude'] + wp2['altitude']) / 2,
                                'flight1': flight1,
                                'flight2': flight2,
                                'distance': distance,
                                'altitude_diff': abs(wp1['altitude'] - wp2['altitude']),
                                'conflict_time': wp1['time'],
                                'conflict_type': 'interpolated_conflict'
                            }
                            conflict_points.append(conflict_point)
                            break  # Found conflict for this time, move to next
                else:
                    continue
                break  # Found conflict, move to next conflict
            
        return conflict_points
    
    def generate_timeline(self) -> List[Dict]:
        """Generate complete animation timeline"""
        timeline = []
        for flight_id, departure_time in self.schedule.items():
            timeline.append({
                'time': departure_time,
                'type': 'departure',
                'flight_id': flight_id,
                'action': 'depart'
            })
        # Add conflict events
        for conflict in self.conflicts:
            flight1 = conflict.get('flight1', '')
            dep1 = self.schedule.get(flight1, '1400')
            t1 = self.add_minutes_to_hhmm(dep1, conflict.get('time1', 0))
            timeline.append({
                'time': t1,
                'type': 'conflict',
                'flight1': flight1,
                'flight2': conflict.get('flight2', ''),
                'location': conflict.get('waypoint1', ''),
                'action': 'conflict_start'
            })
        timeline.sort(key=lambda x: x['time'])
        return timeline
    
    def generate_animation_data(self) -> bool:
        """Generate all animation data to JSON files"""
        try:
            # Generate animation data
            tracks = self.generate_flight_tracks()
            conflict_points = self.generate_conflict_points()
            timeline = self.generate_timeline()
            
            # Filter conflicts based on altitude threshold
            filtered_conflicts = []
            logger.info(f"Starting altitude filtering with {len(conflict_points)} conflicts")
            for conflict in conflict_points:
                # Get altitudes from the original conflict data
                conflict_id = conflict.get('id', 'unknown')
                if conflict_id.startswith('conflict_'):
                    try:
                        conflict_index = int(conflict_id.split('_')[1])
                        if conflict_index < len(self.conflicts):
                            original_conflict = self.conflicts[conflict_index]
                            alt1_orig = original_conflict.get('alt1', 0)
                            alt2_orig = original_conflict.get('alt2', 0)
                            # Check if both aircraft are above the altitude threshold
                            if alt1_orig >= MIN_ALTITUDE_THRESHOLD and alt2_orig >= MIN_ALTITUDE_THRESHOLD:
                                filtered_conflicts.append(conflict)
                                logger.info(f"Keeping conflict {conflict_id}: altitudes {alt1_orig}ft/{alt2_orig}ft (both above {MIN_ALTITUDE_THRESHOLD}ft)")
                            else:
                                logger.info(f"Filtering out conflict {conflict_id}: altitudes {alt1_orig}ft/{alt2_orig}ft (below {MIN_ALTITUDE_THRESHOLD}ft threshold)")
                        else:
                            logger.warning(f"Conflict index {conflict_index} out of range for {conflict_id}")
                            filtered_conflicts.append(conflict)  # Keep it if we can't verify
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error processing conflict {conflict_id}: {e}")
                        filtered_conflicts.append(conflict)  # Keep it if we can't verify
                else:
                    # Fallback: check the single altitude field
                    alt = conflict.get('altitude', 0)
                    if alt >= MIN_ALTITUDE_THRESHOLD:
                        filtered_conflicts.append(conflict)
                        logger.info(f"Keeping conflict {conflict_id}: altitude {alt}ft (above {MIN_ALTITUDE_THRESHOLD}ft)")
                    else:
                        logger.info(f"Filtering out conflict {conflict_id}: altitude {alt}ft (below {MIN_ALTITUDE_THRESHOLD}ft threshold)")
            
            logger.info(f"Altitude filtering complete: {len(filtered_conflicts)} conflicts remaining out of {len(conflict_points)}")
            
            # Update metadata
            self.animation_data['metadata'].update({
                'total_flights': len(tracks),
                'total_conflicts': len(filtered_conflicts),
                'event_duration': len(timeline)
            })
            
            self.animation_data['flights'] = tracks
            self.animation_data['conflicts'] = filtered_conflicts
            self.animation_data['timeline'] = timeline
            
            # Generate main animation data
            with open('animation/animation_data.json', 'w') as f:
                json.dump(self.animation_data, f, indent=2)
            

            
            # Generate conflict points file
            with open('animation/conflict_points.json', 'w') as f:
                json.dump(filtered_conflicts, f, indent=2)
            
            logger.info("Animation data generated successfully!")
            logger.info(f"Generated files:")
            logger.info(f"   animation_data.json - Complete animation data")
            logger.info(f"   conflict_points.json - Conflict locations")
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating animation data: {e}")
            return False
    
    def run(self) -> bool:
        """Run the complete generation process"""
        logger.info("Animation Data Generator")
        logger.info("=" * 50)
        if not self.load_conflict_analysis():
            return False
        self.load_schedule() # Load schedule from pilot_briefing.txt
        logger.info(f"Schedule keys: {list(self.schedule.keys())}")
        logger.info(f"Flight names: {self.flight_names}")
        self.parse_conflict_timing()
        return self.generate_animation_data()


def main():
    """Main function"""
    generator = AnimationDataGenerator()
    success = generator.run()
    
    if success:
        print("\nAnimation data generation completed!")
        print("Ready for 3D web visualization")
    else:
        print("\nAnimation data generation failed!")
        print("Make sure to run analysis first: python execute.py --analyze-only")


if __name__ == "__main__":
    main() 