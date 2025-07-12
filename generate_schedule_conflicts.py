#!/usr/bin/env python3
"""
ATC Conflict Scheduler
======================

Generates departure schedules to ensure aircraft arrive at conflict points simultaneously
within a defined event time window. The first flight departs at the event start time.

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
CONFLICT_ANALYSIS_FILE = "temp/conflict_analysis.json"
SCHEDULE_OUTPUT_FILE = "event_schedule.csv"
BRIEFING_OUTPUT_FILE = "pilot_briefing.txt"

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
            print("Run 'python run_analysis.py --analyze-only' first")
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
        conflicts = data.get('scenario', {}).get('actual_conflicts', [])
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
        """Calculate optimal departure times to maximize simultaneous conflicts."""
        scheduled_flights = {}
        
        # Get all unique flight pairs that have conflicts
        conflict_pairs = set()
        for flight, data in flight_data.items():
            for conflict in data['conflicts']:
                other_flight = conflict['other_flight']
                pair = tuple(sorted([flight, other_flight]))
                conflict_pairs.add(pair)
        
        logging.info(f"Found {len(conflict_pairs)} conflict pairs to schedule")
        
        # Analyze all conflicts to determine optimal departure order
        flight_conflict_scores = {}
        for flight in flight_data:
            flight_conflict_scores[flight] = 0
        
        # Count how many conflicts each flight participates in
        for flight1, flight2 in conflict_pairs:
            flight_conflict_scores[flight1] += 1
            flight_conflict_scores[flight2] += 1
        
        # Find the flight with the most conflicts to start with
        best_starting_flight = max(flight_conflict_scores.items(), key=lambda x: x[1])[0]
        logging.info(f"Selected {best_starting_flight} as starting flight (has {flight_conflict_scores[best_starting_flight]} conflicts)")
        
        # Schedule the best starting flight first
        scheduled_flights[best_starting_flight] = {
            'departure_time': self.start_time,
            'conflicts': flight_data[best_starting_flight]['conflicts'],
            'flight_duration': flight_data[best_starting_flight]['arrival_time']
        }
        
        # For each remaining flight, calculate optimal departure time based on conflicts
        remaining_flights = [f for f in flight_data.keys() if f != best_starting_flight]
        
        for flight in remaining_flights:
            possible_departures = []
            
            # Check all conflicts this flight has with already scheduled flights
            for conflict in flight_data[flight]['conflicts']:
                other_flight = conflict['other_flight']
                if other_flight in scheduled_flights:
                    other_departure = scheduled_flights[other_flight]['departure_time']
                    
                    # Find the matching conflict data
                    conflict_data = None
                    for c in flight_data[other_flight]['conflicts']:
                        if c['other_flight'] == flight and c['conflict_id'] == conflict['conflict_id']:
                            conflict_data = {
                                'this_time': conflict['conflict_time'],
                                'other_time': c['conflict_time']
                            }
                            break
                    
                    if conflict_data:
                        # Calculate optimal departure time for simultaneous conflict
                        # If other flight departs at other_departure, when should this flight depart?
                        required_departure = other_departure + timedelta(minutes=conflict_data['other_time'] - conflict_data['this_time'])
                        
                        if self.start_time <= required_departure <= self.end_time:
                            possible_departures.append(required_departure)
            
            # Choose the best departure time
            if possible_departures:
                # Prefer earlier times to maximize conflicts
                best_departure = min(possible_departures)
            else:
                # Fallback: schedule after the latest scheduled flight
                if scheduled_flights:
                    latest_departure = max(f['departure_time'] for f in scheduled_flights.values())
                    best_departure = latest_departure + timedelta(minutes=1)
                    if best_departure > self.end_time:
                        best_departure = self.end_time
                else:
                    best_departure = self.start_time
            
            scheduled_flights[flight] = {
                'departure_time': best_departure,
                'conflicts': flight_data[flight]['conflicts'],
                'flight_duration': flight_data[flight]['arrival_time']
            }
            
            logging.info(f"Flight {flight} scheduled at {best_departure.strftime('%H:%M')}")
        
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
            departure_str = data['departure_time'].strftime('%H:%M')
            conflicts = len(data['conflicts'])
            notes = f"{conflicts} conflicts" if conflicts > 0 else "No conflicts"
            
            output.append(f"{flight},{departure_str},{flight},{conflicts},{notes}")
        
        return "\n".join(output)
    
    def generate_briefing_output(self, scheduled_flights: Dict, original_data: Dict) -> str:
        """Generate ATC briefing document."""
        output = []
        output.append("ATC CONFLICT EVENT BRIEFING")
        output.append("=" * 50)
        output.append(f"Event Start: {self.start_time.strftime('%H:%M')}")
        output.append(f"Event End: {self.end_time.strftime('%H:%M')}")
        output.append(f"Duration: {self.event_duration} minutes")
        output.append("")
        
        # Flight schedule
        output.append("DEPARTURE SCHEDULE:")
        output.append("-" * 30)
        for flight, data in sorted(scheduled_flights.items(), key=lambda x: x[1]['departure_time']):
            departure_str = data['departure_time'].strftime('%H:%M')
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
                    conflict_time_str = rounded_time.strftime('%H:%M')
                    
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
        print(f"Event Window: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}")
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
        anim_path = 'web_visualization/animation_data.json'
        if os.path.exists(anim_path):
            with open(anim_path, 'r') as f:
                anim_data = json.load(f)
            flight_waypoints = {f['flight_id']: f['waypoints'] for f in anim_data.get('flights', [])}
            def interpolate_position(waypoints, minutes):
                # Find the two waypoints that bracket the time
                prev_wp = None
                for wp in waypoints:
                    if wp['time_from_departure'] > minutes:
                        break
                    prev_wp = wp
                next_wp = None
                for wp in waypoints:
                    if wp['time_from_departure'] >= minutes:
                        next_wp = wp
                        break
                # Ensure both waypoints are valid and have lat/lon
                if not prev_wp or not next_wp or prev_wp == next_wp:
                    return (None, None)
                if any(k not in prev_wp or k not in next_wp for k in ('lat', 'lon')):
                    return (None, None)
                t0 = prev_wp['time_from_departure']
                t1 = next_wp['time_from_departure']
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
                    # Debug output for interpolation
                    print(f"[DEBUG] Conflict: {flight} vs {other_flight}")
                    print(f"[DEBUG]   Scheduled departures: {dep1.strftime('%H:%M')} (flight), {dep2.strftime('%H:%M')} (other)")
                    print(f"[DEBUG]   Conflict times: t1={t1}, t2={t2}")
                    if wp1:
                        t_min1 = wp1[0]['time_from_departure'] if len(wp1) > 0 else None
                        t_max1 = wp1[-1]['time_from_departure'] if len(wp1) > 0 else None
                        print(f"[DEBUG]   {flight} waypoints time range: {t_min1} to {t_max1}")
                    if wp2:
                        t_min2 = wp2[0]['time_from_departure'] if len(wp2) > 0 else None
                        t_max2 = wp2[-1]['time_from_departure'] if len(wp2) > 0 else None
                        print(f"[DEBUG]   {other_flight} waypoints time range: {t_min2} to {t_max2}")
                    lat1, lon1 = interpolate_position(wp1, t1)
                    lat2, lon2 = interpolate_position(wp2, t2)
                    if None in (lat1, lon1, lat2, lon2):
                        print(f"[DEBUG]   Interpolation failed: lat1={lat1}, lon1={lon1}, lat2={lat2}, lon2={lon2}")

        
        # Generate outputs
        logging.info("Generating schedule outputs...")
        try:
            # CSV schedule
            schedule_csv = self.generate_schedule_output(scheduled_flights)
            with open(SCHEDULE_OUTPUT_FILE, 'w') as f:
                f.write(schedule_csv)
            # ATC briefing
            briefing_text = self.generate_briefing_output(scheduled_flights, data)
            with open(BRIEFING_OUTPUT_FILE, 'w') as f:
                f.write(briefing_text)

            print("OK: Scheduling complete!")
            print(f"Generated files:")
            print(f"   - {SCHEDULE_OUTPUT_FILE} - Departure schedule")
            print(f"   - {BRIEFING_OUTPUT_FILE} - ATC briefing")
            print(f"\nDeparture Schedule:")
            for flight, data in sorted(scheduled_flights.items(), key=lambda x: x[1]['departure_time']):
                departure_str = data['departure_time'].strftime('%H:%M')
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
            print("⚠️  Warning: Event duration is less than 1 hour")
        
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