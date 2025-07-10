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
BRIEFING_OUTPUT_FILE = "atc_briefing.txt"

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
            print(f"❌ Invalid time format: {time_str}. Use HH:MM format (e.g., 14:00)")
            sys.exit(1)
    
    def _calculate_duration(self) -> int:
        """Calculate event duration in minutes."""
        duration = self.end_time - self.start_time
        return int(duration.total_seconds() / 60)
    
    def load_conflict_data(self) -> Dict:
        """Load conflict analysis data."""
        if not os.path.exists(CONFLICT_ANALYSIS_FILE):
            print(f"❌ Conflict analysis file not found: {CONFLICT_ANALYSIS_FILE}")
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
        """Calculate optimal departure times for each aircraft."""
        scheduled_flights = {}
        # Start with the first flight at event start time
        first_flight = list(flight_data.keys())[0]
        scheduled_flights[first_flight] = {
            'departure_time': self.start_time,
            'conflicts': flight_data[first_flight]['conflicts'],
            'flight_duration': flight_data[first_flight]['arrival_time']
        }
        logging.info(f"First flight {first_flight} departs at {self.start_time.strftime('%H:%M')}")
        # Calculate departure times for other flights based on conflicts
        for flight, data in flight_data.items():
            if flight == first_flight:
                continue
            possible_departures = []
            for conflict in data['conflicts']:
                other_flight = conflict['other_flight']
                if other_flight in scheduled_flights:
                    other_departure = scheduled_flights[other_flight]['departure_time']
                    # Find the correct arrival times for both flights to the conflict point
                    # If this flight is flight1, use time1; if flight2, use time2
                    if flight == conflict['conflict_id'].split('_')[0]:
                        this_time_to_conflict = conflict['conflict_time']
                        # Find the matching conflict in the other flight's list to get its time
                        for c in flight_data[other_flight]['conflicts']:
                            if c['conflict_id'] == conflict['conflict_id']:
                                other_time_to_conflict = c['conflict_time']
                                break
                        else:
                            other_time_to_conflict = 0
                    else:
                        # This flight is flight2
                        this_time_to_conflict = conflict['conflict_time']
                        # Find the matching conflict in the other flight's list to get its time
                        for c in flight_data[other_flight]['conflicts']:
                            if c['conflict_id'] == conflict['conflict_id']:
                                other_time_to_conflict = c['conflict_time']
                                break
                        else:
                            other_time_to_conflict = 0
                    # Calculate required departure so both arrive at the same time
                    required_departure = other_departure + timedelta(minutes=other_time_to_conflict - this_time_to_conflict)
                    if self.start_time <= required_departure <= self.end_time:
                        possible_departures.append(required_departure)
            if possible_departures:
                best_departure = min(possible_departures)
            else:
                if scheduled_flights:
                    latest_departure = max(f['departure_time'] for f in scheduled_flights.values())
                    best_departure = latest_departure + timedelta(minutes=1)
                    if best_departure > self.end_time:
                        best_departure = self.end_time
                else:
                    best_departure = self.start_time
            scheduled_flights[flight] = {
                'departure_time': best_departure,
                'conflicts': data['conflicts'],
                'flight_duration': data['arrival_time']
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
                    
                    output.append(f"  • With {conflict['other_flight']} at {conflict['location']}")
                    output.append(f"    Time: {conflict_time_str} (departure +{rounded_minutes}min)")
                    output.append(f"    Distance: {conflict['distance']:.1f}nm, Alt diff: {conflict['altitude_diff']}ft")
                    output.append(f"    Phase: {conflict['phase']}")
        
        output.append(f"\nTotal conflicts: {total_conflicts}")
        
        return "\n".join(output)
    
    def update_animation_data_departure_times(self, scheduled_flights):
        """Update animation_data.json with the correct departure_time for each flight."""
        import json
        anim_path = 'web_visualization/animation_data.json'
        if not os.path.exists(anim_path):
            print(f"❌ {anim_path} not found. Cannot update departure times.")
            return
        with open(anim_path, 'r') as f:
            data = json.load(f)
        flights = data.get('flights', [])
        for flight in flights:
            flight_id = flight.get('flight_id')
            if flight_id in scheduled_flights:
                flight['departure_time'] = scheduled_flights[flight_id]['departure_time'].strftime('%H:%M')
        with open(anim_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ Updated departure_time for all flights in {anim_path}")

    def run_scheduling(self) -> None:
        """Run the complete conflict scheduling process."""
        print("🎯 ATC Conflict Scheduler")
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
        
        # Generate outputs
        logging.info("Generating schedule outputs...")
        
        # CSV schedule
        schedule_csv = self.generate_schedule_output(scheduled_flights)
        with open(SCHEDULE_OUTPUT_FILE, 'w') as f:
            f.write(schedule_csv)
        
        # ATC briefing
        briefing_text = self.generate_briefing_output(scheduled_flights, data)
        with open(BRIEFING_OUTPUT_FILE, 'w') as f:
            f.write(briefing_text)
        
        # After generating schedule, update animation_data.json
        self.update_animation_data_departure_times(scheduled_flights)
        
        # Print summary
        print("✅ Scheduling complete!")
        print(f"📁 Generated files:")
        print(f"   • {SCHEDULE_OUTPUT_FILE} - Departure schedule")
        print(f"   • {BRIEFING_OUTPUT_FILE} - ATC briefing")
        
        # Print schedule summary
        print(f"\n📋 Departure Schedule:")
        for flight, data in sorted(scheduled_flights.items(), key=lambda x: x[1]['departure_time']):
            departure_str = data['departure_time'].strftime('%H:%M')
            conflicts = len(data['conflicts'])
            print(f"   {departure_str} - {flight} ({conflicts} conflicts)")

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
            print("❌ End time must be after start time")
            sys.exit(1)
        
        if (end_time - start_time).total_seconds() < 3600:  # Less than 1 hour
            print("⚠️  Warning: Event duration is less than 1 hour")
        
    except ValueError:
        print("❌ Invalid time format. Use HH:MM (e.g., 14:00)")
        sys.exit(1)
    
    # Create scheduler and run
    scheduler = ConflictScheduler(args.start, args.end, args.verbose)
    
    try:
        scheduler.run_scheduling()
    except Exception as e:
        print(f"❌ Scheduling failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 