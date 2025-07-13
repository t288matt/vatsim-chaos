#!/usr/bin/env python3
"""
Animation Data Generator for ATC Conflict Analysis System

Reads existing ATC conflict analysis files and generates animation-ready data
for web visualization.

Recent Changes:
- Removed x/y projected coordinates (Cesium only uses lat/lon/altitude)
- Reads departure times from interpolated points metadata (not pilot_briefing.txt)
- Simplified data structure for cleaner output
- Eliminated circular dependency with scheduling

Input files:
- temp/potential_conflict_data.json (flight plans and conflicts)
- temp/routes_with_added_interpolated_points.json (with departure metadata)

Output files:
- animation_data.json (complete animation data, simplified structure)
- flight_tracks.json (individual flight paths)
- conflict_points.json (conflict locations and timing)
"""

import json
import csv
import re
import os
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any
from env import MIN_ALTITUDE_THRESHOLD
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

def minutes_to_utc_hhmm(minutes: float) -> str:
    # Convert minutes since event start (14:00) to UTC time
    event_start_minutes = 14 * 60  # 14:00 = 840 minutes
    total_minutes = int(round(minutes)) + event_start_minutes
    hours = (total_minutes // 60) % 24
    mins = total_minutes % 60
    return f"{hours:02d}{mins:02d}"

class AnimationDataGenerator:
    """Generates animation data from existing analysis for 3D visualization"""
    
    def __init__(self):
        self.flights = {}
        self.conflicts = []
        self.schedule = {}
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
            
            logger.info(f"Loaded schedule for {len(self.schedule)} flights from interpolated points metadata")
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
            parts = flight_id.split('-')
            departure = parts[0] if len(parts) > 0 else ''
            arrival = parts[1] if len(parts) > 1 else ''
            # Use interpolated points if available
            if interpolated_data and flight_id in interpolated_data:
                waypoints = interpolated_data[flight_id]
                logger.info(f"Using interpolated data for {flight_id}: {len(waypoints)} waypoints")
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
            # Use scheduled departure time if available
            departure_time = self.schedule.get(flight_id, '14:00')
            track = {
                'flight_id': flight_id,
                'departure': departure,
                'arrival': arrival,
                'departure_time': departure_time,
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

    def generate_conflict_points(self) -> List[Dict]:
        """Generate conflict points for animation (fixed for new structure)"""
        conflict_points = []
        conflict_distances = self.parse_conflict_distances()
        for i, conflict in enumerate(self.conflicts):
            lat = conflict.get('lat1', conflict.get('lat2', 0))
            lon = conflict.get('lon1', conflict.get('lon2', 0))
            flight1 = conflict.get('flight1', '')
            flight2 = conflict.get('flight2', '')
            location = conflict.get('waypoint1', '')
            dist_val = conflict_distances.get((flight1, flight2, location))
            if not dist_val:
                dist_val = conflict_distances.get((flight2, flight1, location))
            # --- FIX: Calculate actual UTC time for conflict ---
            dep1 = self.schedule.get(flight1, '1400')
            dep2 = self.schedule.get(flight2, '1400')
            t1 = self.add_minutes_to_hhmm(dep1, conflict.get('time1', 0))
            t2 = self.add_minutes_to_hhmm(dep2, conflict.get('time2', 0))
            conflict_point = {
                'id': f"conflict_{i}",
                'location': location,
                'lat': lat,
                'lon': lon,
                'altitude': conflict.get('alt1', 0),
                'flight1': flight1,
                'flight2': flight2,
                'distance': dist_val if dist_val else conflict.get('distance', 0),
                'altitude_diff': conflict.get('altitude_diff', 0),
                'time1': t1,
                'time2': t2,
                'conflict_type': conflict.get('conflict_type', 'between_waypoints')
            }
            conflict_points.append(conflict_point)
        return conflict_points
    
    def float_minutes_to_hhmm(self, minutes: float) -> str:
        """Convert float minutes to 4-digit UTC HHMM string (rounded to nearest minute)"""
        return minutes_to_utc_hhmm(minutes)

    def generate_timeline(self) -> List[Dict]:
        """Generate complete animation timeline"""
        timeline = []
        # Start with departures
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
            
            # Generate individual files for web components
            with open('animation/flight_tracks.json', 'w') as f:
                json.dump(tracks, f, indent=2)
            
            # Removed: conflict_points.json generation, as it is not used by the frontend
            # with open('animation/conflict_points.json', 'w') as f:
            #     json.dump(filtered_conflicts, f, indent=2)
            
            logger.info("Animation data generated successfully!")
            logger.info(f"Generated files:")
            logger.info(f"   animation_data.json - Complete animation data")
            logger.info(f"   flight_tracks.json - Individual flight paths")
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