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
- **REMOVED XML DEPENDENCY**: Now uses only the single source of truth

Input files:
- temp/routes_with_added_interpolated_points.json (single source of truth with all data)

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

    def generate_flight_tracks(self) -> List[Dict]:
        """Generate animation tracks for each flight from enhanced routes file (single source of truth)"""
        tracks = []
        # Load enhanced routes file (single source of truth)
        interpolated_path = os.path.join('temp', 'routes_with_added_interpolated_points.json')
        interpolated_data = None
        if os.path.exists(interpolated_path):
            with open(interpolated_path, 'r') as f:
                interpolated_data = json.load(f)
                logger.info(f"Loaded enhanced routes data with {len(interpolated_data)} flights")
        else:
            logger.warning(f"Enhanced routes file not found: {interpolated_path}")
            return tracks
        
        # Use flight names from schedule
        flight_names = list(self.schedule.keys())
        
        for flight_id in flight_names:
            if flight_id not in self.schedule:
                raise ValueError(f"Missing scheduled departure for flight {flight_id}!")
            
            # Get flight data from enhanced routes file
            if flight_id not in interpolated_data:
                logger.warning(f"Flight {flight_id} not found in enhanced routes data")
                continue
                
            flight_data = interpolated_data[flight_id]
            if not isinstance(flight_data, dict):
                logger.warning(f"Invalid flight data structure for {flight_id}")
                continue
            
            # Extract route waypoints
            waypoints = flight_data.get('route', [])
            if not waypoints:
                logger.warning(f"No route data found for {flight_id}")
                continue
            
            # Extract departure and arrival from waypoints
            departure = waypoints[0].get('name', '') if waypoints else ''
            arrival = waypoints[-1].get('name', '') if waypoints else ''
            
            # Build track waypoints
            track_waypoints = []
            for i, wp in enumerate(waypoints):
                track_waypoints.append({
                    'index': i,
                    'name': wp.get('name', ''),
                    'lat': wp['lat'],
                    'lon': wp['lon'],
                    'altitude': wp['altitude'],
                    'UTC time': wp.get('time', ''),
                    'stage': wp.get('stage', '')
                })
            
            # Get aircraft type from enhanced data
            aircraft_type = flight_data.get('aircraft_type', 'UNK')
            
            # Get conflicts from enhanced data
            conflicts = flight_data.get('conflicts', [])
            
            # Use scheduled departure time if available
            departure_time = self.schedule[flight_id]
            track = {
                'flight_id': flight_id,
                'departure': departure,
                'arrival': arrival,
                'departure_time': departure_time,
                'aircraft_type': aircraft_type,
                'waypoints': track_waypoints,
                'conflicts': conflicts
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
        """Generate conflict points for animation using enhanced routes file (single source of truth)"""
        conflict_points = []
        processed_pairs = set()  # Track processed aircraft pairs to avoid duplicates
        
        # Load enhanced routes file (single source of truth)
        try:
            with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
                enhanced_routes = json.load(f)
        except FileNotFoundError:
            logger.error("Enhanced routes file not found")
            return conflict_points
        
        # Extract conflicts from enhanced routes data
        for flight_id, flight_data in enhanced_routes.items():
            if flight_id == '_metadata':
                continue
                
            if not isinstance(flight_data, dict):
                continue
                
            conflicts = flight_data.get('conflicts', [])
            aircraft_type = flight_data.get('aircraft_type', 'UNK')
            
            for conflict in conflicts:
                other_flight = conflict['other_flight']
                
                # Create a unique pair identifier (sorted to ensure consistency)
                pair_key = tuple(sorted([flight_id, other_flight]))
                
                # Skip if we've already processed this pair
                if pair_key in processed_pairs:
                    continue
                
                processed_pairs.add(pair_key)
                
                conflict_point = {
                    'id': f"conflict_{flight_id}_{other_flight}",
                    'location': f"{flight_id}-{other_flight}",
                    'lat': conflict['lat'],
                    'lon': conflict['lon'],
                    'altitude': conflict['alt'],
                    'flight1': flight_id,
                    'flight2': other_flight,
                    'distance': conflict['distance'],
                    'altitude_diff': conflict['altitude_diff'],
                    'conflict_time': conflict['conflict_time_utc'],
                    'departure_time': conflict['departure_time'],
                    'aircraft_type': aircraft_type,
                    'conflict_type': 'scheduled_conflict'
                }
                conflict_points.append(conflict_point)
        
        logger.info(f"Generated {len(conflict_points)} unique conflict points from enhanced routes data")
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
        # The conflicts list is no longer populated here, so this loop will be empty
        # if the conflict_points generation is the only source of conflict data.
        # If conflict_points is also filtered, this will need to be updated.
        # For now, keeping it as is, but it might need adjustment if conflicts are
        # no longer directly available from the schedule.
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
                # Check the single altitude field from the conflict data
                alt = conflict.get('altitude', 0)
                conflict_id = conflict.get('id', 'unknown')
                
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
        """Run the complete animation data generation process."""
        print("Animation Data Generator")
        print("=" * 40)
        
        # Load schedule from enhanced routes file
        if not self.load_schedule():
            print("ERROR: Failed to load schedule from enhanced routes file")
            return False
        
        # Generate animation data using single source of truth
        if not self.generate_animation_data():
            print("ERROR: Failed to generate animation data")
            return False
        
        print("OK: Animation data generation complete!")
        print(f"Generated files:")
        print(f"   - animation/animation_data.json - Flight tracks and metadata")
        print(f"   - animation/conflict_points.json - Conflict points for visualization")
        return True


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