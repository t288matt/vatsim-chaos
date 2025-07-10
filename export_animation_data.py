#!/usr/bin/env python3
"""
Animation Data Export Script
============================

Reads existing ATC conflict analysis files and exports animation-ready data
for 3D web visualization. Does not modify any existing scripts or data.

This script reads:
- temp/conflict_analysis.json (flight plans and conflicts)
- event_schedule.csv (departure times)
- atc_briefing.txt (conflict timing info)

Exports:
- animation_data.json (complete animation timeline)
- flight_tracks.json (individual flight paths)
- conflict_points.json (conflict locations and timing)
"""

import json
import csv
import re
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnimationDataExporter:
    """Exports existing analysis data for 3D animation"""
    
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
            with open('temp/conflict_analysis.json', 'r') as f:
                data = json.load(f)

            # The new structure uses 'flight_plans' (list of flight names) and 'crossing_points' (list of conflicts)
            self.flight_names = data.get('flight_plans', [])
            self.conflicts = data.get('crossing_points', [])

            # Try to load detailed flight data if present (for waypoints, etc.)
            self.flights = data.get('flights', {})
            if not self.flights:
                # Warn if only flight names are present
                logging.warning("No detailed flight data found in conflict_analysis.json. Only flight names will be available for animation.")

            logging.info(f"Loaded {len(self.flight_names)} flights and {len(self.conflicts)} conflicts")
            return True

        except FileNotFoundError:
            logging.error("temp/conflict_analysis.json not found. Run analysis first.")
            return False
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing conflict analysis: {e}")
            return False
    
    def load_schedule(self) -> bool:
        """Load departure schedule from existing CSV"""
        try:
            with open('event_schedule.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    flight_id = row.get('Aircraft', '')  # Changed from 'flight_id'
                    departure_time = row.get('Departure_Time', '')  # Changed from 'departure_time'
                    if flight_id and departure_time:
                        self.schedule[flight_id] = departure_time
            
            logger.info(f"Loaded schedule for {len(self.schedule)} flights")
            return True
            
        except FileNotFoundError:
            logger.warning("event_schedule.csv not found. Using default timing.")
            return False
    
    def parse_conflict_timing(self) -> Dict[str, List[Dict]]:
        """Extract conflict timing from ATC briefing"""
        conflict_timing = {}
        
        try:
            with open('atc_briefing.txt', 'r') as f:
                content = f.read()
            
            # Parse conflict timing from briefing
            conflict_pattern = r'(\d{2}:\d{2}) - (.+?) vs (.+?) - (.+)'
            matches = re.findall(conflict_pattern, content)
            
            for match in matches:
                time_str, flight1, flight2, location = match
                conflict_timing[f"{flight1}_{flight2}"] = {
                    'time': time_str,
                    'flight1': flight1,
                    'flight2': flight2,
                    'location': location
                }
            
            logger.info(f"Parsed {len(conflict_timing)} conflict timings from briefing")
            
        except FileNotFoundError:
            logger.warning("atc_briefing.txt not found. Using estimated timing.")
        
        return conflict_timing
    
    def convert_coordinates(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert lat/lon to 3D coordinates (simplified)"""
        # Simple conversion for web visualization
        # In a real implementation, you'd use proper geodetic calculations
        x = lon * 111000  # meters per degree longitude (approximate)
        y = lat * 111000  # meters per degree latitude (approximate)
        return x, y
    
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
        """Generate animation tracks for each flight from XML waypoints"""
        tracks = []
        
        # For this version, we do not load a schedule file. Default all departures to 14:00.
        for flight_id in self.flight_names:
            parts = flight_id.split('-')
            departure = parts[0] if len(parts) > 0 else ''
            arrival = parts[1] if len(parts) > 1 else ''
            waypoints = self.extract_waypoints_from_xml(flight_id)
            track_waypoints = []
            for i, wp in enumerate(waypoints):
                x, y = self.convert_coordinates(wp['lat'], wp['lon'])
                track_waypoints.append({
                    'index': i,
                    'name': wp['name'],
                    'lat': wp['lat'],
                    'lon': wp['lon'],
                    'x': x,
                    'y': y,
                    'altitude': wp['altitude'],
                    'time_from_departure': wp['time_from_departure'],
                    'stage': wp['stage']
                })
            track = {
                'flight_id': flight_id,
                'departure': departure,
                'arrival': arrival,
                'departure_time': '14:00',
                'waypoints': track_waypoints,
                'conflicts': []
            }
            tracks.append(track)
        return tracks
    
    def generate_conflict_points(self) -> List[Dict]:
        """Generate conflict points for animation (fixed for new structure)"""
        conflict_points = []
        for i, conflict in enumerate(self.conflicts):
            # Use lat1/lon1 as the conflict location (or lat2/lon2 if missing)
            lat = conflict.get('lat1', conflict.get('lat2', 0))
            lon = conflict.get('lon1', conflict.get('lon2', 0))
            x, y = self.convert_coordinates(lat, lon)
            conflict_point = {
                'id': f"conflict_{i}",
                'location': conflict.get('waypoint1', ''),
                'lat': lat,
                'lon': lon,
                'x': x,
                'y': y,
                'altitude': conflict.get('alt1', 0),
                'flight1': conflict.get('flight1', ''),
                'flight2': conflict.get('flight2', ''),
                'distance': conflict.get('distance', 0),
                'altitude_diff': conflict.get('altitude_diff', 0),
                'time1': conflict.get('time1', 0),
                'time2': conflict.get('time2', 0),
                'conflict_type': conflict.get('conflict_type', 'between_waypoints')
            }
            conflict_points.append(conflict_point)
        return conflict_points
    
    def float_minutes_to_hhmm(self, minutes: float) -> str:
        """Convert float minutes to HH:MM string (rounded to nearest minute)"""
        base_time = datetime.strptime('14:00', '%H:%M')  # Default event start
        t = base_time + timedelta(minutes=round(minutes))
        return t.strftime('%H:%M')

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
            # Use time1 (float, minutes from event start) for timeline
            t_str = self.float_minutes_to_hhmm(conflict.get('time1', 0))
            timeline.append({
                'time': t_str,
                'type': 'conflict',
                'flight1': conflict.get('flight1', ''),
                'flight2': conflict.get('flight2', ''),
                'location': conflict.get('waypoint1', ''),
                'action': 'conflict_start'
            })
        # Sort timeline by time
        timeline.sort(key=lambda x: x['time'])
        return timeline
    
    def export_animation_data(self) -> bool:
        """Export all animation data to JSON files"""
        try:
            # Generate animation data
            tracks = self.generate_flight_tracks()
            conflict_points = self.generate_conflict_points()
            timeline = self.generate_timeline()
            
            # Update metadata
            self.animation_data['metadata'].update({
                'total_flights': len(tracks),
                'total_conflicts': len(conflict_points),
                'event_duration': len(timeline)
            })
            
            self.animation_data['flights'] = tracks
            self.animation_data['conflicts'] = conflict_points
            self.animation_data['timeline'] = timeline
            
            # Export main animation data
            with open('animation_data.json', 'w') as f:
                json.dump(self.animation_data, f, indent=2)
            
            # Export individual files for web components
            with open('flight_tracks.json', 'w') as f:
                json.dump(tracks, f, indent=2)
            
            with open('conflict_points.json', 'w') as f:
                json.dump(conflict_points, f, indent=2)
            
            logger.info("✅ Animation data exported successfully!")
            logger.info(f"📁 Generated files:")
            logger.info(f"   • animation_data.json - Complete animation data")
            logger.info(f"   • flight_tracks.json - Individual flight paths")
            logger.info(f"   • conflict_points.json - Conflict locations")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting animation data: {e}")
            return False
    
    def run(self) -> bool:
        """Run the complete export process"""
        logger.info("🎬 Animation Data Exporter")
        logger.info("=" * 50)
        if not self.load_conflict_analysis():
            return False
        # No schedule loading
        self.parse_conflict_timing()
        return self.export_animation_data()


def main():
    """Main function"""
    exporter = AnimationDataExporter()
    success = exporter.run()
    
    if success:
        print("\n🎉 Animation data export completed!")
        print("📁 Ready for 3D web visualization")
    else:
        print("\n❌ Animation data export failed!")
        print("💡 Make sure to run analysis first: python run_analysis.py --analyze-only")


if __name__ == "__main__":
    main() 