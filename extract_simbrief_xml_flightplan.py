#!/usr/bin/env python3
"""
SimBrief XML Flight Plan Extractor

This script parses SimBrief XML flight plan files and extracts all waypoints, coordinates, 
altitudes, and timing information for each flight. It supports both the main navlog and 
alternate navlog sections.

FLIGHT ID SYSTEM:
- Each flight is assigned a unique flight ID (FLT0001, FLT0002, etc.) during processing
- Flight IDs are sequential and maintained throughout the entire workflow
- Route information (origin-destination) is preserved alongside flight IDs
- This enables better conflict tracking and separation enforcement

Outputs (for each input XML file):
- <ROUTE>_<HASH>.kml:    KML file for Google Earth visualization of the flight plan
- <ROUTE>_<HASH>_data.json:    JSON file with all waypoints and metadata for further analysis

These outputs are used as the foundation for conflict analysis, scheduling, and 3D animation 
in the ATC event scenario workflow.
"""

import xml.etree.ElementTree as ET
import json
import os
import sys
import argparse
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from shared_types import FlightPlan, Waypoint

def abbreviate_waypoint_name(name: str) -> str:
    """Abbreviate common waypoint names for cleaner display"""
    abbreviations = {
        "TOP OF CLIMB": "TOC",
        "TOP OF DESCENT": "TOD"
    }
    return abbreviations.get(name, name)

def generate_flight_id(flight_counter: int) -> str:
    """
    Generate a unique flight identifier in FLT0001 format.
    
    FLIGHT ID SYSTEM:
    - Sequential numbering starting from 0001
    - Format: FLT0001, FLT0002, FLT0003, etc.
    - Used throughout the workflow for conflict tracking and separation enforcement
    - Enables unique identification even for flights with same origin-destination
    
    Args:
        flight_counter: Sequential counter for flight numbering
        
    Returns:
        Flight ID string in FLT0001 format
    """
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
        
        # Extract aircraft type from XML
        aircraft_type = "UNK"  # Default fallback
        aircraft_elem = root.find('aircraft')
        if aircraft_elem is not None:
            # Try to get ICAO aircraft code
            icao_code = aircraft_elem.findtext('icaocode')
            if icao_code and icao_code.strip():
                aircraft_type = icao_code.strip()
            else:
                # Fallback to base_type if icaocode not available
                base_type = aircraft_elem.findtext('base_type')
                if base_type and base_type.strip():
                    aircraft_type = base_type.strip()
        
        flight_plan = FlightPlan(origin_code, dest_code, route, flight_id, aircraft_type)
        
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
        <p><strong>Aircraft Type:</strong> {flight_plan.aircraft_type}</p>
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
        <p><strong>Time:</strong> {waypoint.get_time_formatted_simbrief()}</p>
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
    print(f"   Aircraft Type: {flight_plan.aircraft_type}")
    print(f"   Route: {flight_plan.origin} to {flight_plan.destination}")
    print(f"   Total waypoints: {len(all_waypoints)}")
    print(f"   Route: {flight_plan.route}")
    
    if all_waypoints:
        print(f"\nWaypoints:")
        for i, wp in enumerate(all_waypoints):
            print(f"   {i+1:2d}. {wp.name:12s} {wp.lat:8.4f}, {wp.lon:8.4f} {wp.altitude:6d}ft {wp.get_time_formatted_simbrief()} (elapsed)")

def main():
    """Main function to process SimBrief XML files"""
    parser = argparse.ArgumentParser(description='Extract flight plans from SimBrief XML files')
    parser.add_argument('--files', nargs='+', help='Specific XML files to process (optional)')
    args = parser.parse_args()
    
    try:
        print("SimBrief XML Flight Plan Extractor")
        print("=" * 50)
        
        # Clean up temp directory
        temp_dir = "temp"
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            print("Removed existing temp directory: temp")
        
        # Determine which files to process
        if args.files:
            # Process specific files provided as arguments
            xml_files = []
            for file_path in args.files:
                if os.path.exists(file_path):
                    xml_files.append(file_path)
                else:
                    print(f"Warning: File not found: {file_path}")
            
            if not xml_files:
                print("No valid XML files provided")
                exit(1)
                
            print(f"Processing {len(xml_files)} specified XML files:")
            for xml_file in xml_files:
                print(f"   - {xml_file}")
        else:
            # Process all XML files in xml_files directory (backward compatibility)
            xml_dir = "xml_files"
            if not os.path.exists(xml_dir):
                print(f"XML directory {xml_dir} not found")
                exit(1)
            xml_files = [os.path.join(xml_dir, f) for f in os.listdir(xml_dir) if f.endswith('.xml')]
            if not xml_files:
                print(f"No XML files found in the {xml_dir} directory")
                exit(1)
            print(f"Processing all {len(xml_files)} XML files in {xml_dir}:")
            for xml_file in xml_files:
                print(f"   - {os.path.basename(xml_file)}")
        
        print("\n" + "=" * 50)
        
        # Track flights with same origin-destination to generate unique IDs
        route_counter = {}  # Track count for each origin-destination pair
        flight_counter = 1  # Global flight counter for unique IDs
        
        success_count = 0
        for xml_path in xml_files:
            xml_filename = os.path.basename(xml_path)
            print(f"Processing {xml_filename}...")
            print("----------------------------------------")
            
            # Extract basic info first to determine flight ID
            try:
                tree = ET.parse(xml_path)
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
            
            flight_plan = extract_flight_plan_from_xml(xml_path, flight_id)
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