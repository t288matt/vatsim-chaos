#!/usr/bin/env python3
"""
Master Script for ATC Conflict Analysis System
==============================================

This script orchestrates the complete workflow for analyzing SimBrief XML flight plans
and generating conflict scenarios for ATC training events.

Workflow:
1. Extract flight plan data from XML files
2. Analyze conflicts between flight plans
3. Generate KML visualization files
4. Merge KML files into a single visualization
5. Generate comprehensive conflict reports

Usage:
    python run_analysis.py [options]

Options:
    --extract-only    Only run the XML extraction step
    --analyze-only    Only run the conflict analysis step
    --kml-only        Only run the KML generation step
    --merge-only      Only run the KML merge step
    --skip-extract    Skip XML extraction (use existing data)
    --skip-kml        Skip KML generation
    --verbose         Enable verbose output
    --help           Show this help message
"""

import os
import sys
import subprocess
import argparse
import time
from datetime import datetime
from typing import List, Optional

# Configuration
SCRIPTS = {
    'extract': 'simbrief_xml_flightplan_extractor.py',
    'analyze': 'analyze_and_report_conflicts.py',
    'merge_kml': 'merge_kml_flightplans.py',
    'schedule': 'generate_schedule_conflicts.py'  # updated from schedule_conflicts.py
}

OUTPUT_FILES = {
    'conflict_report': 'conflict_list.txt',
    'merged_kml': 'merged_flightplans.kml',
    'analysis_data': 'temp/conflict_analysis.json',
    'schedule': 'event_schedule.csv',
    'briefing': 'atc_briefing.txt'
}

