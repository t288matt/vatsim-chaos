#!/usr/bin/env python3
"""
Analyze unique conflicts from pilot briefing
"""
import re
from collections import defaultdict

def extract_conflicts_from_briefing():
    """Extract all conflicts from pilot briefing and count unique ones"""
    
    with open('pilot_briefing.txt', 'r') as f:
        content = f.read()
    
    # Extract all conflict entries
    conflict_pattern = r'FLT(\d+)\s+\([^)]+\)\s+conflicts:\s*\n((?:\s+-\s+With\s+FLT\d+\s+\([^)]+\)\s+at[^\n]*\n)*)'
    
    all_conflicts = set()  # Use set to avoid duplicates
    flight_conflicts = defaultdict(list)
    
    # Find all flight conflict sections
    matches = re.finditer(conflict_pattern, content)
    
    for match in matches:
        flight_id = f"FLT{match.group(1).zfill(4)}"
        conflicts_text = match.group(2)
        
        # Extract individual conflicts for this flight
        conflict_lines = re.findall(r'\s+-\s+With\s+(FLT\d+)\s+\([^)]+\)\s+at[^\n]*', conflicts_text)
        
        for other_flight in conflict_lines:
            # Create sorted pair to avoid duplicates (FLT0001 vs FLT0002 = FLT0002 vs FLT0001)
            conflict_pair = tuple(sorted([flight_id, other_flight]))
            all_conflicts.add(conflict_pair)
            flight_conflicts[flight_id].append(other_flight)
    
    return all_conflicts, flight_conflicts

def manual_count():
    """Manually count conflicts from the briefing"""
    
    # Based on the pilot briefing, here are the unique conflicts:
    unique_conflicts = [
        ("FLT0001", "FLT0005"),
        ("FLT0001", "FLT0012"), 
        ("FLT0001", "FLT0013"),
        ("FLT0002", "FLT0009"),
        ("FLT0002", "FLT0010"),
        ("FLT0002", "FLT0014"),
        ("FLT0003", "FLT0014"),
        ("FLT0004", "FLT0006"),
        ("FLT0005", "FLT0008"),
        ("FLT0005", "FLT0012"),
        ("FLT0005", "FLT0013"),
        ("FLT0007", "FLT0014"),
        ("FLT0008", "FLT0014"),
        ("FLT0009", "FLT0010"),
        ("FLT0009", "FLT0011"),
        ("FLT0009", "FLT0018"),
        ("FLT0010", "FLT0011"),
        ("FLT0010", "FLT0018"),
        ("FLT0011", "FLT0012"),
        ("FLT0011", "FLT0013"),
        ("FLT0011", "FLT0018"),
        ("FLT0012", "FLT0013"),
        ("FLT0012", "FLT0018"),
        ("FLT0012", "FLT0019"),
        ("FLT0012", "FLT0020"),
        ("FLT0013", "FLT0018"),
        ("FLT0013", "FLT0019"),
        ("FLT0013", "FLT0020"),
        ("FLT0016", "FLT0017"),
        ("FLT0017", "FLT0019"),
        ("FLT0017", "FLT0020"),
        ("FLT0019", "FLT0020"),
        ("FLT0019", "FLT0021"),
        ("FLT0020", "FLT0021"),
    ]
    
    # Convert to sorted tuples to ensure uniqueness
    unique_pairs = set()
    for flight1, flight2 in unique_conflicts:
        unique_pairs.add(tuple(sorted([flight1, flight2])))
    
    return unique_pairs

def main():
    print("=== MANUAL CONFLICT ANALYSIS ===")
    
    unique_pairs = manual_count()
    
    print(f"Total unique conflicts: {len(unique_pairs)}")
    print()
    
    print("Unique conflict pairs:")
    for i, (flight1, flight2) in enumerate(sorted(unique_pairs), 1):
        print(f"{i:2d}. {flight1} vs {flight2}")
    
    print()
    print("=== SUMMARY ===")
    print(f"Total unique conflicts: {len(unique_pairs)}")
    print("Note: Briefing mentions 'Total conflicts: 68' but this includes duplicates")
    print("The 68 count includes both FLT0001 vs FLT0002 AND FLT0002 vs FLT0001")
    print("Unique conflicts (counting each pair only once):", len(unique_pairs))

if __name__ == "__main__":
    main() 