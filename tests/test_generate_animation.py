#!/usr/bin/env python3
"""
Unit tests for generate_animation.py
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, mock_open, MagicMock
import sys

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_animation


class TestGenerateAnimation(unittest.TestCase):
    """Test cases for animation data generation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_conflict_data = {
            'flight_plans': ['YSSY-YSWG', 'YMER-YORG'],
            'potential_conflicts': [
                {
                    'flight1': 'YSSY-YSWG',
                    'flight2': 'YMER-YORG',
                    'lat1': -34.7963,
                    'lon1': 149.4166,
                    'lat2': -34.7678,
                    'lon2': 149.4399,
                    'alt1': 20000,
                    'alt2': 20000,
                    'time1': 1800,
                    'time2': 2100,
                    'distance': 2.0
                }
            ],
            'scenario': {
                'departure_schedule': [
                    {'flight': 'YSSY-YSWG', 'departure_time': 0},
                    {'flight': 'YMER-YORG', 'departure_time': 5}
                ],
                'potential_conflicts': [
                    {
                        'flight1': 'YSSY-YSWG',
                        'flight2': 'YMER-YORG',
                        'lat1': -34.7963,
                        'lon1': 149.4166,
                        'lat2': -34.7678,
                        'lon2': 149.4399,
                        'alt1': 20000,
                        'alt2': 20000,
                        'time1': 1800,
                        'time2': 2100,
                        'distance': 2.0,
                        'flight1_arrival': 1800,
                        'flight2_arrival': 2105,
                        'time_diff': 305
                    }
                ],
                'total_conflicts': 1
            }
        }

    def test_animation_data_generator_init(self):
        """Test animation data generator initialization."""
        generator = generate_animation.AnimationDataGenerator()
        
        self.assertEqual(generator.flight_names, [])
        self.assertEqual(generator.conflicts, [])
        self.assertEqual(generator.schedule, {})
        self.assertEqual(generator.flights, {})

    def test_load_conflict_analysis_success(self):
        """Test successful loading of conflict analysis data."""
        generator = generate_animation.AnimationDataGenerator()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temp directory structure
            os.makedirs(os.path.join(temp_dir, 'temp'), exist_ok=True)
            
            with patch('generate_animation.TEMP_DIRECTORY', temp_dir):
                # Create sample conflict analysis file
                json_file = os.path.join(temp_dir, 'conflict_analysis.json')
                with open(json_file, 'w') as f:
                    json.dump(self.sample_conflict_data, f)
                
                success = generator.load_conflict_analysis()
                
                self.assertTrue(success)
                self.assertEqual(len(generator.flight_names), 2)
                self.assertEqual(len(generator.conflicts), 1)

    def test_load_conflict_analysis_file_not_found(self):
        """Test loading conflict analysis when file doesn't exist."""
        generator = generate_animation.AnimationDataGenerator()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('generate_animation.TEMP_DIRECTORY', temp_dir):
                success = generator.load_conflict_analysis()
                self.assertFalse(success)

    def test_load_conflict_analysis_malformed_json(self):
        """Test loading conflict analysis with malformed JSON."""
        generator = generate_animation.AnimationDataGenerator()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, 'temp'), exist_ok=True)
            
            with patch('generate_animation.TEMP_DIRECTORY', temp_dir):
                # Create malformed JSON file
                json_file = os.path.join(temp_dir, 'conflict_analysis.json')
                with open(json_file, 'w') as f:
                    f.write('{ invalid json }')
                
                success = generator.load_conflict_analysis()
                self.assertFalse(success)

    def test_load_schedule_success(self):
        """Test successful loading of departure schedule."""
        generator = generate_animation.AnimationDataGenerator()
        
        sample_briefing = """DEPARTURE SCHEDULE:
------------------------
10:00 - YSSY-YSWG (2 conflicts)
10:05 - YMER-YORG (1 conflict)
"""
        
        with patch('builtins.open', mock_open(read_data=sample_briefing)):
            success = generator.load_schedule()
            
            self.assertTrue(success)
            self.assertIn('YSSY-YSWG', generator.schedule)
            self.assertIn('YMER-YORG', generator.schedule)

    def test_load_schedule_file_not_found(self):
        """Test loading schedule when file doesn't exist."""
        generator = generate_animation.AnimationDataGenerator()
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            success = generator.load_schedule()
            self.assertFalse(success)

    def test_parse_conflict_timing(self):
        """Test parsing conflict timing from briefing."""
        generator = generate_animation.AnimationDataGenerator()
        
        sample_briefing = """CONFLICTS:
10:30 - YSSY-YSWG vs YMER-YORG - EXETA/AVBEG
10:45 - YSNW-YWLM vs YSSY-YSWG - TONTO/EXETA
"""
        
        with patch('builtins.open', mock_open(read_data=sample_briefing)):
            timing = generator.parse_conflict_timing()
            
            self.assertEqual(len(timing), 2)
            self.assertIn('YSSY-YSWG_YMER-YORG', timing)
            self.assertIn('YSNW-YWLM_YSSY-YSWG', timing)

    def test_parse_conflict_distances(self):
        """Test parsing conflict distances from briefing."""
        generator = generate_animation.AnimationDataGenerator()
        
        sample_briefing = """YSSY-YSWG conflicts:
- With YMER-YORG at -34.7963,149.4166
  Distance: 2.1 nm
- With YSNW-YWLM at -34.3785,150.6301
  Distance: 3.2 nm
"""
        
        with patch('builtins.open', mock_open(read_data=sample_briefing)):
            distances = generator.parse_conflict_distances()
            
            self.assertEqual(len(distances), 2)
            key = ('YSSY-YSWG', 'YMER-YORG', '-34.7963,149.4166')
            self.assertIn(key, distances)
            self.assertEqual(distances[key], '2.1')

    def test_convert_coordinates(self):
        """Test coordinate conversion."""
        generator = generate_animation.AnimationDataGenerator()
        
        lat, lon = -33.9399, 151.1753
        x, y = generator.convert_coordinates(lat, lon)
        
        # Should return reasonable values
        self.assertIsInstance(x, float)
        self.assertIsInstance(y, float)
        self.assertNotEqual(x, 0)
        self.assertNotEqual(y, 0)

    def test_extract_waypoints_from_xml_success(self):
        """Test successful waypoint extraction from XML."""
        generator = generate_animation.AnimationDataGenerator()
        
        sample_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<OFP>
    <navlog>
        <fix>
            <ident>EXETA</ident>
            <pos_lat>-34.7963</pos_lat>
            <pos_long>149.4166</pos_long>
            <altitude_feet>20000</altitude_feet>
            <time_total>1800</time_total>
            <stage>cruise</stage>
        </fix>
    </navlog>
    <origin>
        <icao_code>YSSY</icao_code>
        <pos_lat>-33.9399</pos_lat>
        <pos_long>151.1753</pos_long>
    </origin>
    <destination>
        <icao_code>YSWG</icao_code>
        <pos_lat>-35.1653</pos_lat>
        <pos_long>147.4664</pos_long>
    </destination>
