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

Generates departure schedules to maximize unique aircraft pairs in conflict
by adjusting departure times based on conflict analysis data.

FLIGHT ID SYSTEM:
- Uses unique flight IDs (FLT0001, FLT0002, etc.) for scheduling and separation
- Flight IDs are maintained throughout the entire workflow
- Route information (origin-destination) is preserved for separation rules
- Enables unique identification even for flights with same origin-destination

SEPARATION RULES:
- MIN_DEPARTURE_SEPARATION_MINUTES: Minimum time between departures from same airport
- MIN_SAME_ROUTE_SEPARATION_MINUTES: Minimum time between flights with same origin-destination
- These rules prevent aircraft with identical routes from departing too close together

Algorithm:
1. Start with aircraft that has longest time to first conflict
2. Use greedy selection: immediate conflicts + bonus for future potential
3. Calculate departure times based on conflict timing
4. Try all conflicts and pick best one
5. Handle edge cases and constraints properly

Usage:
    python generate_schedule_conflicts.py --start 14:00 --end 18:00
    python generate_schedule_conflicts.py
    python generate_schedule_conflicts.py --start 14:00 --end 18:00 --max-conflicts 10
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set, Any
import logging
from collections import defaultdict
from env import (
    MIN_DEPARTURE_SEPARATION_MINUTES, MIN_SAME_ROUTE_SEPARATION_MINUTES, BATCH_SIZE,
    TIME_TOLERANCE_MINUTES, MAX_DEPARTURE_TIME_MINUTES, DEPARTURE_TIME_STEP_MINUTES,
    TRANSITION_ALTITUDE_FT
)
from shared_types import FlightPlan, Waypoint

# Configuration
CONFLICT_ANALYSIS_FILE = "temp/potential_conflict_data.json"
BRIEFING_OUTPUT_FILE = "pilot_briefing.txt"

# =============================================================================
# SCHEDULING FUNCTIONS (Moved from find_potential_conflicts.py)
# =============================================================================