class AnalysisRunner:
    """Master script for running the complete ATC conflict analysis workflow."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = time.time()
        
    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "🔍" if level == "INFO" else "⚠️" if level == "WARNING" else "❌"
        print(f"[{timestamp}] {prefix} {message}")
    
    def run_script(self, script_name: str, description: str) -> bool:
        """Run a Python script and return success status."""
        self.log(f"Starting {description}...")
        
        try:
            # Check if script exists
            if not os.path.exists(script_name):
                self.log(f"Script {script_name} not found!", "ERROR")
                return False
            
            # Run the script
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=not self.verbose,
                text=True,
                check=True
            )
            
            if self.verbose and result.stdout:
                print(result.stdout)
            
            self.log(f"✅ {description} completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"❌ {description} failed with exit code {e.returncode}", "ERROR")
            if self.verbose and e.stderr:
                print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            self.log(f"❌ {description} failed: {e}", "ERROR")
            return False
    
    def check_prerequisites(self) -> bool:
        """Check if all required files and directories exist."""
        self.log("Checking prerequisites...")
        
        # Check for XML files
        xml_files = [f for f in os.listdir('.') if f.endswith('.xml')]
        if not xml_files:
            self.log("No XML files found in current directory!", "ERROR")
            return False
        
        self.log(f"Found {len(xml_files)} XML files")
        
        # Check for required scripts
        for script_type, script_name in SCRIPTS.items():
            if not os.path.exists(script_name):
                self.log(f"Required script {script_name} not found!", "ERROR")
                return False
        
        self.log("✅ All prerequisites met")
        return True
    
    def run_extraction(self) -> bool:
        """Run the XML flight plan extraction step."""
        return self.run_script(
            SCRIPTS['extract'],
            "XML Flight Plan Extraction"
        )
    
    def run_analysis(self) -> bool:
        """Run the conflict analysis step."""
        return self.run_script(
            SCRIPTS['analyze'],
            "Conflict Analysis and Reporting"
        )
    
    def run_kml_merge(self) -> bool:
        """Run the KML merge step."""
        return self.run_script(
            SCRIPTS['merge_kml'],
            "KML Flight Plan Merge"
        )
    
    def run_scheduling(self, start_time: Optional[str] = None, end_time: Optional[str] = None) -> bool:
        """Run the conflict scheduling step."""
        if not start_time or not end_time:
            self.log("Scheduling requires --start-time and --end-time parameters", "ERROR")
            return False
        
        # Build command with time parameters
        cmd = [sys.executable, SCRIPTS['schedule'], '--start', start_time, '--end', end_time]
        if self.verbose:
            cmd.append('--verbose')
        
        self.log("Starting Conflict Scheduling...")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=not self.verbose,
                text=True,
                check=True
            )
            
            if self.verbose and result.stdout:
                print(result.stdout)
            
            self.log("✅ Conflict Scheduling completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Conflict Scheduling failed with exit code {e.returncode}", "ERROR")
            if self.verbose and e.stderr:
                print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            self.log(f"❌ Conflict Scheduling failed: {e}", "ERROR")
            return False
    

    
    def check_outputs(self) -> None:
        """Check and report on generated output files."""
        self.log("Checking generated outputs...")
        
        outputs_found = []
        outputs_missing = []
        
        for output_name, output_path in OUTPUT_FILES.items():
            if isinstance(output_path, list):
                # Handle list of files (like visualizations)
                for file_path in output_path:
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        outputs_found.append(f"  ✅ {output_name}: {file_path} ({size:,} bytes)")
                    else:
                        outputs_missing.append(f"  ❌ {output_name}: {file_path} (missing)")
            else:
                # Handle single file
                if os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    outputs_found.append(f"  ✅ {output_name}: {output_path} ({size:,} bytes)")
                else:
                    outputs_missing.append(f"  ❌ {output_name}: {output_path} (missing)")
        
        if outputs_found:
            self.log("Generated files:")
            for output in outputs_found:
                print(output)
        
        if outputs_missing:
            self.log("Missing files:", "WARNING")
            for output in outputs_missing:
                print(output)
    
    def run_complete_workflow(self, skip_extract: bool = False, skip_kml: bool = False, 
                            skip_schedule: bool = False, start_time: Optional[str] = None, 
                            end_time: Optional[str] = None) -> bool:
        """Run the complete analysis workflow."""
        self.log("🚀 Starting ATC Conflict Analysis Workflow")
        print("=" * 60)
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
        
        # Step 1: Extract flight plan data (unless skipped)
        if not skip_extract:
            if not self.run_extraction():
                return False
        else:
            self.log("⏭️  Skipping XML extraction (using existing data)")
        
        # Step 2: Analyze conflicts
        if not self.run_analysis():
            return False
        
        # Step 3: Merge KML files (unless skipped)
        if not skip_kml:
            if not self.run_kml_merge():
                return False
        else:
            self.log("⏭️  Skipping KML merge")
        
        # Step 4: Schedule conflicts (unless skipped)
        if not skip_schedule and start_time and end_time:
            if not self.run_scheduling(start_time, end_time):
                return False
        elif not skip_schedule and (not start_time or not end_time):
            self.log("⚠️  Skipping scheduling (requires --start-time and --end-time)")
        else:
            self.log("⏭️  Skipping conflict scheduling")
        
        # Check outputs
        self.check_outputs()
        
        # Summary
        elapsed_time = time.time() - self.start_time
        self.log(f"🎯 Workflow completed in {elapsed_time:.1f} seconds")
        
        return True
    
    def run_single_step(self, step: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> bool:
        """Run a single step of the workflow."""
        self.log(f"🎯 Running single step: {step}")
        
        if step == 'extract':
            return self.run_extraction()
        elif step == 'analyze':
            return self.run_analysis()
        elif step == 'merge_kml':
            return self.run_kml_merge()
        elif step == 'schedule':
            return self.run_scheduling(start_time, end_time)
        else:
            self.log(f"Unknown step: {step}", "ERROR")
            return False

def main():
    """Main function to parse arguments and run the workflow."""
    parser = argparse.ArgumentParser(
        description="Master script for ATC Conflict Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_analysis.py                    # Run complete workflow
  python run_analysis.py --extract-only     # Only extract XML data
  python run_analysis.py --analyze-only     # Only analyze conflicts
  python run_analysis.py --skip-extract     # Skip extraction, use existing data
  python run_analysis.py --verbose          # Enable verbose output
        """
    )
    
    # Step selection options
    parser.add_argument('--extract-only', action='store_true',
                       help='Only run the XML extraction step')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only run the conflict analysis step')
    parser.add_argument('--kml-only', action='store_true',
                       help='Only run the KML generation step')
    parser.add_argument('--merge-only', action='store_true',
                       help='Only run the KML merge step')
    parser.add_argument('--schedule-only', action='store_true',
                       help='Only run the conflict scheduling step')
    
    # Skip options
    parser.add_argument('--skip-extract', action='store_true',
                       help='Skip XML extraction (use existing data)')
    parser.add_argument('--skip-kml', action='store_true',
                       help='Skip KML generation and merge')
    parser.add_argument('--skip-schedule', action='store_true',
                       help='Skip conflict scheduling')
    
    # Scheduling options
    parser.add_argument('--start-time', help='Event start time for scheduling (HH:MM)')
    parser.add_argument('--end-time', help='Event end time for scheduling (HH:MM)')
    
    # Output options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Create runner
    runner = AnalysisRunner(verbose=args.verbose)
    
    try:
        # Determine what to run
        if args.extract_only:
            success = runner.run_single_step('extract')
        elif args.analyze_only:
            success = runner.run_single_step('analyze')
        elif args.kml_only:
            success = runner.run_single_step('merge_kml')
        elif args.merge_only:
            success = runner.run_single_step('merge_kml')
        elif args.schedule_only:
            success = runner.run_single_step('schedule', args.start_time, args.end_time)
        else:
            # Run complete workflow
            success = runner.run_complete_workflow(
                skip_extract=args.skip_extract,
                skip_kml=args.skip_kml,
                skip_schedule=args.skip_schedule,
                start_time=args.start_time,
                end_time=args.end_time
            )
        
        if success:
            print("\n🎉 Analysis workflow completed successfully!")
            print("📁 Check the generated files:")
            print("   • conflict_list.txt - Detailed conflict report")
            print("   • merged_flightplans.kml - Google Earth visualization")
            print("   • temp/conflict_analysis.json - Raw analysis data")
            if args.start_time and args.end_time:
                print("   • event_schedule.csv - Departure schedule")
                print("   • atc_briefing.txt - ATC briefing document")
        else:
            print("\n❌ Analysis workflow failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 