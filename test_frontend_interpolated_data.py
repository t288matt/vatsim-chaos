#!/usr/bin/env python3
"""
Frontend Interpolated Data Tests

Tests that the frontend can properly read and process interpolated data format.
Validates the data conversion logic and ensures no regressions.
"""

import json
import os
import sys
from typing import Dict, List, Any

def test_interpolated_data_structure():
    """Test that interpolated data has correct structure"""
    print("🔍 Testing interpolated data structure...")
    
    try:
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            data = json.load(f)
        
        # Check that it's an object with flight data
        assert isinstance(data, dict), "Data should be an object"
        
        # Check for metadata
        assert '_metadata' in data, "Missing _metadata section"
        metadata = data['_metadata']
        assert 'departure_schedule' in metadata, "Missing departure_schedule in metadata"
        assert 'total_flights' in metadata, "Missing total_flights in metadata"
        assert 'total_conflicts' in metadata, "Missing total_conflicts in metadata"
        
        # Check flight data
        flight_count = 0
        for key, value in data.items():
            if key != '_metadata':
                assert isinstance(value, dict), f"Flight {key} should be an object"
                assert 'route' in value, f"Flight {key} missing route"
                assert 'aircraft_type' in value, f"Flight {key} missing aircraft_type"
                flight_count += 1
        
        print(f"✅ Interpolated data structure: {flight_count} flights, {metadata['total_conflicts']} conflicts")
        return True
        
    except Exception as e:
        print(f"❌ Interpolated data structure test failed: {e}")
        return False

def test_waypoint_data_integrity():
    """Test that waypoint data is complete and consistent"""
    print("🔍 Testing waypoint data integrity...")
    
    try:
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            data = json.load(f)
        
        total_waypoints = 0
        
        for flight_id, flight_data in data.items():
            if flight_id == '_metadata':
                continue
                
            route = flight_data.get('route', [])
            assert len(route) > 0, f"Flight {flight_id} has no route waypoints"
            
            for i, wp in enumerate(route):
                # Required fields
                required_fields = ['lat', 'lon', 'altitude', 'time']
                for field in required_fields:
                    assert field in wp, f"Waypoint {i} in {flight_id} missing {field}"
                
                # Validate data types
                assert isinstance(wp['lat'], (int, float)), f"Invalid lat type in {flight_id}"
                assert isinstance(wp['lon'], (int, float)), f"Invalid lon type in {flight_id}"
                assert isinstance(wp['altitude'], (int, float)), f"Invalid altitude type in {flight_id}"
                assert isinstance(wp['time'], str), f"Invalid time type in {flight_id}"
                
                total_waypoints += 1
        
        print(f"✅ Waypoint data integrity: {total_waypoints} waypoints validated")
        return True
        
    except Exception as e:
        print(f"❌ Waypoint data integrity test failed: {e}")
        return False

def test_conflict_data_in_interpolated():
    """Test that conflict data is properly embedded in interpolated data"""
    print("🔍 Testing conflict data in interpolated format...")
    
    try:
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            data = json.load(f)
        
        total_conflicts = 0
        
        for flight_id, flight_data in data.items():
            if flight_id == '_metadata':
                continue
                
            if 'conflicts' in flight_data:
                conflicts = flight_data['conflicts']
                total_conflicts += len(conflicts)
                
                for conflict in conflicts:
                    # Required fields
                    required_fields = ['other_flight', 'conflict_time_utc', 'lat', 'lon', 'alt', 'distance', 'altitude_diff', 'departure_time']
                    for field in required_fields:
                        assert field in conflict, f"Conflict missing {field}"
                    
                    # Validate data types
                    assert isinstance(conflict['lat'], (int, float)), f"Invalid lat type"
                    assert isinstance(conflict['lon'], (int, float)), f"Invalid lon type"
                    assert isinstance(conflict['alt'], (int, float)), f"Invalid alt type"
                    assert isinstance(conflict['distance'], (int, float)), f"Invalid distance type"
        
        print(f"✅ Conflict data in interpolated format: {total_conflicts} conflicts validated")
        return True
        
    except Exception as e:
        print(f"❌ Conflict data in interpolated format test failed: {e}")
        return False

def test_departure_schedule_metadata():
    """Test that departure schedule metadata is complete"""
    print("🔍 Testing departure schedule metadata...")
    
    try:
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            data = json.load(f)
        
        metadata = data['_metadata']
        departure_schedule = metadata['departure_schedule']
        
        # Check that all flights have departure times
        flight_count = 0
        for flight_id, schedule_data in departure_schedule.items():
            assert 'departure_time' in schedule_data, f"Flight {flight_id} missing departure_time"
            assert 'conflicts' in schedule_data, f"Flight {flight_id} missing conflicts count"
            
            # Validate time format (HHMM)
            departure_time = schedule_data['departure_time']
            assert len(departure_time) == 4, f"Invalid departure time format: {departure_time}"
            assert departure_time.isdigit(), f"Invalid departure time format: {departure_time}"
            
            flight_count += 1
        
        print(f"✅ Departure schedule metadata: {flight_count} flights with departure times")
        return True
        
    except Exception as e:
        print(f"❌ Departure schedule metadata test failed: {e}")
        return False

