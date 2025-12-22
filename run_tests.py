"""
Test runner for AI SlideRush CLIP integration

Runs all tests with detailed output and summary.
"""

import sys
import unittest
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def run_all_tests():
    """Run all test suites and display results"""
    
    print("=" * 70)
    print("AI SlideRush - CLIP Integration Test Suite")
    print("=" * 70)
    print()
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 70)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


def run_specific_suite(suite_name):
    """Run a specific test suite"""
    
    test_files = {
        'clip': 'tests.test_clip_client',
        'matcher': 'tests.test_image_matcher',
        'integration': 'tests.test_integration_clip'
    }
    
    if suite_name not in test_files:
        print(f"Unknown test suite: {suite_name}")
        print(f"Available suites: {', '.join(test_files.keys())}")
        return 1
    
    print(f"\nRunning {suite_name} tests...\n")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_files[suite_name])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Run specific suite
        exit_code = run_specific_suite(sys.argv[1])
    else:
        # Run all tests
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
