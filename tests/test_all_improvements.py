#!/usr/bin/env python3
"""
Comprehensive test runner for all search improvements
"""
import os
import sys
import subprocess

def run_test(test_file, description):
    """Run a single test file and return success/failure"""
    print(f"\n{'='*60}")
    print(f"🧪 Running: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=False, 
                              text=True, 
                              check=True)
        print(f"✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    """Run all improvement tests"""
    print("🚀 Running Comprehensive Search Improvement Tests")
    print("Testing all features: Summary Storage, Improved Search, Mapping Updates")
    
    tests = [
        ("tests/test_mapping_update.py", "Elasticsearch Mapping Updates"),
        ("tests/test_summary_storage.py", "Summary Storage & Caching"), 
        ("tests/test_improved_search.py", "Improved Search & Confidence Scoring"),
    ]
    
    results = []
    
    for test_file, description in tests:
        if os.path.exists(test_file):
            success = run_test(test_file, description)
            results.append((description, success))
        else:
            print(f"⚠️  Test file {test_file} not found - skipping")
            results.append((description, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status:12} {description}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All improvement tests passed! Your search system is enhanced with:")
        print("   📚 AI Summary caching in Elasticsearch")
        print("   🎯 Improved confidence scoring algorithm") 
        print("   🔍 Enhanced multi-field search queries")
        print("   🗺️  Proper Elasticsearch field mappings")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