</OFP>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(sample_xml)
            xml_file = f.name
        
        try:
            with patch('os.listdir', return_value=[xml_file]):
                waypoints = generator.extract_waypoints_from_xml('YSSY-YSWG')
                
                self.assertGreater(len(waypoints), 0)
                # Check structure of waypoints
                for wp in waypoints:
                    self.assertIn('name', wp)
                    self.assertIn('lat', wp)
                    self.assertIn('lon', wp)
                    self.assertIn('altitude', wp)
        finally:
            os.unlink(xml_file)

    def test_extract_waypoints_from_xml_no_file(self):
        """Test waypoint extraction when XML file doesn't exist."""
        generator = generate_animation.AnimationDataGenerator()
        
        with patch('os.listdir', return_value=[]):
            waypoints = generator.extract_waypoints_from_xml('YSSY-YSWG')
            self.assertEqual(len(waypoints), 0)

    def test_generate_flight_tracks(self):
        """Test flight track generation."""
        generator = generate_animation.AnimationDataGenerator()
        generator.flight_names = ['YSSY-YSWG', 'YMER-YORG']
        generator.flights = {
            'YSSY-YSWG': [
                {'name': 'YSSY', 'lat': -33.9399, 'lon': 151.1753, 'altitude': 0, 'time_from_departure': 0},
                {'name': 'EXETA', 'lat': -34.7963, 'lon': 149.4166, 'altitude': 20000, 'time_from_departure': 30},
                {'name': 'YSWG', 'lat': -35.1653, 'lon': 147.4664, 'altitude': 0, 'time_from_departure': 60}
            ]
        }
        
        tracks = generator.generate_flight_tracks()
        
        self.assertEqual(len(tracks), 2)
        # Check structure of tracks
        for track in tracks:
            self.assertIn('flight_id', track)
            self.assertIn('waypoints', track)
            self.assertIn('color', track)

    def test_generate_conflict_points(self):
        """Test conflict point generation."""
        generator = generate_animation.AnimationDataGenerator()
        generator.conflicts = self.sample_conflict_data['potential_conflicts']
        
        points = generator.generate_conflict_points()
        
        self.assertEqual(len(points), 1)
        # Check structure of conflict points
        for point in points:
            self.assertIn('lat', point)
            self.assertIn('lon', point)
            self.assertIn('altitude', point)
            self.assertIn('description', point)

    def test_float_minutes_to_hhmm(self):
        """Test time conversion from float minutes to HH:MM format."""
        generator = generate_animation.AnimationDataGenerator()
        
        # Test various time values
        self.assertEqual(generator.float_minutes_to_hhmm(0), '00:00')
        self.assertEqual(generator.float_minutes_to_hhmm(30), '00:30')
        self.assertEqual(generator.float_minutes_to_hhmm(60), '01:00')
        self.assertEqual(generator.float_minutes_to_hhmm(90), '01:30')
        self.assertEqual(generator.float_minutes_to_hhmm(120), '02:00')

    def test_generate_timeline(self):
        """Test timeline generation."""
        generator = generate_animation.AnimationDataGenerator()
        generator.schedule = {
            'YSSY-YSWG': '10:00',
            'YMER-YORG': '10:05'
        }
        
        timeline = generator.generate_timeline()
        
        self.assertGreater(len(timeline), 0)
        # Check structure of timeline entries
        for entry in timeline:
            self.assertIn('time', entry)
            self.assertIn('description', entry)

    def test_generate_animation_data_success(self):
        """Test successful animation data generation."""
        generator = generate_animation.AnimationDataGenerator()
        generator.flight_names = ['YSSY-YSWG']
        generator.conflicts = self.sample_conflict_data['potential_conflicts']
        generator.schedule = {'YSSY-YSWG': '10:00'}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('generate_animation.WEB_VISUALIZATION_DIR', temp_dir):
                success = generator.generate_animation_data()
                
                self.assertTrue(success)
                # Check that output files were created
                self.assertTrue(os.path.exists(os.path.join(temp_dir, 'animation_data.json')))
                self.assertTrue(os.path.exists(os.path.join(temp_dir, 'flight_tracks.json')))
                self.assertTrue(os.path.exists(os.path.join(temp_dir, 'conflict_points.json')))

    def test_generate_animation_data_no_conflicts(self):
        """Test animation data generation with no conflicts."""
        generator = generate_animation.AnimationDataGenerator()
        generator.flight_names = ['YSSY-YSWG']
        generator.conflicts = []
        generator.schedule = {'YSSY-YSWG': '10:00'}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('generate_animation.WEB_VISUALIZATION_DIR', temp_dir):
                success = generator.generate_animation_data()
                
                self.assertTrue(success)
                # Should still create files even with no conflicts
                self.assertTrue(os.path.exists(os.path.join(temp_dir, 'animation_data.json')))

    @patch('builtins.print')
    def test_run_success(self, mock_print):
        """Test successful run of animation generator."""
        generator = generate_animation.AnimationDataGenerator()
        
        with patch.object(generator, 'load_conflict_analysis', return_value=True):
            with patch.object(generator, 'load_schedule', return_value=True):
                with patch.object(generator, 'generate_animation_data', return_value=True):
                    success = generator.run()
                    self.assertTrue(success)

    @patch('builtins.print')
    def test_run_load_failure(self, mock_print):
        """Test run when conflict analysis loading fails."""
        generator = generate_animation.AnimationDataGenerator()
        
        with patch.object(generator, 'load_conflict_analysis', return_value=False):
            success = generator.run()
            self.assertFalse(success)

    @patch('builtins.print')
    def test_main_function(self, mock_print):
        """Test main function execution."""
        with patch('generate_animation.AnimationDataGenerator') as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.run.return_value = True
            mock_generator_class.return_value = mock_generator
            
            generate_animation.main()
            
            mock_generator_class.assert_called_once()
            mock_generator.run.assert_called_once()


if __name__ == '__main__':
    unittest.main() 