#!/usr/bin/env python3
"""
Script to count unique conflicts in pilot briefing files.
"""

import re
from collections import defaultdict

def extract_conflicts_from_file(filename):
    """Extract all conflicts from a pilot briefing file."""
    conflicts = []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content into sections by flight conflicts
        sections = re.split(r'(FLT\d+ \([A-Z0-9]+\) conflicts:)', content)
        
        current_flight = None
        for i, section in enumerate(sections):
            if section.startswith('FLT'):
                # Extract flight ID from the header
                flight_match = re.search(r'FLT(\d+)', section)
                if flight_match:
                    current_flight = f"FLT{flight_match.group(1)}"
            elif current_flight and 'With FLT' in section:
                # Find all "With FLT..." lines in this section
                with_lines = re.findall(r'With FLT(\d+)', section)
                for other_flight in with_lines:
                    other_flight_id = f"FLT{other_flight}"
                    # Create sorted pair to avoid duplicates
                    conflict_pair = tuple(sorted([current_flight, other_flight_id]))
                    conflicts.append(conflict_pair)
        
        return conflicts
    
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return []

def count_unique_conflicts(filename):
    """Count unique conflicts in a pilot briefing file."""
    conflicts = extract_conflicts_from_file(filename)
    unique_conflicts = set(conflicts)
    return len(unique_conflicts), conflicts, unique_conflicts

def main():
    files = ['pilot_briefing.txt', 'pilot_briefing copy.txt']
    
    for filename in files:
        print(f"\nAnalyzing {filename}:")
        print("=" * 50)
        
        unique_count, all_conflicts, unique_conflicts = count_unique_conflicts(filename)
        
        print(f"Total conflicts found: {len(all_conflicts)}")
        print(f"Unique conflicts: {unique_count}")
        
        if unique_conflicts:
            print("\nUnique conflict pairs:")
            for pair in sorted(unique_conflicts):
                print(f"  {pair[0]} <-> {pair[1]}")
        
        # Show duplicates if any
        if len(all_conflicts) != unique_count:
            print(f"\nDuplicate conflicts found: {len(all_conflicts) - unique_count}")
            conflict_counts = defaultdict(int)
            for conflict in all_conflicts:
                conflict_counts[conflict] += 1
            
            for conflict, count in conflict_counts.items():
                if count > 1:
                    print(f"  {conflict[0]} <-> {conflict[1]}: {count} times")

if __name__ == "__main__":
    main() 