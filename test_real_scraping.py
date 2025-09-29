#!/usr/bin/env python3
"""
Test script to verify real cricket data scraping is working
"""

import asyncio
import logging
from cricket_scraper import get_live_matches, get_match_schedule, get_tournaments

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_real_scraping():
    """Test the real cricket data scraping functionality."""
    
    print("🏏 Testing Real Cricket Data Scraping")
    print("=" * 50)
    
    # Test 1: Live Matches
    print("\n🔴 Test 1: Live Matches")
    print("-" * 30)
    try:
        live_matches = await get_live_matches()
        print(f"✅ Found {len(live_matches)} live matches")
        
        for i, match in enumerate(live_matches[:3], 1):  # Show first 3 matches
            print(f"\n📊 Match {i}:")
            print(f"   🆔 ID: {match.match_id}")
            print(f"   🏆 Title: {match.title}")
            print(f"   🥇 Team 1: {match.team1.name} ({match.team1.short_name})")
            print(f"   🥈 Team 2: {match.team2.name} ({match.team2.short_name})")
            print(f"   📊 Status: {match.status.value}")
            print(f"   📍 Venue: {match.venue}")
            print(f"   📅 Date: {match.date}")
            print(f"   🏏 Format: {match.format}")
            
            # Check if we have real data vs placeholder
            if match.match_id.startswith("fallback_") or "Cricket vs Updates" in match.title:
                print(f"   ⚠️  WARNING: This appears to be fallback data")
            else:
                print(f"   ✅ This appears to be REAL cricket data!")
                
    except Exception as e:
        print(f"❌ Error testing live matches: {e}")
    
    # Test 2: Match Schedule  
    print("\n\n📅 Test 2: Match Schedule")
    print("-" * 30)
    try:
        schedule_matches = await get_match_schedule(days=2)
        print(f"✅ Found {len(schedule_matches)} scheduled matches")
        
        for i, match in enumerate(schedule_matches[:2], 1):  # Show first 2 matches
            print(f"\n📊 Scheduled Match {i}:")
            print(f"   🆔 ID: {match.match_id}")
            print(f"   🏆 Title: {match.title}")
            print(f"   🥇 Team 1: {match.team1.name}")
            print(f"   🥈 Team 2: {match.team2.name}")
            print(f"   📊 Status: {match.status.value}")
            print(f"   📅 Date: {match.date}")
            
    except Exception as e:
        print(f"❌ Error testing schedule: {e}")
    
    # Test 3: Tournaments
    print("\n\n🏆 Test 3: Tournaments")
    print("-" * 30)
    try:
        tournaments = await get_tournaments()
        print(f"✅ Found {len(tournaments)} tournaments")
        
        for i, tournament in enumerate(tournaments[:2], 1):  # Show first 2 tournaments
            print(f"\n🏆 Tournament {i}:")
            print(f"   🆔 ID: {tournament.tournament_id}")
            print(f"   📛 Name: {tournament.name}")
            print(f"   🏏 Format: {tournament.format}")
            print(f"   📊 Status: {tournament.status}")
            
    except Exception as e:
        print(f"❌ Error testing tournaments: {e}")
    
    print("\n" + "=" * 50)
    print("🔍 Test Summary:")
    print("✅ Real data scraping test completed!")
    print("📊 Check the results above to verify real vs placeholder data")

if __name__ == "__main__":
    asyncio.run(test_real_scraping())