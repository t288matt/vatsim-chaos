#!/usr/bin/env python3
"""
Frontend Data Integrity Tests

Tests the current frontend data to establish baseline before making changes.
Data-led tests that validate actual user-facing functionality.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

def test_animation_data_structure():
    """Test that animation_data.json has correct structure"""
    print("🔍 Testing animation_data.json structure...")
    
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        
        # Check required top-level keys
        required_keys = ['metadata', 'flights', 'conflicts']
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"
        
        # Check metadata
        metadata = data['metadata']
        assert 'total_flights' in metadata, "Missing total_flights in metadata"
        assert 'total_conflicts' in metadata, "Missing total_conflicts in metadata"
        assert 'event_duration' in metadata, "Missing event_duration in metadata"
        
        print(f"✅ Animation data structure: {metadata['total_flights']} flights, {metadata['total_conflicts']} conflicts")
        return True
        
    except Exception as e:
        print(f"❌ Animation data structure test failed: {e}")
        return False

def test_flight_data_integrity():
    """Test that flight data is complete and consistent"""
    print("🔍 Testing flight data integrity...")
    
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        
        flights = data['flights']
        assert len(flights) > 0, "No flights found"
        
        # Test each flight
        for flight in flights:
            # Required fields
            required_fields = ['flight_id', 'departure', 'arrival', 'departure_time', 'aircraft_type', 'waypoints']
            for field in required_fields:
                assert field in flight, f"Flight {flight.get('flight_id', 'UNKNOWN')} missing {field}"
            
            # Test waypoints
            waypoints = flight['waypoints']
            assert len(waypoints) > 0, f"Flight {flight['flight_id']} has no waypoints"
            
            for wp in waypoints:
                wp_required = ['lat', 'lon', 'altitude', 'UTC time']
                for field in wp_required:
                    assert field in wp, f"Waypoint in {flight['flight_id']} missing {field}"
        
        print(f"✅ Flight data integrity: {len(flights)} flights validated")
        return True
        
    except Exception as e:
        print(f"❌ Flight data integrity test failed: {e}")
        return False

def test_conflict_data_integrity():
    """Test that conflict data is complete and consistent"""
    print("🔍 Testing conflict data integrity...")
    
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        
        flights = data['flights']
        total_conflicts = 0
        
        # Test conflicts embedded in each flight
        for flight in flights:
            if 'conflicts' in flight:
                conflicts = flight['conflicts']
                total_conflicts += len(conflicts)
                
                for conflict in conflicts:
                    # Required fields
                    required_fields = ['other_flight', 'conflict_time_utc', 'lat', 'lon', 'alt', 'distance', 'altitude_diff', 'departure_time']
                    for field in required_fields:
                        assert field in conflict, f"Conflict missing {field}"
                    
                    # Validate data types
                    assert isinstance(conflict['lat'], (int, float)), f"Invalid lat type: {type(conflict['lat'])}"
                    assert isinstance(conflict['lon'], (int, float)), f"Invalid lon type: {type(conflict['lon'])}"
                    assert isinstance(conflict['alt'], (int, float)), f"Invalid alt type: {type(conflict['alt'])}"
                    assert isinstance(conflict['distance'], (int, float)), f"Invalid distance type: {type(conflict['distance'])}"
        
        print(f"✅ Conflict data integrity: {total_conflicts} conflicts validated")
        return True
        
    except Exception as e:
        print(f"❌ Conflict data integrity test failed: {e}")
        return False

def test_timing_consistency():
    """Test that timing data is consistent across flights"""
    print("🔍 Testing timing consistency...")
    
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        
        flights = data['flights']
        
        # Check that all flights have departure times
        departure_times = set()
        for flight in flights:
            departure_time = flight['departure_time']
            departure_times.add(departure_time)
            
            # Validate time format (HHMM)
            assert len(departure_time) == 4, f"Invalid departure time format: {departure_time}"
            assert departure_time.isdigit(), f"Invalid departure time format: {departure_time}"
        
        # Check that waypoint times are consistent
        for flight in flights:
            waypoints = flight['waypoints']
            for wp in waypoints:
                utc_time = wp['UTC time']
                assert len(utc_time) == 4, f"Invalid UTC time format: {utc_time}"
                assert utc_time.isdigit(), f"Invalid UTC time format: {utc_time}"
        
        print(f"✅ Timing consistency: {len(departure_times)} unique departure times")
        return True
        
    except Exception as e:
        print(f"❌ Timing consistency test failed: {e}")
        return False

def test_geographic_bounds():
    """Test that geographic data is within expected bounds"""
    print("🔍 Testing geographic bounds...")
    
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        
        flights = data['flights']
        
        # Collect all coordinates
        all_lats = []
        all_lons = []
        
        # Flight waypoints
        for flight in flights:
            for wp in flight['waypoints']:
                all_lats.append(wp['lat'])
                all_lons.append(wp['lon'])
            
            # Conflict points embedded in flights
            if 'conflicts' in flight:
                for conflict in flight['conflicts']:
                    all_lats.append(conflict['lat'])
                    all_lons.append(conflict['lon'])
        
        # Check bounds (Australia)
        min_lat, max_lat = min(all_lats), max(all_lats)
        min_lon, max_lon = min(all_lons), max(all_lons)
        
        # Validate reasonable bounds for Australia
        assert -45 <= min_lat <= -10, f"Latitude out of bounds: {min_lat}"
        assert -45 <= max_lat <= -10, f"Latitude out of bounds: {max_lat}"
        assert 110 <= min_lon <= 155, f"Longitude out of bounds: {min_lon}"
        assert 110 <= max_lon <= 155, f"Longitude out of bounds: {max_lon}"
        
        print(f"✅ Geographic bounds: Lat {min_lat:.2f} to {max_lat:.2f}, Lon {min_lon:.2f} to {max_lon:.2f}")
        return True
        
    except Exception as e:
        print(f"❌ Geographic bounds test failed: {e}")
        return False

def test_altitude_ranges():
    """Test that altitude data is within reasonable ranges"""
    print("🔍 Testing altitude ranges...")
    
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        
        flights = data['flights']
        
        # Collect all altitudes
        all_altitudes = []
        
        # Flight waypoints
        for flight in flights:
            for wp in flight['waypoints']:
                all_altitudes.append(wp['altitude'])
            
            # Conflict points embedded in flights
            if 'conflicts' in flight:
                for conflict in flight['conflicts']:
                    all_altitudes.append(conflict['alt'])
        
        # Check reasonable altitude ranges
        min_alt, max_alt = min(all_altitudes), max(all_altitudes)
        
        # Validate reasonable bounds for aircraft
        assert 0 <= min_alt <= 50000, f"Altitude out of bounds: {min_alt}"
        assert 0 <= max_alt <= 50000, f"Altitude out of bounds: {max_alt}"
        
        print(f"✅ Altitude ranges: {min_alt} to {max_alt} feet")
        return True
        
    except Exception as e:
        print(f"❌ Altitude ranges test failed: {e}")
        return False

def test_conflict_detection_accuracy():
    """Test that conflict detection produces reasonable results"""
    print("🔍 Testing conflict detection accuracy...")
    
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        
        flights = data['flights']
        total_conflicts = 0
        
        # Check conflicts embedded in each flight
        for flight in flights:
            if 'conflicts' in flight:
                conflicts = flight['conflicts']
                total_conflicts += len(conflicts)
                
                for conflict in conflicts:
                    distance = conflict['distance']
                    altitude_diff = conflict['altitude_diff']
                    
                    # Distance should be small (conflict threshold)
                    assert 0 <= distance <= 10, f"Unreasonable conflict distance: {distance}nm"
                    
                    # Altitude difference should be small (conflict threshold)
                    assert 0 <= altitude_diff <= 1000, f"Unreasonable altitude difference: {altitude_diff}ft"
        
        print(f"✅ Conflict detection accuracy: {total_conflicts} conflicts with reasonable values")
        return True
        
    except Exception as e:
        print(f"❌ Conflict detection accuracy test failed: {e}")
        return False

def test_user_workflow_simulation():
    """Simulate user workflow to test end-to-end functionality"""
    print("🔍 Testing user workflow simulation...")
    
    try:
        with open('animation/animation_data.json', 'r') as f:
            data = json.load(f)
        
        flights = data['flights']
        
        # Count total conflicts
        total_conflicts = 0
        for flight in flights:
            if 'conflicts' in flight:
                total_conflicts += len(flight['conflicts'])
        
        # Simulate what a user would see
        print(f"📊 User would see:")
        print(f"   - {len(flights)} flights")
        print(f"   - {total_conflicts} conflicts")
        
        # Check that flights have realistic routes
        route_count = 0
        for flight in flights:
            if flight['departure'] and flight['arrival']:
                route_count += 1
                print(f"   - {flight['flight_id']}: {flight['departure']} → {flight['arrival']} ({flight['aircraft_type']})")
        
        assert route_count > 0, "No valid routes found"
        
        # Check that conflicts involve real flights
        conflict_flights = set()
        for flight in flights:
            if 'conflicts' in flight:
                for conflict in flight['conflicts']:
                    conflict_flights.add(conflict['other_flight'])
        
        flight_ids = {f['flight_id'] for f in flights}
        assert conflict_flights.issubset(flight_ids), "Conflicts reference non-existent flights"
        
        print(f"✅ User workflow simulation: {route_count} routes, {len(conflict_flights)} flights in conflicts")
        return True
        
    except Exception as e:
        print(f"❌ User workflow simulation test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("🚀 Starting Frontend Data Integrity Tests")
    print("=" * 50)
    
    tests = [
        test_animation_data_structure,
        test_flight_data_integrity,
        test_conflict_data_integrity,
        test_timing_consistency,
        test_geographic_bounds,
        test_altitude_ranges,
        test_conflict_detection_accuracy,
        test_user_workflow_simulation
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
        print("✅ All tests passed! Baseline established.")
        return True
    else:
        print("❌ Some tests failed. Fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 