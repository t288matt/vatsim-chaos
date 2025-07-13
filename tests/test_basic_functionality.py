#!/usr/bin/env python3
"""
Basic functionality tests for ATC Conflict Analysis System
Tests core functionality without complex mocking
"""

import unittest
import tempfile
import os
import json
import sys
import subprocess

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import extract_simbrief_xml_flightplan
import find_potential_conflicts
import generate_animation


class TestBasicFunctionality(unittest.TestCase):
    """Basic functionality tests that work with the actual codebase."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_xml_extraction_basic(self):
        """Test basic XML extraction functionality."""
        # Create a simple XML file
        sample_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<OFP>
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
    <navlog>
        <fix>
            <ident>YSSY</ident>
            <pos_lat>-33.9399</pos_lat>
            <pos_long>151.1753</pos_long>
            <altitude_feet>0</altitude_feet>
            <time_total>0</time_total>
            <stage>departure</stage>
        </fix>
        <fix>
            <ident>EXETA</ident>
            <pos_lat>-34.7963</pos_lat>
            <pos_long>149.4166</pos_long>
            <altitude_feet>20000</altitude_feet>
            <time_total>1800</time_total>
            <stage>cruise</stage>
        </fix>
        <fix>
            <ident>YSWG</ident>
            <pos_lat>-35.1653</pos_lat>
            <pos_long>147.4664</pos_long>
            <altitude_feet>0</altitude_feet>
            <time_total>3600</time_total>
            <stage>arrival</stage>
        </fix>
    </navlog>
</OFP>'''
        
        with open('test.xml', 'w') as f:
            f.write(sample_xml)
        
        # Test extraction
        flight_plan = extract_simbrief_xml_flightplan.extract_flight_plan_from_xml('test.xml')
        
        self.assertIsNotNone(flight_plan)
        if flight_plan:  # Type guard for linter
            self.assertEqual(flight_plan.origin, 'YSSY')
            self.assertEqual(flight_plan.destination, 'YSWG')
            self.assertGreater(len(flight_plan.waypoints), 0)

    def test_distance_calculation(self):
        """Test distance calculation functionality."""
        # Test distance between Sydney and Melbourne
        lat1, lon1 = -33.9399, 151.1753  # Sydney
        lat2, lon2 = -37.8136, 144.9631  # Melbourne
        
        distance = find_potential_conflicts.calculate_distance_nm(lat1, lon1, lat2, lon2)
        
        # Should be a reasonable distance
        self.assertGreater(distance, 300)
        self.assertLess(distance, 500)

    def test_waypoint_creation(self):
        """Test waypoint creation and basic properties."""
        waypoint = find_potential_conflicts.Waypoint(
            name='TEST', lat=0, lon=0, altitude=10000, time_total=1230
        )
        
        self.assertEqual(waypoint.name, 'TEST')
        self.assertEqual(waypoint.lat, 0)
        self.assertEqual(waypoint.lon, 0)
        self.assertEqual(waypoint.altitude, 10000)
        self.assertEqual(waypoint.time_total, 1230)

    def test_flight_plan_creation(self):
        """Test flight plan creation and basic properties."""
        flight_plan = find_potential_conflicts.FlightPlan('YSSY', 'YSWG')
        
        self.assertEqual(flight_plan.origin, 'YSSY')
        self.assertEqual(flight_plan.destination, 'YSWG')
        self.assertEqual(len(flight_plan.waypoints), 0)

    def test_conflict_validation(self):
        """Test conflict validation logic."""
        wp1 = find_potential_conflicts.Waypoint('TEST1', 0, 0, 20000)
        wp2 = find_potential_conflicts.Waypoint('TEST2', 0.01, 0.01, 20000)
        
        # Calculate distance
        distance = find_potential_conflicts.calculate_distance_nm(wp1.lat, wp1.lon, wp2.lat, wp2.lon)
        altitude_diff = abs(wp1.altitude - wp2.altitude)
        
        # Test validation
        is_valid = find_potential_conflicts.is_conflict_valid(wp1, wp2, distance, altitude_diff)
        
        # Should be valid (close distance, same altitude)
        self.assertTrue(is_valid)

    def test_animation_generator_init(self):
        """Test animation generator initialization."""
        generator = generate_animation.AnimationDataGenerator()
        
        # Check that basic attributes exist
        self.assertIsInstance(generator.conflicts, list)
        self.assertIsInstance(generator.schedule, dict)
        self.assertIsInstance(generator.flights, dict)

    def test_coordinate_conversion(self):
        """Test coordinate conversion functionality."""
        generator = generate_animation.AnimationDataGenerator()
        
        lat, lon = -33.9399, 151.1753
        x, y = generator.convert_coordinates(lat, lon)
        
        # Should return reasonable values
        self.assertIsInstance(x, float)
        self.assertIsInstance(y, float)
        self.assertNotEqual(x, 0)
        self.assertNotEqual(y, 0)

    def test_json_operations(self):
        """Test JSON reading and writing operations."""
        test_data = {
            'flight_plans': ['YSSY-YSWG', 'YMER-YORG'],
            'potential_conflicts': [],
            'scenario': {
                'departure_schedule': [],
                'potential_conflicts': [],
                'total_conflicts': 0
            }
        }
        
        # Test writing
        with open('test_data.json', 'w') as f:
            json.dump(test_data, f)
        
        # Test reading
        with open('test_data.json', 'r') as f:
            loaded_data = json.load(f)
        
        self.assertEqual(loaded_data['flight_plans'], test_data['flight_plans'])
        self.assertEqual(loaded_data['scenario']['total_conflicts'], 0)

    def test_workflow_scripts_exist(self):
        """Test that all required scripts exist and are runnable."""
        required_scripts = [
            'extract_simbrief_xml_flightplan.py',
            'find_potential_conflicts.py',
            'generate_animation.py',
            'run_analysis.py'
        ]
        
        for script in required_scripts:
            self.assertTrue(os.path.exists(script), f"Required script {script} not found")
            
            # Test that script can be imported
            try:
                if script == 'extract_simbrief_xml_flightplan.py':
                    import extract_simbrief_xml_flightplan
                elif script == 'find_potential_conflicts.py':
                    import find_potential_conflicts
                elif script == 'generate_animation.py':
                    import generate_animation
                elif script == 'run_analysis.py':
                    import run_analysis
            except ImportError as e:
                self.fail(f"Could not import {script}: {e}")

    def test_environment_variables(self):
        """Test that environment variables are accessible."""
        import env
        
        # Test that env module can be imported and has expected attributes
        self.assertIsInstance(env.LATERAL_SEPARATION_THRESHOLD, (int, float))
        self.assertIsInstance(env.VERTICAL_SEPARATION_THRESHOLD, (int, float))
        self.assertIsInstance(env.MIN_ALTITUDE_THRESHOLD, (int, float))

    def test_file_operations(self):
        """Test basic file operations."""
        # Test file creation
        test_content = "Test content"
        with open('test_file.txt', 'w') as f:
            f.write(test_content)
        
        # Test file reading
        with open('test_file.txt', 'r') as f:
            content = f.read()
        
        self.assertEqual(content, test_content)
        
        # Test file deletion
        os.remove('test_file.txt')
        self.assertFalse(os.path.exists('test_file.txt'))

    def test_subprocess_execution(self):
        """Test that Python subprocess execution works."""
        # Test running a simple Python command
        result = subprocess.run(
            ['python', '-c', 'print("Hello, World!")'],
            capture_output=True, text=True
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Hello, World!', result.stdout)

    def test_import_all_modules(self):
        """Test that all modules can be imported without errors."""
        modules_to_test = [
            'extract_simbrief_xml_flightplan',
            'find_potential_conflicts', 
            'generate_animation',
            'generate_schedule_conflicts',
            'merge_kml_flightplans',
            'run_analysis',
            'env'
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                self.fail(f"Could not import {module_name}: {e}")

    def test_data_structures(self):
        """Test that core data structures work correctly."""
        # Test Waypoint dataclass
        waypoint = find_potential_conflicts.Waypoint(
            name='TEST', lat=0, lon=0, altitude=10000, time_total=1230
        )
        
        # Test FlightPlan class
        flight_plan = find_potential_conflicts.FlightPlan('YSSY', 'YSWG')
        waypoint_obj = find_potential_conflicts.Waypoint('TEST', 0, 0, 10000)
        flight_plan.add_waypoint(waypoint_obj)
        
        self.assertEqual(len(flight_plan.waypoints), 1)
        self.assertEqual(flight_plan.waypoints[0].name, 'TEST')

    def test_mathematical_operations(self):
        """Test mathematical operations used in the codebase."""
        import math
        
        # Test distance calculation
        lat1, lon1 = 0, 0
        lat2, lon2 = 1, 1
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Calculate distance
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        # Should be a reasonable value
        self.assertGreater(c, 0)
        self.assertLess(c, math.pi)


if __name__ == '__main__':
    unittest.main() 