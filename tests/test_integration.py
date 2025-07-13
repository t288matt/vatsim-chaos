#!/usr/bin/env python3
"""
Integration tests for the complete ATC Conflict Analysis workflow
"""

import unittest
import tempfile
import os
import json
import shutil
import subprocess
import sys
from unittest.mock import patch, mock_open
import xml.etree.ElementTree as ET

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run_analysis
import extract_simbrief_xml_flightplan
import find_potential_conflicts
import generate_animation
import generate_schedule_conflicts


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create sample XML files for testing
        self.create_sample_xml_files()

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def create_sample_xml_files(self):
        """Create sample XML flight plan files for testing."""
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
        
        # Create multiple XML files with slight variations
        xml_files = [
            ('YSSYYSWG_XML_1752350843.xml', sample_xml),
            ('YMERYORG_XML_1752350911.xml', sample_xml.replace('YSSY', 'YMER').replace('YSWG', 'YORG')),
            ('YSNWYWLM_XML_1752352938.xml', sample_xml.replace('YSSY', 'YSNW').replace('YSWG', 'YWLM'))
        ]
        
        for filename, content in xml_files:
            with open(filename, 'w') as f:
                f.write(content)

    def test_full_workflow_integration(self):
        """Test the complete workflow from XML extraction to animation generation."""
        # Step 1: Extract flight plans
        xml_files = extract_simbrief_xml_flightplan.find_xml_files()
        self.assertEqual(len(xml_files), 3)
        
        flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
        self.assertEqual(len(flight_plans), 3)
        
        # Step 2: Find potential conflicts
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        self.assertIsInstance(conflicts, list)
        
        # Step 3: Generate conflict scenario
        if conflicts:
            scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
            self.assertIn('departure_schedule', scenario)
            self.assertIn('potential_conflicts', scenario)
            self.assertIn('total_conflicts', scenario)
        
        # Step 4: Save analysis data
        analysis_data = {
            'flight_plans': [fp.get_route_identifier() for fp in flight_plans],
            'potential_conflicts': conflicts,
            'scenario': scenario if conflicts else {
                'departure_schedule': [],
                'potential_conflicts': [],
                'total_conflicts': 0
            }
        }
        
        # Create temp directory
        os.makedirs('temp', exist_ok=True)
        find_potential_conflicts.save_analysis_data(analysis_data)
        
        # Step 5: Generate animation data
        generator = generate_animation.AnimationDataGenerator()
        success = generator.load_conflict_analysis()
        self.assertTrue(success)
        
        # Create web_visualization directory
        os.makedirs('web_visualization', exist_ok=True)
        with patch('generate_animation.WEB_VISUALIZATION_DIR', 'web_visualization'):
            success = generator.generate_animation_data()
            self.assertTrue(success)

    def test_workflow_with_no_conflicts(self):
        """Test workflow behavior when no conflicts are detected."""
        # Create XML files with routes that don't intersect
        no_conflict_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<OFP>
    <origin>
        <icao_code>YSSY</icao_code>
        <pos_lat>-33.9399</pos_lat>
        <pos_long>151.1753</pos_long>
    </origin>
    <destination>
        <icao_code>YMML</icao_code>
        <pos_lat>-37.8136</pos_lat>
        <pos_long>144.9631</pos_long>
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
            <ident>YMML</ident>
            <pos_lat>-37.8136</pos_lat>
            <pos_long>144.9631</pos_long>
            <altitude_feet>0</altitude_feet>
            <time_total>3600</time_total>
            <stage>arrival</stage>
        </fix>
    </navlog>
