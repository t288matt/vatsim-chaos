#!/usr/bin/env python3
"""
Shared types and classes used across multiple modules.

This module contains unified class definitions for FlightPlan and Waypoint
that are used throughout the ATC Conflict Analysis System. This eliminates
duplicate class definitions and ensures consistent behavior across all modules.

UNIFIED CLASS DEFINITIONS:
- FlightPlan: Complete flight plan with waypoints and metadata
- Waypoint: Navigation waypoint with coordinates and flight data

All modules now import these classes from shared_types.py instead of defining
their own versions, ensuring data consistency and reducing code duplication.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Waypoint:
    """
    Represents a navigation waypoint with coordinates and flight data.
    
    This is the unified waypoint class used throughout the system.
    Provides both standard time formatting and SimBrief-specific formatting.
    """
    name: str
    lat: float
    lon: float
    altitude: int
    time_total: int = 0
    stage: str = ""
    waypoint_type: str = ""
    
    def get_time_formatted(self) -> str:
        """Convert total time to HH:MM format."""
        total_minutes = self.get_time_minutes()
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def get_time_formatted_simbrief(self) -> str:
        """Convert total time to 4-digit UTC HHMM format (SimBrief style)."""
        # SimBrief XML gives time_total in minutes (e.g., 1359 = 13 minutes 59 seconds)
        total_minutes = self.time_total
        if self.time_total > 10000:  # Heuristic: treat as seconds
            total_minutes = self.time_total // 60
        hours = (total_minutes // 60) % 24
        minutes = total_minutes % 60
        return f"{hours:02d}{minutes:02d}"
    
    def get_time_minutes(self) -> float:
        """Get time in minutes as float."""
        return self.time_total / 60.0
    
    def to_dict(self) -> dict:
        """Convert waypoint to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'lat': self.lat,
            'lon': self.lon,
            'altitude': self.altitude,
            'elapsed_time': self.get_time_formatted(),
            'time_seconds': self.time_total,
            'stage': self.stage,
            'type': self.waypoint_type
        }
    
    def __str__(self) -> str:
        """String representation of waypoint."""
        return f"{self.name}: {self.lat:.6f}, {self.lon:.6f}, {self.altitude}ft, {self.get_time_formatted()}"


class FlightPlan:
    """
    Represents a complete flight plan with waypoints and metadata.
    
    This is the unified flight plan class used throughout the system.
    Provides complete JSON serialization and route management capabilities.
    """
    
    def __init__(self, origin: str, destination: str, route: str = "", flight_id: str = "", aircraft_type: str = "UNK"):
        self.origin = origin
        self.destination = destination
        self.route = route
        self.flight_id = flight_id
        self.aircraft_type = aircraft_type
        self.waypoints: List[Waypoint] = []
        self.departure: Optional[Waypoint] = None
        self.arrival: Optional[Waypoint] = None
    
    def add_waypoint(self, waypoint: Waypoint) -> None:
        """Add a waypoint to the flight plan."""
        self.waypoints.append(waypoint)
    
    def set_departure(self, waypoint: Waypoint) -> None:
        """Set the departure waypoint."""
        self.departure = waypoint
    
    def set_arrival(self, waypoint: Waypoint) -> None:
        """Set the arrival waypoint."""
        self.arrival = waypoint
    
    def get_all_waypoints(self) -> List[Waypoint]:
        """Get all waypoints including departure and arrival."""
        all_waypoints = []
        if self.departure:
            all_waypoints.append(self.departure)
        all_waypoints.extend(self.waypoints)
        if self.arrival:
            # Check if the last waypoint is already the destination airport
            if self.waypoints and self.waypoints[-1].name == self.arrival.name:
                # Skip adding arrival waypoint if it's already the last waypoint
                # This prevents duplicate destination waypoints with wrong timestamps
                pass
            else:
                all_waypoints.append(self.arrival)
        return all_waypoints
    
    def get_route_identifier(self) -> str:
        """Get a unique identifier for this route."""
        if self.flight_id:
            return self.flight_id
        elif self.route:
            return self.route
        else:
            return f"{self.origin}-{self.destination}"
    
    def to_dict(self) -> dict:
        """Convert flight plan to dictionary for JSON serialization."""
        return {
            'origin': self.origin,
            'destination': self.destination,
            'route': self.route,
            'flight_id': self.flight_id,
            'aircraft_type': self.aircraft_type,
            'departure': self.departure.to_dict() if self.departure else None,
            'waypoints': [wp.to_dict() for wp in self.waypoints],
            'arrival': self.arrival.to_dict() if self.arrival else None,
            'all_waypoints': [wp.to_dict() for wp in self.get_all_waypoints()]
        } 