#!/usr/bin/env python3
"""
Unit Tests for ATC Conflict Scheduler

Tests the refactored scheduling algorithm that maximizes unique aircraft pairs in conflict.
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from generate_schedule_conflicts import ConflictScheduler, datetime_to_utc_hhmm, minutes_to_utc_hhmm

class TestConflictScheduler(unittest.TestCase):
    """Test cases for the ConflictScheduler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scheduler = ConflictScheduler("14:00", "18:00", verbose=False)
        self.scheduler.start_time = datetime.strptime("14:00", "%H:%M")
        self.scheduler.end_time = datetime.strptime("18:00", "%H:%M")
        
        # Sample conflict data
        self.sample_conflicts = [
            {
                'flight1': 'YMES-YSRI',
                'flight2': 'YSSY-YSWG',
                'time1': 40.36,  # YMES-YSRI conflict time (minutes after departure)
                'time2': 24.07,  # YSSY-YSWG conflict time (minutes after departure)
                'distance': 2.61,
                'altitude_diff': 519,
                'lat1': -34.7096,
                'lon1': 149.6681,
                'lat2': -34.7255,
                'lon2': 149.7174,
                'alt1': 19481,
                'alt2': 20000,
                'stage1': 'cruise',
                'stage2': 'cruise',
                'waypoint1': '-34.7096,149.6681',
                'waypoint2': '-34.7255,149.7174',
                'conflict_type': 'enroute',
                'is_waypoint': False,
                'segment1': 'CB-AKMIR',
                'segment2': 'EXETA-AVBEG'
            },
            {
                'flight1': 'YSNW-YWLM',
                'flight2': 'YSSY-YSWG',
                'time1': 7.26,   # YSNW-YWLM conflict time
                'time2': 12.57,  # YSSY-YSWG conflict time
                'distance': 1.75,
                'altitude_diff': 823,
                'lat1': -34.4318,
                'lon1': 150.6207,
                'lat2': -34.4140,
                'lon2': 150.6487,
                'alt1': 19177,
                'alt2': 20000,
                'stage1': 'climb',
                'stage2': 'cruise',
                'waypoint1': '-34.4318,150.6207',
                'waypoint2': '-34.4140,150.6487',
                'conflict_type': 'enroute',
                'is_waypoint': False,
                'segment1': 'NWA-TOC',
                'segment2': 'TOC-EXETA'
            }
        ]
        
        self.sample_data = {
            'flight_plans': ['YMER-YORG', 'YMES-YSRI', 'YSNW-YWLM', 'YSSY-YSWG'],
            'scenario': {
                'potential_conflicts': self.sample_conflicts,
                'total_conflicts': 2
            }
        }

    def test_parse_time_valid(self):
        """Test parsing valid time strings."""
        self.assertEqual(self.scheduler._parse_time("14:00"), datetime.strptime("14:00", "%H:%M"))
        self.assertEqual(self.scheduler._parse_time("18:30"), datetime.strptime("18:30", "%H:%M"))
        self.assertEqual(self.scheduler._parse_time("09:15"), datetime.strptime("09:15", "%H:%M"))

    def test_parse_time_invalid(self):
        """Test parsing invalid time strings."""
        with self.assertRaises(SystemExit):
            self.scheduler._parse_time("25:00")  # Invalid hour
        with self.assertRaises(SystemExit):
            self.scheduler._parse_time("14:60")  # Invalid minute
        with self.assertRaises(SystemExit):
            self.scheduler._parse_time("14.00")  # Wrong format

    def test_calculate_duration(self):
        """Test event duration calculation."""
        self.assertEqual(self.scheduler._calculate_duration(), 240)  # 4 hours = 240 minutes

    def test_find_aircraft_with_longest_time_to_first_conflict(self):
        """Test finding aircraft with longest time to first conflict."""
        # YMES-YSRI has conflict at 40.36 minutes (longest)
        # YSNW-YWLM has conflict at 7.26 minutes
        # YSSY-YSWG has conflicts at 24.07 and 12.57 minutes (earliest is 12.57)
        
        result = self.scheduler.find_aircraft_with_longest_time_to_first_conflict(self.sample_conflicts)
        self.assertEqual(result, 'YMES-YSRI')  # Should be YMES-YSRI with 40.36 minutes

    def test_find_aircraft_with_longest_time_no_conflicts(self):
        """Test handling when no conflicts exist."""
        result = self.scheduler.find_aircraft_with_longest_time_to_first_conflict([])
        self.assertIsNone(result)

    def test_calculate_conflict_score(self):
        """Test conflict score calculation for greedy selection."""
        scheduled_aircraft = {'YMES-YSRI', 'YSSY-YSWG'}
        all_aircraft = ['YMER-YORG', 'YMES-YSRI', 'YSNW-YWLM', 'YSSY-YSWG']
        
        # YSNW-YWLM should have score: 1 immediate conflict (with YSSY-YSWG) * 10 + 0 future potential = 10
        score = self.scheduler.calculate_conflict_score('YSNW-YWLM', scheduled_aircraft, self.sample_conflicts, all_aircraft)
        self.assertEqual(score, 10)
        
        # YMER-YORG should have score: 0 immediate conflicts * 10 + 0 future potential = 0
        score = self.scheduler.calculate_conflict_score('YMER-YORG', scheduled_aircraft, self.sample_conflicts, all_aircraft)
        self.assertEqual(score, 0)

    def test_calculate_conflict_score_with_future_potential(self):
        """Test conflict score with future potential conflicts."""
        scheduled_aircraft = {'YMES-YSRI'}  # Only one aircraft scheduled
        all_aircraft = ['YMER-YORG', 'YMES-YSRI', 'YSNW-YWLM', 'YSSY-YSWG']
        
        # YSSY-YSWG should have: 1 immediate conflict (with YMES-YSRI) * 10 + 1 future potential (with YSNW-YWLM) = 11
        score = self.scheduler.calculate_conflict_score('YSSY-YSWG', scheduled_aircraft, self.sample_conflicts, all_aircraft)
        self.assertEqual(score, 11)

    def test_find_optimal_departure_time(self):
        """Test finding optimal departure time based on conflict timing."""
        scheduled_aircraft = {
            'YMES-YSRI': datetime.strptime("14:00", "%H:%M"),
            'YSSY-YSWG': datetime.strptime("14:05", "%H:%M")
        }
        all_aircraft = ['YMER-YORG', 'YMES-YSRI', 'YSNW-YWLM', 'YSSY-YSWG']
        
        # Test YSNW-YWLM scheduling
        departure_time, conflict_count = self.scheduler.find_optimal_departure_time(
            'YSNW-YWLM', scheduled_aircraft, self.sample_conflicts, all_aircraft
        )
        
        # Should find a valid departure time that creates conflicts
        self.assertIsNotNone(departure_time)
        self.assertGreater(conflict_count, 0)

    def test_find_optimal_departure_time_no_conflicts(self):
        """Test finding departure time when aircraft has no conflicts."""
        scheduled_aircraft = {'YMES-YSRI': datetime.strptime("14:00", "%H:%M")}
        all_aircraft = ['YMER-YORG', 'YMES-YSRI', 'YSNW-YWLM', 'YSSY-YSWG']
        
        # YMER-YORG has no conflicts in sample data
        departure_time, conflict_count = self.scheduler.find_optimal_departure_time(
            'YMER-YORG', scheduled_aircraft, self.sample_conflicts, all_aircraft
        )
        
        # Should return fallback time with 0 conflicts
        self.assertIsNotNone(departure_time)
        self.assertEqual(conflict_count, 0)

    def test_validate_and_adjust_departure_time_within_window(self):
        """Test departure time validation within event window."""
        scheduled_aircraft = {}
        departure_time = datetime.strptime("15:30", "%H:%M")  # Within 14:00-18:00 window
        
        result = self.scheduler._validate_and_adjust_departure_time(departure_time, 'YMES-YSRI', scheduled_aircraft)
        self.assertEqual(result, departure_time)  # Should be unchanged

    def test_validate_and_adjust_departure_time_before_window(self):
        """Test departure time adjustment when before event window."""
        scheduled_aircraft = {}
        departure_time = datetime.strptime("13:30", "%H:%M")  # Before 14:00 start
        
        result = self.scheduler._validate_and_adjust_departure_time(departure_time, 'YMES-YSRI', scheduled_aircraft)
        self.assertEqual(result, self.scheduler.start_time)  # Should be clamped to start time

    def test_validate_and_adjust_departure_time_after_window(self):
        """Test departure time adjustment when after event window."""
        scheduled_aircraft = {}
        departure_time = datetime.strptime("19:30", "%H:%M")  # After 18:00 end
        
        result = self.scheduler._validate_and_adjust_departure_time(departure_time, 'YMES-YSRI', scheduled_aircraft)
        self.assertEqual(result, self.scheduler.end_time)  # Should be clamped to end time

    def test_validate_and_adjust_departure_time_same_airport_violation(self):
        """Test departure time adjustment for same airport violation."""
        # Both aircraft from YMES airport
        scheduled_aircraft = {'YMES-YSRI': datetime.strptime("14:00", "%H:%M")}
        departure_time = datetime.strptime("14:01", "%H:%M")  # Only 1 minute apart (violates 2-minute rule)
        
        result = self.scheduler._validate_and_adjust_departure_time(departure_time, 'YMES-YORG', scheduled_aircraft)
        # Should be adjusted to 14:02 (2 minutes after 14:00)
        expected_time = datetime.strptime("14:02", "%H:%M")
        self.assertEqual(result, expected_time)

    def test_validate_and_adjust_departure_time_different_airports(self):
        """Test that different airports can depart at same time."""
        scheduled_aircraft = {'YMES-YSRI': datetime.strptime("14:00", "%H:%M")}
        departure_time = datetime.strptime("14:00", "%H:%M")  # Same time, different airport
        
        result = self.scheduler._validate_and_adjust_departure_time(departure_time, 'YSSY-YSWG', scheduled_aircraft)
        self.assertEqual(result, departure_time)  # Should be unchanged (different airports)

    def test_find_fallback_departure_time(self):
        """Test fallback departure time calculation."""
        scheduled_aircraft = {'YMES-YSRI': datetime.strptime("14:00", "%H:%M")}
        
        # Test aircraft from different airport
        result = self.scheduler._find_fallback_departure_time('YSSY-YSWG', scheduled_aircraft)
        self.assertEqual(result, self.scheduler.start_time)  # Should be event start time
        
        # Test aircraft from same airport
        result = self.scheduler._find_fallback_departure_time('YMES-YORG', scheduled_aircraft)
        expected_time = datetime.strptime("14:02", "%H:%M")  # 2 minutes after 14:00
        self.assertEqual(result, expected_time)

    def test_count_unique_conflict_pairs(self):
        """Test counting unique aircraft pairs in conflict."""
        scheduled_aircraft = {
            'YMES-YSRI': datetime.strptime("14:00", "%H:%M"),
            'YSSY-YSWG': datetime.strptime("14:05", "%H:%M")
        }
        
        # YSNW-YWLM should have 1 conflict pair with YSSY-YSWG
        count = self.scheduler._count_unique_conflict_pairs('YSNW-YWLM', datetime.strptime("14:10", "%H:%M"), scheduled_aircraft, self.sample_conflicts)
        self.assertEqual(count, 1)

    def test_count_future_potential(self):
        """Test counting future potential conflicts."""
        unscheduled_aircraft = {'YSNW-YWLM', 'YSSY-YSWG'}
        
        # YMES-YSRI has 1 potential conflict with unscheduled aircraft (only YSSY-YSWG)
        potential = self.scheduler._count_future_potential('YMES-YSRI', unscheduled_aircraft, self.sample_conflicts)
        self.assertEqual(potential, 1)

    def test_schedule_aircraft_for_maximum_conflicts(self):
        """Test the complete scheduling algorithm."""
        scheduled_flights = self.scheduler.schedule_aircraft_for_maximum_conflicts(self.sample_data)
        
        # Should schedule all 4 aircraft
        self.assertEqual(len(scheduled_flights), 4)
        
        # Check that all aircraft have departure times
        for aircraft, data in scheduled_flights.items():
            self.assertIn('departure_time', data)
            self.assertIn('conflicts', data)
            self.assertIsInstance(data['departure_time'], datetime)

    def test_schedule_aircraft_for_maximum_conflicts_empty_data(self):
        """Test scheduling with empty conflict data."""
        empty_data = {'flight_plans': [], 'scenario': {'potential_conflicts': []}}
        result = self.scheduler.schedule_aircraft_for_maximum_conflicts(empty_data)
        self.assertEqual(result, {})

    def test_generate_schedule_output(self):
        """Test CSV schedule output generation."""
        scheduled_flights = {
            'YMES-YSRI': {
                'departure_time': datetime.strptime("14:00", "%H:%M"),
                'conflicts': [{'other_flight': 'YSSY-YSWG'}],
                'flight_duration': 60
            },
            'YSSY-YSWG': {
                'departure_time': datetime.strptime("14:05", "%H:%M"),
                'conflicts': [{'other_flight': 'YMES-YSRI'}],
                'flight_duration': 60
            }
        }
        
        output = self.scheduler.generate_schedule_output(scheduled_flights)
        lines = output.split('\n')
        
        self.assertEqual(lines[0], "Aircraft,Departure_Time,Route,Expected_Conflicts,Notes")
        self.assertIn("YMES-YSRI,1400,YMES-YSRI,1,1 conflicts", lines)
        self.assertIn("YSSY-YSWG,1405,YSSY-YSWG,1,1 conflicts", lines)

    def test_generate_briefing_output(self):
        """Test ATC briefing output generation."""
        scheduled_flights = {
            'YMES-YSRI': {
                'departure_time': datetime.strptime("14:00", "%H:%M"),
                'conflicts': [{
                    'other_flight': 'YSSY-YSWG',
                    'conflict_time': 40.36,
                    'location': '-34.7096,149.6681',
                    'distance': 2.61,
                    'altitude_diff': 519,
                    'phase': 'cruise'
                }],
                'flight_duration': 60
            }
        }
        
        output = self.scheduler.generate_briefing_output(scheduled_flights, self.sample_data)
        
        # Check key sections
        self.assertIn("ATC CONFLICT EVENT BRIEFING", output)
        self.assertIn("Event Start: 1400", output)
        self.assertIn("Event End: 1800", output)
        self.assertIn("DEPARTURE SCHEDULE:", output)
        self.assertIn("CONFLICT ANALYSIS:", output)
        self.assertIn("YMES-YSRI conflicts:", output)

    @patch('builtins.open', create=True)
    @patch('json.dump')
    def test_update_interpolated_points_with_schedule(self, mock_json_dump, mock_open):
        """Test updating interpolated points with schedule metadata."""
        # Mock the interpolated points file
        mock_interp_data = {
            'YMES-YSRI': [
                {'time': 0, 'lat': -36.9086, 'lon': 149.9014, 'altitude': 8},
                {'time': 40, 'lat': -34.7096, 'lon': 149.6681, 'altitude': 19481}
            ],
            'YSSY-YSWG': [
                {'time': 0, 'lat': -33.9461, 'lon': 151.1772, 'altitude': 23},
                {'time': 24, 'lat': -34.7255, 'lon': 149.7174, 'altitude': 20000}
            ]
        }
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(mock_interp_data)
        
        scheduled_flights = {
            'YMES-YSRI': {
                'departure_time': datetime.strptime("14:00", "%H:%M"),
                'conflicts': [],
                'flight_duration': 60
            },
            'YSSY-YSWG': {
                'departure_time': datetime.strptime("14:05", "%H:%M"),
                'conflicts': [],
                'flight_duration': 60
            }
        }
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            self.scheduler.update_interpolated_points_with_schedule(scheduled_flights)
        
        # Verify that json.dump was called (indicating file was updated)
        mock_json_dump.assert_called_once()

    def test_datetime_to_utc_hhmm(self):
        """Test datetime to UTC HHMM string conversion."""
        dt = datetime.strptime("14:30", "%H:%M")
        result = datetime_to_utc_hhmm(dt)
        self.assertEqual(result, "1430")
        
        dt = datetime.strptime("09:05", "%H:%M")
        result = datetime_to_utc_hhmm(dt)
        self.assertEqual(result, "0905")

    def test_minutes_to_utc_hhmm(self):
        """Test minutes to UTC HHMM string conversion."""
        result = minutes_to_utc_hhmm(840)  # 14:00
        self.assertEqual(result, "1400")
        
        result = minutes_to_utc_hhmm(545)  # 09:05
        self.assertEqual(result, "0905")
        
        result = minutes_to_utc_hhmm(1440)  # 24:00 (should wrap to 00:00)
        self.assertEqual(result, "0000")

