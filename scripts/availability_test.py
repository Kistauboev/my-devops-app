#!/usr/bin/env python3
"""
Availability testing script for DevPlatform.
Tests 99.9% availability requirement over 24 hours (or shorter test period).

Usage:
    python scripts/availability_test.py [--duration HOURS]
"""

import asyncio
import time
import httpx
import argparse
from typing import Dict, Any
from datetime import datetime, timedelta


API_BASE = "http://localhost:8000"
CHECK_INTERVAL = 60  # Check every 60 seconds
TARGET_AVAILABILITY = 99.9


async def check_platform_health(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Check platform health and return status."""
    try:
        response = await client.get(f"{API_BASE}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            return {
                "healthy": data.get("status") == "ok",
                "timestamp": datetime.now().isoformat(),
                "data": data,
            }
        return {
            "healthy": False,
            "timestamp": datetime.now().isoformat(),
            "error": f"HTTP {response.status_code}",
        }
    except Exception as e:
        return {
            "healthy": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


async def run_availability_test(duration_hours: float = 1.0):
    """Run availability test for specified duration."""
    duration_seconds = duration_hours * 3600
    end_time = time.time() + duration_seconds
    
    print("=" * 80)
    print("DevPlatform Availability Test")
    print(f"Target: {TARGET_AVAILABILITY}% availability")
    print(f"Duration: {duration_hours} hours ({duration_seconds/60:.0f} minutes)")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print("=" * 80)
    print()
    
    start_time = time.time()
    total_checks = 0
    successful_checks = 0
    failed_checks = 0
    downtime_seconds = 0
    last_check_time = start_time
    
    async with httpx.AsyncClient() as client:
        print(f"Starting test at {datetime.now().isoformat()}")
        print("Monitoring platform health...")
        print()
        
        while time.time() < end_time:
            check_start = time.time()
            result = await check_platform_health(client)
            check_duration = time.time() - check_start
            
            total_checks += 1
            
            if result["healthy"]:
                successful_checks += 1
                status = "✅"
            else:
                failed_checks += 1
                downtime_seconds += CHECK_INTERVAL  # Approximate downtime
                status = "❌"
            
            # Print status every 10 checks or on failure
            if total_checks % 10 == 0 or not result["healthy"]:
                elapsed = time.time() - start_time
                availability = (successful_checks / total_checks * 100) if total_checks > 0 else 0
                print(f"{status} Check #{total_checks} | "
                      f"Availability: {availability:.3f}% | "
                      f"Elapsed: {elapsed/60:.1f}m | "
                      f"Response: {check_duration*1000:.0f}ms")
                if not result["healthy"]:
                    print(f"   Error: {result.get('error', 'Unknown')}")
            
            # Wait for next check
            sleep_time = CHECK_INTERVAL - check_duration
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
    
    # Final results
    total_time = time.time() - start_time
    availability_percent = (successful_checks / total_checks * 100) if total_checks > 0 else 0
    meets_sla = availability_percent >= TARGET_AVAILABILITY
    
    print()
    print("=" * 80)
    print("Test Results")
    print("=" * 80)
    print(f"Total checks: {total_checks}")
    print(f"Successful: {successful_checks}")
    print(f"Failed: {failed_checks}")
    print(f"Total test time: {total_time/3600:.2f} hours")
    print(f"Estimated downtime: {downtime_seconds/60:.1f} minutes")
    print()
    print(f"Availability: {availability_percent:.3f}%")
    print(f"Target: {TARGET_AVAILABILITY}%")
    print(f"SLA Met: {'✅ YES' if meets_sla else '❌ NO'}")
    print()
    
    if meets_sla:
        print("✅ AVAILABILITY TEST PASSED")
        print(f"   Platform meets {TARGET_AVAILABILITY}% availability requirement")
    else:
        print("⚠️  AVAILABILITY TEST FAILED")
        print(f"   Platform availability ({availability_percent:.3f}%) is below target ({TARGET_AVAILABILITY}%)")
        print(f"   Allowed downtime: {total_time * (100 - TARGET_AVAILABILITY) / 100 / 60:.1f} minutes")
        print(f"   Actual downtime: {downtime_seconds / 60:.1f} minutes")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test DevPlatform availability")
    parser.add_argument(
        "--duration",
        type=float,
        default=1.0,
        help="Test duration in hours (default: 1.0)",
    )
    args = parser.parse_args()
    
    try:
        asyncio.run(run_availability_test(args.duration))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()





