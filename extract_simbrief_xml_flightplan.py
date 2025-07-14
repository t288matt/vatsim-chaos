#!/usr/bin/env python3
"""
SimBrief XML Flight Plan Extractor

This script parses SimBrief XML flight plan files and extracts all waypoints, coordinates, altitudes, and timing information for each flight. It supports both the main navlog and alternate navlog sections.

Outputs (for each input XML file):
- <ROUTE>_<HASH>.kml:    KML file for Google Earth visualization of the flight plan
- <ROUTE>_<HASH>_data.json:    JSON file with all waypoints and metadata for further analysis

These outputs are used as the foundation for conflict analysis, scheduling, and 3D animation in the ATC event scenario workflow.
"""

import xml.etree.ElementTree as ET
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

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
        """Convert total minutes from departure to 4-digit UTC HHMM format"""
        # SimBrief XML gives time_total in minutes (e.g., 1359 = 13 minutes 59 seconds)
        total_minutes = self.time_total
        if self.time_total > 10000:  # Heuristic: treat as seconds
            total_minutes = self.time_total // 60
        hours = (total_minutes // 60) % 24
        minutes = total_minutes % 60
        return f"{hours:02d}{minutes:02d}"
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'lat': self.lat,
            'lon': self.lon,
            'altitude': self.altitude,
            'elapsed_time': self.get_time_formatted(),
            'time_seconds': self.time_total,
            'stage': self.stage,
            'type': self.waypoint_type
        }
    
    def __str__(self):
        return f"{self.name}: {self.lat:.6f}, {self.lon:.6f}, {self.altitude}ft, {self.get_time_formatted()}"

class FlightPlan:
    def __init__(self, origin: str, destination: str, route: str = "", flight_id: str = ""):
        self.origin = origin
        self.destination = destination
        self.route = route
        self.flight_id = flight_id
        self.waypoints: List[Waypoint] = []
        self.departure: Optional[Waypoint] = None
        self.arrival: Optional[Waypoint] = None
        
    def add_waypoint(self, waypoint: Waypoint):
        self.waypoints.append(waypoint)
    
    def set_departure(self, waypoint: Waypoint):
        self.departure = waypoint
        
    def set_arrival(self, waypoint: Waypoint):
        self.arrival = waypoint
    
    def get_all_waypoints(self) -> List[Waypoint]:
        """Get all waypoints including departure and arrival"""
        all_wps = []
        if self.departure:
            all_wps.append(self.departure)
        all_wps.extend(self.waypoints)
        if self.arrival:
            all_wps.append(self.arrival)
        return all_wps
    
    def to_dict(self) -> Dict:
        return {
            'origin': self.origin,
            'destination': self.destination,
            'route': self.route,
            'flight_id': self.flight_id,
            'departure': self.departure.to_dict() if self.departure else None,
            'waypoints': [wp.to_dict() for wp in self.waypoints],
            'arrival': self.arrival.to_dict() if self.arrival else None,
            'all_waypoints': [wp.to_dict() for wp in self.get_all_waypoints()]
        }

def abbreviate_waypoint_name(name: str) -> str:
    """Abbreviate common waypoint names for cleaner display"""
    abbreviations = {
        "TOP OF CLIMB": "TOC",
        "TOP OF DESCENT": "TOD"
    }
    return abbreviations.get(name, name)

def generate_flight_id(flight_counter: int) -> str:
    """Generate a unique flight identifier in FLT0001 format"""
    return f"FLT{flight_counter:04d}"

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
        print(f"Error parsing waypoint {ident}: {e}")
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
        print(f"Error parsing airport {icao}: {e}")
        return None

