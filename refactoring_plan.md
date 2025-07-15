# Refactoring Plan: Move Scheduling Logic from find_potential_conflicts.py

## Overview
Move scheduling functions from `find_potential_conflicts.py` to `generate_schedule_conflicts.py` to improve separation of concerns.

## Current State
- `find_potential_conflicts.py` contains both conflict detection AND scheduling logic
- `generate_schedule_conflicts.py` exists but is underutilized
- Hardcoded constants that should be in `env.py`

## Step-by-Step Refactoring Plan

### Phase 1: Add Constants to env.py

1. **Add scheduling constants to `env.py`:**
   ```python
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
   ```

### Phase 2: Move Functions to generate_schedule_conflicts.py

2. **Copy functions from `find_potential_conflicts.py` to `generate_schedule_conflicts.py`:**
   - `optimize_departure_times()`
   - `generate_conflict_scenario()`

3. **Update imports in `generate_schedule_conflicts.py`:**
   ```python
   from env import (TIME_TOLERANCE_MINUTES, MAX_DEPARTURE_TIME_MINUTES, 
                   DEPARTURE_TIME_STEP_MINUTES)
   from find_potential_conflicts import FlightPlan, Waypoint
   ```

### Phase 3: Clean Up find_potential_conflicts.py

4. **Remove scheduling functions from `find_potential_conflicts.py`:**
   - Remove `optimize_departure_times()`
   - Remove `generate_conflict_scenario()`
   - Remove hardcoded constants: `TIME_TOLERANCE`, `MAX_DEPARTURE_TIME`, `DEPARTURE_TIME_STEP`

5. **Update imports in `find_potential_conflicts.py`:**
   - Remove scheduling-related imports
   - Keep only conflict detection imports

### Phase 4: Update Function Calls

6. **Update any files that call the moved functions:**
   - Update imports to get scheduling functions from `generate_schedule_conflicts.py`
   - Update function calls to use the new module

### Phase 5: Testing

7. **Run comprehensive tests:**
   - Run `test_refactoring_comprehensive.py`
   - Verify all tests pass
   - Compare results with baseline

8. **Run full workflow:**
   - Execute `execute.py`
   - Verify output files are generated correctly
   - Check conflict detection and scheduling still work

## Expected Benefits

✅ **Single Responsibility**: Each file has one clear purpose
✅ **Better Organization**: Scheduling logic with other scheduling code  
✅ **Easier Maintenance**: Related functions are together
✅ **Cleaner Dependencies**: Clear separation of concerns
✅ **Configurable Constants**: All hardcoded values moved to env.py

## Risk Mitigation

- **Comprehensive Tests**: Full test suite to catch regressions
- **Baseline Comparison**: Compare results before/after refactoring
- **Incremental Changes**: Make changes step by step
- **Rollback Plan**: Keep original files as backup

## Success Criteria

- All tests pass
- No change in conflict detection results
- No change in scheduling results  
- Cleaner, more maintainable code structure
- All hardcoded values moved to configuration 