def test_frontend_data_conversion():
    """Test that interpolated data can be converted to frontend format"""
    print("🔍 Testing frontend data conversion...")
    
    try:
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            interpolated_data = json.load(f)
        
        # Simulate frontend conversion logic
        flights = []
        conflicts = []
        
        # Process each flight from interpolated data
        for flight_id, flight_data in interpolated_data.items():
            if flight_id == '_metadata':
                continue
                
            if flight_data and isinstance(flight_data, dict) and 'route' in flight_data:
                # Convert route waypoints to frontend format
                waypoints = []
                for i, wp in enumerate(flight_data['route']):
                    waypoint = {
                        'index': i,
                        'name': wp.get('name', ''),
                        'lat': wp['lat'],
                        'lon': wp['lon'],
                        'altitude': wp['altitude'],
                        'UTC time': wp['time'],
                        'stage': wp.get('stage', '')
                    }
                    waypoints.append(waypoint)
                
                # Find departure and arrival from waypoints
                departure = waypoints[0]['name'] if waypoints else ''
                arrival = ''
                for i in range(len(waypoints) - 1, -1, -1):
                    if waypoints[i]['name'] and not waypoints[i]['name'].startswith('CONFLICT_'):
                        arrival = waypoints[i]['name']
                        break
                
                # Get departure time from metadata
                departure_time = interpolated_data['_metadata']['departure_schedule'].get(flight_id, {}).get('departure_time', '1400')
                
                # Create flight object
                flight = {
                    'flight_id': flight_id,
                    'departure': departure,
                    'arrival': arrival,
                    'departure_time': departure_time,
                    'aircraft_type': flight_data.get('aircraft_type', 'UNK'),
                    'waypoints': waypoints
                }
                
                flights.append(flight)
                
                # Extract conflicts from flight data
                if 'conflicts' in flight_data and isinstance(flight_data['conflicts'], list):
                    for conflict in flight_data['conflicts']:
                        conflicts.append({
                            'flight1': flight_id,
                            'flight2': conflict['other_flight'],
                            'conflict_time': conflict['conflict_time_utc'],
                            'lat': conflict['lat'],
                            'lon': conflict['lon'],
                            'altitude': conflict['alt'],
                            'distance': conflict['distance'],
                            'altitude_diff': conflict['altitude_diff']
                        })
        
        # Validate conversion results
        assert len(flights) > 0, "No flights converted"
        assert all('flight_id' in f for f in flights), "All flights should have flight_id"
        assert all('waypoints' in f for f in flights), "All flights should have waypoints"
        assert all(len(f['waypoints']) > 0 for f in flights), "All flights should have waypoints"
        
        print(f"✅ Frontend data conversion: {len(flights)} flights, {len(conflicts)} conflicts converted")
        return True
        
    except Exception as e:
        print(f"❌ Frontend data conversion test failed: {e}")
        return False

def test_data_consistency():
    """Test that interpolated data is consistent with animation data"""
    print("🔍 Testing data consistency between formats...")
    
    try:
        # Load interpolated data
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            interpolated_data = json.load(f)
        
        # Load animation data for comparison
        with open('animation/animation_data.json', 'r') as f:
            animation_data = json.load(f)
        
        # Compare flight counts
        interpolated_flight_count = len([k for k in interpolated_data.keys() if k != '_metadata'])
        animation_flight_count = len(animation_data['flights'])
        
        assert interpolated_flight_count == animation_flight_count, f"Flight count mismatch: {interpolated_flight_count} vs {animation_flight_count}"
        
        # Compare conflict counts
        interpolated_conflict_count = interpolated_data['_metadata']['total_conflicts']
        animation_conflict_count = sum(len(f.get('conflicts', [])) for f in animation_data['flights'])
        
        assert interpolated_conflict_count == animation_conflict_count, f"Conflict count mismatch: {interpolated_conflict_count} vs {animation_conflict_count}"
        
        print(f"✅ Data consistency: {interpolated_flight_count} flights, {interpolated_conflict_count} conflicts match")
        return True
        
    except Exception as e:
        print(f"❌ Data consistency test failed: {e}")
        return False

def test_unique_conflict_pairs():
    """Test that only unique conflict pairs (unordered, by time) are counted"""
    print("🔍 Testing unique conflict pairs...")
    try:
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            data = json.load(f)
        
        pair_set = set()
        duplicate_count = 0
        all_pairs = []
        for flight_id, flight_data in data.items():
            if flight_id == '_metadata':
                continue
            if 'conflicts' in flight_data:
                for conflict in flight_data['conflicts']:
                    pair = tuple(sorted([flight_id, conflict['other_flight']]))
                    key = (pair[0], pair[1], conflict['conflict_time_utc'])
                    if key in pair_set:
                        duplicate_count += 1
                        all_pairs.append((key, 'DUPLICATE'))
                    else:
                        pair_set.add(key)
                        all_pairs.append((key, 'UNIQUE'))
        print(f"✅ Unique conflict pairs: {len(pair_set)}")
        if duplicate_count > 0:
            print(f"❌ Found {duplicate_count} duplicate conflict pairs!")
            for p in all_pairs:
                if p[1] == 'DUPLICATE':
                    print(f"   Duplicate: {p[0]}")
            return False
        return True
    except Exception as e:
        print(f"❌ Unique conflict pairs test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("🚀 Starting Frontend Interpolated Data Tests")
    print("=" * 50)
    
    tests = [
        test_interpolated_data_structure,
        test_waypoint_data_integrity,
        test_conflict_data_in_interpolated,
        test_departure_schedule_metadata,
        test_frontend_data_conversion,
        test_data_consistency,
        test_unique_conflict_pairs
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All tests passed! Interpolated data is ready for frontend use.")
        return True
    else:
        print("❌ Some tests failed. Fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 