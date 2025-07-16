#!/usr/bin/env python3
"""
Simplified Master Script for ATC Conflict Analysis System
Runs all workflow steps in order, no options.
"""
import os
import sys
import subprocess

def run_step(script, desc, args=None):
    print(f"\n=== {desc} ===")
    cmd = [sys.executable, script]
    if args:
        cmd += args
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"ERROR: {desc} failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_step('extract_simbrief_xml_flightplan.py', 'Extracting flight plan data')
    run_step('find_potential_conflicts.py', 'Analyzing conflicts')
    run_step('merge_kml_flightplans.py', 'Merging KML files')
    run_step('generate_schedule_conflicts.py', 'Scheduling conflicts')
    run_step('generate_animation.py', 'Exporting frontend animation data')
    run_step('audit_conflict.py', 'Auditing conflict data')
    print("\nAll workflow steps completed successfully!") 