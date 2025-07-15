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
LATERAL_SEPARATION_THRESHOLD = 3.0

# Vertical separation threshold for conflict detection (feet)
# Aircraft with altitude difference less than this are considered in conflict
VERTICAL_SEPARATION_THRESHOLD = 900

# Minimum altitude threshold for conflict detection (feet)
# Only conflicts above this altitude are reported (filters out ground conflicts)
MIN_ALTITUDE_THRESHOLD = 5000

# Distance threshold for filtering duplicate conflicts (nautical miles)
# Conflicts within this distance of each other are considered duplicates
DUPLICATE_FILTER_DISTANCE = 4.0

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