def optimize_departure_times(flight_plans: List[FlightPlan], potential_conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Optimize departure times to maximize conflicts.
    Enforce: No two flights can depart from the same airport within 2 minutes of each other.
    """
    # Group conflicts by flight pairs
    conflict_groups = defaultdict(list)
    for conflict in potential_conflicts:
        key = (conflict['flight1_idx'], conflict['flight2_idx'])
        conflict_groups[key].append(conflict)
    
    # Start with first flight at time 0
    departure_times = {0: 0}
    conflict_scores = defaultdict(int)
    flight_origin = {i: fp.origin for i, fp in enumerate(flight_plans)}
    
    # For each flight pair, find the best departure time for the second flight
    for (flight1_idx, flight2_idx), conflicts in conflict_groups.items():
        if flight1_idx == 0:  # First flight is our reference
            # Find the time difference that creates the most conflicts
            time_diffs = []
            for conflict in conflicts:
                time_diff = abs(conflict['time1'] - conflict['time2'])
                time_diffs.append(time_diff)
            
            # Use the most common time difference, or average if multiple
            if time_diffs:
                suggested_time = sum(time_diffs) / len(time_diffs)
                # Enforce 2-min separation from same-origin flights
                origin = flight_origin[flight2_idx]
                candidate_time = int(suggested_time)
                while any(abs(candidate_time - t) < MIN_DEPARTURE_SEPARATION_MINUTES and flight_origin[idx] == origin for idx, t in departure_times.items() if idx != flight2_idx):
                    candidate_time += MIN_DEPARTURE_SEPARATION_MINUTES
                departure_times[flight2_idx] = candidate_time
                # Count how many conflicts this creates
                for conflict in conflicts:
                    conflict_scores[flight2_idx] += 1
    
    # For remaining flights, find best departure times
    remaining_flights = set(range(len(flight_plans))) - set(departure_times.keys())
    for flight_idx in remaining_flights:
        best_time = 0
        best_score = 0
        origin = flight_origin[flight_idx]
        
        for test_time in range(0, MAX_DEPARTURE_TIME_MINUTES, DEPARTURE_TIME_STEP_MINUTES):
            # Enforce 2-min separation from same-origin flights
            if any(abs(test_time - t) < MIN_DEPARTURE_SEPARATION_MINUTES and flight_origin[idx] == origin for idx, t in departure_times.items() if idx != flight_idx):
                continue
            
            score = 0
            for conflict in potential_conflicts:
                if conflict['flight1_idx'] == flight_idx or conflict['flight2_idx'] == flight_idx:
                    other_flight = conflict['flight2_idx'] if conflict['flight1_idx'] == flight_idx else conflict['flight1_idx']
                    if other_flight in departure_times:
                        other_time = departure_times[other_flight]
                        flight_time = conflict['time1'] if conflict['flight1_idx'] == flight_idx else conflict['time2']
                        other_conflict_time = conflict['time2'] if conflict['flight1_idx'] == flight_idx else conflict['time1']
                        
                        if conflict['flight1_idx'] == flight_idx:
                            conflict_time = other_time + other_conflict_time
                            suggested_departure = conflict_time - flight_time
                        else:
                            conflict_time = other_time + other_conflict_time
                            suggested_departure = conflict_time - flight_time
                        
                        if abs(test_time - suggested_departure) < TIME_TOLERANCE_MINUTES:
                            score += 1
            
            if score > best_score:
                best_score = score
                best_time = test_time
        
        departure_times[flight_idx] = int(best_time)
        conflict_scores[flight_idx] = best_score
    
    return {
        'departure_times': departure_times,
        'conflict_scores': conflict_scores
    }


def generate_conflict_scenario(flight_plans: List[FlightPlan], potential_conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a complete conflict scenario with departure times.
    
    Args:
        flight_plans: List of flight plans
        potential_conflicts: List of detected conflicts
    
    Returns:
        Complete conflict scenario with departure schedule and actual conflicts
    """
    # Optimize departure times
    optimization = optimize_departure_times(flight_plans, potential_conflicts)
    departure_times = optimization['departure_times']
    conflict_scores = optimization['conflict_scores']
    
    # Calculate potential conflicts with departure times
    potential_conflicts_with_timing = []
    for conflict in potential_conflicts:
        flight1_idx = conflict['flight1_idx']
        flight2_idx = conflict['flight2_idx']
        if flight1_idx in departure_times and flight2_idx in departure_times:
            # Calculate when each aircraft reaches the conflict point
            flight1_arrival = departure_times[flight1_idx] + conflict['time1']
            flight2_arrival = departure_times[flight2_idx] + conflict['time2']
            potential_conflict_with_timing = dict(conflict)
            potential_conflict_with_timing['flight1_arrival'] = flight1_arrival
            potential_conflict_with_timing['flight2_arrival'] = flight2_arrival
            potential_conflict_with_timing['time_diff'] = abs(flight1_arrival - flight2_arrival)
            potential_conflicts_with_timing.append(potential_conflict_with_timing)
    
    return {
        'departure_schedule': [
            {
                'flight': f"{flight_plans[i].origin}-{flight_plans[i].destination}",
                'departure_time': departure_times[i],
                'conflict_score': conflict_scores.get(i, 0)
            }
            for i in range(len(flight_plans))
        ],
        'potential_conflicts': potential_conflicts_with_timing,
        'total_conflicts': len(potential_conflicts_with_timing)
    }

def datetime_to_utc_hhmm(dt) -> str:
    return dt.strftime('%H%M')

def minutes_to_utc_hhmm(minutes: float) -> str:
    total_minutes = int(round(minutes))
    hours = (total_minutes // 60) % 24
    mins = total_minutes % 60
    return f"{hours:02d}{mins:02d}"

def extract_flight_route_info(flight_data: Dict) -> Dict[str, Dict[str, str]]:
    """Extract origin-destination information for each flight from flight data."""
    route_info = {}
    
    for flight_id, flight_info in flight_data.items():
        if isinstance(flight_info, dict) and 'waypoints' in flight_info:
            # Extract origin and destination from waypoints
            waypoints = flight_info['waypoints']
            if waypoints:
                # First waypoint is usually departure
                origin = waypoints[0].get('name', '')
                # Last waypoint is usually arrival
                destination = waypoints[-1].get('name', '') if len(waypoints) > 1 else ''
                
                route_info[flight_id] = {
                    'origin': origin,
                    'destination': destination
                }
    
    return route_info

class ConflictScheduler:
    """Schedules aircraft departures to maximize unique aircraft pairs in conflict."""
    
    def __init__(self, start_time: str, end_time: str, verbose: bool = False):
        self.start_time = self._parse_time(start_time)
        self.end_time = self._parse_time(end_time)
        self.verbose = verbose
        self.event_duration = self._calculate_duration()
        
        # Setup logging
        # logging.basicConfig(
        #     level=logging.DEBUG if verbose else logging.INFO,
        #     format='%(asctime)s - %(levelname)s - %(message)s'
        # )
        
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
        
        # logging.info(f"Loaded conflict data with {len(data.get('flight_plans', []))} flight plans")
        return data
    
    def find_aircraft_with_longest_time_to_first_conflict(self, conflicts: List[Dict]) -> Optional[str]:
        """Find the aircraft that has the longest time to its first conflict."""
        aircraft_conflict_times = {}
        
        for conflict in conflicts:
            flight1 = conflict['flight1']
            flight2 = conflict['flight2']
            time1 = conflict['time1']  # minutes after departure
            time2 = conflict['time2']  # minutes after departure
            
            # Track the earliest conflict time for each aircraft
            if flight1 not in aircraft_conflict_times or time1 < aircraft_conflict_times[flight1]:
                aircraft_conflict_times[flight1] = time1
            if flight2 not in aircraft_conflict_times or time2 < aircraft_conflict_times[flight2]:
                aircraft_conflict_times[flight2] = time2
        
        # Find aircraft with longest time to first conflict
        if not aircraft_conflict_times:
            return None
        
        longest_time_aircraft = max(aircraft_conflict_times.items(), key=lambda x: x[1])
        # logging.info(f"Aircraft with longest time to first conflict: {longest_time_aircraft[0]} ({longest_time_aircraft[1]} minutes)")
        return longest_time_aircraft[0]
    
    def calculate_conflict_score(self, aircraft: str, scheduled_aircraft: Set[str], 
                               conflicts: List[Dict], all_aircraft: List[str]) -> int:
        """Calculate conflict score for greedy selection."""
        immediate_conflicts = 0
        future_potential = 0
        
        # Count immediate conflicts with already-scheduled aircraft
        for conflict in conflicts:
            if conflict['flight1'] == aircraft and conflict['flight2'] in scheduled_aircraft:
                immediate_conflicts += 1
            elif conflict['flight2'] == aircraft and conflict['flight1'] in scheduled_aircraft:
                immediate_conflicts += 1
        
        # Count potential conflicts with unscheduled aircraft (bonus points)
        for conflict in conflicts:
            if conflict['flight1'] == aircraft and conflict['flight2'] not in scheduled_aircraft:
                future_potential += 1
            elif conflict['flight2'] == aircraft and conflict['flight1'] not in scheduled_aircraft:
                future_potential += 1
        
        # Weighted score: immediate conflicts count more than future potential
        score = immediate_conflicts * 10 + future_potential
        return score
    
    def find_optimal_departure_time(self, aircraft: str, scheduled_aircraft: Dict[str, datetime],
                                   conflicts: List[Dict], all_aircraft: List[str], route_info: Optional[Dict] = None) -> Tuple[datetime, int]:
        """Find optimal departure time that creates the most unique aircraft pairs in conflict."""
        route_info = route_info or {}
        best_departure_time = None
        best_conflict_count = 0
        # Get all conflicts for this aircraft
        aircraft_conflicts = []
        for conflict in conflicts:
            if conflict['flight1'] == aircraft or conflict['flight2'] == aircraft:
                aircraft_conflicts.append(conflict)
        if not aircraft_conflicts:
            # --- Integration: Use near-conflict logic for no-conflict aircraft ---
            if route_info is not None:
                near_dep = self.find_near_conflict_departure_time(
                    aircraft, scheduled_aircraft, route_info, self.start_time, self.end_time)
                if near_dep:
                    return near_dep, 0
            # Fallback
            return self._find_fallback_departure_time(aircraft, scheduled_aircraft, route_info), 0
        # Try each conflict to find the best departure time
        for conflict in aircraft_conflicts:
            if conflict['flight1'] == aircraft:
                other_aircraft = conflict['flight2']
                conflict_time_after_departure = conflict['time1']
                other_conflict_time = conflict['time2']
            else:
                other_aircraft = conflict['flight1']
                conflict_time_after_departure = conflict['time2']
                other_conflict_time = conflict['time1']
            # Skip if other aircraft is not scheduled yet  
            if other_aircraft not in scheduled_aircraft:
                continue
            # Calculate departure time to make aircraft arrive at conflict point simultaneously
            other_departure_time = scheduled_aircraft[other_aircraft]
            other_arrival_at_conflict = other_departure_time + timedelta(minutes=other_conflict_time)
            # Calculate when this aircraft should depart to arrive at the same time
            calculated_departure = other_arrival_at_conflict - timedelta(minutes=conflict_time_after_departure)
            # Validate and adjust the departure time
            valid_departure = self._validate_and_adjust_departure_time(
                calculated_departure, aircraft, scheduled_aircraft, route_info
            )
            if valid_departure:
                # Count how many unique aircraft pairs this creates
                conflict_count = self._count_unique_conflict_pairs(
                    aircraft, valid_departure, scheduled_aircraft, conflicts
                )
                if conflict_count > best_conflict_count:
                    best_conflict_count = conflict_count
                    best_departure_time = valid_departure
        if best_departure_time is None:
            # No valid conflicts found - use fallback
            return self._find_fallback_departure_time(aircraft, scheduled_aircraft, route_info), 0
        return best_departure_time, best_conflict_count
    
    def _validate_and_adjust_departure_time(self, departure_time: datetime, aircraft: str,
                                          scheduled_aircraft: Dict[str, datetime], flight_data: Dict = {}) -> Optional[datetime]:
        """Validate departure time and adjust if needed."""
        # Check if within event window
        if departure_time < self.start_time:
            departure_time = self.start_time
        elif departure_time > self.end_time:
            departure_time = self.end_time
        
        # Get flight route information
        flight_data = flight_data or {}
        aircraft_route = flight_data.get(aircraft, {})
        aircraft_origin = aircraft_route.get('origin', '')
        aircraft_dest = aircraft_route.get('destination', '')
        
        for scheduled_aircraft_id, scheduled_time in scheduled_aircraft.items():
            scheduled_route = flight_data.get(scheduled_aircraft_id, {})
            scheduled_origin = scheduled_route.get('origin', '')
            scheduled_dest = scheduled_route.get('destination', '')
            
            # Check same airport separation (2 minutes)
            if scheduled_origin and aircraft_origin and scheduled_origin == aircraft_origin:
                time_diff = abs((departure_time - scheduled_time).total_seconds() / 60)
                if time_diff < MIN_DEPARTURE_SEPARATION_MINUTES:
                    # Try to find a nearby time that respects the rule
                    if departure_time > scheduled_time:
                        adjusted_time = scheduled_time + timedelta(minutes=MIN_DEPARTURE_SEPARATION_MINUTES)
                    else:
                        adjusted_time = scheduled_time - timedelta(minutes=MIN_DEPARTURE_SEPARATION_MINUTES)
                    # Check if adjusted time is within event window
                    if self.start_time <= adjusted_time <= self.end_time:
                        departure_time = adjusted_time
                    else:
                        return None  # No valid time found
            
            # Check same route separation (5 minutes)
            if (scheduled_origin and aircraft_origin and scheduled_dest and aircraft_dest and 
                scheduled_origin == aircraft_origin and scheduled_dest == aircraft_dest):
                time_diff = abs((departure_time - scheduled_time).total_seconds() / 60)
                if time_diff < MIN_SAME_ROUTE_SEPARATION_MINUTES:
                    # Try to find a nearby time that respects the rule
                    if departure_time > scheduled_time:
                        adjusted_time = scheduled_time + timedelta(minutes=MIN_SAME_ROUTE_SEPARATION_MINUTES)
                    else:
                        adjusted_time = scheduled_time - timedelta(minutes=MIN_SAME_ROUTE_SEPARATION_MINUTES)
                    # Check if adjusted time is within event window
                    if self.start_time <= adjusted_time <= self.end_time:
                        departure_time = adjusted_time
                    else:
                        return None  # No valid time found
        
        return departure_time
    
    def _find_fallback_departure_time(self, aircraft: str, scheduled_aircraft: Dict[str, datetime], flight_data: Dict = {}) -> datetime:
        """Find fallback departure time when no conflicts are possible."""
        # Start at event start time
        departure_time = self.start_time
        
        # Get flight route information
        flight_data = flight_data or {}
        aircraft_route = flight_data.get(aircraft, {})
        aircraft_origin = aircraft_route.get('origin', '')
        aircraft_dest = aircraft_route.get('destination', '')
        
        for scheduled_aircraft_id, scheduled_time in scheduled_aircraft.items():
            scheduled_route = flight_data.get(scheduled_aircraft_id, {})
            scheduled_origin = scheduled_route.get('origin', '')
            scheduled_dest = scheduled_route.get('destination', '')
            
            # Check same airport separation (2 minutes)
            if scheduled_origin and aircraft_origin and scheduled_origin == aircraft_origin:
                time_diff = abs((departure_time - scheduled_time).total_seconds() / 60)
                if time_diff < MIN_DEPARTURE_SEPARATION_MINUTES:
                    departure_time = scheduled_time + timedelta(minutes=MIN_DEPARTURE_SEPARATION_MINUTES)
            
            # Check same route separation (5 minutes)
            if (scheduled_origin and aircraft_origin and scheduled_dest and aircraft_dest and 
                scheduled_origin == aircraft_origin and scheduled_dest == aircraft_dest):
                time_diff = abs((departure_time - scheduled_time).total_seconds() / 60)
                if time_diff < MIN_SAME_ROUTE_SEPARATION_MINUTES:
                    departure_time = scheduled_time + timedelta(minutes=MIN_SAME_ROUTE_SEPARATION_MINUTES)
        
        # Ensure within event window
        if departure_time > self.end_time:
            departure_time = self.end_time
        
        return departure_time
    
    def _count_unique_conflict_pairs(self, aircraft: str, departure_time: datetime,
                                   scheduled_aircraft: Dict[str, datetime], conflicts: List[Dict]) -> int:
        """Count unique aircraft pairs in conflict for this departure time."""
        conflict_pairs = set()
        
        for conflict in conflicts:
            if conflict['flight1'] == aircraft and conflict['flight2'] in scheduled_aircraft:
                # Calculate if this conflict would occur with the given departure time
                other_departure = scheduled_aircraft[conflict['flight2']]
                other_arrival = other_departure + timedelta(minutes=conflict['time2'])
                this_arrival = departure_time + timedelta(minutes=conflict['time1'])
                
                # Check if conflicts occur at roughly the same time (within 2 minutes)
                time_diff = abs((this_arrival - other_arrival).total_seconds() / 60)
                if time_diff <= 2:
                    conflict_pairs.add(tuple(sorted([aircraft, conflict['flight2']])))
            
            elif conflict['flight2'] == aircraft and conflict['flight1'] in scheduled_aircraft:
                # Calculate if this conflict would occur with the given departure time
                other_departure = scheduled_aircraft[conflict['flight1']]
                other_arrival = other_departure + timedelta(minutes=conflict['time1'])
                this_arrival = departure_time + timedelta(minutes=conflict['time2'])
                
                # Check if conflicts occur at roughly the same time (within 2 minutes)
                time_diff = abs((this_arrival - other_arrival).total_seconds() / 60)
                if time_diff <= 2:
                    conflict_pairs.add(tuple(sorted([aircraft, conflict['flight1']])))
        
        return len(conflict_pairs)
    
    def schedule_aircraft_for_maximum_conflicts(self, data: Dict) -> Dict[str, Dict]:
        """Schedule aircraft to maximize unique aircraft pairs in conflict."""
        conflicts = data.get('scenario', {}).get('potential_conflicts', [])
        all_aircraft = data.get('flight_plans', [])
        all_flight_data = data.get('flights')
        if not isinstance(all_flight_data, dict):
            all_flight_data = {}
        
        # Extract route information for separation rules
        route_info = extract_flight_route_info(all_flight_data)
        
        if not all_aircraft:
            print("No aircraft found in conflict data")
            return {}
        # Step 1: Find aircraft with longest time to first conflict
        first_aircraft = self.find_aircraft_with_longest_time_to_first_conflict(conflicts)
        if not first_aircraft:
            first_aircraft = all_aircraft[0]  # Fallback
        scheduled_aircraft = {}
        unscheduled_aircraft = set(all_aircraft)
        # Schedule first aircraft at event start time
        first_departure = self.start_time
        scheduled_aircraft[first_aircraft] = first_departure
        unscheduled_aircraft.remove(first_aircraft)
        # logging.info(f"Scheduled first aircraft {first_aircraft} at {datetime_to_utc_hhmm(first_departure)}")
        # Step 2: Greedy scheduling for remaining aircraft
        batch_size = BATCH_SIZE  # Recalculate scores every 3 aircraft
        aircraft_scheduled_since_recalc = 0
        while unscheduled_aircraft:
            # Recalculate scores every batch_size aircraft
            if aircraft_scheduled_since_recalc >= batch_size:
                aircraft_scheduled_since_recalc = 0
            # Calculate conflict scores for all unscheduled aircraft
            best_aircraft = None
            best_score = -1
            for aircraft in unscheduled_aircraft:
                score = self.calculate_conflict_score(aircraft, set(scheduled_aircraft.keys()), conflicts, all_aircraft)
                # If immediate conflicts are equal, consider future potential
                if score == best_score and best_aircraft:
                    # Check future potential for tie-breaking
                    future_potential_best = self._count_future_potential(best_aircraft, unscheduled_aircraft, conflicts)
                    future_potential_current = self._count_future_potential(aircraft, unscheduled_aircraft, conflicts)
                    if future_potential_current > future_potential_best:
                        best_aircraft = aircraft
                        best_score = score
                elif score > best_score:
                    best_aircraft = aircraft
                    best_score = score
            if not best_aircraft:
                # No aircraft with conflicts - pick the first one
                best_aircraft = list(unscheduled_aircraft)[0]
            # Find optimal departure time for selected aircraft
            departure_time, conflict_count = self.find_optimal_departure_time(
                best_aircraft, scheduled_aircraft, conflicts, all_aircraft, route_info
            )
            if departure_time is None:
                # No valid departure time found - skip this aircraft
                print(f"Could not find valid departure time for {best_aircraft}, skipping")
                unscheduled_aircraft.remove(best_aircraft)
                continue
            # Schedule the aircraft
            scheduled_aircraft[best_aircraft] = departure_time
            unscheduled_aircraft.remove(best_aircraft)
            aircraft_scheduled_since_recalc += 1
            # logging.info(f"Scheduled {best_aircraft} at {datetime_to_utc_hhmm(departure_time)} (creates {conflict_count} conflicts)")
        # Convert to the expected output format
        scheduled_flights = {}
        for aircraft, departure_time in scheduled_aircraft.items():
            # Count conflicts for this aircraft
            aircraft_conflicts = []
            for conflict in conflicts:
                if conflict['flight1'] == aircraft or conflict['flight2'] == aircraft:
                    other_aircraft = conflict['flight2'] if conflict['flight1'] == aircraft else conflict['flight1']
                    aircraft_conflicts.append({
                        'conflict_id': f"{aircraft}_{other_aircraft}",
                        'other_flight': other_aircraft,
                        'conflict_time': conflict['time1'] if conflict['flight1'] == aircraft else conflict['time2'],
                        'location': conflict.get('waypoint1', 'Unknown'),
                        'distance': conflict.get('distance', 0),
                        'altitude_diff': conflict.get('altitude_diff', 0),
                        'phase': conflict.get('stage1', 'Unknown')
                    })
            scheduled_flights[aircraft] = {
                'departure_time': departure_time,
                'conflicts': aircraft_conflicts,
                'flight_duration': 60  # Default duration
            }
        return scheduled_flights
    
    def _count_future_potential(self, aircraft: str, unscheduled_aircraft: Set[str], conflicts: List[Dict]) -> int:
        """Count potential conflicts with unscheduled aircraft."""
        potential = 0
        for conflict in conflicts:
            if conflict['flight1'] == aircraft and conflict['flight2'] in unscheduled_aircraft:
                potential += 1
            elif conflict['flight2'] == aircraft and conflict['flight1'] in unscheduled_aircraft:
                potential += 1
        return potential
    
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
        """Generate ATC briefing document with full flight details."""
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
        output.append("Takeoff Time | Flight | Origin-Dest | Aircraft | Level | Route")
        output.append("-" * 80)
        
        # Load flight data from individual JSON files to get origin/destination
        flights_dict = {}
        temp_dir = "temp"
        for flight in scheduled_flights.keys():
            flight_file = os.path.join(temp_dir, f"{flight}_data.json")
            if os.path.exists(flight_file):
                try:
                    with open(flight_file, 'r') as f:
                        flight_data = json.load(f)
                        flights_dict[flight] = flight_data
                except Exception as e:
                    print(f"Error loading {flight_file}: {e}")
        
        for flight, data in sorted(scheduled_flights.items(), key=lambda x: x[1]['departure_time']):
            departure_str = datetime_to_utc_hhmm(data['departure_time'])
            conflicts = len(data['conflicts'])
            
            # Get flight data from loaded files
            flight_data = flights_dict.get(flight, {})
            aircraft_type = flight_data.get('aircraft_type', 'UNK')
            origin = flight_data.get('origin', 'UNK')
            destination = flight_data.get('destination', 'UNK')
            origin_dest = f"{origin}-{destination}"
            
            # Get route from flight data
            route = flight_data.get('route', 'DCT')
            
            # Get level (altitude) - use cruise altitude if available
            level = "FL360"  # Default level
            waypoints = flight_data.get('waypoints', [])
            if waypoints:
                # Find the highest altitude in waypoints (cruise level)
                max_alt = max((wp.get('altitude', 0) for wp in waypoints), default=36000)
                if max_alt > 0:
                    if max_alt < TRANSITION_ALTITUDE_FT:
                        # Below transition altitude: show as plain number
                        level = f"{max_alt}"
                    else:
                        # Above transition altitude: show as flight level
                        level = f"FL{max_alt//100:02d}"
            
            output.append(f"{departure_str:>10} | {flight:>6} | {origin_dest:>12} | {aircraft_type:>8} | {level:>5} | {route}")
        
        output.append("")
        
        # Full flight details section
        output.append("DETAILED FLIGHT INFORMATION:")
        output.append("-" * 35)
        
        for flight, data in sorted(scheduled_flights.items(), key=lambda x: x[1]['departure_time']):
            flight_data = flights_dict.get(flight, {})
            departure_str = datetime_to_utc_hhmm(data['departure_time'])
            
            output.append(f"\n{flight} - {flight_data.get('aircraft_type', 'UNK')}")
            output.append(f"  Route: {flight_data.get('origin', 'UNK')} -> {flight_data.get('destination', 'UNK')}")
            output.append(f"  Departure: {departure_str}")
            output.append(f"  Aircraft: {flight_data.get('aircraft_type', 'UNK')}")
            
            # Flight profile with proper FL/ft display
            waypoints = flight_data.get('waypoints', [])
            if waypoints:
                output.append("  Flight Profile:")
                for i, wp in enumerate(waypoints):
                    wp_name = wp.get('name', f'WP{i+1}')
                    wp_alt = wp.get('altitude', 0)
                    
                    # Format altitude with proper FL/ft concept
                    if wp_alt < TRANSITION_ALTITUDE_FT:
                        alt_display = f"{wp_alt}ft"
                    else:
                        alt_display = f"FL{wp_alt//100:02d}"
                    
                    output.append(f"    {wp_name}: {alt_display}")
            
            # Conflict information
            if data['conflicts']:
                output.append("  Conflicts:")
                for conflict in data['conflicts']:
                    other_flight = conflict['other_flight']
                    other_aircraft_type = flights_dict.get(other_flight, {}).get('aircraft_type', 'UNK')
                    
                    # Calculate conflict time
                    departure_time = data['departure_time']
                    conflict_time_minutes = conflict['conflict_time']
                    rounded_minutes = round(conflict_time_minutes)
                    rounded_time = departure_time + timedelta(minutes=rounded_minutes)
                    conflict_time_str = datetime_to_utc_hhmm(rounded_time)
                    
                    # Format altitude difference with proper units
                    alt_diff = conflict['altitude_diff']
                    if alt_diff < TRANSITION_ALTITUDE_FT:
                        alt_diff_display = f"{alt_diff}ft"
                    else:
                        alt_diff_display = f"FL{alt_diff//100:02d}"
                    
                    output.append(f"    - With {other_flight} ({other_aircraft_type}) at {conflict['location']}")
                    output.append(f"      Time: {conflict_time_str} (departure +{rounded_minutes}min)")
                    output.append(f"      Distance: {conflict['distance']:.1f}nm, Alt diff: {alt_diff_display}")
                    output.append(f"      Phase: {conflict['phase']}")
            else:
                output.append("  Conflicts: None")
        
        output.append("")
        
        # Conflict analysis summary
        output.append("CONFLICT ANALYSIS SUMMARY:")
        output.append("-" * 30)
        
        total_conflicts = 0
        for flight, data in scheduled_flights.items():
            if data['conflicts']:
                flight_aircraft_type = flights_dict.get(flight, {}).get('aircraft_type', 'UNK')
                output.append(f"\n{flight} ({flight_aircraft_type}) conflicts:")
                for conflict in data['conflicts']:
                    total_conflicts += 1
                    
                    other_flight = conflict['other_flight']
                    other_aircraft_type = flights_dict.get(other_flight, {}).get('aircraft_type', 'UNK')
                    
                    departure_time = data['departure_time']
                    conflict_time_minutes = conflict['conflict_time']
                    rounded_minutes = round(conflict_time_minutes)
                    rounded_time = departure_time + timedelta(minutes=rounded_minutes)
                    conflict_time_str = datetime_to_utc_hhmm(rounded_time)
                    
                    # Format altitude difference
                    alt_diff = conflict['altitude_diff']
                    if alt_diff < TRANSITION_ALTITUDE_FT:
                        alt_diff_display = f"{alt_diff}ft"
                    else:
                        alt_diff_display = f"FL{alt_diff//100:02d}"
                    
                    output.append(f"  - With {other_flight} ({other_aircraft_type}) at {conflict['location']}")
                    output.append(f"    Time: {conflict_time_str} (departure +{rounded_minutes}min)")
                    output.append(f"    Distance: {conflict['distance']:.1f}nm, Alt diff: {alt_diff_display}")
                    output.append(f"    Phase: {conflict['phase']}")
        
        output.append(f"\nTotal conflicts: {total_conflicts}")
        
        return "\n".join(output)
    
    def update_interpolated_points_with_schedule(self, scheduled_flights: Dict) -> None:
        """Update interpolated points file with departure schedule metadata, aircraft type, and conflict data."""
        try:
            interp_path = 'temp/routes_with_added_interpolated_points.json'
            if not os.path.exists(interp_path):
                print(f"Interpolated points file not found: {interp_path}")
                return
            with open(interp_path, 'r') as f:
                routes = json.load(f)

            # Load aircraft types and conflict data from potential_conflict_data.json
            with open('temp/potential_conflict_data.json', 'r') as f:
                conflict_data = json.load(f)
            
            # Build a mapping from flight_id to aircraft_type (handle nested structure)
            acft_type_map = {}
            if 'flights' in conflict_data:
                # Structure: {"flights": {"FLT0001": {"aircraft_type": "E190", ...}}}
                for flight_id, flight in conflict_data['flights'].items():
                    if isinstance(flight, dict) and 'aircraft_type' in flight:
                        acft_type_map[flight_id] = flight['aircraft_type']
            else:
                # Structure: {"FLT0001": {"aircraft_type": "E190", ...}}
                for flight_id, flight in conflict_data.items():
                    if isinstance(flight, dict) and 'aircraft_type' in flight:
                        acft_type_map[flight_id] = flight['aircraft_type']
            
            # Update all points with scheduled UTC times
            new_routes = {}
            for flight_id, points in routes.items():
                if flight_id == '_metadata':
                    continue
                dep_dt = scheduled_flights.get(flight_id, {}).get('departure_time')
                if dep_dt is not None:
                    dep_min = dep_dt.hour * 60 + dep_dt.minute
                    for pt in points:
                        if isinstance(pt, dict):
                            orig_time = pt.get('time', 0)
                            utc_minutes = dep_min + (orig_time if isinstance(orig_time, (int, float)) else 0)
                            utc_minutes = utc_minutes % (24 * 60)
                            hours = int(utc_minutes // 60)
                            mins = int(utc_minutes % 60)
                            pt['time'] = f"{hours:02d}{mins:02d}"
                
                # Compose new structure with aircraft type
                new_routes[flight_id] = {
                    'aircraft_type': acft_type_map.get(flight_id, 'UNK'),
                    'route': points,
                    'conflicts': []  # Will be populated below
                }

            # Add conflict data to each flight
            for flight_id, flight_data in scheduled_flights.items():
                if flight_id in new_routes:
                    dep_dt = flight_data['departure_time']
                    dep_min = dep_dt.hour * 60 + dep_dt.minute
                    departure_time_str = datetime_to_utc_hhmm(dep_dt)
                    
                    # Add conflicts for this flight
                    for conflict in flight_data.get('conflicts', []):
                        other_flight = conflict['other_flight']
                        conflict_time = conflict['conflict_time']
                        utc_minutes = dep_min + conflict_time
                        utc_minutes = utc_minutes % (24 * 60)
                        hours = int(utc_minutes // 60)
                        mins = int(utc_minutes % 60)
                        conflict_time_utc = f"{hours:02d}{mins:02d}"
                        
                        # Find the original conflict data to get lat/lon/alt
                        original_conflict = None
                        for orig_conflict in conflict_data.get('potential_conflicts', []):
                            if ((orig_conflict['flight1'] == flight_id and orig_conflict['flight2'] == other_flight) or
                                (orig_conflict['flight1'] == other_flight and orig_conflict['flight2'] == flight_id)):
                                original_conflict = orig_conflict
                                break
                        
                        # Create conflict entry with data from original conflict
                        conflict_entry = {
                            'other_flight': other_flight,
                            'conflict_time_utc': conflict_time_utc,
                            'lat': original_conflict.get('lat1', 0) if original_conflict else 0,
                            'lon': original_conflict.get('lon1', 0) if original_conflict else 0,
                            'alt': original_conflict.get('alt1', 0) if original_conflict else 0,
                            'distance': conflict.get('distance', 0),
                            'altitude_diff': conflict.get('altitude_diff', 0),
                            'departure_time': departure_time_str
                        }
                        new_routes[flight_id]['conflicts'].append(conflict_entry)

            # Update conflict-specific points with exact scheduled conflict times
            for flight_id, flight_data in scheduled_flights.items():
                if flight_id in new_routes:
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
                        for pt in new_routes[flight_id]['route']:
                            if isinstance(pt, dict) and (pt.get('name', '').startswith('CONFLICT_') and other_flight in pt.get('name', '')):
                                pt['time'] = conflict_hhmm
                                break

            # Sort all points by UTC time
            for flight_id in new_routes:
                if flight_id != '_metadata' and isinstance(new_routes[flight_id]['route'], list):
                    new_routes[flight_id]['route'].sort(key=lambda x: int(x.get('time', '0000')))

            # Add departure schedule metadata
            new_routes['_metadata'] = {
                'departure_schedule': {},
                'event_start': datetime_to_utc_hhmm(self.start_time),
                'event_end': datetime_to_utc_hhmm(self.end_time),
                'total_flights': len(scheduled_flights),
                'total_conflicts': sum(len(data.get('conflicts', [])) for data in scheduled_flights.values())
            }
            for flight_id, flight_data in scheduled_flights.items():
                new_routes['_metadata']['departure_schedule'][flight_id] = {
                    'departure_time': datetime_to_utc_hhmm(flight_data['departure_time']),
                    'conflicts': len(flight_data.get('conflicts', []))
                }
            
            with open(interp_path, 'w') as f:
                json.dump(new_routes, f, indent=2)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def run_scheduling(self) -> None:
        """Run the complete conflict scheduling process."""
        print("ATC Conflict Scheduler")
        print("=" * 40)
        print(f"Event Window: {datetime_to_utc_hhmm(self.start_time)} - {datetime_to_utc_hhmm(self.end_time)}")
        print(f"Duration: {self.event_duration} minutes")
        print()
        
        # Load conflict data
        # logging.info("Loading conflict analysis data...")
        data = self.load_conflict_data()
        
        # Get aircraft types from original data
        flights_dict = data.get('flights', {})
        
        # Schedule aircraft for maximum conflicts
        # logging.info("Scheduling aircraft to maximize unique conflict pairs...")
        scheduled_flights = self.schedule_aircraft_for_maximum_conflicts(data)
        
        # Update interpolated points with schedule
        # logging.info("Updating interpolated points with schedule...")
        self.update_interpolated_points_with_schedule(scheduled_flights)

        # Generate outputs
        # logging.info("Generating schedule outputs...")
        try:
            # ATC briefing
            briefing_text = self.generate_briefing_output(scheduled_flights, data)
            with open(BRIEFING_OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(briefing_text)

            print("OK: Scheduling complete!")
            print(f"Generated files:")
            print(f"   - {BRIEFING_OUTPUT_FILE} - ATC briefing")
            print(f"\nDeparture Schedule:")
            for flight, data in sorted(scheduled_flights.items(), key=lambda x: x[1]['departure_time']):
                departure_str = datetime_to_utc_hhmm(data['departure_time'])
                conflicts = len(data['conflicts'])
                aircraft_type = flights_dict.get(flight, {}).get('aircraft_type', 'UNK')
                print(f"   {departure_str} - {flight} ({aircraft_type}) ({conflicts} conflicts)")
        except Exception as e:
            print(f"ERROR: Exception during output generation: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def find_near_conflict_departure_time(self, aircraft: str, scheduled_aircraft: Dict[str, datetime], all_flight_data: Dict, event_start: datetime, event_end: datetime) -> Optional[datetime]:
        """
        For a no-conflict aircraft, find a departure time that brings it as close as possible (in 3D space and time) to any scheduled aircraft during their flights.
        Returns the optimal departure time, or None if not possible.
        """
        import math
        # logging.info(f"find_near_conflict_departure_time called for aircraft {aircraft}")
        # logging.info(f"Scheduled aircraft: {list(scheduled_aircraft.keys())}")
        
        # Helper to compute 3D distance (lat/lon in degrees, altitude in feet)
        def haversine(lat1, lon1, lat2, lon2):
            R = 3440.065  # Nautical miles
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            return 2*R*math.asin(math.sqrt(a))
        def dist3d(lat1, lon1, alt1, lat2, lon2, alt2):
            dnm = haversine(lat1, lon1, lat2, lon2)
            dft = abs(alt1 - alt2)
            # Weight vertical separation less than horizontal (e.g., 1000ft = 0.16nm)
            return math.sqrt(dnm**2 + (dft/6076.12)**2)
        # Get this aircraft's waypoints
        my_fp = all_flight_data.get(aircraft)
        if not my_fp or 'waypoints' not in my_fp:
            # logging.warning(f"No waypoints found for aircraft {aircraft}")
            return None
        my_wps = my_fp['waypoints']
        # logging.info(f"Aircraft {aircraft} has {len(my_wps)} waypoints")
        
        min_dist = float('inf')
        best_dep = None
        candidates_tried = 0
        valid_candidates = 0
        time_window = 2  # minutes: only consider waypoints within this time window
        
        # Try a range of candidate departure times (every minute in event window)
        for dep_min in range(int((event_end - event_start).total_seconds()//60)):
            candidate_dep = event_start + timedelta(minutes=dep_min)
            candidates_tried += 1
            
            # Check 2-min separation from same-airport departures
            my_origin = aircraft.split('-')[0]
            conflict = False
            for sched_id, sched_time in scheduled_aircraft.items():
                if sched_id.split('-')[0] == my_origin:
                    if abs((candidate_dep - sched_time).total_seconds()/60) < MIN_DEPARTURE_SEPARATION_MINUTES:
                        conflict = True
                        break
            if conflict:
                continue
            valid_candidates += 1
            
            # For each scheduled aircraft, compute closest approach in space and time
            for sched_id, sched_time in scheduled_aircraft.items():
                sched_fp = all_flight_data.get(sched_id)
                if not sched_fp or 'waypoints' not in sched_fp:
                    continue
                sched_wps = sched_fp['waypoints']
                # For each pair of waypoints, check if times align within window
                for i, my_wp in enumerate(my_wps):
                    my_abs_time = (candidate_dep - event_start).total_seconds()/60 + my_wp.get('time_total', 0)/60
                    for j, sched_wp in enumerate(sched_wps):
                        sched_abs_time = (scheduled_aircraft[sched_id] - event_start).total_seconds()/60 + sched_wp.get('time_total', 0)/60
                        if abs(my_abs_time - sched_abs_time) <= time_window:
                            d = dist3d(my_wp['lat'], my_wp['lon'], my_wp['altitude'], 
                                      sched_wp['lat'], sched_wp['lon'], sched_wp['altitude'])
                            if d < min_dist:
                                min_dist = d
                                best_dep = candidate_dep
                                # logging.debug(f"New min dist: {d:.2f}nm at dep {candidate_dep} (my_wp[{i}] vs {sched_id} wp[{j}]) times: {my_abs_time:.1f} vs {sched_abs_time:.1f}")
        # logging.info(f"find_near_conflict_departure_time: tried {candidates_tried} candidates, {valid_candidates} valid")
        if best_dep:
            # logging.info(f"Best departure time for {aircraft}: {best_dep} (min space-time distance: {min_dist:.2f}nm)")
            return best_dep
        else:
            # logging.warning(f"No valid departure time found for {aircraft}, returning None")
            return None

def main():
    """Main function to parse arguments and run scheduling."""
    parser = argparse.ArgumentParser(
        description="Generate departure schedules for ATC conflict events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_schedule_conflicts.py --start 14:00 --end 18:00
  python generate_schedule_conflicts.py --start 14:00 --end 18:00 --verbose
  python generate_schedule_conflicts.py --start 09:00 --end 12:00
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