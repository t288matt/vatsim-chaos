# =============================================================================
# ATC Conflict Analysis System - Environment Configuration
# =============================================================================
# 
# This file contains all configurable parameters for the ATC conflict analysis system.
# The system now uses unique flight IDs (FLT0001, FLT0002, etc.) instead of 
# origin-destination pairs for better conflict tracking and separation enforcement.
#
# FLIGHT ID SYSTEM:
#   - Each flight gets a unique ID (FLT0001, FLT0002, etc.) during XML processing
#   - Flight IDs are maintained throughout the entire workflow
#   - Route information (origin-destination) is preserved alongside flight IDs
#   - Separation rules apply to both flight IDs and routes
# =============================================================================

# =============================================================================
# CONFLICT DETECTION PARAMETERS
# =============================================================================

# Lateral separation threshold for conflict detection (nautical miles)
# Aircraft closer than this distance are considered in conflict
LATERAL_SEPARATION_THRESHOLD = 5.0

# Vertical separation threshold for conflict detection (feet)
# Aircraft with altitude difference less than this are considered in conflict
VERTICAL_SEPARATION_THRESHOLD = 900

# Minimum altitude threshold for conflict detection (feet)
# Only conflicts above this altitude are reported (filters out ground conflicts)
MIN_ALTITUDE_THRESHOLD = 5000



# No-conflict zones around airports (format: "ICAO_CODE/DISTANCE_NM")
# Conflicts within these distances of airports are not counted
# Example: ["YSSY/45"] means no conflicts within 45nm of Sydney Airport
NO_CONFLICT_AIRPORT_DISTANCES = ["YSSY/35", "YSCB/15"]

# =============================================================================
# DEPARTURE SCHEDULING PARAMETERS
# =============================================================================

# Minimum separation between departures from the same airport (minutes)
# Prevents aircraft from departing simultaneously from the same origin
MIN_DEPARTURE_SEPARATION_MINUTES = 2

# Minimum separation between flights with same origin-destination (minutes)
# Enforces 5-minute separation for flights with identical routes
# This prevents aircraft with same route from departing too close together
MIN_SAME_ROUTE_SEPARATION_MINUTES = 5

# Batch size for conflict score recalculation during scheduling
# Recalculates scores every N aircraft to balance accuracy vs performance
# Smaller values = more accurate but slower, larger values = faster but less accurate
BATCH_SIZE = 1

# =============================================================================
# ROUTE INTERPOLATION PARAMETERS
# =============================================================================

# Distance between interpolated route points (nautical miles)
# Smaller values create more detailed route analysis but increase processing time
INTERPOLATION_SPACING_NM = 1.5

# =============================================================================
# SCHEDULING OPTIMIZATION PARAMETERS
# =============================================================================

# Time tolerance for departure time optimization (minutes)
# Allows flexibility when optimizing departure times for conflict maximization
TIME_TOLERANCE_MINUTES = 2

# Maximum departure time range for optimization (minutes)
MAX_DEPARTURE_TIME_MINUTES = 120

# Step size for departure time optimization (minutes)
DEPARTURE_TIME_STEP_MINUTES = 5 

# Transition altitude for feet/flight level display in pilot briefing
# Altitudes below this are shown in feet, above in flight levels
TRANSITION_ALTITUDE_FT = 10500 