</OFP>'''
        
        # Replace existing files with non-conflicting routes
        for filename in os.listdir('.'):
            if filename.endswith('.xml'):
                with open(filename, 'w') as f:
                    f.write(no_conflict_xml)
        
        # Run workflow
        xml_files = extract_simbrief_xml_flightplan.find_xml_files()
        flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        
        # Should handle no conflicts gracefully
        self.assertEqual(len(conflicts), 0)
        
        scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
        self.assertEqual(scenario['total_conflicts'], 0)

    def test_workflow_error_handling(self):
        """Test workflow error handling with invalid inputs."""
        # Test with malformed XML
        malformed_xml = '<OFP><invalid>'
        with open('malformed.xml', 'w') as f:
            f.write(malformed_xml)
        
        xml_files = extract_simbrief_xml_flightplan.find_xml_files()
        flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
        
        # Should handle malformed XML gracefully
        self.assertLessEqual(len(flight_plans), len(xml_files))

    def test_data_consistency_across_modules(self):
        """Test that data structures are consistent across all modules."""
        # Extract flight plans
        xml_files = extract_simbrief_xml_flightplan.find_xml_files()
        flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
        
        # Check flight plan structure
        for fp in flight_plans:
            self.assertIsInstance(fp, extract_simbrief_xml_flightplan.FlightPlan)
            self.assertIsInstance(fp.origin, str)
            self.assertIsInstance(fp.destination, str)
            self.assertIsInstance(fp.waypoints, list)
        
        # Find conflicts
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        
        # Check conflict structure
        for conflict in conflicts:
            self.assertIn('flight1', conflict)
            self.assertIn('flight2', conflict)
            self.assertIn('lat1', conflict)
            self.assertIn('lon1', conflict)
            self.assertIn('lat2', conflict)
            self.assertIn('lon2', conflict)
            self.assertIn('alt1', conflict)
            self.assertIn('alt2', conflict)
            self.assertIn('distance', conflict)

    def test_output_file_generation(self):
        """Test that all expected output files are generated."""
        # Run the complete workflow
        xml_files = extract_simbrief_xml_flightplan.find_xml_files()
        flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
        
        # Save analysis data
        analysis_data = {
            'flight_plans': [fp.get_route_identifier() for fp in flight_plans],
            'potential_conflicts': conflicts,
            'scenario': scenario
        }
        
        os.makedirs('temp', exist_ok=True)
        find_potential_conflicts.save_analysis_data(analysis_data)
        
        # Generate animation data
        os.makedirs('web_visualization', exist_ok=True)
        generator = generate_animation.AnimationDataGenerator()
        generator.load_conflict_analysis()
        with patch('generate_animation.WEB_VISUALIZATION_DIR', 'web_visualization'):
            generator.generate_animation_data()
        
        # Check that expected files exist
        expected_files = [
            'temp/conflict_analysis.json',
            'web_visualization/animation_data.json',
            'web_visualization/flight_tracks.json',
            'web_visualization/conflict_points.json'
        ]
        
        for file_path in expected_files:
            self.assertTrue(os.path.exists(file_path), f"Expected file {file_path} not found")

    def test_json_data_structure_consistency(self):
        """Test that JSON data structures are consistent and valid."""
        # Run workflow and save data
        xml_files = extract_simbrief_xml_flightplan.find_xml_files()
        flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
        
        analysis_data = {
            'flight_plans': [fp.get_route_identifier() for fp in flight_plans],
            'potential_conflicts': conflicts,
            'scenario': scenario
        }
        
        os.makedirs('temp', exist_ok=True)
        find_potential_conflicts.save_analysis_data(analysis_data)
        
        # Load and validate JSON structure
        with open('temp/conflict_analysis.json', 'r') as f:
            data = json.load(f)
        
        # Check required fields
        self.assertIn('flight_plans', data)
        self.assertIn('potential_conflicts', data)
        self.assertIn('scenario', data)
        
        # Check scenario structure
        scenario_data = data['scenario']
        self.assertIn('departure_schedule', scenario_data)
        self.assertIn('potential_conflicts', scenario_data)
        self.assertIn('total_conflicts', scenario_data)
        
        # Validate data types
        self.assertIsInstance(data['flight_plans'], list)
        self.assertIsInstance(data['potential_conflicts'], list)
        self.assertIsInstance(scenario_data['total_conflicts'], int)

    def test_workflow_performance(self):
        """Test workflow performance with larger datasets."""
        # Create more XML files to test performance
        for i in range(5):
            filename = f'test_flight_{i}.xml'
            with open(filename, 'w') as f:
                f.write(self.create_sample_xml_files.__doc__)  # Use the sample XML
        
        # Time the workflow execution
        import time
        start_time = time.time()
        
        xml_files = extract_simbrief_xml_flightplan.find_xml_files()
        flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
        conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
        scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(execution_time, 30.0, f"Workflow took {execution_time:.2f} seconds")

    def test_error_recovery(self):
        """Test that the workflow can recover from various error conditions."""
        # Test with missing files
        if os.path.exists('temp/conflict_analysis.json'):
            os.remove('temp/conflict_analysis.json')
        
        # Should handle missing files gracefully
        generator = generate_animation.AnimationDataGenerator()
        success = generator.load_conflict_analysis()
        self.assertFalse(success)  # Should fail gracefully
        
        # Test with empty XML files
        with open('empty.xml', 'w') as f:
            f.write('')
        
        xml_files = extract_simbrief_xml_flightplan.find_xml_files()
        flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
        
        # Should handle empty files gracefully
        self.assertIsInstance(flight_plans, list)


class TestWorkflowRegression(unittest.TestCase):
    """Regression tests to ensure workflow behavior doesn't change unexpectedly."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_workflow_output_consistency(self):
        """Test that workflow produces consistent outputs for same inputs."""
        # Create identical test data
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
        
        # Create identical XML files
        for i in range(2):
            with open(f'test_{i}.xml', 'w') as f:
                f.write(sample_xml)
        
        # Run workflow twice
        results = []
        for run in range(2):
            xml_files = extract_simbrief_xml_flightplan.find_xml_files()
            flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(xml_files)
            conflicts = find_potential_conflicts.find_potential_conflicts(flight_plans)
            scenario = find_potential_conflicts.generate_conflict_scenario(flight_plans, conflicts)
            
            results.append({
                'flight_plans': [fp.get_route_identifier() for fp in flight_plans],
                'conflicts_count': len(conflicts),
                'scenario_conflicts': scenario['total_conflicts']
            })
        
        # Results should be identical
        self.assertEqual(results[0], results[1])


if __name__ == '__main__':
    unittest.main() 