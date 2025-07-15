#!/usr/bin/env python3
"""
Shared types and classes used across multiple modules.
This module contains common data structures to avoid circular imports.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Waypoint:
    """Represents a navigation waypoint with coordinates and flight data."""
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
    
    def get_time_minutes(self) -> float:
        """Get time in minutes as float."""
        return self.time_total / 60.0


class FlightPlan:
    """Represents a complete flight plan with waypoints and metadata."""
    
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