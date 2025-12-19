# DevPlatform Testing Scripts

This directory contains testing and validation scripts for DevPlatform.

## Scripts

### `performance_test.py`

Tests the platform's ability to handle 10 concurrent preview environments as per performance requirements.

**Usage:**
```bash
python scripts/performance_test.py
```

**What it does:**
- Deploys 10 preview environments concurrently
- Monitors system CPU and memory usage
- Validates that CPU utilization remains below 80%
- Checks memory availability
- Reports deployment success/failure rates

**Requirements:**
- Backend API running on `http://localhost:8000`
- `psutil` library installed (`pip install psutil`)
- `httpx` library (already in requirements.txt)

**Expected Output:**
```
✅ PERFORMANCE TEST PASSED
   Platform can handle 10 concurrent preview environments
```

---

### `availability_test.py`

Tests the platform's 99.9% availability requirement over a specified duration.

**Usage:**
```bash
# 1-hour test (default)
python scripts/availability_test.py

# Custom duration
python scripts/availability_test.py --duration 24.0  # 24 hours
```

**What it does:**
- Continuously checks platform health every 60 seconds
- Tracks successful and failed health checks
- Calculates availability percentage
- Validates SLA compliance (99.9% target)
- Reports downtime and availability metrics

**Requirements:**
- Backend API running on `http://localhost:8000`
- `httpx` library (already in requirements.txt)

**Expected Output:**
```
✅ AVAILABILITY TEST PASSED
   Platform meets 99.9% availability requirement
```

**Options:**
- `--duration HOURS`: Test duration in hours (default: 1.0)

---

## Installation

Install additional dependencies for performance testing:

```bash
pip install psutil
```

Or add to `backend/requirements.txt`:
```
psutil==5.9.0
```

---

## Running All Tests

```bash
# Unit tests
cd backend && pytest test_main.py -v

# Integration tests
cd backend && pytest test_integration.py -v

# Performance test
python scripts/performance_test.py

# Availability test (1 hour)
python scripts/availability_test.py --duration 1.0
```

---

## Notes

- Performance test requires actual Kubernetes cluster or mocked ClusterManager
- Availability test can run for any duration (recommended: 1 hour for quick validation, 24 hours for full validation)
- Both scripts provide detailed output and pass/fail status
- Scripts are designed to be non-destructive and safe to run












