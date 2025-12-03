#!/usr/bin/env python3
"""
Image Provider Testing Script
Tests Pexels and Unsplash integration independently and together
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("  🧪 AI SlideRush - Image Provider Test")
print("="*60)

# Test environment variables
print("\n1️⃣ ENVIRONMENT VARIABLES:")
pexels_key = os.getenv('PEXELS_API_KEY')
unsplash_key = os.getenv('UNSPLASH_ACCESS_KEY')
provider_mode = os.getenv('IMAGE_PROVIDER_MODE', 'mixed')

print(f"   PEXELS_API_KEY: {'✅ Set' if pexels_key else '❌ Not set'}")
print(f"   UNSPLASH_ACCESS_KEY: {'✅ Set' if unsplash_key else '⚠️ Not set'}")
print(f"   IMAGE_PROVIDER_MODE: {provider_mode}")

# Import functions from app
try:
    from app import (
        fetch_images_from_pexels, 
        fetch_images_from_unsplash,
        get_images,
        IMAGE_PROVIDER_MODE
    )
    print("\n2️⃣ IMPORTS: ✅ Successfully imported functions")
except ImportError as e:
    print(f"\n2️⃣ IMPORTS: ❌ Failed to import: {e}")
    sys.exit(1)

# Test queries
test_queries = [
    "nature landscape",
    "business meeting",
    "technology innovation"
]

print(f"\n3️⃣ TESTING PEXELS:")
print("-" * 60)
for query in test_queries[:1]:  # Test just one to avoid rate limits
    print(f"\n   Query: '{query}'")
    results = fetch_images_from_pexels(query, count=1)
    if results:
        print(f"   ✅ Found {len(results)} image(s)")
        img = results[0]
        print(f"   📸 Author: {img['author']}")
        print(f"   🌐 Source: {img['source']}")
        print(f"   🔗 URL: {img['url'][:60]}...")
    else:
        print(f"   ⚠️ No results (check API key or rate limit)")

print(f"\n4️⃣ TESTING UNSPLASH:")
print("-" * 60)
if unsplash_key:
    for query in test_queries[:1]:
        print(f"\n   Query: '{query}'")
        results = fetch_images_from_unsplash(query, count=1)
        if results:
            print(f"   ✅ Found {len(results)} image(s)")
            img = results[0]
            print(f"   📸 Author: {img['author']}")
            print(f"   🌐 Source: {img['source']}")
            print(f"   🔗 URL: {img['url'][:60]}...")
        else:
            print(f"   ⚠️ No results (check API key or rate limit)")
else:
    print("   ⚠️ Skipped (UNSPLASH_ACCESS_KEY not set)")

print(f"\n5️⃣ TESTING UNIFIED get_images() - MODE: {IMAGE_PROVIDER_MODE}")
print("-" * 60)
for query in test_queries[:1]:
    print(f"\n   Query: '{query}'")
    results = get_images(query, count=1)
    if results:
        print(f"   ✅ Found {len(results)} image(s)")
        img = results[0]
        print(f"   📸 Author: {img['author']}")
        print(f"   🌐 Source: {img['source']}")
        print(f"   🔗 URL: {img['url'][:60]}...")
        print(f"   ℹ️ Attribution: {img['attribution']}")
    else:
        print(f"   ❌ No results from any provider")

print("\n" + "="*60)
print("✅ Test completed!")
print("="*60)
