#!/usr/bin/env python3
"""
Unit tests for extract_simbrief_xml_flightplan.py
"""

import unittest
import tempfile
import os
import xml.etree.ElementTree as ET
from unittest.mock import patch, mock_open, MagicMock
import sys
import json

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import extract_simbrief_xml_flightplan


class TestExtractSimbriefXMLFlightplan(unittest.TestCase):
    """Test cases for XML flight plan extraction functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_xml = '''<?xml version="1.0" encoding="UTF-8"?>
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

    def test_parse_waypoint_from_fix_valid(self):
        """Test parsing a valid waypoint from XML fix element."""
        root = ET.fromstring(self.sample_xml)
        navlog = root.find('.//navlog')
        self.assertIsNotNone(navlog)
        if navlog:  # Type guard for linter
            fix = navlog.findall('fix')[1]  # EXETA waypoint
        
        waypoint = extract_simbrief_xml_flightplan.parse_waypoint_from_fix(fix)
        
        self.assertIsNotNone(waypoint)
        if waypoint:  # Type guard for linter
            self.assertEqual(waypoint.name, 'EXETA')
            self.assertEqual(waypoint.lat, -34.7963)
            self.assertEqual(waypoint.lon, 149.4166)
            self.assertEqual(waypoint.altitude, 20000)
            self.assertEqual(waypoint.time_total, 1800)
            self.assertEqual(waypoint.stage, 'cruise')

    def test_parse_waypoint_from_fix_missing_data(self):
        """Test parsing waypoint with missing data."""
        incomplete_xml = '''<fix>
            <ident>TEST</ident>
            <pos_lat>-33.9399</pos_lat>
            <!-- Missing pos_long and altitude -->
        </fix>'''
        fix = ET.fromstring(incomplete_xml)
        
        waypoint = extract_simbrief_xml_flightplan.parse_waypoint_from_fix(fix)
        
        self.assertIsNone(waypoint)

    def test_parse_airport_info_valid(self):
        """Test parsing valid airport information."""
        root = ET.fromstring(self.sample_xml)
        origin = root.find('.//origin')
        
        waypoint = extract_simbrief_xml_flightplan.parse_airport_info(origin)
        
        self.assertIsNotNone(waypoint)
        self.assertEqual(waypoint.name, 'YSSY')
        self.assertEqual(waypoint.lat, -33.9399)
        self.assertEqual(waypoint.lon, 151.1753)
        self.assertEqual(waypoint.altitude, 0)

    def test_parse_airport_info_missing_data(self):
        """Test parsing airport info with missing data."""
        incomplete_xml = '''<origin>
            <icao_code>YSSY</icao_code>
            <!-- Missing coordinates -->
        </origin>'''
        airport = ET.fromstring(incomplete_xml)
        
        waypoint = extract_simbrief_xml_flightplan.parse_airport_info(airport)
        
        self.assertIsNone(waypoint)

    def test_extract_flight_plan_from_xml_valid(self):
        """Test extracting complete flight plan from valid XML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(self.sample_xml)
            xml_file = f.name
        
        try:
            flight_plan = extract_simbrief_xml_flightplan.extract_flight_plan_from_xml(xml_file)
            
            self.assertIsNotNone(flight_plan)
            self.assertEqual(flight_plan.origin, 'YSSY')
            self.assertEqual(flight_plan.destination, 'YSWG')
            self.assertEqual(len(flight_plan.waypoints), 1)  # Only EXETA, airports are separate
            self.assertIsNotNone(flight_plan.departure)
            self.assertIsNotNone(flight_plan.arrival)
        finally:
            os.unlink(xml_file)

    def test_extract_flight_plan_from_xml_invalid_file(self):
        """Test extracting flight plan from non-existent file."""
        flight_plan = extract_simbrief_xml_flightplan.extract_flight_plan_from_xml('nonexistent.xml')
        self.assertIsNone(flight_plan)

    def test_extract_flight_plan_from_xml_malformed(self):
        """Test extracting flight plan from malformed XML."""
        malformed_xml = '<OFP><invalid>'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(malformed_xml)
            xml_file = f.name
        
        try:
            flight_plan = extract_simbrief_xml_flightplan.extract_flight_plan_from_xml(xml_file)
            self.assertIsNone(flight_plan)
        finally:
            os.unlink(xml_file)

    def test_find_xml_files(self):
        """Test finding XML files in directory."""
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['test1.xml', 'test2.txt', 'test3.xml']
            
            xml_files = extract_simbrief_xml_flightplan.find_xml_files()
            
            self.assertEqual(len(xml_files), 2)
            self.assertIn('test1.xml', xml_files)
            self.assertIn('test3.xml', xml_files)

    def test_extract_flight_plans(self):
        """Test extracting multiple flight plans."""
        with patch('extract_simbrief_xml_flightplan.find_xml_files') as mock_find:
            with patch('extract_simbrief_xml_flightplan.extract_flight_plan_from_xml') as mock_extract:
                mock_find.return_value = ['test1.xml', 'test2.xml']
                mock_extract.side_effect = [
                    extract_simbrief_xml_flightplan.FlightPlan('YSSY', 'YSWG'),
                    extract_simbrief_xml_flightplan.FlightPlan('YMER', 'YORG')
                ]
                
                flight_plans = extract_simbrief_xml_flightplan.extract_flight_plans(['test1.xml', 'test2.xml'])
                
                self.assertEqual(len(flight_plans), 2)
                self.assertEqual(flight_plans[0].origin, 'YSSY')
                self.assertEqual(flight_plans[1].origin, 'YMER')

    def test_waypoint_time_formatting(self):
        """Test waypoint time formatting methods."""
        waypoint = extract_simbrief_xml_flightplan.Waypoint(
            name='TEST', lat=0, lon=0, altitude=10000, time_total=1230
        )
        
        self.assertEqual(waypoint.get_time_formatted(), '12:30')
        self.assertEqual(waypoint.get_time_minutes(), 20.5)

    def test_flight_plan_route_identifier(self):
        """Test flight plan route identifier generation."""
        flight_plan = extract_simbrief_xml_flightplan.FlightPlan('YSSY', 'YSWG')
        self.assertEqual(flight_plan.get_route_identifier(), 'YSSY-YSWG')

    def test_flight_plan_waypoint_management(self):
        """Test flight plan waypoint management."""
        flight_plan = extract_simbrief_xml_flightplan.FlightPlan('YSSY', 'YSWG')
        waypoint = extract_simbrief_xml_flightplan.Waypoint('TEST', 0, 0, 10000)
        
        flight_plan.add_waypoint(waypoint)
        self.assertEqual(len(flight_plan.waypoints), 1)
        
        all_waypoints = flight_plan.get_all_waypoints()
        self.assertEqual(len(all_waypoints), 1)  # Only waypoint, no departure/arrival set

    @patch('builtins.print')
    def test_main_function(self, mock_print):
        """Test main function execution."""
        with patch('extract_simbrief_xml_flightplan.find_xml_files') as mock_find:
            with patch('extract_simbrief_xml_flightplan.extract_flight_plans') as mock_extract:
                mock_find.return_value = ['test.xml']
                mock_extract.return_value = [
                    extract_simbrief_xml_flightplan.FlightPlan('YSSY', 'YSWG')
                ]
                
                extract_simbrief_xml_flightplan.main()
                
                mock_find.assert_called_once()
                mock_extract.assert_called_once_with(['test.xml'])


if __name__ == '__main__':
    unittest.main() 