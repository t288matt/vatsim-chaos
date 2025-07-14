#!/usr/bin/env python3
"""
Check 5 flights for aircraft type data integrity
"""

import json

def check_flight_integrity(flight_id):
    """Check aircraft type for a specific flight across all files."""
    print(f"\n=== Checking {flight_id} ===")
    
    # Check animation_data.json
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        for flight in data.get('flights', []):
            if flight.get('flight_id') == flight_id:
                acft_type = flight.get('aircraft_type', 'MISSING')
                print(f"✅ animation_data.json: {acft_type}")
                break
        else:
            print("❌ animation_data.json: Flight not found")
    except Exception as e:
        print(f"❌ animation_data.json: Error - {e}")
    
    # Check potential_conflict_data.json
    try:
        with open('temp/potential_conflict_data.json', 'r') as f:
            data = json.load(f)
        if 'flights' in data and flight_id in data['flights']:
            acft_type = data['flights'][flight_id].get('aircraft_type', 'MISSING')
            print(f"✅ potential_conflict_data.json: {acft_type}")
        else:
            print("❌ potential_conflict_data.json: Flight not found")
    except Exception as e:
        print(f"❌ potential_conflict_data.json: Error - {e}")
    
    # Check individual flight data file
    try:
        with open(f'temp/{flight_id}_data.json', 'r') as f:
            data = json.load(f)
        acft_type = data.get('aircraft_type', 'MISSING')
        print(f"✅ {flight_id}_data.json: {acft_type}")
    except Exception as e:
        print(f"❌ {flight_id}_data.json: Error - {e}")
    
    # Check routes_with_added_interpolated_points.json
    try:
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            data = json.load(f)
        if flight_id in data:
            acft_type = data[flight_id].get('aircraft_type', 'MISSING')
            print(f"✅ routes_with_added_interpolated_points.json: {acft_type}")
        else:
            print("❌ routes_with_added_interpolated_points.json: Flight not found")
    except Exception as e:
        print(f"❌ routes_with_added_interpolated_points.json: Error - {e}")

def main():
    """Check 5 specific flights."""
    flights_to_check = ['FLT0001', 'FLT0002', 'FLT0003', 'FLT0004', 'FLT0005']
    
    print("🔍 Aircraft Type Data Integrity Check - 5 Flights")
    print("=" * 60)
    
    for flight_id in flights_to_check:
        check_flight_integrity(flight_id)
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print("Expected aircraft types:")
    print("  FLT0001: E190")
    print("  FLT0002: DH8D") 
    print("  FLT0003: PC12")
    print("  FLT0004: S22T")
    print("  FLT0005: DH8D")

if __name__ == "__main__":
    main() 