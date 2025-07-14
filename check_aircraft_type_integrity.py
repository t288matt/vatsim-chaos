#!/usr/bin/env python3
"""
Aircraft Type Data Integrity Check
Verifies that aircraft types are present and consistent across all JSON files.
"""

import json
import os
import sys
from pathlib import Path

def check_json_file(file_path, description):
    """Check aircraft type data in a JSON file."""
    print(f"\n=== Checking {description} ===")
    print(f"File: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    aircraft_types = []
    
    if isinstance(data, dict):
        # Check if it's a flight data structure
        if 'aircraft_type' in data:
            acft_type = data['aircraft_type']
            aircraft_types.append(acft_type)
            print(f"✅ Found aircraft_type: {acft_type}")
        elif 'flight_id' in data:
            print(f"⚠️  Flight data found but no aircraft_type: {data.get('flight_id', 'Unknown')}")
        
        # Check if it's a flights array structure
        if 'flights' in data and isinstance(data['flights'], list):
            for flight in data['flights']:
                if isinstance(flight, dict) and 'aircraft_type' in flight:
                    acft_type = flight['aircraft_type']
                    aircraft_types.append(acft_type)
                    flight_id = flight.get('flight_id', 'Unknown')
                    print(f"✅ Flight {flight_id}: {acft_type}")
                elif isinstance(flight, dict) and 'flight_id' in flight:
                    flight_id = flight.get('flight_id', 'Unknown')
                    print(f"⚠️  Flight {flight_id}: No aircraft_type found")
        
        # Check if it's a conflict structure
        if 'flight1' in data and 'flight2' in data:
            print(f"ℹ️  Conflict data: {data.get('flight1')} vs {data.get('flight2')}")
    
    elif isinstance(data, list):
        # Check each item in the list
        for i, item in enumerate(data):
            if isinstance(item, dict):
                if 'aircraft_type' in item:
                    acft_type = item['aircraft_type']
                    aircraft_types.append(acft_type)
                    print(f"✅ Item {i}: {acft_type}")
                elif 'flight_id' in item:
                    flight_id = item.get('flight_id', 'Unknown')
                    print(f"⚠️  Item {i} ({flight_id}): No aircraft_type found")
    
    if aircraft_types:
        print(f"📊 Aircraft types found: {len(aircraft_types)}")
        unique_types = set(aircraft_types)
        print(f"📋 Unique aircraft types: {sorted(unique_types)}")
        return True
    else:
        print("❌ No aircraft types found")
        return False

def main():
    """Main function to check all JSON files."""
    print("🔍 Aircraft Type Data Integrity Check")
    print("=" * 50)
    
    # Files to check
    files_to_check = [
        ("animation/animation_data.json", "Main Animation Data"),
        ("animation/conflict_points.json", "Conflict Points Data"),
        ("temp/potential_conflict_data.json", "Potential Conflict Data"),
        ("temp/routes_with_added_interpolated_points.json", "Routes with Interpolated Points")
    ]
    
    # Check individual flight data files
    temp_dir = Path("temp")
    if temp_dir.exists():
        flight_files = list(temp_dir.glob("FLT*_data.json"))
        for flight_file in flight_files:
            files_to_check.append((str(flight_file), f"Flight Data: {flight_file.stem}"))
    
    results = []
    
    for file_path, description in files_to_check:
        if os.path.exists(file_path):
            success = check_json_file(file_path, description)
            results.append((file_path, success))
        else:
            print(f"\n❌ File not found: {file_path}")
            results.append((file_path, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    successful_checks = sum(1 for _, success in results if success)
    total_checks = len(results)
    
    print(f"Total files checked: {total_checks}")
    print(f"Successful checks: {successful_checks}")
    print(f"Failed checks: {total_checks - successful_checks}")
    
    if successful_checks == total_checks:
        print("✅ All files have proper aircraft type data!")
    else:
        print("⚠️  Some files are missing aircraft type data.")
        for file_path, success in results:
            status = "✅" if success else "❌"
            print(f"{status} {file_path}")

if __name__ == "__main__":
    main() 