#!/usr/bin/env python3
"""
Capture baseline data before refactoring.
This script runs the current system and captures key outputs to verify
the refactoring doesn't change the results.
"""

import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import find_potential_conflicts
from find_potential_conflicts import FlightPlan, Waypoint


def create_baseline_test_data():
    """Create consistent test data for baseline capture."""
    flight_plans = [
        FlightPlan("YSBK", "YSSY", "YSBK-YSSY", "FLT0001", "B738"),
        FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0002", "DH8D"),
        FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0003", "PC12")
    ]
    
    # Add waypoints that will create predictable conflicts
    waypoints1 = [
        Waypoint("YSBK", -33.8688, 151.2093, 0, 0, "departure", "airport"),
        Waypoint("WP1", -34.0, 151.0, 10000, 600, "climb", "waypoint"),
        Waypoint("WP2", -35.0, 150.0, 20000, 1200, "cruise", "waypoint"),
        Waypoint("YSSY", -33.9399, 151.1753, 0, 1800, "arrival", "airport")
    ]
    
    waypoints2 = [
        Waypoint("YSCB", -35.2809, 149.1300, 0, 0, "departure", "airport"),
        Waypoint("WP1", -34.0, 151.0, 10000, 600, "climb", "waypoint"),  # Same as FLT0001
        Waypoint("WP2", -35.0, 150.0, 20000, 1200, "cruise", "waypoint"),  # Same as FLT0001
        Waypoint("YSSY", -33.9399, 151.1753, 0, 1800, "arrival", "airport")
    ]
    
    waypoints3 = [
        Waypoint("YSCB", -35.2809, 149.1300, 0, 0, "departure", "airport"),
        Waypoint("WP3", -34.5, 150.5, 15000, 900, "climb", "waypoint"),
        Waypoint("WP4", -34.0, 150.0, 18000, 1500, "cruise", "waypoint"),
        Waypoint("YSSY", -33.9399, 151.1753, 0, 1800, "arrival", "airport")
    ]
    
    for i, waypoints in enumerate([waypoints1, waypoints2, waypoints3]):
        for wp in waypoints:
            flight_plans[i].add_waypoint(wp)
    
    return flight_plans


def capture_conflict_detection_baseline():
    """Capture baseline conflict detection results."""
    print("Capturing conflict detection baseline...")
    
    flight_plans = create_baseline_test_data()
    conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
    
    baseline_data = {
        'timestamp': datetime.now().isoformat(),
        'flight_plans_count': len(flight_plans),
        'conflicts_count': len(conflicts),
        'conflicts': []
    }
    
    for conflict in conflicts:
        baseline_data['conflicts'].append({
            'flight1': conflict['flight1'],
            'flight2': conflict['flight2'],
            'distance': conflict['distance'],
            'altitude_diff': conflict['altitude_diff'],
            'time1': conflict['time1'],
            'time2': conflict['time2'],
            'is_waypoint': conflict['is_waypoint']
        })
    
    return baseline_data


def capture_scheduling_baseline():
    """Capture baseline scheduling results."""
    print("Capturing scheduling baseline...")
    
    flight_plans = create_baseline_test_data()
    conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
    
    if conflicts:
        scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
        
        baseline_data = {
            'timestamp': datetime.now().isoformat(),
            'total_conflicts': scenario['total_conflicts'],
            'departure_schedule': scenario['departure_schedule'],
            'potential_conflicts': []
        }
        
        for conflict in scenario['potential_conflicts']:
            baseline_data['potential_conflicts'].append({
                'flight1': conflict['flight1'],
                'flight2': conflict['flight2'],
                'flight1_arrival': conflict.get('flight1_arrival'),
                'flight2_arrival': conflict.get('flight2_arrival'),
                'time_diff': conflict.get('time_diff')
            })
        
        return baseline_data
    else:
        return {'timestamp': datetime.now().isoformat(), 'total_conflicts': 0}


def capture_function_signatures():
    """Capture function signatures to ensure they don't change."""
    print("Capturing function signatures...")
    
    signatures = {
        'timestamp': datetime.now().isoformat(),
        'functions': {}
    }
    
    # Capture key function signatures
    key_functions = [
        'find_potential_conflicts',
        'optimize_departure_times', 
        'generate_conflict_scenario',
        'calculate_distance_nm',
        'is_conflict_valid'
    ]
    
    for func_name in key_functions:
        if hasattr(find_potential_conflicts, func_name):
            func = getattr(find_potential_conflicts, func_name)
            signatures['functions'][func_name] = {
                'name': func.__name__,
                'module': func.__module__,
                'doc': func.__doc__[:100] if func.__doc__ else None
            }
    
    return signatures


def main():
    """Capture all baseline data."""
    print("=== Capturing Baseline Data for Refactoring ===")
    
    baseline = {
        'conflict_detection': capture_conflict_detection_baseline(),
        'scheduling': capture_scheduling_baseline(),
        'function_signatures': capture_function_signatures()
    }
    
    # Save baseline data
    baseline_file = 'baseline_before_refactoring.json'
    with open(baseline_file, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    print(f"Baseline data saved to {baseline_file}")
    print(f"Conflict detection: {baseline['conflict_detection']['conflicts_count']} conflicts")
    print(f"Scheduling: {baseline['scheduling']['total_conflicts']} total conflicts")
    print("Baseline capture complete!")


if __name__ == '__main__':
    main() 