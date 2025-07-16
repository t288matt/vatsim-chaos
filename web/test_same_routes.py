#!/usr/bin/env python3
"""
Test script for same origin-destination route validation.
This script tests the validation endpoint to ensure it correctly detects duplicate routes.
"""

import requests
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_route_validation():
    """Test the route validation endpoint"""
    
    # Test data - simulate files with same routes
    test_files = [
        "flight1.xml",  # YSSY-YSWG
        "flight2.xml",  # YSSY-YSWG (duplicate)
        "flight3.xml",  # YBDG-YSBK (unique)
        "flight4.xml",  # YSSY-YSWG (another duplicate)
    ]
    
    try:
        # Test the validation endpoint
        response = requests.post(
            'http://localhost:5000/validate-same-routes',
            json={'files': test_files},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Route validation test successful!")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            if result.get('has_duplicates'):
                print("✅ Duplicate routes detected correctly")
                for route in result.get('duplicate_routes', []):
                    print(f"  - {route['route']}: {route['count']} files")
            else:
                print("ℹ️ No duplicate routes found")
                
        else:
            print(f"❌ Route validation test failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the Flask app is running.")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    print("Testing same origin-destination route validation...")
    test_route_validation() 