class TestConflictSchedulerIntegration(unittest.TestCase):
    """Integration tests for the complete scheduling workflow."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create temp directory
        os.makedirs('temp', exist_ok=True)
        
        # Create sample conflict data file
        self.sample_conflict_data = {
            'flight_plans': ['YMER-YORG', 'YMES-YSRI', 'YSNW-YWLM', 'YSSY-YSWG'],
            'scenario': {
                'potential_conflicts': [
                    {
                        'flight1': 'YMES-YSRI',
                        'flight2': 'YSSY-YSWG',
                        'time1': 40.36,
                        'time2': 24.07,
                        'distance': 2.61,
                        'altitude_diff': 519,
                        'lat1': -34.7096,
                        'lon1': 149.6681,
                        'lat2': -34.7255,
                        'lon2': 149.7174,
                        'alt1': 19481,
                        'alt2': 20000,
                        'stage1': 'cruise',
                        'stage2': 'cruise',
                        'waypoint1': '-34.7096,149.6681',
                        'waypoint2': '-34.7255,149.7174',
                        'conflict_type': 'enroute',
                        'is_waypoint': False,
                        'segment1': 'CB-AKMIR',
                        'segment2': 'EXETA-AVBEG'
                    }
                ],
                'total_conflicts': 1
            }
        }
        
        with open('temp/potential_conflict_data.json', 'w') as f:
            json.dump(self.sample_conflict_data, f)
        
        # Create sample interpolated points file
        self.sample_interp_data = {
            'YMES-YSRI': [
                {'time': 0, 'lat': -36.9086, 'lon': 149.9014, 'altitude': 8},
                {'time': 40, 'lat': -34.7096, 'lon': 149.6681, 'altitude': 19481}
            ],
            'YSSY-YSWG': [
                {'time': 0, 'lat': -33.9461, 'lon': 151.1772, 'altitude': 23},
                {'time': 24, 'lat': -34.7255, 'lon': 149.7174, 'altitude': 20000}
            ]
        }
        
        with open('temp/routes_with_added_interpolated_points.json', 'w') as f:
            json.dump(self.sample_interp_data, f)

    def tearDown(self):
        """Clean up after tests."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_complete_scheduling_workflow(self):
        """Test the complete scheduling workflow from start to finish."""
        scheduler = ConflictScheduler("14:00", "18:00", verbose=False)
        
        # Run the complete scheduling process
        scheduler.run_scheduling()
        
        # Check that output files were created
        self.assertTrue(os.path.exists('pilot_briefing.txt'))
        
        # Check that interpolated points were updated
        with open('temp/routes_with_added_interpolated_points.json', 'r') as f:
            updated_data = json.load(f)
        
        # Should have metadata with departure schedule
        self.assertIn('_metadata', updated_data)
        self.assertIn('departure_schedule', updated_data['_metadata'])
        
        # Should have scheduled all aircraft
        departure_schedule = updated_data['_metadata']['departure_schedule']
        self.assertEqual(len(departure_schedule), 4)

    def test_scheduling_with_verbose_output(self):
        """Test scheduling with verbose logging enabled."""
        scheduler = ConflictScheduler("14:00", "18:00", verbose=True)
        
        # Should not raise any exceptions
        try:
            scheduler.run_scheduling()
        except Exception as e:
            self.fail(f"Scheduling with verbose output failed: {e}")

    def test_scheduling_with_different_time_windows(self):
        """Test scheduling with different event time windows."""
        # Test 1-hour window
        scheduler = ConflictScheduler("15:00", "16:00", verbose=False)
        scheduler.run_scheduling()
        self.assertTrue(os.path.exists('pilot_briefing.txt'))
        
        # Test 6-hour window
        scheduler = ConflictScheduler("12:00", "18:00", verbose=False)
        scheduler.run_scheduling()
        self.assertTrue(os.path.exists('pilot_briefing.txt'))

class TestConflictSchedulerEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up edge case test fixtures."""
        self.scheduler = ConflictScheduler("14:00", "18:00", verbose=False)

    def test_missing_conflict_data_file(self):
        """Test handling when conflict data file is missing."""
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(SystemExit):
                self.scheduler.load_conflict_data()

    def test_invalid_conflict_data_json(self):
        """Test handling when conflict data JSON is invalid."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json}')  # Invalid JSON - missing quotes around "json"
        
        with patch('generate_schedule_conflicts.CONFLICT_ANALYSIS_FILE', f.name):
            with self.assertRaises(SystemExit):
                self.scheduler.load_conflict_data()
        
        os.unlink(f.name)

    def test_scheduling_with_no_conflicts(self):
        """Test scheduling when no conflicts exist between aircraft."""
        data = {
            'flight_plans': ['YMER-YORG', 'YMES-YSRI'],
            'scenario': {
                'potential_conflicts': [],  # No conflicts
                'total_conflicts': 0
            }
        }
        
        scheduled_flights = self.scheduler.schedule_aircraft_for_maximum_conflicts(data)
        
        # Should still schedule all aircraft
        self.assertEqual(len(scheduled_flights), 2)
        
        # All aircraft should have 0 conflicts
        for aircraft, data in scheduled_flights.items():
            self.assertEqual(len(data['conflicts']), 0)

    def test_scheduling_with_single_aircraft(self):
        """Test scheduling with only one aircraft."""
        data = {
            'flight_plans': ['YMES-YSRI'],
            'scenario': {
                'potential_conflicts': [],
                'total_conflicts': 0
            }
        }
        
        scheduled_flights = self.scheduler.schedule_aircraft_for_maximum_conflicts(data)
        
        # Should schedule the single aircraft
        self.assertEqual(len(scheduled_flights), 1)
        self.assertIn('YMES-YSRI', scheduled_flights)

    def test_constraint_violation_handling(self):
        """Test handling when all departure times violate constraints."""
        # Create a scenario where all calculated departure times are outside the event window
        conflicts = [
            {
                'flight1': 'YMES-YSRI',
                'flight2': 'YSSY-YSWG',
                'time1': 300,  # 5 hours after departure (outside 4-hour window)
                'time2': 24.07,
                'distance': 2.61,
                'altitude_diff': 519
            }
        ]
        
        data = {
            'flight_plans': ['YMES-YSRI', 'YSSY-YSWG'],
            'scenario': {
                'potential_conflicts': conflicts,
                'total_conflicts': 1
            }
        }
        
        # Should not raise an exception, should handle gracefully
        scheduled_flights = self.scheduler.schedule_aircraft_for_maximum_conflicts(data)
        self.assertEqual(len(scheduled_flights), 2)

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2) 