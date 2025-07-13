# =============================================================================
# Conflict Schedule Generation Script
#
# TIME HANDLING:
#   - May use minutes after departure internally for calculations.
#   - All output and reporting (CSV, briefings, etc.) must use UTC 'HHMM' strings (4-digit, zero-padded).
#   - Converts times to UTC strings before writing any output files.
# =============================================================================
#!/usr/bin/env python3
"""
ATC Conflict Scheduler
======================

Generates departure schedules to ensure aircraft arrive at conflict points simultaneously
within a defined event time window. The first flight departs at the event start time.

Recent Changes:
- Eliminated circular dependency with animation generation
- Uses interpolated points directly for position interpolation
- Adds departure schedule metadata to interpolated points file
- No longer depends on animation_data.json

Usage:
    python schedule_conflicts.py --start 14:00 --end 18:00
    python schedule_conflicts.py --start 14:00 --end 18:00 --verbose
    python schedule_conflicts.py --start 14:00 --end 18:00 --max-conflicts 10
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

# Configuration
CONFLICT_ANALYSIS_FILE = "temp/potential_conflict_data.json"
BRIEFING_OUTPUT_FILE = "pilot_briefing.txt"

def datetime_to_utc_hhmm(dt) -> str:
    return dt.strftime('%H%M')

def minutes_to_utc_hhmm(minutes: float) -> str:
    total_minutes = int(round(minutes))
    hours = (total_minutes // 60) % 24
    mins = total_minutes % 60
    return f"{hours:02d}{mins:02d}"

class ConflictScheduler:
    """Schedules aircraft departures to create simultaneous conflicts."""
    
    def __init__(self, start_time: str, end_time: str, verbose: bool = False):
        self.start_time = self._parse_time(start_time)
        self.end_time = self._parse_time(end_time)
        self.verbose = verbose
        self.event_duration = self._calculate_duration()
        
        # Setup logging
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def _parse_time(self, time_str: str) -> datetime:
        """Parse time string in HH:MM format."""
        try:
            return datetime.strptime(time_str, "%H:%M")
        except ValueError:
            print(f"ERROR: Invalid time format: {time_str}. Use HH:MM format (e.g., 14:00)")
            sys.exit(1)
    
    def _calculate_duration(self) -> int:
        """Calculate event duration in minutes."""
        duration = self.end_time - self.start_time
        return int(duration.total_seconds() / 60)
    
    def load_conflict_data(self) -> Dict:
        """Load conflict analysis data."""
        if not os.path.exists(CONFLICT_ANALYSIS_FILE):
            print(f"ERROR: Conflict analysis file not found: {CONFLICT_ANALYSIS_FILE}")
            print("Run 'python execute.py --analyze-only' first")
            sys.exit(1)
        
        with open(CONFLICT_ANALYSIS_FILE, 'r') as f:
            data = json.load(f)
        
        logging.info(f"Loaded conflict data with {len(data.get('flight_plans', []))} flight plans")
        return data
    
    def filter_duplicate_conflicts(self, conflicts: List[Dict]) -> List[Dict]:
        """
        Filter out conflicts that are too close to previous conflicts between the same routes.
        Uses the same 4.0 nm logic as the main analysis system.
        """
        last_conflict_location = {}
        filtered_conflicts = []
        
        for conflict in conflicts:
            # Route pair key (order independent)
            route_pair = tuple(sorted([conflict['flight1'], conflict['flight2']]))
            lat = conflict.get('lat1', 0)
            lon = conflict.get('lon1', 0)
            prev = last_conflict_location.get(route_pair)
            
            if prev:
                prev_lat, prev_lon = prev
                # Calculate distance using the same logic as main system
                distance = self._calculate_distance_nm(lat, lon, prev_lat, prev_lon)
                if distance < 4.0:  # Same threshold as main system
                    continue  # Skip this conflict, too close to previous
            
            filtered_conflicts.append(conflict)
            last_conflict_location[route_pair] = (lat, lon)
        
        return filtered_conflicts
    
    def _calculate_distance_nm(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in nautical miles."""
        import math
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in nautical miles
        earth_radius_nm = 3440.065  # 6371 km / 1.852 km/nm
        
        return earth_radius_nm * c

    def analyze_conflicts_for_scheduling(self, data: Dict) -> Dict[str, Dict]:
        """Analyze conflicts and prepare for scheduling."""
        conflicts = data.get('scenario', {}).get('potential_conflicts', [])
        flight_plans = data.get('flight_plans', [])
        
        # Apply the same filtering logic as the main analysis system
        filtered_conflicts = self.filter_duplicate_conflicts(conflicts)
        
        # Create flight plan lookup - include ALL flights, not just those with conflicts
        flight_data = {}
        
        # First, add all flights from flight_plans (even those without conflicts)
        for flight_plan in flight_plans:
            flight_data[flight_plan] = {
                'arrival_time': 60,  # Default 60 minutes if no conflict data
                'conflicts': []
            }
        
        # Then add conflict information for flights that have conflicts
        for conflict in filtered_conflicts:
            flight1 = conflict['flight1']
            flight2 = conflict['flight2']
            
            # Calculate flight durations (simplified - using arrival times)
            flight1_arrival = conflict.get('flight1_arrival', 60)
            flight2_arrival = conflict.get('flight2_arrival', 60)
            
            # Ensure both flights are in flight_data
            if flight1 not in flight_data:
                flight_data[flight1] = {
                    'arrival_time': flight1_arrival,
                    'conflicts': []
                }
            if flight2 not in flight_data:
                flight_data[flight2] = {
                    'arrival_time': flight2_arrival,
                    'conflicts': []
                }
            
            # Update arrival times if we have conflict data
            flight_data[flight1]['arrival_time'] = flight1_arrival
            flight_data[flight2]['arrival_time'] = flight2_arrival
            
            # Store conflict information
            conflict_info = {
                'conflict_id': f"{flight1}_{flight2}",
                'other_flight': flight2 if flight1 == flight1 else flight1,
                'conflict_time': conflict.get('time1', 0),
                'location': conflict.get('waypoint1', 'Unknown'),
                'distance': conflict.get('distance', 0),
                'altitude_diff': conflict.get('altitude_diff', 0),
                'phase': conflict.get('stage1', 'Unknown')
            }
            
            flight_data[flight1]['conflicts'].append(conflict_info)
            flight_data[flight2]['conflicts'].append({
                **conflict_info,
                'other_flight': flight1,
                'conflict_time': conflict.get('time2', 0),
                'location': conflict.get('waypoint2', 'Unknown'),
                'phase': conflict.get('stage2', 'Unknown')
            })
        
        return flight_data
    
    def calculate_departure_times(self, flight_data: Dict) -> Dict[str, Dict]:
        """Calculate optimal departure times to maximize simultaneous conflicts.
        
        FIXED: Now respects conflict analysis departure times instead of using "most conflicts" rule.
        The algorithm loads intended departure times from conflict analysis and schedules flights
        in chronological order, ensuring accurate timing based on conflict analysis results.
        
        Previous Issue: The algorithm incorrectly prioritized flights with "most conflicts" 
        and forced them to depart at event start time, ignoring intended departure times.
        
        Current Fix: Uses conflict analysis departure times to ensure flights depart at 
        their intended times (e.g., YSSY-YSWG at 14:16 instead of 14:00).
        """
        scheduled_flights = {}
        
        # Load conflict analysis data to get intended departure times
        conflict_data = self.load_conflict_data()
        departure_schedule = conflict_data.get('scenario', {}).get('departure_schedule', [])
        
        # Create lookup for intended departure times (minutes after event start)
        intended_departures = {}
        for flight_schedule in departure_schedule:
            flight = flight_schedule['flight']
            departure_minutes = flight_schedule['departure_time']
            intended_departures[flight] = departure_minutes
        
        # Sort flights by their intended departure time (earliest first)
        sorted_flights = sorted(intended_departures.items(), key=lambda x: x[1])
        
        # Schedule flights in order of their intended departure times
        for flight, intended_minutes in sorted_flights:
            # Calculate actual departure time
            departure_time = self.start_time + timedelta(minutes=intended_minutes)
            
            # Ensure departure time is within event window
            if departure_time < self.start_time:
                departure_time = self.start_time
            elif departure_time > self.end_time:
                departure_time = self.end_time
            
            scheduled_flights[flight] = {
                'departure_time': departure_time,
                'conflicts': flight_data[flight]['conflicts'],
                'flight_duration': flight_data[flight]['arrival_time']
            }
            
            logging.info(f"Flight {flight} scheduled at {datetime_to_utc_hhmm(departure_time)} (intended: +{intended_minutes}min)")
        
        # Now optimize timing to maximize simultaneous conflicts
        # This is a simplified optimization - in practice you might want more sophisticated logic
        optimized_scheduled_flights = self._optimize_conflict_timing(scheduled_flights, flight_data)
        
        return optimized_scheduled_flights
    
    def _optimize_conflict_timing(self, scheduled_flights: Dict, flight_data: Dict) -> Dict[str, Dict]:
        """Optimize departure times to maximize simultaneous conflicts."""
        # For now, return the scheduled flights as-is
        # In a more sophisticated implementation, you could:
        # 1. Analyze conflict timing between flights
        # 2. Adjust departure times to make conflicts happen simultaneously
        # 3. Ensure all flights still depart within the event window
        
        return scheduled_flights
    
    def _find_available_slot(self, used_times: List[datetime]) -> datetime:
        """Find an available departure time slot."""
        # Start 15 minutes after event start
        current_time = self.start_time + timedelta(minutes=15)
        
        while current_time <= self.end_time:
            # Check if this time is available (with 5-minute buffer)
            available = True
            for used_time in used_times:
                if abs((current_time - used_time).total_seconds()) < 300:  # 5 minutes
                    available = False
                    break
            
            if available:
                return current_time
            
            current_time += timedelta(minutes=15)
        
        # If no slot found, use end time - 30 minutes
        return self.end_time - timedelta(minutes=30)
    
    def generate_schedule_output(self, scheduled_flights: Dict) -> str:
        """Generate CSV schedule output."""
        output = []
        output.append("Aircraft,Departure_Time,Route,Expected_Conflicts,Notes")
        
        for flight, data in scheduled_flights.items():
            departure_str = datetime_to_utc_hhmm(data['departure_time'])
            conflicts = len(data['conflicts'])
            notes = f"{conflicts} conflicts" if conflicts > 0 else "No conflicts"
            
            output.append(f"{flight},{departure_str},{flight},{conflicts},{notes}")
        
        return "\n".join(output)
    
    def generate_briefing_output(self, scheduled_flights: Dict, original_data: Dict) -> str:
        """Generate ATC briefing document."""
        output = []
        output.append("ATC CONFLICT EVENT BRIEFING")
        output.append("=" * 50)
        output.append(f"Event Start: {datetime_to_utc_hhmm(self.start_time)}")
        output.append(f"Event End: {datetime_to_utc_hhmm(self.end_time)}")
        output.append(f"Duration: {self.event_duration} minutes")
        output.append("")
        
        # Flight schedule
        output.append("DEPARTURE SCHEDULE:")
        output.append("-" * 30)
        for flight, data in sorted(scheduled_flights.items(), key=lambda x: x[1]['departure_time']):
            departure_str = datetime_to_utc_hhmm(data['departure_time'])
            conflicts = len(data['conflicts'])
            output.append(f"{departure_str} - {flight} ({conflicts} conflicts)")
        
        output.append("")
        
        # Conflict analysis with timing
        output.append("CONFLICT ANALYSIS:")
        output.append("-" * 30)
        
        total_conflicts = 0
        for flight, data in scheduled_flights.items():
            if data['conflicts']:
                output.append(f"\n{flight} conflicts:")
                for conflict in data['conflicts']:
                    total_conflicts += 1
                    
                    # Calculate conflict time based on departure time and flight duration to conflict
                    departure_time = data['departure_time']
                    conflict_time_minutes = conflict['conflict_time']
                    conflict_actual_time = departure_time + timedelta(minutes=conflict_time_minutes)
                    
                    # Round the displayed time to nearest minute while keeping decimal precision for calculations
                    rounded_minutes = round(conflict_time_minutes)
                    rounded_time = departure_time + timedelta(minutes=rounded_minutes)
                    conflict_time_str = datetime_to_utc_hhmm(rounded_time)
                    
                    output.append(f"  - With {conflict['other_flight']} at {conflict['location']}")
                    output.append(f"    Time: {conflict_time_str} (departure +{rounded_minutes}min)")
                    output.append(f"    Distance: {conflict['distance']:.1f}nm, Alt diff: {conflict['altitude_diff']}ft")
                    output.append(f"    Phase: {conflict['phase']}")
        
        output.append(f"\nTotal conflicts: {total_conflicts}")
        
        return "\n".join(output)
    


    def run_scheduling(self) -> None:
        """Run the complete conflict scheduling process."""
        print("ATC Conflict Scheduler")
        print("=" * 40)
        print(f"Event Window: {datetime_to_utc_hhmm(self.start_time)} - {datetime_to_utc_hhmm(self.end_time)}")
        print(f"Duration: {self.event_duration} minutes")
        print()
        
        # Load conflict data
        logging.info("Loading conflict analysis data...")
        data = self.load_conflict_data()
        
        # Analyze conflicts for scheduling
        logging.info("Analyzing conflicts for scheduling...")
        flight_data = self.analyze_conflicts_for_scheduling(data)
        
        # Calculate departure times
        logging.info("Calculating optimal departure times...")
        scheduled_flights = self.calculate_departure_times(flight_data)
        
        # After scheduling, update each conflict with actual lateral separation at scheduled conflict time
        import json
        interp_path = 'temp/routes_with_added_interpolated_points.json'
        if os.path.exists(interp_path):
            with open(interp_path, 'r') as f:
                routes_data = json.load(f)
            # Extract flight waypoints from interpolated points (excluding metadata)
            flight_waypoints = {}
            for flight_id, points in routes_data.items():
                if flight_id != '_metadata':
                    flight_waypoints[flight_id] = points
            def interpolate_position(waypoints, minutes):
                # Find the two waypoints that bracket the time
                prev_wp = None
                for wp in waypoints:
                    # Convert time to minutes for comparison (handle both string and float)
                    time_val = wp.get('time', '1400')
                    if isinstance(time_val, str):
                        wp_minutes = int(time_val[:2]) * 60 + int(time_val[2:]) if len(time_val) == 4 else 0
                    else:
                        wp_minutes = int(time_val) if isinstance(time_val, (int, float)) else 0
                    if wp_minutes > minutes:
                        break
                    prev_wp = wp
                next_wp = None
                for wp in waypoints:
                    time_val = wp.get('time', '1400')
                    if isinstance(time_val, str):
                        wp_minutes = int(time_val[:2]) * 60 + int(time_val[2:]) if len(time_val) == 4 else 0
                    else:
                        wp_minutes = int(time_val) if isinstance(time_val, (int, float)) else 0
                    if wp_minutes >= minutes:
                        next_wp = wp
                        break
                # Ensure both waypoints are valid and have lat/lon
                if not prev_wp or not next_wp or prev_wp == next_wp:
                    return (None, None)
                if any(k not in prev_wp or k not in next_wp for k in ('lat', 'lon')):
                    return (None, None)
                # Convert times to minutes for interpolation
                t0_val = prev_wp.get('time', '1400')
                t1_val = next_wp.get('time', '1400')
                if isinstance(t0_val, str):
                    t0 = int(t0_val[:2]) * 60 + int(t0_val[2:]) if len(t0_val) == 4 else 0
                else:
                    t0 = int(t0_val) if isinstance(t0_val, (int, float)) else 0
                if isinstance(t1_val, str):
                    t1 = int(t1_val[:2]) * 60 + int(t1_val[2:]) if len(t1_val) == 4 else 0
                else:
                    t1 = int(t1_val) if isinstance(t1_val, (int, float)) else 0
                frac = (minutes - t0) / (t1 - t0) if t1 > t0 else 0
                lat = prev_wp['lat'] + frac * (next_wp['lat'] - prev_wp['lat'])
                lon = prev_wp['lon'] + frac * (next_wp['lon'] - prev_wp['lon'])
                return (lat, lon)
            for flight, data in scheduled_flights.items():
                for conflict in data['conflicts']:
                    other_flight = conflict['other_flight']
                    # Get scheduled departure times
                    dep1 = scheduled_flights[flight]['departure_time']
                    dep2 = scheduled_flights[other_flight]['departure_time'] if other_flight in scheduled_flights else self.start_time
                    # Get conflict time offsets
                    t1 = conflict['conflict_time']
                    t2 = None
                    for c in scheduled_flights[other_flight]['conflicts']:
                        if c['other_flight'] == flight and c['conflict_id'] == conflict['conflict_id']:
                            t2 = c['conflict_time']
                            break
                    if t2 is None:
                        t2 = t1
                    # Calculate absolute times since event start
                    abs1 = (dep1 - self.start_time).total_seconds() / 60.0 + t1
                    abs2 = (dep2 - self.start_time).total_seconds() / 60.0 + t2
                    # Interpolate positions
                    wp1 = flight_waypoints.get(flight, [])
                    wp2 = flight_waypoints.get(other_flight, [])
                    lat1, lon1 = interpolate_position(wp1, t1)
                    lat2, lon2 = interpolate_position(wp2, t2)
                    if None in (lat1, lon1, lat2, lon2):
                        print(f"[DEBUG]   Interpolation failed: lat1={lat1}, lon1={lon1}, lat2={lat2}, lon2={lon2}")
        
        # Update interpolated points with scheduled UTC times (4-digit HHMM)
        try:
            interp_path = 'temp/routes_with_added_interpolated_points.json'
            if os.path.exists(interp_path):
                with open(interp_path, 'r') as f:
                    routes = json.load(f)

                for flight_id, points in routes.items():
                    dep_dt = scheduled_flights.get(flight_id, {}).get('departure_time')
                    if dep_dt is not None:
                        dep_min = dep_dt.hour * 60 + dep_dt.minute
                        for pt in points:
                            # Get offset in minutes after departure
                            orig_time = pt.get('time', 0)
                            # Compute UTC minutes
                            utc_minutes = dep_min + (orig_time if isinstance(orig_time, (int, float)) else 0)
                            # Wrap around 24h
                            utc_minutes = utc_minutes % (24 * 60)
                            # Convert to HHMM string
                            hours = int(utc_minutes // 60)
                            mins = int(utc_minutes % 60)
                            pt['time'] = f"{hours:02d}{mins:02d}"

                # Update conflict-specific points with exact scheduled conflict times (also as UTC HHMM)
                for flight_id, flight_data in scheduled_flights.items():
                    if flight_id in routes:
                        dep_dt = flight_data['departure_time']
                        dep_min = dep_dt.hour * 60 + dep_dt.minute
                        for conflict in flight_data.get('conflicts', []):
                            other_flight = conflict['other_flight']
                            conflict_time = conflict['conflict_time']
                            utc_minutes = dep_min + conflict_time
                            utc_minutes = utc_minutes % (24 * 60)
                            hours = int(utc_minutes // 60)
                            mins = int(utc_minutes % 60)
                            conflict_hhmm = f"{hours:02d}{mins:02d}"
                            # Find the conflict point for this flight
                            for pt in routes[flight_id]:
                                if (pt.get('name', '').startswith('CONFLICT_') and other_flight in pt.get('name', '')):
                                    pt['time'] = conflict_hhmm
                                    logging.info(f'Updated conflict point for {flight_id} vs {other_flight} to UTC time {pt["time"]}')
                                    break

                # Sort all points by UTC time (as integer)
                for flight_id in routes:
                    if flight_id != '_metadata':  # Skip metadata section
                        routes[flight_id].sort(key=lambda x: int(x.get('time', '0000')))

                # Add departure schedule metadata to the file
                routes['_metadata'] = {
                    'departure_schedule': {},
                    'event_start': datetime_to_utc_hhmm(self.start_time),
                    'event_end': datetime_to_utc_hhmm(self.end_time),
                    'total_flights': len(scheduled_flights),
                    'total_conflicts': sum(len(data.get('conflicts', [])) for data in scheduled_flights.values())
                }
                
                # Add departure times for each flight
                for flight_id, flight_data in scheduled_flights.items():
                    routes['_metadata']['departure_schedule'][flight_id] = {
                        'departure_time': datetime_to_utc_hhmm(flight_data['departure_time']),
                        'conflicts': len(flight_data.get('conflicts', []))
                    }

                with open(interp_path, 'w') as f:
                    json.dump(routes, f, indent=2)
                logging.info('Updated interpolated points with scheduled UTC times (HHMM) and departure schedule metadata')
        except Exception as e:
            logging.warning(f'Failed to update interpolated points with schedule: {e}')
            import traceback
            traceback.print_exc()

        # Validation: Ensure all 'time' fields are 4-digit UTC 'HHMM' strings
        try:
            with open(interp_path, 'r') as f:
                routes = json.load(f)
            import re
            hhmm_pattern = re.compile(r'^[0-2][0-9][0-5][0-9]$')
            for flight_id, points in routes.items():
                # Skip metadata section
                if flight_id == '_metadata':
                    continue
                for pt in points:
                    t = pt.get('time', '')
                    if not (isinstance(t, str) and len(t) == 4 and hhmm_pattern.match(t)):
                        raise ValueError(f"Non-UTC time found in {flight_id}: {pt}")
            print('Validation passed: All interpolation times are UTC HHMM strings.')
        except Exception as e:
            print(f'Validation failed: {e}')
            raise

        # Generate outputs
        logging.info("Generating schedule outputs...")
        try:
            # ATC briefing
            briefing_text = self.generate_briefing_output(scheduled_flights, data)
            with open(BRIEFING_OUTPUT_FILE, 'w') as f:
                f.write(briefing_text)

            print("OK: Scheduling complete!")
            print(f"Generated files:")
            print(f"   - {BRIEFING_OUTPUT_FILE} - ATC briefing")
            print(f"\nDeparture Schedule:")
            for flight, data in sorted(scheduled_flights.items(), key=lambda x: x[1]['departure_time']):
                departure_str = datetime_to_utc_hhmm(data['departure_time'])
                conflicts = len(data['conflicts'])
                print(f"   {departure_str} - {flight} ({conflicts} conflicts)")
        except Exception as e:
            print(f"ERROR: Exception during output generation: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

def main():
    """Main function to parse arguments and run scheduling."""
    parser = argparse.ArgumentParser(
        description="Generate departure schedules for ATC conflict events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python schedule_conflicts.py --start 14:00 --end 18:00
  python schedule_conflicts.py --start 14:00 --end 18:00 --verbose
  python schedule_conflicts.py --start 09:00 --end 12:00
        """
    )
    
    parser.add_argument('--start', required=True, help='Event start time (HH:MM)')
    parser.add_argument('--end', required=True, help='Event end time (HH:MM)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate time parameters
    try:
        start_time = datetime.strptime(args.start, "%H:%M")
        end_time = datetime.strptime(args.end, "%H:%M")
        
        if start_time >= end_time:
            print("ERROR: End time must be after start time")
            sys.exit(1)
        
        if (end_time - start_time).total_seconds() < 3600:  # Less than 1 hour
            print("Warning: Event duration is less than 1 hour")
        
    except ValueError:
        print("ERROR: Invalid time format. Use HH:MM (e.g., 14:00)")
        sys.exit(1)
    
    # Create scheduler and run
    scheduler = ConflictScheduler(args.start, args.end, args.verbose)
    
    try:
        scheduler.run_scheduling()
    except Exception as e:
        print(f"ERROR: Scheduling failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("\n[ERROR] Unhandled exception in generate_schedule_conflicts.py:")
        traceback.print_exc()
        exit(1) 