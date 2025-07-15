#!/usr/bin/env python3
"""
Comprehensive Test Suite for ATC Conflict Analysis System
Tests current functionality before refactoring to ensure no regressions.

This test suite includes:
1. Unit tests for individual functions
2. Integration tests for workflow components
3. Regression tests with data validation
4. Data-driven tests to verify output consistency
"""

import json
import os
import sys
import tempfile
import shutil
from typing import Dict, List, Any
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we'll be testing
import find_potential_conflicts
import generate_schedule_conflicts
import env
from find_potential_conflicts import FlightPlan, Waypoint, Conflict


class TestConflictDetection(unittest.TestCase):
    """Unit tests for conflict detection functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.sample_waypoints = [
            Waypoint("DEP", -33.8688, 151.2093, 0, 0, "departure", "airport"),
            Waypoint("WP1", -34.0, 151.0, 10000, 600, "climb", "waypoint"),
            Waypoint("WP2", -35.0, 150.0, 20000, 1200, "cruise", "waypoint"),
            Waypoint("ARR", -36.0, 149.0, 0, 1800, "arrival", "airport")
        ]
        
        self.flight_plan1 = FlightPlan("YSBK", "YSSY", "YSBK-YSSY", "FLT0001", "B738")
        for wp in self.sample_waypoints:
            self.flight_plan1.add_waypoint(wp)
        
        self.flight_plan2 = FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0002", "DH8D")
        # Create a flight plan that will conflict with flight_plan1
        conflict_waypoints = [
            Waypoint("DEP2", -34.0, 151.0, 0, 0, "departure", "airport"),
            Waypoint("WP1", -34.0, 151.0, 10000, 600, "climb", "waypoint"),  # Same location as FLT0001
            Waypoint("WP2", -35.0, 150.0, 20000, 1200, "cruise", "waypoint"),
            Waypoint("ARR2", -36.0, 149.0, 0, 1800, "arrival", "airport")
        ]
        for wp in conflict_waypoints:
            self.flight_plan2.add_waypoint(wp)
    
    def test_waypoint_creation(self):
        """Test Waypoint class creation and methods."""
        wp = Waypoint("TEST", -33.0, 151.0, 10000, 600, "climb", "waypoint")
        self.assertEqual(wp.name, "TEST")
        self.assertEqual(wp.lat, -33.0)
        self.assertEqual(wp.lon, 151.0)
        self.assertEqual(wp.altitude, 10000)
        self.assertEqual(wp.get_time_minutes(), 10.0)  # 600 seconds = 10 minutes
    
    def test_flight_plan_creation(self):
        """Test FlightPlan class creation and methods."""
        self.assertEqual(self.flight_plan1.origin, "YSBK")
        self.assertEqual(self.flight_plan1.destination, "YSSY")
        self.assertEqual(self.flight_plan1.flight_id, "FLT0001")
        self.assertEqual(self.flight_plan1.aircraft_type, "B738")
        self.assertEqual(len(self.flight_plan1.waypoints), 4)
        self.assertEqual(self.flight_plan1.get_route_identifier(), "FLT0001")
    
    def test_distance_calculation(self):
        """Test distance calculation between coordinates."""
        lat1, lon1 = -33.8688, 151.2093  # Sydney
        lat2, lon2 = -35.2809, 149.1300  # Canberra
        distance = find_potential_conflicts.calculate_distance_nm(lat1, lon1, lat2, lon2)
        self.assertGreater(distance, 100)  # Should be roughly 150nm
        self.assertLess(distance, 200)
    
    def test_conflict_detection_basic(self):
        """Test basic conflict detection between two flight plans."""
        flight_plans = [self.flight_plan1, self.flight_plan2]
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        
        # Should find at least one conflict since waypoints overlap
        self.assertGreater(len(conflicts), 0)
        
        # Check conflict structure
        if conflicts:
            conflict = conflicts[0]
            self.assertIn('flight1', conflict)
            self.assertIn('flight2', conflict)
            self.assertIn('distance', conflict)
            self.assertIn('altitude_diff', conflict)
            self.assertIn('time1', conflict)
            self.assertIn('time2', conflict)


class TestSchedulingLogic(unittest.TestCase):
    """Unit tests for scheduling functionality."""
    
    def setUp(self):
        """Set up test data for scheduling tests."""
        self.sample_conflicts = [
            {
                'flight1': 'FLT0001',
                'flight2': 'FLT0002',
                'flight1_idx': 0,
                'flight2_idx': 1,
                'time1': 10.0,
                'time2': 12.0,
                'distance': 2.5,
                'altitude_diff': 500
            }
        ]
        
        self.sample_flight_plans = [
            FlightPlan("YSBK", "YSSY", "YSBK-YSSY", "FLT0001", "B738"),
            FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0002", "DH8D")
        ]
    
    def test_optimize_departure_times_structure(self):
        """Test that optimize_departure_times returns correct structure."""
        result = find_potential_conflicts.optimize_departure_times(
            self.sample_flight_plans, self.sample_conflicts
        )
        
        self.assertIn('departure_times', result)
        self.assertIn('conflict_scores', result)
        self.assertIsInstance(result['departure_times'], dict)
        self.assertIsInstance(result['conflict_scores'], dict)
    
    def test_generate_conflict_scenario_structure(self):
        """Test that generate_conflict_scenario returns correct structure."""
        result = find_potential_conflicts.generate_conflict_scenario(
            self.sample_flight_plans, self.sample_conflicts
        )
        
        self.assertIn('departure_schedule', result)
        self.assertIn('potential_conflicts', result)
        self.assertIn('total_conflicts', result)
        self.assertIsInstance(result['departure_schedule'], list)
        self.assertIsInstance(result['potential_conflicts'], list)
        self.assertIsInstance(result['total_conflicts'], int)


class TestEnvironmentConfiguration(unittest.TestCase):
    """Unit tests for environment configuration."""
    
    def test_env_constants_exist(self):
        """Test that all required environment constants exist."""
        required_constants = [
            'LATERAL_SEPARATION_THRESHOLD',
            'VERTICAL_SEPARATION_THRESHOLD', 
            'MIN_ALTITUDE_THRESHOLD',
            'MIN_DEPARTURE_SEPARATION_MINUTES',
            'MIN_SAME_ROUTE_SEPARATION_MINUTES',
            'BATCH_SIZE',
            'INTERPOLATION_SPACING_NM',
            'NO_CONFLICT_AIRPORT_DISTANCES'
        ]
        
        for constant in required_constants:
            self.assertTrue(hasattr(env, constant), f"Missing constant: {constant}")
    
    def test_env_constants_values(self):
        """Test that environment constants have reasonable values."""
        self.assertGreater(env.LATERAL_SEPARATION_THRESHOLD, 0)
        self.assertGreater(env.VERTICAL_SEPARATION_THRESHOLD, 0)
        self.assertGreater(env.MIN_ALTITUDE_THRESHOLD, 0)
        self.assertGreater(env.MIN_DEPARTURE_SEPARATION_MINUTES, 0)
        self.assertGreater(env.MIN_SAME_ROUTE_SEPARATION_MINUTES, 0)
        self.assertGreater(env.BATCH_SIZE, 0)
        self.assertGreater(env.INTERPOLATION_SPACING_NM, 0)
        self.assertIsInstance(env.NO_CONFLICT_AIRPORT_DISTANCES, list)


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for the complete workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_temp = "temp"
        
        # Create test data structure
        os.makedirs(os.path.join(self.test_dir, "temp"), exist_ok=True)
        
        # Create sample flight data files
        self.create_test_flight_data()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_flight_data(self):
        """Create sample flight data files for testing."""
        test_flights = [
            {
                "origin": "YSBK",
                "destination": "YSSY", 
                "route": "YSBK-YSSY",
                "flight_id": "FLT0001",
                "aircraft_type": "B738",
                "departure": {
                    "name": "YSBK",
                    "lat": -33.8688,
                    "lon": 151.2093,
                    "altitude": 0,
                    "time_seconds": 0,
                    "stage": "departure",
                    "type": "airport"
                },
                "waypoints": [
                    {
                        "name": "WP1",
                        "lat": -34.0,
                        "lon": 151.0,
                        "altitude": 10000,
                        "time_seconds": 600,
                        "stage": "climb",
                        "type": "waypoint"
                    }
                ]
            },
            {
                "origin": "YSCB",
                "destination": "YSSY",
                "route": "YSCB-YSSY", 
                "flight_id": "FLT0002",
                "aircraft_type": "DH8D",
                "departure": {
                    "name": "YSCB",
                    "lat": -35.2809,
                    "lon": 149.1300,
                    "altitude": 0,
                    "time_seconds": 0,
                    "stage": "departure",
                    "type": "airport"
                },
                "waypoints": [
                    {
                        "name": "WP1",
                        "lat": -34.0,
                        "lon": 151.0,
                        "altitude": 10000,
                        "time_seconds": 600,
                        "stage": "climb",
                        "type": "waypoint"
                    }
                ]
            }
        ]
        
        for i, flight_data in enumerate(test_flights):
            filename = f"FLT000{i+1}_data.json"
            filepath = os.path.join(self.test_dir, "temp", filename)
            with open(filepath, 'w') as f:
                json.dump(flight_data, f)
    
    @patch('find_potential_conflicts.TEMP_DIRECTORY', 'temp')
    def test_end_to_end_workflow(self):
        """Test the complete workflow from flight data to conflict report."""
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        try:
            # Test flight plan extraction
            flight_plans = find_potential_conflicts.extract_flight_plans()
            self.assertEqual(len(flight_plans), 2)
            self.assertEqual(flight_plans[0].flight_id, "FLT0001")
            self.assertEqual(flight_plans[1].flight_id, "FLT0002")
            
            # Test conflict detection
            conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
            self.assertIsInstance(conflicts, list)
            
            # Test scheduling
            if conflicts:
                scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
                self.assertIn('departure_schedule', scenario)
                self.assertIn('potential_conflicts', scenario)
                self.assertIn('total_conflicts', scenario)
            
        finally:
            os.chdir(original_cwd)


class TestDataValidation(unittest.TestCase):
    """Data-driven tests to validate output consistency."""
    
    def test_conflict_data_structure(self):
        """Test that conflict data has consistent structure."""
        # Create test flight plans
        flight_plans = [
            FlightPlan("YSBK", "YSSY", "YSBK-YSSY", "FLT0001", "B738"),
            FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0002", "DH8D")
        ]
        
        # Add waypoints that will create a conflict
        for fp in flight_plans:
            fp.add_waypoint(Waypoint("WP1", -34.0, 151.0, 10000, 600, "climb", "waypoint"))
        
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        
        if conflicts:
            conflict = conflicts[0]
            required_fields = [
                'flight1', 'flight2', 'lat1', 'lon1', 'lat2', 'lon2',
                'alt1', 'alt2', 'distance', 'altitude_diff', 'time1', 'time2',
                'stage1', 'stage2', 'is_waypoint'
            ]
            
            for field in required_fields:
                self.assertIn(field, conflict, f"Missing field: {field}")
            
            # Validate data types
            self.assertIsInstance(conflict['distance'], (int, float))
            self.assertIsInstance(conflict['altitude_diff'], int)
            self.assertIsInstance(conflict['time1'], (int, float))
            self.assertIsInstance(conflict['time2'], (int, float))
            self.assertIsInstance(conflict['is_waypoint'], bool)
    
    def test_scheduling_data_structure(self):
        """Test that scheduling data has consistent structure."""
        flight_plans = [
            FlightPlan("YSBK", "YSSY", "YSBK-YSSY", "FLT0001", "B738"),
            FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0002", "DH8D")
        ]
        
        # Create a simple conflict
        conflicts = [{
            'flight1': 'FLT0001',
            'flight2': 'FLT0002',
            'flight1_idx': 0,
            'flight2_idx': 1,
            'time1': 10.0,
            'time2': 12.0,
            'distance': 2.5,
            'altitude_diff': 500
        }]
        
        scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
        
        # Validate departure schedule structure
        for schedule_item in scenario['departure_schedule']:
            required_fields = ['flight', 'departure_time', 'conflict_score']
            for field in required_fields:
                self.assertIn(field, schedule_item, f"Missing field: {field}")
            
            self.assertIsInstance(schedule_item['departure_time'], int)
            self.assertIsInstance(schedule_item['conflict_score'], int)
    
    def test_conflict_thresholds(self):
        """Test that conflicts respect the defined thresholds."""
        flight_plans = [
            FlightPlan("YSBK", "YSSY", "YSBK-YSSY", "FLT0001", "B738"),
            FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0002", "DH8D")
        ]
        
        # Add waypoints that will create a conflict
        for fp in flight_plans:
            fp.add_waypoint(Waypoint("WP1", -34.0, 151.0, 10000, 600, "climb", "waypoint"))
        
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        
        for conflict in conflicts:
            # Check lateral separation threshold
            self.assertLess(conflict['distance'], env.LATERAL_SEPARATION_THRESHOLD)
            
            # Check vertical separation threshold
            self.assertLess(conflict['altitude_diff'], env.VERTICAL_SEPARATION_THRESHOLD)
            
            # Check minimum altitude threshold
            self.assertGreater(conflict['alt1'], env.MIN_ALTITUDE_THRESHOLD)
            self.assertGreater(conflict['alt2'], env.MIN_ALTITUDE_THRESHOLD)


class TestRegressionBaseline(unittest.TestCase):
    """Regression tests to establish baseline behavior."""
    
    def test_conflict_count_consistency(self):
        """Test that conflict detection produces consistent results."""
        flight_plans = [
            FlightPlan("YSBK", "YSSY", "YSBK-YSSY", "FLT0001", "B738"),
            FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0002", "DH8D")
        ]
        
        # Add identical waypoints to both flights
        for fp in flight_plans:
            fp.add_waypoint(Waypoint("WP1", -34.0, 151.0, 10000, 600, "climb", "waypoint"))
            fp.add_waypoint(Waypoint("WP2", -35.0, 150.0, 20000, 1200, "cruise", "waypoint"))
        
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        
        # Should find conflicts at both waypoints
        self.assertGreater(len(conflicts), 0)
        
        # All conflicts should be between the same two flights
        for conflict in conflicts:
            self.assertIn(conflict['flight1'], ['FLT0001', 'FLT0002'])
            self.assertIn(conflict['flight2'], ['FLT0001', 'FLT0002'])
    
    def test_scheduling_consistency(self):
        """Test that scheduling produces consistent results."""
        flight_plans = [
            FlightPlan("YSBK", "YSSY", "YSBK-YSSY", "FLT0001", "B738"),
            FlightPlan("YSCB", "YSSY", "YSCB-YSSY", "FLT0002", "DH8D")
        ]
        
        conflicts = [{
            'flight1': 'FLT0001',
            'flight2': 'FLT0002',
            'flight1_idx': 0,
            'flight2_idx': 1,
            'time1': 10.0,
            'time2': 12.0,
            'distance': 2.5,
            'altitude_diff': 500
        }]
        
        # Run scheduling multiple times
        results = []
        for _ in range(3):
            scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
            results.append(scenario)
        
        # Results should be consistent
        for i in range(1, len(results)):
            self.assertEqual(results[i]['total_conflicts'], results[0]['total_conflicts'])
            self.assertEqual(len(results[i]['departure_schedule']), len(results[0]['departure_schedule']))


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2) 