#!/usr/bin/env python3
"""
Performance testing script for DevPlatform.
Tests concurrent deployment of 10 preview environments to validate performance requirements.

Usage:
    python scripts/performance_test.py
"""

import asyncio
import time
import httpx
import psutil
import subprocess
from typing import List, Dict, Any
from datetime import datetime


API_BASE = "http://localhost:8000"
NUM_ENVIRONMENTS = 10


async def deploy_preview_environment(pr_number: int, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Simulate deploying a preview environment."""
    webhook_payload = {
        "action": "opened",
        "pull_request": {
            "number": pr_number,
            "state": "open",
        },
        "repository": {
            "owner": {"login": "test-org"},
            "name": "test-repo",
        },
    }
    
    try:
        response = await client.post(f"{API_BASE}/webhook/github", json=webhook_payload, timeout=30.0)
        return {
            "pr_number": pr_number,
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text,
        }
    except Exception as e:
        return {
            "pr_number": pr_number,
            "success": False,
            "error": str(e),
        }


async def check_health(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Check platform health."""
    try:
        response = await client.get(f"{API_BASE}/health", timeout=5.0)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_system_metrics() -> Dict[str, Any]:
    """Get current system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_gb": memory.available / (1024**3),
        "memory_total_gb": memory.total / (1024**3),
    }


async def run_performance_test():
    """Run performance test with 10 concurrent preview environments."""
    print("=" * 80)
    print("DevPlatform Performance Test")
    print("Testing 10 concurrent preview environment deployments")
    print("=" * 80)
    print()
    
    # Initial system state
    initial_metrics = get_system_metrics()
    print(f"Initial System State:")
    print(f"  CPU: {initial_metrics['cpu_percent']:.1f}%")
    print(f"  Memory: {initial_metrics['memory_percent']:.1f}% ({initial_metrics['memory_available_gb']:.2f} GB available)")
    print()
    
    # Check platform health
    async with httpx.AsyncClient() as client:
        health = await check_health(client)
        print(f"Platform Health: {health.get('status', 'unknown')}")
        print()
        
        # Deploy 10 concurrent preview environments
        print(f"Deploying {NUM_ENVIRONMENTS} preview environments concurrently...")
        start_time = time.time()
        
        tasks = [deploy_preview_environment(i + 1, client) for i in range(NUM_ENVIRONMENTS)]
        results = await asyncio.gather(*tasks)
        
        deployment_time = time.time() - start_time
        
        # Check system metrics after deployment
        await asyncio.sleep(2)  # Wait for deployments to settle
        final_metrics = get_system_metrics()
        
        # Analyze results
        successful = sum(1 for r in results if r.get("success", False))
        failed = NUM_ENVIRONMENTS - successful
        
        print()
        print("=" * 80)
        print("Test Results")
        print("=" * 80)
        print(f"Total deployments: {NUM_ENVIRONMENTS}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Deployment time: {deployment_time:.2f} seconds")
        print()
        
        print("System Metrics After Deployment:")
        print(f"  CPU: {final_metrics['cpu_percent']:.1f}%")
        print(f"  Memory: {final_metrics['memory_percent']:.1f}% ({final_metrics['memory_available_gb']:.2f} GB available)")
        print()
        
        # Performance requirements check
        cpu_under_80 = final_metrics['cpu_percent'] < 80
        memory_available = final_metrics['memory_available_gb'] > 1.0  # At least 1GB available
        
        print("Performance Requirements:")
        print(f"  ✅ CPU under 80%: {cpu_under_80} ({final_metrics['cpu_percent']:.1f}%)")
        print(f"  ✅ Memory available: {memory_available} ({final_metrics['memory_available_gb']:.2f} GB)")
        print()
        
        if cpu_under_80 and memory_available and successful >= NUM_ENVIRONMENTS * 0.8:
            print("✅ PERFORMANCE TEST PASSED")
            print("   Platform can handle 10 concurrent preview environments")
        else:
            print("⚠️  PERFORMANCE TEST NEEDS ATTENTION")
            if not cpu_under_80:
                print(f"   CPU usage ({final_metrics['cpu_percent']:.1f}%) exceeds 80% threshold")
            if not memory_available:
                print(f"   Memory availability ({final_metrics['memory_available_gb']:.2f} GB) is low")
            if successful < NUM_ENVIRONMENTS * 0.8:
                print(f"   Only {successful}/{NUM_ENVIRONMENTS} deployments succeeded")
        
        print()
        print("Detailed Results:")
        for result in results:
            status = "✅" if result.get("success") else "❌"
            print(f"  {status} PR #{result['pr_number']}: {result.get('status_code', result.get('error', 'unknown'))}")
        
        print()
        print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(run_performance_test())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()