def extract_flight_plan_from_xml(xml_file: str, flight_id: str = "") -> Optional[FlightPlan]:
    """Extract flight plan from SimBrief XML file"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Extract basic flight information
        origin_elem = root.find('origin')
        dest_elem = root.find('destination')
        route_elem = root.find('.//route')
        
        origin_code = origin_elem.findtext('icao_code', '') if origin_elem else 'UNKNOWN'
        dest_code = dest_elem.findtext('icao_code', '') if dest_elem else 'UNKNOWN'
        route = route_elem.text if (route_elem is not None and route_elem.text is not None) else ""
        
        flight_plan = FlightPlan(origin_code, dest_code, route, flight_id)
        
        # Parse departure airport
        if origin_elem:
            departure = parse_airport_info(origin_elem)
            if departure:
                flight_plan.set_departure(departure)
                print(f"Departure: {departure}")
        
        # Parse arrival airport
        if dest_elem:
            arrival = parse_airport_info(dest_elem)
            if arrival:
                flight_plan.set_arrival(arrival)
                print(f"Arrival: {arrival}")
        
        # Parse main navlog waypoints
        navlog = root.find('navlog')
        if navlog is not None:
            print(f"\nParsing main navlog waypoints...")
            for fix in navlog.findall('fix'):
                waypoint = parse_waypoint_from_fix(fix)
                if waypoint:
                    flight_plan.add_waypoint(waypoint)
                    print(f"  - {waypoint}")
        # Do NOT parse alternate navlog waypoints anymore
        # alt_navlog = root.find('alternate_navlog')
        # if alt_navlog is not None:
        #     print(f"\nParsing alternate navlog waypoints...")
        #     for fix in alt_navlog.findall('fix'):
        #         waypoint = parse_waypoint_from_fix(fix)
        #         if waypoint:
        #             flight_plan.add_waypoint(waypoint)
        #             print(f"  - {waypoint}")
        
        return flight_plan
        
    except Exception as e:
        print(f"Error parsing XML file: {e}")
        return None

def create_kml_from_flight_plan(flight_plan: FlightPlan, filename: str) -> str:
    """Create KML content from flight plan"""
    all_waypoints = flight_plan.get_all_waypoints()
    
    # Define 40 diverse colors for different routes (in KML format: AABBGGRR)
    route_colors = [
        "ff0000ff",  # Red
        "ff00ff00",  # Green  
        "ffff0000",  # Blue
        "ffff00ff",  # Magenta
        "ff00ffff",  # Cyan
        "ffffff00",  # Yellow
        "ff8000ff",  # Orange
        "ff0080ff",  # Purple
        "ff800080",  # Dark Purple
        "ff008080",  # Teal
        "ffff8000",  # Light Blue
        "ff8000ff",  # Pink
        "ff00ff80",  # Lime Green
        "ffff0080",  # Light Red
        "ff800080",  # Dark Blue
        "ffff4000",  # Light Orange
        "ff4000ff",  # Light Purple
        "ff00ff40",  # Bright Green
        "ffff0040",  # Bright Red
        "ff400080",  # Dark Pink
        "ffff6000",  # Orange Red
        "ff6000ff",  # Purple Pink
        "ff00ff60",  # Bright Lime
        "ffff0060",  # Bright Pink
        "ff600080",  # Dark Magenta
        "ffff2000",  # Light Yellow
        "ff2000ff",  # Light Blue
        "ff00ff20",  # Pale Green
        "ffff0020",  # Pale Red
        "ff200080",  # Pale Purple
        "ffffa000",  # Gold
        "ffa000ff",  # Lavender
        "ff00ffa0",  # Mint Green
        "ffff00a0",  # Salmon
        "ffa00080",  # Plum
        "ffffc000",  # Amber
        "ffc000ff",  # Violet
        "ff00ffc0",  # Aqua
        "ffff00c0",  # Rose
        "ffc00080",  # Orchid
        "ffffe000",  # Light Gold
        "ffe000ff",  # Light Lavender
        "ff00ffe0",  # Light Mint
        "ffff00e0",  # Light Salmon
        "ffe00080",  # Light Plum
    ]
    
    # Get color based on route (use origin-destination as key)
    route_key = f"{flight_plan.origin}-{flight_plan.destination}"
    color_index = hash(route_key) % len(route_colors)
    route_color = route_colors[color_index]
    
    kml_template = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{flight_plan.flight_id} Flight Plan - {flight_plan.origin} to {flight_plan.destination}</name>
    <description>Flight plan extracted from SimBrief XML</description>
    
    <!-- Flight Information -->
            <Snippet maxLines="2">{flight_plan.flight_id}: {flight_plan.origin} to {flight_plan.destination}</Snippet>
    
    <!-- Flight Path Line -->
    <Placemark>
      <name>{flight_plan.flight_id} Flight Path</name>
      <description>
        <![CDATA[
        <h3>{flight_plan.flight_id} Flight Plan</h3>
        <p><strong>Flight ID:</strong> {flight_plan.flight_id}</p>
        <p><strong>Route:</strong> {flight_plan.origin} to {flight_plan.destination}</p>
        <p><strong>Route:</strong> {flight_plan.route}</p>
        <p><strong>Waypoints:</strong> {len(all_waypoints)}</p>
        <p><strong>Distance:</strong> ~{len(all_waypoints) * 50} nm</p>
        ]]>
      </description>
      <Style>
        <LineStyle>
          <color>{route_color}</color>
          <width>4</width>
        </LineStyle>
        <PolyStyle>
          <color>7f{route_color[2:]}</color>
        </PolyStyle>
      </Style>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
'''
    
    # Add coordinates
    for waypoint in all_waypoints:
        kml_template += f"          {waypoint.lon},{waypoint.lat},{waypoint.altitude}\n"
    
    kml_template += '''        </coordinates>
      </LineString>
    </Placemark>
    
    <!-- Waypoints -->
'''
    
    # Add waypoint markers with matching route color
    for i, waypoint in enumerate(all_waypoints):
        # Use route color for all waypoints in this flight plan
        waypoint_color = route_color
        scale = "1.5" if i == 0 or i == len(all_waypoints)-1 else "1.0"  # Larger for departure/arrival
        
        kml_template += f'''    <Placemark>
      <name>{waypoint.name}</name>
      <description>
        <![CDATA[
        <h3>{waypoint.name}</h3>
        <p><strong>Coordinates:</strong> {waypoint.lat:.6f}, {waypoint.lon:.6f}</p>
        <p><strong>Altitude:</strong> {waypoint.altitude} ft</p>
        <p><strong>Time:</strong> {waypoint.get_time_formatted()}</p>
        <p><strong>Stage:</strong> {waypoint.stage}</p>
        <p><strong>Type:</strong> {waypoint.waypoint_type}</p>
        ]]>
      </description>
      <Style>
        <LabelStyle>
          <color>{waypoint_color}</color>
          <scale>{scale}</scale>
        </LabelStyle>
      </Style>
    </Placemark>
'''
    
    kml_template += '''  </Document>
</kml>'''
    
    return kml_template

def save_flight_data(flight_plan: FlightPlan, base_filename: str):
    """Save flight plan data to JSON and KML files in temp directory"""
    
    # Create temp directory if it doesn't exist
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        print(f"Created temp directory: {temp_dir}")
    
    # Save as JSON in temp directory
    json_filename = os.path.join(temp_dir, f"{base_filename}_data.json")
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(flight_plan.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"Saved flight data to {json_filename}")
    
    # Save as KML in temp directory
    kml_filename = os.path.join(temp_dir, f"{base_filename}.kml")
    kml_content = create_kml_from_flight_plan(flight_plan, base_filename)
    with open(kml_filename, 'w', encoding='utf-8') as f:
        f.write(kml_content)
    print(f"Saved KML to {kml_filename}")
    
    # Print summary
    all_waypoints = flight_plan.get_all_waypoints()
    print(f"\nFlight Plan Summary:")
    print(f"   Flight ID: {flight_plan.flight_id}")
    print(f"   Route: {flight_plan.origin} to {flight_plan.destination}")
    print(f"   Total waypoints: {len(all_waypoints)}")
    print(f"   Route: {flight_plan.route}")
    
    if all_waypoints:
        print(f"\nWaypoints:")
        for i, wp in enumerate(all_waypoints):
            print(f"   {i+1:2d}. {wp.name:12s} {wp.lat:8.4f}, {wp.lon:8.4f} {wp.altitude:6d}ft {wp.get_time_formatted()} (elapsed)")

def main():
    """Main function to process all SimBrief XML files in the directory"""
    try:
        print("SimBrief XML Flight Plan Extractor")
        print("=" * 50)
        temp_dir = "temp"
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            print("Removed existing temp directory: temp")
        xml_files = [f for f in os.listdir('.') if f.endswith('.xml')]
        if not xml_files:
            print(f"No XML files found in the current directory")
            exit(1)
        print(f"Found {len(xml_files)} XML files to process:")
        for xml_file in xml_files:
            print(f"   - {xml_file}")
        print("\n" + "=" * 50)
        
        # Track flights with same origin-destination to generate unique IDs
        route_counter = {}  # Track count for each origin-destination pair
        flight_counter = 1  # Global flight counter for unique IDs
        
        success_count = 0
        for xml_filename in xml_files:
            print(f"Processing {xml_filename}...")
            print("----------------------------------------")
            
            # Extract basic info first to determine flight ID
            try:
                tree = ET.parse(xml_filename)
                root = tree.getroot()
                origin_elem = root.find('origin')
                dest_elem = root.find('destination')
                origin_code = origin_elem.findtext('icao_code', '') if origin_elem else 'UNKNOWN'
                dest_code = dest_elem.findtext('icao_code', '') if dest_elem else 'UNKNOWN'
                route_key = f"{origin_code}-{dest_code}"
                
                # Generate unique flight ID
                flight_id = generate_flight_id(flight_counter)
                flight_counter += 1
                
                print(f"Flight ID: {flight_id} for route {route_key}")
                
            except Exception as e:
                print(f"Error reading basic flight info from {xml_filename}: {e}")
                continue
            
            flight_plan = extract_flight_plan_from_xml(xml_filename, flight_id)
            if not flight_plan:
                print(f"Failed to extract flight plan from {xml_filename}")
                continue
            
            # Use flight ID as base filename instead of XML filename
            base_filename = flight_id
            save_flight_data(flight_plan, base_filename)
            print(f"Successfully processed {xml_filename} as {flight_id}")
            success_count += 1
        if success_count == 0:
            print("No flight plans were successfully processed. Exiting.")
            exit(1)
        print(f"\nCompleted processing {success_count} XML files!")
        print("All flight data and KML files have been created in temp directory.")
    except Exception as e:
        print(f"Fatal error in extraction: {e}")
        import traceback
        traceback.print_exc()
        exit(2)

if __name__ == "__main__":
    main() 