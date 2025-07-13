#!/usr/bin/env python3
"""
Unit tests for find_potential_conflicts.py
"""

import unittest
import tempfile
import os
import json
import math
from unittest.mock import patch, mock_open, MagicMock
import sys

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import find_potential_conflicts


class TestFindPotentialConflicts(unittest.TestCase):
    """Test cases for conflict analysis functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_flight_plans = [
            find_potential_conflicts.FlightPlan('YSSY', 'YSWG'),
            find_potential_conflicts.FlightPlan('YMER', 'YORG')
        ]
        
        # Add waypoints to flight plans
        wp1 = find_potential_conflicts.Waypoint('EXETA', -34.7963, 149.4166, 20000, 1800, 'cruise')
        wp2 = find_potential_conflicts.Waypoint('AVBEG', -34.7678, 149.4399, 20000, 2100, 'cruise')
        
        self.sample_flight_plans[0].add_waypoint(wp1)
        self.sample_flight_plans[0].add_waypoint(wp2)
        
        # Add departure and arrival waypoints
        dep1 = find_potential_conflicts.Waypoint('YSSY', -33.9399, 151.1753, 0, 0, 'departure')
        arr1 = find_potential_conflicts.Waypoint('YSWG', -35.1653, 147.4664, 0, 3600, 'arrival')
        self.sample_flight_plans[0].set_departure(dep1)
        self.sample_flight_plans[0].set_arrival(arr1)

    def test_calculate_distance_nm(self):
        """Test distance calculation between two points."""
        # Test known distance (Sydney to Melbourne approximately)
        lat1, lon1 = -33.9399, 151.1753  # Sydney
        lat2, lon2 = -37.8136, 144.9631  # Melbourne
        
        distance = find_potential_conflicts.calculate_distance_nm(lat1, lon1, lat2, lon2)
        
        # Should be approximately 400-500 nm
        self.assertGreater(distance, 400)
        self.assertLess(distance, 500)

    def test_calculate_distance_nm_same_point(self):
        """Test distance calculation for same point."""
        lat, lon = -33.9399, 151.1753
        distance = find_potential_conflicts.calculate_distance_nm(lat, lon, lat, lon)
        self.assertAlmostEqual(distance, 0.0, places=2)

    def test_get_compass_direction(self):
        """Test compass direction calculation."""
        # North
        direction = find_potential_conflicts.get_compass_direction(0, 0, 1, 0)
        self.assertEqual(direction, 'N')
        
        # South
        direction = find_potential_conflicts.get_compass_direction(0, 0, -1, 0)
        self.assertEqual(direction, 'S')
        
        # East
        direction = find_potential_conflicts.get_compass_direction(0, 0, 0, 1)
        self.assertEqual(direction, 'E')
        
        # West
        direction = find_potential_conflicts.get_compass_direction(0, 0, 0, -1)
        self.assertEqual(direction, 'W')

    def test_abbreviate_waypoint_name(self):
        """Test waypoint name abbreviation."""
        # Test coordinate waypoint
        coord_name = "-34.7963,149.4166"
        abbreviated = find_potential_conflicts.abbreviate_waypoint_name(coord_name)
        self.assertEqual(abbreviated, "coord")
        
        # Test regular waypoint
        regular_name = "EXETA"
        abbreviated = find_potential_conflicts.abbreviate_waypoint_name(regular_name)
        self.assertEqual(abbreviated, "EXETA")

    def test_is_conflict_valid(self):
        """Test conflict validation logic."""
        wp1 = find_potential_conflicts.Waypoint('TEST1', 0, 0, 20000)
        wp2 = find_potential_conflicts.Waypoint('TEST2', 0.01, 0.01, 20000)
        
        # Calculate distance
        distance = find_potential_conflicts.calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
        altitude_diff = abs(wp1.altitude - wp2.altitude)
        
        # Should be valid conflict (close distance, same altitude)
        is_valid = find_potential_conflicts.is_conflict_valid(wp1, wp2, distance, altitude_diff)
        self.assertTrue(is_valid)
        
        # Test with different altitudes (should still be valid)
        wp2.altitude = 25000
        altitude_diff = abs(wp1.altitude - wp2.altitude)
        is_valid = find_potential_conflicts.is_conflict_valid(wp1, wp2, distance, altitude_diff)
        self.assertTrue(is_valid)

    def test_is_conflict_valid_too_far(self):
        """Test conflict validation with too much separation."""
        wp1 = find_potential_conflicts.Waypoint('TEST1', 0, 0, 20000)
        wp2 = find_potential_conflicts.Waypoint('TEST2', 1, 1, 20000)  # Much further
        
        distance = find_potential_conflicts.calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
        altitude_diff = abs(wp1.altitude - wp2.altitude)
        
        # Should be invalid (too far apart)
        is_valid = find_potential_conflicts.is_conflict_valid(wp1, wp2, distance, altitude_diff)
        self.assertFalse(is_valid)

    def test_is_conflict_valid_altitude_too_different(self):
        """Test conflict validation with too much altitude difference."""
        wp1 = find_potential_conflicts.Waypoint('TEST1', 0, 0, 20000)
        wp2 = find_potential_conflicts.Waypoint('TEST2', 0.01, 0.01, 40000)  # Much higher
        
        distance = find_potential_conflicts.calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
        altitude_diff = abs(wp1.altitude - wp2.altitude)
        
        # Should be invalid (altitude difference too large)
        is_valid = find_potential_conflicts.is_conflict_valid(wp1, wp2, distance, altitude_diff)
        self.assertFalse(is_valid)

    def test_get_phase_for_time(self):
        """Test flight phase detection based on time."""
        waypoints = [
            find_potential_conflicts.Waypoint('DEP', 0, 0, 0, 0, 'departure'),
            find_potential_conflicts.Waypoint('TOC', 0, 0, 20000, 1800, 'climb'),
            find_potential_conflicts.Waypoint('TOD', 0, 0, 20000, 3600, 'cruise'),
            find_potential_conflicts.Waypoint('ARR', 0, 0, 0, 5400, 'arrival')
        ]
        
        # Test different phases
        self.assertEqual(find_potential_conflicts.get_phase_for_time(waypoints, 0), 'departure')
        self.assertEqual(find_potential_conflicts.get_phase_for_time(waypoints, 1800), 'climb')
        self.assertEqual(find_potential_conflicts.get_phase_for_time(waypoints, 2700), 'cruise')
        self.assertEqual(find_potential_conflicts.get_phase_for_time(waypoints, 5400), 'arrival')

    def test_interpolate_route_segments(self):
        """Test route segment interpolation."""
        waypoints = [
            find_potential_conflicts.Waypoint('WP1', 0, 0, 10000, 0),
            find_potential_conflicts.Waypoint('WP2', 1, 1, 20000, 1800)
        ]
        
        segments = find_potential_conflicts.interpolate_route_segments(waypoints)
        
        self.assertGreater(len(segments), 0)
        # Check that segments have required fields
        for segment in segments:
            self.assertIn('lat', segment)
            self.assertIn('lon', segment)
            self.assertIn('altitude', segment)
            self.assertIn('time', segment)

    def test_find_potential_conflicts_basic(self):
        """Test basic conflict detection."""
        conflicts = find_potential_conflicts.find_potential_conflicts(self.sample_flight_plans)
        
        # Should return a list
        self.assertIsInstance(conflicts, list)
        
        # Check structure of conflicts if any found
        if conflicts:
            conflict = conflicts[0]
            self.assertIn('flight1', conflict)
            self.assertIn('flight2', conflict)
            self.assertIn('lat1', conflict)
            self.assertIn('lon1', conflict)
            self.assertIn('lat2', conflict)
            self.assertIn('lon2', conflict)
            self.assertIn('alt1', conflict)
            self.assertIn('alt2', conflict)
            self.assertIn('distance', conflict)

    def test_optimize_departure_times(self):
        """Test departure time optimization."""
        conflicts = find_potential_conflicts.find_potential_conflicts(self.sample_flight_plans)
        
        if conflicts:
            optimization = find_potential_conflicts.optimize_departure_times(self.sample_flight_plans, conflicts)
            
            self.assertIn('departure_times', optimization)
            self.assertIn('conflict_scores', optimization)
            
            # Check that departure times are assigned
            departure_times = optimization['departure_times']
            self.assertGreater(len(departure_times), 0)

    def test_generate_conflict_scenario(self):
        """Test conflict scenario generation."""
        conflicts = find_potential_conflicts.find_potential_conflicts(self.sample_flight_plans)
        
        if conflicts:
            scenario = find_potential_conflicts.generate_conflict_scenario(self.sample_flight_plans, conflicts)
            
            self.assertIn('departure_schedule', scenario)
            self.assertIn('potential_conflicts', scenario)
            self.assertIn('total_conflicts', scenario)
            
            # Check departure schedule structure
            schedule = scenario['departure_schedule']
            if schedule:
                flight_schedule = schedule[0]
                self.assertIn('flight', flight_schedule)
                self.assertIn('departure_time', flight_schedule)
                self.assertIn('conflict_score', flight_schedule)

    def test_filter_duplicate_conflicts(self):
        """Test duplicate conflict filtering."""
        conflicts = [
            {
                'flight1': 'YSSY-YSWG',
                'flight2': 'YMER-YORG',
                'lat1': -34.7963,
                'lon1': 149.4166,
                'lat2': -34.7678,
                'lon2': 149.4399,
                'alt1': 20000,
                'alt2': 20000,
                'distance': 2.0
            },
            {
                'flight1': 'YSSY-YSWG',
                'flight2': 'YMER-YORG',
                'lat1': -34.7964,  # Very close to first
                'lon1': 149.4167,
                'lat2': -34.7679,
                'lon2': 149.4400,
                'alt1': 20000,
                'alt2': 20000,
                'distance': 2.1
            }
        ]
        
        filtered = find_potential_conflicts.filter_duplicate_conflicts(conflicts)
        
        # Should filter out the duplicate
        self.assertLess(len(filtered), len(conflicts))

    def test_format_location(self):
        """Test location formatting."""
        conflict = {
            'is_waypoint': True,
            'waypoint1': 'EXETA',
            'waypoint2': 'AVBEG'
        }
        
        location = find_potential_conflicts.format_location(conflict, [])
        self.assertEqual(location, 'EXETA/AVBEG')

    def test_save_analysis_data(self):
        """Test analysis data saving."""
        analysis_data = {
            'flight_plans': ['YSSY-YSWG', 'YMER-YORG'],
            'potential_conflicts': [],
            'scenario': {
                'departure_schedule': [],
                'potential_conflicts': [],
                'total_conflicts': 0
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('find_potential_conflicts.TEMP_DIRECTORY', temp_dir):
                find_potential_conflicts.save_analysis_data(analysis_data)
                
                # Check that file was created
                json_file = os.path.join(temp_dir, 'conflict_analysis.json')
                self.assertTrue(os.path.exists(json_file))
                
                # Check that data was saved correctly
                with open(json_file, 'r') as f:
                    saved_data = json.load(f)
                
                self.assertEqual(saved_data['flight_plans'], analysis_data['flight_plans'])

    @patch('builtins.print')
    def test_main_function(self, mock_print):
        """Test main function execution."""
        with patch('find_potential_conflicts.find_xml_files') as mock_find:
            with patch('find_potential_conflicts.extract_flight_plans') as mock_extract:
                with patch('find_potential_conflicts.find_potential_conflicts') as mock_find_conflicts:
                    with patch('find_potential_conflicts.generate_conflict_scenario') as mock_scenario:
                        with patch('find_potential_conflicts.save_analysis_data') as mock_save:
                            mock_find.return_value = ['test.xml']
                            mock_extract.return_value = self.sample_flight_plans
                            mock_find_conflicts.return_value = []
                            mock_scenario.return_value = {
                                'departure_schedule': [],
                                'potential_conflicts': [],
                                'total_conflicts': 0
                            }
                            
                            find_potential_conflicts.main()
                            
                            mock_find.assert_called_once()
                            mock_extract.assert_called_once()
                            mock_find_conflicts.assert_called_once()
                            mock_scenario.assert_called_once()
                            mock_save.assert_called_once()


if __name__ == '__main__':
    unittest.main() 